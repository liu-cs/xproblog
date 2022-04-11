from copy import deepcopy
from os.path import join
from uuid import uuid4
import re
from treelib import Tree
import tree_util

_BASIC_FACTS_BEGIN = '%BEGIN:BASIC_FACTS'
_BASIC_FACTS_END = '%END:BASIC_FACTS'
_PROVED_FACT_TAG = '"is proved because:"'
_OR_BRANCH_TAG = 'or-branch:'

_MAX_BFS_LEVEL = 20


class TreeBuilder:

    def __init__(self, path, kb_file, xproblog_output):
        self._basic_facts = self._load_basic_facts(path, kb_file)
        self._proved_facts = self._load_proved_facts(xproblog_output)
        self._proof_trees = self._build_proof_trees()

    def _load_basic_facts(self, path, kb_file):
        with open(join(path, kb_file)) as f:
            lines = f.readlines()
        basic_facts = []
        begin = False
        for line in lines:
            if begin:
                if _BASIC_FACTS_END in line:
                    break
                fact = line.strip().rstrip('.').replace(' ', '')
                if '::' in fact:
                    fact = fact[fact.index('::') + 2:]
                basic_facts.append(fact)
                continue
            if _BASIC_FACTS_BEGIN in line:
                begin = True
        return set(basic_facts)

    def _load_proved_facts(self, xproblog_output):
        proved_facts = dict()
        i = 0
        while i < len(xproblog_output):
            line = xproblog_output[i]
            jump = False
            if _PROVED_FACT_TAG in line:
                fact = line[:line.index('"')].replace(' ', '')
                proof = []
                for j in range(i + 1, len(xproblog_output)):
                    line2 = xproblog_output[j]
                    if _PROVED_FACT_TAG in line2:
                        i = j
                        jump = True
                        break
                    proof.append(line2.replace(' ', ''))

                proof = frozenset(proof)
                if not fact in proved_facts:
                    proved_facts[fact] = set()
                proved_facts[fact].add(proof)

            if not jump:
                i += 1

        for fact in self._basic_facts:
            if fact in proved_facts:
                proved_facts.pop(fact)

        return proved_facts

    def _build_proof_trees(self):

        def expand(tree, fact, parent, checked_facts):
            queue = []
            proofs = sorted(self._proved_facts[fact],
                            key=lambda proof: len(proof))
            for i in range(len(proofs)):
                proof = proofs[i]
                if len(proofs) > 1:
                    # Create an or-node branch for each proof.
                    tag = 'Proof %d' % (i + 1)
                    data = _OR_BRANCH_TAG + fact
                    new_parent = data + str(uuid4())
                    tree.create_node(tag, new_parent, parent, data)
                else:
                    new_parent = parent
                for fact in sorted(proof):
                    if not (fact in self._basic_facts
                            or fact in self._proved_facts):
                        continue
                    nid = fact + str(uuid4())
                    fact_str = '#%s#' % fact if fact in self._basic_facts else fact
                    tree.create_node(fact_str, nid, new_parent, fact_str)
                    queue.append((fact, new_parent))
                    checked_facts.add(fact)
            return queue

        checked_facts = deepcopy(self._basic_facts)
        trees = dict()
        for fact in sorted(self._proved_facts.keys()):
            tree = Tree()
            tree.create_node(tag='root', identifier='root',
                             data='root')  # A dummy root node.
            nid = fact + str(uuid4())
            tree.create_node(tag=fact,
                             identifier=nid,
                             parent='root',
                             data=fact)

            queue = expand(tree, fact, nid, checked_facts)
            level = 0
            while level < _MAX_BFS_LEVEL:
                level += 1
                new_queue = []  # The queue for the next level.
                for (child_fact, parent) in queue:
                    if not child_fact in self._proved_facts:
                        continue
                    if child_fact in checked_facts:
                        continue

                    # Don't include cyclic proofs.
                    cyclic = False
                    ancestor = parent
                    while ancestor != tree.root:
                        if tree.get_node(ancestor).data == child_fact:
                            cyclic = True
                            break
                        ancestor = tree.parent(ancestor).identifier
                    if cyclic:
                        continue

                    for item in expand(tree, child_fact, parent,
                                       checked_facts):
                        new_queue.append(item)
                queue = new_queue
            trees[fact] = tree

        return trees

    def build_tree(self, query):
        tree1 = self._build_and_or_tree(query)
        tree2 = self._build_regular_tree(tree1)
        return tree1, tree2

    def _build_and_or_tree(self, query):

        def find_first_leaf_to_expand(tree):
            found_leaf = None
            for nid in tree_util.bfs_get_leaves(tree):
                node = tree.get_node(nid)
                if re.search(r'^#.+#$', node.data):  # A basic fact.
                    continue
                if tree_util.nonleaf_exists_with_same_data(node.data, tree):
                    continue
                found_leaf = node
                break
            return found_leaf

        if query in self._basic_facts:
            tree = Tree()
            tree.create_node(tag='root', identifier='root', data='root')
            data = '#%s#' % query
            tree.create_node(data, data, 'root', data)
            return tree

        if not query in self._proof_trees:
            err_msg = 'KeyError: \'%s\' is not a proved fact' % query
            raise Exception(err_msg)

        tree = deepcopy(self._proof_trees[query])
        leaf = find_first_leaf_to_expand(tree)
        while leaf:
            # assert leaf.data in self._proof_trees
            tree2 = deepcopy(self._proof_trees[leaf.data])
            tree2 = tree2.subtree(tree2.children(tree2.root)[0].identifier)
            tree.merge(leaf.identifier, tree2)
            leaf = find_first_leaf_to_expand(tree)

        self._remove_cyclic_proof(tree)
        return tree

    def _build_regular_tree(self, and_or_tree):

        def build_regular_tree(and_or_tree):
            tree1 = and_or_tree
            assert tree1.root != 'root'
            tree2 = Tree()
            tree2.create_node(tag='root', identifier='root', data='root')
            node = tree1.get_node(tree1.root)
            tree2.create_node(node.tag, node.identifier, 'root', node.data)

            if tree_util.is_leaf(tree1.root, tree1):
                return tree2

            if self._is_or_node(tree1.root, tree1):
                first_branch = tree1.children(tree1.root)[0].identifier
                tree2.merge(tree1.root,
                            build_regular_tree(tree1.subtree(first_branch)))
                return tree2

            for ch in tree1.children(tree1.root):
                tree2.merge(tree1.root,
                            build_regular_tree(tree1.subtree(ch.identifier)))
            return tree2

        tree1 = and_or_tree
        real_root = tree1.children(tree1.root)[0].identifier
        tree2 = build_regular_tree(tree1.subtree(real_root))

        # TODO: Some leaf-nodes may actually be non-terminals,
        #       try to further expand those nodes.
        # for nid in tree_util.bfs_get_leaves(tree2):
        #     ...

        self._reorg_or_branches(tree2)
        return tree2

    def _remove_cyclic_proof(self, tree):
        size = tree.size() + 1
        while tree.size() < size:
            size = tree.size()
            for nid in tree_util.bfs_get_leaves(tree):
                if tree_util.ancestor_has_same_data(nid, tree):
                    tree.remove_node(tree.parent(nid).identifier)
                    break
        self._reorg_or_branches(tree)

    def _reorg_or_branches(self, tree):
        if tree.size() == 0:
            return
        for nid in tree.expand_tree(mode=Tree.WIDTH, sorting=False):
            if self._is_or_node(nid, tree):
                # Remove duplicated branches.
                current = 0
                children = [ch.identifier for ch in tree.children(nid)]
                while current < len(children):
                    for i in range(current + 1, len(children)):
                        if self._identical_tree(
                                tree.subtree(children[current]),
                                tree.subtree(children[i])):
                            tree.remove_node(children[i])
                    current += 1
                    children = [ch.identifier for ch in tree.children(nid)]

                # Rename each branch if necessary.
                children = tree.children(nid)
                if len(children) == 1:
                    subtree = tree.subtree(children[0].identifier)
                    tree.remove_node(children[0].identifier)
                    tree.merge(nid, subtree)
                else:
                    for i in range(len(children)):
                        children[i].tag = 'Proof %d' % (i + 1)

    def _is_or_node(self, nid, tree):
        if tree_util.is_leaf(nid, tree):
            return False
        if _OR_BRANCH_TAG in tree.children(nid)[0].data:
            for ch in tree.children(nid):
                assert _OR_BRANCH_TAG in ch.data
            return True
        return False

    def _identical_tree(self, tree1, tree2):
        if ((tree_util.is_leaf(tree1.root, tree1)
             and tree_util.is_pre_leaf(tree2.root, tree2))
                or (tree_util.is_pre_leaf(tree1.root, tree1)
                    and tree_util.is_leaf(tree2.root, tree2))):
            root1 = tree1.get_node(tree1.root)
            root2 = tree2.get_node(tree2.root)
            return root1.data == root2.data

        if tree1.size() != tree2.size():
            return False

        data1 = tree1.get_node(tree1.root).data
        data2 = tree2.get_node(tree2.root).data

        if data1 != data2:
            return False

        if tree1.size() == 1:
            return True

        ch_list_1 = tree1.children(tree1.root)
        ch_list_2 = tree2.children(tree2.root)

        if len(ch_list_1) != len(ch_list_2):
            return False

        for i in range(len(ch_list_1)):
            ch_1 = tree1.get_node(ch_list_1[i].identifier)
            ch_2 = tree2.get_node(ch_list_2[i].identifier)
            if not self._identical_tree(tree1.subtree(ch_1.identifier),
                                        tree2.subtree(ch_2.identifier)):
                return False

        return True
