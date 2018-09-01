from datetime import datetime
from collections import defaultdict
import os
import os.path
import re
import glob
import shutil
from collections.abc import Iterable

from urllib.request import url2pathname, pathname2url

forbidden_fname_chars = ':;\\!?*"<>|'
xmlEscapedChars = "'"

# Characters to escape when converting to SQL-compatible strings
PATHNAME_CHARS = "~!@$&*()-_=+:',."

initial_period_re = re.compile(r"^(\.+)")
tuple_re = re.compile(r"\(([^\)]+)\)")

ts_fmt = '%Y-%m-%d %H:%M%S'


# Descriptor factories for Metadata and its subclasses

def make_descriptor_func(decode_func, encode_func=None):

    def desc_func(name):

        def get_(self):
            raw_value = self.get_item(name)
            return decode_func(raw_value) if raw_value else None

        if encode_func:
            def set_(self, value):
                set_value = encode_func(value)
                self.set_item(name, set_value)

            def del_(self):
                self.del_item(name)
        else:
            set_, del_ = None, None

        return property(get_, set_, del_)

    return desc_func

date_descriptor = make_descriptor_func(datetime.fromtimestamp, lambda dt: int(dt.timestamp()))
int_descriptor = make_descriptor_func(int, str)

def make_numcount_descriptors(numname, countname, fieldname, alttotal=''):

    def get_num(self):
        try:
            return int(self.get_item(fieldname).split('/')[0])
        except (KeyError, IndexError):
            return None

    def set_num(self, value):
        count = getattr(self, countname)
        if count:
            self.set_item(fieldname, '%d/%d' % (value, count))
        else:
            self.set_item(fieldname, '%d' % value)

    def del_num(self):
        self.del_item(fieldname)

    num_descriptor = property(get_num, set_num, del_num)

    def get_count(self):
        try:
            count = self.get_item(alttotal)
            if count is None:
                count = self.get_item(fieldname).split('/')[1]
            return int(count)
        except (KeyError, IndexError):
            return None

    def set_count(self, value):
        num = getattr(self, numname)
        if num:
            self.set_item(fieldname, '%d/%d' % (num, value))

    def del_count(self):
        num = getattr(self, numname)
        if num:
            self.set_item(fieldname, '%d' % num)

    count_descriptor = property(get_count, set_count, del_count)

    def get_numcount(self):
        try:
            count = self.get_item(alttotal)
            if count is not None:
                return int(self.get_item(fieldname)), int(count)
            numcount = self.get_item(fieldname)
            if '/' in numcount:
                num, count = numcount.split('/')
                return int(num), int(count)
            else:
                return int(numcount), None
        except (KeyError, IndexError, TypeError):
            return None, None

    def set_numcount(self, value):
        num, count = value
        if count:
            self.set_item(fieldname, '%d/%d' % (num, count))
        else:
            self.set_item(fieldname, '%d' % num)

    def del_numcount(self):
        self.del_item(fieldname)

    numcount_descriptor = property(get_numcount, set_numcount, del_numcount)

    return num_descriptor, count_descriptor, numcount_descriptor


# Some metadata utility functions

sort_key_defaults = {'album_artist': '',
                     'artist': '',
                     'album': '',
                     'dn': 0,
                     'tn': 0}
def sort_key(*args):
    if len(args) == 0:
        args = ['album_artist', 'artist', 'album', 'dn', 'tn']
    def _inner(track, a=args):
        return tuple([getattr(track, arg) or sort_key_defaults[arg] for arg in a])
    return _inner

def generate_disc_lens(metadatas):
    # Make mapping from disc number to number of tracks on the disc
    disc_lens = defaultdict(int)
    for metadata in metadatas:
        dn = metadata.dn
        if dn:
            disc_lens[dn] += 1
        else:
            return None # All of the tracks must have metadata
    return disc_lens


# Filename escaping/conversion

def filter_fname(f):
    """ "Sanitizes" a filename: replaces forbidden characters and ending periods in directory names"""

    for c in forbidden_fname_chars: # Replace characters in filename
        f = f.replace(c, '_')
    dir_name, fname = os.path.split(f)

    if dir_name != '' and dir_name[-1] == '.': # Period at end of directory name?
        dir_name = dir_name[:-1] + '_'
    if fname.startswith('.'): # initial period in filename
        fname = '_' + fname[1:]

    return os.path.join(dir_name, fname)

def escape_fname(f):
    return "'%s'" % f.replace("'", "'\\''")

def filter_path_elements(elements):
    """Wrapper function for filter_fname that also handles the artist/album/song title
       containing forward slashes
       basedir is the top-level directory (assumed not to contain forbidden characters)
       elements is the list of path elementst hat may contain slashes; artist, album, title, etc."""
    # Remove forward slashes and leading periods in the path elements
    for i, element in enumerate(elements):
        element = element.replace('/', '_')
        if element.startswith('.'):
            element = '_%s' % element[1:]
        elements[i] = element
    return filter_fname(os.path.join(*elements))

