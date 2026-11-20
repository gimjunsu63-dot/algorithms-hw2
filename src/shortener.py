from urllib.parse import urlsplit

from base62 import encode
from hash_table import HashTable
from linear_probing import LinearProbingTable


class Shortener:
    def __init__(self, table: str = "chaining") -> None:
        self._url_to_code: HashTable[str] | LinearProbingTable[str]
        self._code_to_url: HashTable[str] | LinearProbingTable[str]
        if table == "chaining":
            self._url_to_code = HashTable()
            self._code_to_url = HashTable()
        elif table == "linear":
            self._url_to_code = LinearProbingTable()
            self._code_to_url = LinearProbingTable()
        else:
            raise ValueError("table must be 'chaining' or 'linear'")
        self._next_id = 1

    def shorten(self, url: str) -> str:
        self._validate_url(url)

        existing_code = self._url_to_code.get(url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        self._next_id += 1
        return code

    def expand(self, code: str) -> str | None:
        return self._code_to_url.get(code)

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if (
            not url
            or len(url) > 2048
            or url.strip() != url
            or any(character.isspace() for character in url)
        ):
            raise ValueError("invalid URL")

        try:
            parsed_url = urlsplit(url)
            hostname = parsed_url.hostname
            _ = parsed_url.port
        except ValueError as error:
            raise ValueError("invalid URL") from error

        if parsed_url.scheme.lower() not in ("http", "https") or not hostname:
            raise ValueError("invalid URL")
