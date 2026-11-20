from __future__ import annotations

from typing import Generic, TypeVar


_Value = TypeVar("_Value")


class LinearProbingTable(Generic[_Value]):
    def __init__(self, bucket_count: int = 4093) -> None:
        if isinstance(bucket_count, bool) or not isinstance(bucket_count, int):
            raise TypeError("bucket_count must be an integer")
        if bucket_count <= 0:
            raise ValueError("bucket_count must be positive")

        self.bucket_count = bucket_count
        self._buckets: list[tuple[str, _Value] | None] = [None] * bucket_count
        self._size = 0
        self.last_comparisons = 0

    def bucket_index(self, key: str) -> int:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        value = 0
        for character in key:
            value = (value * 31 + ord(character)) % self.bucket_count
        return value

    def put(self, key: str, value: _Value) -> None:
        index = self.bucket_index(key)
        for _ in range(self.bucket_count):
            entry = self._buckets[index]
            if entry is None:
                self._buckets[index] = (key, value)
                self._size += 1
                return
            if entry[0] == key:
                return
            index = (index + 1) % self.bucket_count

        raise OverflowError("hash table is full")

    def get(self, key: str) -> _Value | None:
        index = self.bucket_index(key)
        self.last_comparisons = 0
        for _ in range(self.bucket_count):
            self.last_comparisons += 1
            entry = self._buckets[index]
            if entry is None:
                return None
            if entry[0] == key:
                return entry[1]
            index = (index + 1) % self.bucket_count

        return None

    def __len__(self) -> int:
        return self._size
