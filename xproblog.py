#!/usr/bin/python

from os import getcwd
from os.path import exists, join
import subprocess
import time
import re

from kb_processor import process_kb_files
from tree_builder import TreeBuilder

_XPROBLOG_TAG = '"xproblog:"'
_XPROBLOG_OUTFILE = '~xproblog.out'


def _run_problog(path, kb_file):
    kb_file_path = join(path, kb_file)
    cmd = ['problog', kb_file_path]
    start_time = time.time()

    print('Run problog with\n', ' '.join(cmd))
    print('Start time:\n', time.asctime(time.localtime(time.time())))
    print('Program\'s output:\n')

    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               bufsize=1,
                               universal_newlines=True)

    xproblog_lines = []
    problog_outputs = []
    while True:
        line = process.stdout.readline()
        if not line:
            break

        if line.startswith(_XPROBLOG_TAG):
            xproblog_lines.append(line[len(_XPROBLOG_TAG):].rstrip())
        else:
            line = re.sub(r'\s+', '', line)
            problog_outputs.append(line.strip())

    process.kill()

    print('')
    for l in problog_outputs:
        print(l)

    time_taken = int(time.time() - start_time)
    print('\nFinished running\n', ' '.join(cmd))
    print('End time:\n', time.asctime(time.localtime(time.time())))
    print('Time taken:\n',
          '%s min %s sec' % (time_taken // 60, time_taken % 60))

    xproblog_outfile = join(path, _XPROBLOG_OUTFILE)
    with open(xproblog_outfile, 'w') as f:
        for l in problog_outputs:
            f.write('problog:' + l + '\n')
        for l in xproblog_lines:
            f.write('xproblog:' + l + '\n')
    print('xproblog outputs written to file', xproblog_outfile)

    return problog_outputs, xproblog_lines


def _load_xproblog_outputs(path, file):
    problog_outputs = []
    xproblog_lines = []
    file = join(path, file)
    if exists(file):
        with open(file) as f:
            lines = [l.strip() for l in f.readlines()]
            for l in lines:
                if l.startswith('problog:'):
                    problog_outputs.append(l[l.index(':') + 1:])
                elif l.startswith('xproblog:'):
                    xproblog_lines.append(l[l.index(':') + 1:])
                else:
                    pass
    return problog_outputs, xproblog_lines


def main():
    path = getcwd() + '/kb'
    kb_file, no_change = process_kb_files(path)
    if no_change and exists(join(path, _XPROBLOG_OUTFILE)):
        problog_outputs, xproblog_lines = _load_xproblog_outputs(
            path, _XPROBLOG_OUTFILE)
        if problog_outputs and xproblog_lines:
            print('KB has no change, skip running problog.')
        else:
            problog_outputs, xproblog_lines = _run_problog(path, kb_file)
    else:
        problog_outputs, xproblog_lines = _run_problog(path, kb_file)

    tree_builder = TreeBuilder(path, kb_file, xproblog_lines)

    print('Trees for the proved facts:\n')
    for l in problog_outputs:
        query = l[:l.index(':')]
        and_or_tree, regular_tree = tree_builder.build_tree(query)
        print(l)
        and_or_tree.show()
        # regular_tree.show()


if __name__ == '__main__':
    main()