def excape_xml_chars(s):
    s = s.replace('&', "&amp;")
    s = s.replace('<', "&lt;")
    s = s.replace('>', "&gt;")
    for c in xmlEscapedChars:
        s = s.replace(c, "&#%d;" % ord(c))
    return s

def pathname2sql(path):
    pathDir, pathBase = os.path.split(path)
    # Fix filenames with periods at the start
    m = initial_period_re.match(pathBase)
    if m:
        numPeriods = len(m.group(1))
        path = os.path.join(pathDir, "%s%s" % ('_' * numPeriods, pathBase[numPeriods:]))
    sqlloc = pathname2url(path)
    # Escape troublesome characters
    for c in PATHNAME_CHARS:
          sqlloc = sqlloc.replace("%%%X" % ord(c), c)
    return "file://" + sqlloc

def sql2pathname(uri):
    # Just strip the "file://" from the start and run through url2pathname
    return url2pathname(uri[7:])

# Similar to pathname2sql, but converts a pathname for a VLC playlist
def pathname2xml(path):
    base = pathname2sql(path)

    decode_chars = ';'

    base = excape_xml_chars(base)
    for c in decode_chars:
        base = base.replace("%%%02X" % ord(c), c)

    return base


# Value interpretation/conversion

def value_is_none(v):
    return v is None or (isinstance(v, Iterable) and all(sv is None for sv in v))

def convert_str_value(v, convertNumbers=True):
    if v == '' or v == "None" or v is None:
        return None
    elif isinstance(v, str) and convertNumbers and v.isdigit():
        return int(v)
    else:
        try:
            return datetime.strptime(v, ts_fmt)
        except ValueError:
            pass

        m = tuple_re.match(v)
        if m:
            return tuple(map(lambda x: convert_str_value(x.strip()), m.group(1).split(',')))

    return v


# Other filename utilities

def get_fnames(dir_):
    """Gets a list of music file names in a directory."""
    # Try using glob
    g = glob.glob(dir_)
    if g != [dir_]:
        return sorted(g)

    from mfile import mapping as mfile_mapping
    allowed_exts = set(mfile_mapping.keys())

    fnames = os.listdir(dir_)
    return sorted([os.path.join(dir_, fname) for fname in fnames if
                        os.path.splitext(fname)[1].lower() in allowed_exts])

def get_common_prefix_len(s1, s2):
    i = 0
    while s1[:i+1] == s2[:i+1]:
        i += 1
    return i

def remove_common_path_elements(path1, path2):
    sl_split = path1.split(os.sep)
    dl_split = path2.split(os.sep)
    cpl = get_common_prefix_len(sl_split, dl_split)

    return os.sep.join(sl_split[cpl:]), os.sep.join(dl_split[cpl:])

# Takes the intersection of two lists of filenames: returns the files exclusive to the first,
# the common names, and the names exclusive to the second.
def compare_filesets(filelist1, filelist2, sort=False):
    #Turn all to lowercase and remove periods os.path.exists doesn't care about
    #these
    def demote(s):
        return s.lower().replace('.', '')

    return boolean_diff(filelist1, filelist2, demote, sort)

def boolean_diff(l1, l2, transform=lambda x: x, sort=False):
    translated1 = dict(zip(map(transform, l1), l1))
    translated2 = dict(zip(map(transform, l2), l2))
    set1 = set(translated1.keys())
    set2 = set(translated2.keys())
    on1not2 = [translated1[f] for f in set1 - set2]
    on2not1 = [translated2[f] for f in set2 - set1]
    common = [translated1[f] for f in set1 & set2]
    if sort:
        return sorted(on1not2), sorted(common), sorted(on2not1)
    else:
        return on1not2, common, on2not1



def run_with_backups(args, file_to_backup, backup_dir, num_backups):
    prog_name = args[0]
    if not os.path.isdir(backup_dir):
        os.makedirs(backup_dir)

    backup_nums = range(num_backups)
    pre_backup_mtimes = []
    for i in backup_nums:
        pre_backup_loc = os.path.join(backup_dir, '%s-backup-%d-pre.db' %
            (prog_name, i + 1))
        if not os.path.isfile(pre_backup_loc):
            backup_num = i
            break
        else:
            pre_backup_mtimes.append((os.path.getmtime(pre_backup_loc), i))
    else:
        backup_num = sorted(pre_backup_mtimes)[0][1]

    backup_dest = os.path.join(backup_dir, '%s-backup-%d-pre.db' %
        (prog_name, backup_num + 1))
    shutil.copy2(file_to_backup, backup_dest)

    os.spawnvp(os.P_WAIT, prog_name, args[1:])

    shutil.copy2(file_to_backup, os.path.join(backup_dir, '%s-backup-%d-post.db' %
        (prog_name, backup_num + 1)))
