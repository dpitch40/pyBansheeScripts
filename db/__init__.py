import config

def open_db(fname):
    if config.DefaultDb is None:
        raise ValueError('Must specify config.DefaultDb')

    return config.DefaultDb.from_file(fname)
