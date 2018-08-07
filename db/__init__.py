import importlib

import config
if config.DefaultDb:
    config.DefaultDb = importlib.import_module('db.' + config.DefaultDb)

def open_db(fname):
    if config.DefaultDb is None:
        raise ValueError('Must specify config.DefaultDb')

    return config.DefaultDb.from_file(fname)
