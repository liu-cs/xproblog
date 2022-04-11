from uuid import uuid4
from treelib import Tree


def is_leaf(nid, tree):
    return True if not tree.children(nid) else False


def is_pre_leaf(nid, tree):
    if is_leaf(nid, tree):
        return False
    for ch in tree.children(nid):
        if not is_leaf(ch.identifier, tree):
            return False
    return True


def is_ancestor(aid, nid, tree):
    if nid == tree.root:
        return False
    if aid == tree.root:
        return True

    ancestor = tree.parent(nid).identifier
    while ancestor != tree.root:
        if ancestor == aid:
            return True
        ancestor = tree.parent(ancestor).identifier
    return False


def ancestor_has_same_data(nid, tree):
    if nid == tree.root:
        return False

    data = tree.get_node(nid).data
    if tree.get_node(tree.root).data == data:
        return True

    ancestor = tree.parent(nid).identifier
    while ancestor != tree.root:
        if tree.get_node(ancestor).data == data:
            return True
        ancestor = tree.parent(ancestor).identifier

    return False


def bfs_get_leaves(tree):
    if tree.size() == 0:
        yield from ()
    for nid in tree.expand_tree(mode=Tree.WIDTH, sorting=False):
        if is_leaf(nid, tree):
            yield nid


def nonleaf_exists_with_same_data(data, tree):
    for nid in tree.expand_tree(mode=Tree.WIDTH, sorting=False):
        if is_leaf(nid, tree):
            continue
        if tree.get_node(nid).data == data:
            return True
    return False


def bfs_search_nonleaf_with_data(data, tree):
    nonleaves = []
    for nid in tree.expand_tree(mode=Tree.WIDTH, sorting=False):
        if is_leaf(nid, tree):
            continue
        if tree.get_node(nid).data == data:
            nonleaves.append(nid)
    return nonleaves


def identical_tree_with_data(tree1, tree2):
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
        if not identical_tree_with_data(tree1.subtree(ch_1.identifier),
                                        tree2.subtree(ch_2.identifier)):
            return False

    return True


def deepcopy(tree):

    def _deepcopy(tree):
        tree2 = Tree()
        tree2.create_node(tag='root', identifier='root', data='root')

        root = tree.get_node(tree.root)
        nid = root.identifier + str(uuid4())
        tree2.create_node(root.tag, nid, 'root', root.data)

        if is_leaf(root.identifier, tree):
            return tree2

        for ch in tree.children(tree.root):
            tree2.merge(nid, _deepcopy(tree.subtree(ch.identifier)))

        return tree2

    tree = _deepcopy(tree)
    root = tree.children(tree.root)[0]
    return tree.subtree(root.identifier)
