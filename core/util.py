from datetime import datetime
from collections import defaultdict
import os
import os.path

forbidden_fname_chars = ':;\\!?*"<>|'
xmlEscapedChars = "'"

def make_descriptor_func(decode_func, encode_func=None, unpack_list=False):

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

def make_numcount_descriptors(numname, countname, fieldname, unpack_list=False):

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
            return int(self.get_item(fieldname).split('/')[1])
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

def sort_key(track):
    return (track.album_artist if track.album_artist else track.artist, track.album,
            track.dn, track.tn, getattr(track, 'location', None))

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

def get_fnames(dir):
    """Gets a list of music file names in a directory."""
    allowed_exts = {'.mp3', '.ogg', '.flac'}

    fnames = os.listdir(dir)
    return sorted([os.path.join(dir, fname) for fname in fnames if
                        os.path.splitext(fname)[1].lower() in allowed_exts])

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

def filter_path_elements(elements):
    """Wrapper function for filter_fname that also handles the artist/album/song title
       containing forward slashes
       basedir is the top-level directory (assumed not to contain forbidden characters)
       elements is the list of path elementst hat may contain slashes; artist, album, title, etc."""
    # Remove forward slashes in the path elements
    elements = [element.replace('/', '_') for element in elements]
    return filter_fname(os.path.join(*elements))
