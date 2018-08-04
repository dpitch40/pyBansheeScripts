import abc
import pprint

class FormattingDictLike(abc.ABC):
    sigil = ' '

    all_keys = ()
    format_lines = []

    @abc.abstractmethod
    def to_dict(self):
        raise NotImplementedError

    def _format_dict(self):
        d = self.to_dict()
        for k, v in d.items():
            d[k] = self._format_value(k, v)
        return d

    def _format_value(self, k, v):
        if hasattr(self, '_format_%s' % k):
            v = getattr(self, '_format_%s' % k)(v)
        return v

    def format(self):
        d = self._format_dict()
        for k, v in d.items():
            if v is None:
                d[k] = ''
        return (self.sigil * 3) + ' ' + '\n    '.join([l % d for l in self.format_lines])

    def __str__(self):
        return '<%s>' % self.__class__.__name__

    def __repr__(self):
        return pprint.pformat(self.to_dict())
