import argparse
import os
import os.path
import string

from core.util import get_sort_char
import config

group_names = set(string.ascii_uppercase + '0')
group_names.add('Singletons')

def list_dirs(directory):
    for subitem in os.listdir(directory):
        full_path = os.path.join(directory, subitem)
        if os.path.isdir(full_path):
            yield (full_path, subitem)

def is_grouped(directory):
    for full_path, subitem in list_dirs(directory):
        if subitem not in group_names:
            return False
    return True

def run(action, directory, test):
    if not os.path.isdir(directory):
        print('%s does not exist.' % directory)
        raise SystemExit

    already_grouped = is_grouped(directory)
    if already_grouped and action == 'group':
        print('Directory is already grouped, exiting')
        raise SystemExit
    elif not already_grouped and action == 'ungroup':
        print('Directory is already ungrouped, exiting')
        raise SystemExit

    changes = list()
    if action == 'ungroup':
        for d, base in list_dirs(directory):
            if base == 'Singletons':
                continue
            for artist in os.listdir(d):
                changes.append((os.path.join(d, artist),
                                os.path.join(directory, artist)))
            changes.append((d, None))
    else:
        for d, artist in list_dirs(directory):
            if artist == 'Singletons':
                continue
            group_char = get_sort_char(artist)
            changes.append((d, os.path.join(directory, group_char, artist)))

    # Preview_changes
    for from_, to in changes:
        if to is None:
            print('DELETING\t%s' % from_)
            if not test:
                os.rmdir(from_)
        else:
            print('MOVING\t%s -> %s' % (from_, to))
            if not test:
                parent = os.path.dirname(to)
                if not os.path.isdir(parent):
                    os.makedirs(parent)
                os.rename(from_, to)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('action', choices=['group', 'ungroup'],
                        help='Whether to group or ungroup artists on the device.')
    parser.add_argument('directory', help='The directory to work on.')

    args = parser.parse_args()

    run(args.action, args.directory, args.test)

if __name__ == '__main__':
    main()
