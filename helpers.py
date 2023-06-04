import datetime
import json

import redis
from pytimeparse import parse


class JSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(JSONDecoder, self).__init__(*args, **kwargs)
        self.parse_string = self._parse_string
        self.scan_once = json.scanner.py_make_scanner(self)  # noqa

    @classmethod
    def _str2dt(cls, value: str) -> datetime.datetime or None:
        if isinstance(value, str):
            try:
                value = datetime.datetime.fromisoformat(value)
            except ValueError:
                value = None
        else:
            value = None
        return value

    @classmethod
    def _str2td(cls, value: str) -> datetime.timedelta or None:
        if isinstance(value, str):
            try:
                value = datetime.timedelta(seconds=parse(value))
            except TypeError:
                value = None
        else:
            value = None
        return value

    @classmethod
    def _parse_string(cls, s, end, strict=True):
        (s, end) = json.decoder.scanstring(s, end, strict)  # noqa
        dt, td = cls._str2dt(s), cls._str2td(s)
        s = dt if dt is not None else td if td is not None else s
        return s, end


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, datetime.timedelta):
            return str(o)
        return super(JSONEncoder, self).default(o)


class Session:
    def __init__(self, clear: bool = True, url: str = None, **kwargs):
        if url is None:
            self._r = redis.Redis(**kwargs)
        else:
            self._r = redis.Redis.from_url(url=url, **kwargs)
        if clear:
            self.clear()

    def get(self, key: str):
        return json.loads(self._r.get(key), cls=JSONDecoder)

    def set(self, key: str, data):
        return self._r.set(key, json.dumps(data, cls=JSONEncoder))

    def exists(self, key: str):
        return self._r.exists(key)

    def clear(self):
        return self._r.flushall()
