#!/usr/bin/python

from os import getcwd, listdir
from os.path import exists, isfile, join
from shutil import copyfile
import re

_SPECIAL_TOKENS = ('use_module(', 'query(')
_IGNORED_PTNS = ('not ', ' is ')

_KB_FILE = '~xproblog.kb'


def process_kb_files(dir_path):
    kb_file = join(dir_path, _KB_FILE)
    kb_file_bak = join(dir_path, _KB_FILE + '.bak')
    if exists(kb_file):
        copyfile(kb_file, kb_file_bak)

    files = []
    for f in listdir(dir_path):
        if not isfile(join(dir_path, f)):
            continue
        if f.endswith('.py'):
            continue
        # Ignore temporary files.
        if f.startswith('~'):
            continue
        files.append(f)
    print('The following KB files will be processed:', sorted(files))

    lines = []
    for file in files:
        with open(join(dir_path, file)) as f:
            lines += [l.strip() for l in f.readlines()]

    special_lines = []
    filtered_lines = []
    for l in lines:
        if len(l) == 0:
            continue
        if l[0] == '%':  # This is a comment line.
            continue

        l = re.sub(r'\s+', ' ', l)

        special = False
        for t in _SPECIAL_TOKENS:
            if t in l:
                special = True
                break

        if special:
            special_lines.append(l)
        else:
            # Temporarily replace the '.' in a probability
            # in front of '::' with '_dot_'.
            if '::' in l:
                l = (l[:l.index('::')].replace('.', '_dot_') +
                     l[l.index('::'):])
            filtered_lines.append(l)

    joined_lines = ''.join(filtered_lines)
    sentences = [s.strip() for s in joined_lines[:-1].split('.')]

    facts = []
    rules = []
    for s in sentences:
        s = s.replace('_dot_', '.')
        if ':-' in s:
            rules.append(s)
        else:
            facts.append(s)

    parsed_rules = []
    for r in rules:
        head = r[:r.index(':-')].replace(' ', '')
        if '::' in head:
            prob = head[:head.index('::')]
            head = head[head.index('::') + 2:]
        else:
            prob = None

        # Parse the body of the rule.
        body_str = r[r.index(':-') + 2:] + ','
        body = []
        marker = 0
        for i in range(len(body_str)):
            if body_str[i] == ',' and not _in_parentheses(i, body_str):
                predicate = body_str[marker:i].strip()
                body.append(predicate)
                marker = i + 1

        # Extend the body with Problog's write command, later on
        # our code will rely on these outputs to build reasoning trees.
        extended_body = []
        for predicate in body:
            include = True
            for ptn in _IGNORED_PTNS:
                if ptn in predicate:
                    include = False
                    break
            if include:
                extended_body.append('write("xproblog:"),write(%s),nl,' %
                                     predicate)
        body.append(
            'write("xproblog:"),write(%s),write("is proved because:"),nl' %
            head)
        body.append(''.join(extended_body)[:-1])

        parsed_rules.append((prob, head, body))

    with open(kb_file, 'w') as file:
        print('Problog KB written to file', kb_file)

        file.write('%BEGIN:BASIC_FACTS\n')
        for f in facts:
            file.write(f + '.\n')
        file.write('%END:BASIC_FACTS\n\n')

        file.write('%BEGIN:RULES\n')
        for (prob, head, body) in parsed_rules:
            if prob:
                file.write('%s::%s :-\n' % (prob, head))
            else:
                file.write(head + ' :-\n')

            for line in body[:-1]:
                file.write('\t%s,\n' % line)
            file.write('\t%s.\n' % body[-1])
        file.write('%END:RULES\n\n')

        for l in special_lines:
            if 'use_module(' in l and not '.py' in l:
                continue
            file.write(l + '\n')

    no_change = False
    if exists(kb_file_bak):
        with open(kb_file_bak) as file1:
            with open(kb_file) as file2:
                if file1.readlines() == file2.readlines():
                    no_change = True

    return _KB_FILE, no_change


def _in_parentheses(index, str):
    """Finds out if index in str is inside a pair of parentheses or not.
    Args:
        str: An input string.
        index: An index within str.
    Returns:
        True or False.
    Raises:
        Exception: An error occurred when index is out of range.
    """

    if index < 0 or index >= len(str):
        raise Exception('Error: index %d is out of range!' % index)

    if index == 0 or index == len(str) - 1:
        return False

    left_stack = []
    for i in range(index):
        char = str[i]
        if char == '(':
            left_stack.append(char)
        elif char == ')':
            if left_stack:
                left_stack.pop()
        else:
            pass

    right_stack = []
    for i in reversed(range(index + 1, len(str))):
        char = str[i]
        if char == ')':
            right_stack.append(char)
        elif char == '(':
            if right_stack:
                right_stack.pop()
        else:
            pass

    return left_stack and right_stack


def test():
    path = getcwd() + '/kb'
    file, no_change = process_kb_files(path)
    print(file, no_change)


if __name__ == '__main__':
    test()
