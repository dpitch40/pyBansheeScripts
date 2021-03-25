import abc
import pprint

from core.util import value_is_none
import config

class FormattingDictLike(abc.ABC):
    sigil = ' '

    all_keys = ()
    format_lines = []

    @abc.abstractmethod
    def to_dict(self):
        raise NotImplementedError

    def _format_dict(self, **overrides):
        d = self.to_dict()
        d.update(overrides)
        fd = dict()
        for k, v in d.items():
            formatted = self._format_value(k, v)
            if formatted is not None:
                fd[k] = formatted
        return fd

    def _format_value(self, k, v):
        if value_is_none(v):
            return None
        if hasattr(self, '_format_%s' % k):
            v = getattr(self, '_format_%s' % k)(v)
        else:
            v = str(v)
        return v

    def format(self, **overrides):
        d = self._format_dict(**overrides)

        formatted_lines = []
        for l in self.format_lines:
            formatted_line = []
            for field in l:
                formatted_field = d.get(field, None)
                if formatted_field:
                    formatted_line.append(formatted_field)
            if formatted_line:
                formatted_lines.append(' - '.join(formatted_line))

        return (self.sigil * 3) + ' ' + '\n    '.join(formatted_lines)
    def __str__(self):
        return '<%s>' % self.__class__.__name__
    def __repr__(self):
        return pprint.pformat(self.to_dict())

    # Specific formatting methods for subclasses

    def _format_album_artist(self, value):
        return '(%s)' % value

    def _format_length(self, value):
        return '%.3fs' % (value / 1000)

    def _format_tnc(self, value):
        if value[1] is None:
            return '%d' % value[0]
        else:
            return '%d/%d' % value

    _format_dnc = _format_tnc

    def _format_bitrate(self, bitrate):
        bitrate = bitrate / 1000
        if bitrate % 1 == 0:
            bitrate = int(bitrate)
        return '%dkbps' % bitrate

    def _format_fsize(self, fsize):
        return '%.2fMB' % (fsize / 1000000)

    def _format_rating(self, value):
        return '%d/%d' % (value, config.MaxStars)

    def _format_play_count(self, value):
        if value > 1:
            return '%d plays' % value
        else:
            return '%d play' % value

    def _format_skip_count(self, value):
        if value > 1:
            return '%d skips' % value
        else:
            return '%d skip' % value

    def _format_date_added(self, value):
        return 'Added %s' % value.strftime('%Y-%m-%d %H:%M:%S')

    def _format_last_played(self, value):
        return 'last played %s' % value.strftime('%Y-%m-%d %H:%M:%S')

    def _format_last_played(self, value):
        return 'last skipped %s' % value.strftime('%Y-%m-%d %H:%M:%S')

    def _format_grouping(self, value):
        return f'({value},)'
