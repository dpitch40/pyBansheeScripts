import importlib
import config

def open_db(fname):
    return config.DefaultDb().from_file(fname)

def db_from_metadata(metadata):
    return config.DefaultDb().from_metadata(metadata)
