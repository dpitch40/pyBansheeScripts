import importlib

import config
if config.DefaultDb:
    full_path = 'db.' + config.DefaultDb
    import_path, class_name = full_path.rsplit('.', 1)
    config.DefaultDb = getattr(importlib.import_module(import_path), class_name)

def open_db(fname):
    if config.DefaultDb is None:
        raise ValueError('Must specify config.DefaultDb')

    return config.DefaultDb.from_file(fname)

def db_from_metadata(metadata):
    if config.DefaultDb is None:
        raise ValueError('Must specify config.DefaultDb')

    return config.DefaultDb.from_metadata(metadata)
