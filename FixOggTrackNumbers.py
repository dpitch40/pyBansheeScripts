"""Necessary because the M11 doesn't recognize track/discnumbers in "#/#" format; it
   requires separate tracknumber and tracktotal fields
"""

import argparse
import os
import os.path
import re
import collections

from mutagen.oggvorbis import OggVorbis

tc_re = re.compile(r'(\d+)/(\d+)')

def run(directory, test):
    if not os.path.isdir(directory):
        print('%s does not exist.' % directory)
        raise SystemExit

    changes = collections.defaultdict(dict)
    not_changed = list()
    for dirpath, dirnames, filenames in os.walk(directory):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext == '.ogg':
                path = os.path.join(dirpath, fname)
                oggfile = OggVorbis(path)
                if 'tracknumber' in oggfile:
                    tracknumber = oggfile['tracknumber'][0]
                    m = tc_re.match(tracknumber)
                    if m:
                        tn, tc = m.groups()
                        changes[path] = {'tracknumber': tn,
                                         'tracktotal': tc}
                if 'discnumber' in oggfile:
                    discnumber = oggfile['discnumber'][0]
                    m = tc_re.match(discnumber)
                    if m:
                        dn, dc = m.groups()
                        changes[path] = {'discnumber': dn,
                                         'disctotal': dc}

                if not changes[path]:
                    not_changed.append(path)
                    del changes[path]
                elif not test:
                    if 'tracknumber' in changes[path]:
                        oggfile['tracknumber'] = [changes[path]['tracknumber']]
                        oggfile['tracktotal'] = [changes[path]['tracktotal']]
                    if 'discnumber' in changes[path]:
                        oggfile['discnumber'] = [changes[path]['discnumber']]
                        oggfile['disctotal'] = [changes[path]['disctotal']]
                    oggfile.save()
    for path, changes in sorted(changes.items()):
        print(path, '\t', changes)
    # print('\n'.join(sorted(not_changed)))
    # print(len(not_changed))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', "--test", action="store_true",
                        help="Only preview changes, do not actually make them.")
    parser.add_argument('directory', help='The directory to work on.')

    args = parser.parse_args()

    run(args.directory, args.test)

if __name__ == '__main__':
    main()
