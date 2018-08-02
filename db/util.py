from datetime import datetime

def date_descriptor(name):

    def get_(self):
        timestamp = self.wrapped_dict[name]
        return datetime.fromtimestamp(timestamp) if timestamp else None

    def set_(self, value):
        self.wrapped_dict[name] = int(value.timestamp()) if value is not None else None

    def del_(self):
        del self.wrapped_dict[name]

    return property(get_, set_, del_)
