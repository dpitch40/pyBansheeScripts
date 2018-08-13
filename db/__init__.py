import importlib
import config

# import config
# if config.DefaultDb:
#     full_path = 'db.' + config.DefaultDb
#     import_path, class_name = full_path.rsplit('.', 1)
#     config.DefaultDb = getattr(importlib.import_module(import_path), class_name)

def open_db(fname):
    return config.DefaultDb.from_file(fname)

def db_from_metadata(metadata):
    return config.DefaultDb.from_metadata(metadata)
