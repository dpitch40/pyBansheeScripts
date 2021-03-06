class NotAllowedError(Exception):
    pass

class MappingWrapper(object):
    """Class that allows attribute-like access to a wrapped dictionary with a prespecified range of keys,
       with automatic mapping of keys.
    """

    mapping = {}
    all_keys = ()
    read_only_keys = ()

    def __init__(self, d=None):
        if d is None:
            d = dict()
        self.set_dict(d)

    def set_dict(self, d):
        self.wrapped = d

    def _map_key(self, key):
        return self.mapping.get(key, key)

    def get_item(self, key):
        return self.wrapped.get(key, None)

    def set_item(self, key, value):
        self.wrapped[key] = value

    def del_item(self, key):
        del self.wrapped[key]

    def __getattr__(self, key):
        if key in self.all_keys:
            mapped_key = self._map_key(key)
            return self.get_item(mapped_key)
        else:
            return super(MappingWrapper, self).__getattribute__(key)

    def __setattr__(self, key, value):
        if key in self.all_keys:
            if key in self.read_only_keys:
                raise NotAllowedError('%s is read-only' % key)
            # __setattr__ takes priority over descriptors, so we have to check if we need to use one
            if isinstance(getattr(self.__class__, key, None), property):
                super(MappingWrapper, self).__setattr__(key, value)
            else:
                mapped_key = self._map_key(key)
                self.set_item(mapped_key, value)
        else:
            super(MappingWrapper, self).__setattr__(key, value)

    def __delattr__(self, key):
        if key in self.all_keys:
            if key in self.read_only_keys:
                raise NotAllowedError('%s is read-only' % key)
            # __delattr__ takes priority over descriptors, so we have to check if we need to use one
            if isinstance(getattr(self.__class__, key, None), property):
                super(MappingWrapper, self).__delattr__(key)
            else:
                mapped_key = self._map_key(key)
                self.del_item(mapped_key)
        else:
            super(MappingWrapper, self).__delattr__(key)
