import os
import threading
from typing import Any, Optional

import redis
import fnmatch


class MemoryRedis:
    def __init__(self):
        self._values: dict[str, Any] = {}
        self._sets: dict[str, set[str]] = {}
        self._zsets: dict[str, dict[str, float]] = {}
        self._lists: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def ping(self):
        return True

    def get(self, key: str):
        return self._values.get(key)

    def set(self, key: str, value: Any, nx: bool = False, ex: Optional[int] = None):
        with self._lock:
            if nx and key in self._values:
                return False
            self._values[key] = value
            return True

    def setex(self, key: str, _timeout: int, value: Any):
        self._values[key] = value
        return True

    def expire(self, _key: str, _timeout: int):
        return True

    def delete(self, key: str):
        with self._lock:
            removed = 0
            if key in self._values:
                del self._values[key]
                removed += 1
            if key in self._sets:
                del self._sets[key]
                removed += 1
            if key in self._zsets:
                del self._zsets[key]
                removed += 1
            return removed

    def sadd(self, key: str, value: Any):
        with self._lock:
            bucket = self._sets.setdefault(key, set())
            before = len(bucket)
            bucket.add(str(value))
            return 1 if len(bucket) > before else 0

    def srem(self, key: str, value: Any):
        with self._lock:
            bucket = self._sets.setdefault(key, set())
            if str(value) in bucket:
                bucket.remove(str(value))
                return 1
            return 0

    def smembers(self, key: str):
        with self._lock:
            return set(self._sets.get(key, set()))

    def zadd(self, key: str, mapping: dict[str, float]):
        with self._lock:
            z = self._zsets.setdefault(key, {})
            for member, score in mapping.items():
                z[str(member)] = float(score)
            return True

    def zrange(self, key: str, start: int, end: int):
        with self._lock:
            z = self._zsets.get(key, {})
            ordered = [
                member
                for member, _score in sorted(
                    z.items(), key=lambda item: (float(item[1]), str(item[0]))
                )
            ]
            if end == -1:
                end = len(ordered) - 1
            if end < start:
                return []
            return ordered[start : end + 1]

    def zrangebyscore(self, key: str, min: str, max: str):
        with self._lock:
            z = self._zsets.get(key, {})
            min_score = float("-inf") if min == "-inf" else float(min)
            max_score = float("inf") if max == "+inf" else float(max)
            members = [m for m, s in z.items() if min_score <= float(s) <= max_score]
            return sorted(members)

    def zremrangebyscore(self, key: str, min: float, max: float):
        with self._lock:
            z = self._zsets.get(key, {})
            min_score = float("-inf") if min == "-inf" else float(min)
            max_score = float("inf") if max == "+inf" else float(max)
            to_remove = [
                member
                for member, score in z.items()
                if min_score <= float(score) <= max_score
            ]
            for member in to_remove:
                del z[member]
            return len(to_remove)

    def eval(self, _script: str, _numkeys: int, key: str, value: Any):
        with self._lock:
            current = self._values.get(key)
            value = str(value)
            if current is None:
                self._values[key] = value
                return 1
            if str(current) == value:
                return 1
            return 0

    def incrby(self, key: str, amount: int):
        with self._lock:
            current = self._values.get(key, 0)
            try:
                current_int = int(current)
            except Exception:
                current_int = 0
            next_value = current_int + int(amount)
            self._values[key] = next_value
            return next_value

    def rpush(self, key: str, *values: Any):
        with self._lock:
            lst = self._lists.setdefault(key, [])
            for value in values:
                lst.append(str(value))
            return len(lst)

    def lrange(self, key: str, start: int, end: int):
        with self._lock:
            lst = self._lists.get(key, [])
            if end == -1:
                end = len(lst) - 1
            if end < start:
                return []
            return list(lst[start : end + 1])

    def lpop(self, key: str, count: Optional[int] = None):
        with self._lock:
            lst = self._lists.get(key, [])
            if not lst:
                return None
            if count is None:
                return lst.pop(0)
            count_int = int(count)
            popped = lst[:count_int]
            del lst[:count_int]
            return popped

    def ltrim(self, key: str, start: int, end: int):
        with self._lock:
            lst = self._lists.get(key, [])
            if not lst:
                return True
            if end == -1:
                end = len(lst) - 1
            self._lists[key] = lst[start : end + 1]
            return True

    def scan(self, cursor: int = 0, match: Optional[str] = None, count: int = 10):
        with self._lock:
            all_keys = (
                set(self._values.keys())
                | set(self._sets.keys())
                | set(self._zsets.keys())
                | set(self._lists.keys())
            )
            keys = sorted(all_keys)
            if match:
                keys = [k for k in keys if fnmatch.fnmatch(k, match)]
            return 0, keys[: int(count) if count else len(keys)]

    def geoadd(self, *_args, **_kwargs):
        return 1

    def pipeline(self):
        parent = self

        class Pipe:
            def expire(self, key, timeout):
                parent.expire(key, timeout)
                return self

            def srem(self, key, value):
                parent.srem(key, value)
                return self

            def sadd(self, key, value):
                parent.sadd(key, value)
                return self

            def delete(self, key):
                parent.delete(key)
                return self

            def setex(self, key, timeout, value):
                parent.setex(key, timeout, value)
                return self

            def rpush(self, key, value):
                parent.rpush(key, value)
                return self

            def execute(self):
                return True

        return Pipe()


_singleton_lock = threading.Lock()
_singleton_client: Optional[Any] = None


def get_redis():
    global _singleton_client
    if _singleton_client is not None:
        return _singleton_client

    with _singleton_lock:
        if _singleton_client is not None:
            return _singleton_client

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
        allow_fallback = os.environ.get(
            "REDIS_ALLOW_MEMORY_FALLBACK", ""
        ).strip().lower() in {"1", "true", "yes", "on"}
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        try:
            client.ping()
            _singleton_client = client
            return _singleton_client
        except Exception:
            if not allow_fallback:
                _singleton_client = client
                return _singleton_client
            _singleton_client = MemoryRedis()
            return _singleton_client
