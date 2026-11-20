from __future__ import annotations

from typing import Generic, TypeVar


_Value = TypeVar("_Value")


class _Node(Generic[_Value]):
    __slots__ = ("key", "value", "next")

    def __init__(
        self, key: str, value: _Value, next_node: _Node[_Value] | None = None
    ) -> None:
        self.key = key
        self.value = value
        self.next = next_node


class HashTable(Generic[_Value]):
    def __init__(self, bucket_count: int = 4093) -> None:
        if isinstance(bucket_count, bool) or not isinstance(bucket_count, int):
            raise TypeError("bucket_count must be an integer")
        if bucket_count <= 0:
            raise ValueError("bucket_count must be positive")

        self.bucket_count = bucket_count
        self._buckets: list[_Node[_Value] | None] = [None] * bucket_count
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
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                return
            node = node.next

        self._buckets[index] = _Node(key, value, self._buckets[index])
        self._size += 1

    def get(self, key: str) -> _Value | None:
        index = self.bucket_index(key)
        self.last_comparisons = 0
        node = self._buckets[index]
        while node is not None:
            self.last_comparisons += 1
            if node.key == key:
                return node.value
            node = node.next
        return None

    def __len__(self) -> int:
        return self._size
