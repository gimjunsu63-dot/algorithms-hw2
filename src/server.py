"""HTTP interface for the in-memory URL shortener."""

from __future__ import annotations

import argparse
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import cast
from urllib.parse import parse_qsl, urlsplit

from linear_probing import LinearProbingTable
from shortener import Shortener


def _page(title: str, content: str) -> str:
    return (
        "<!doctype html>"
        '<html lang="ko"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:sans-serif;line-height:1.5;margin:2rem auto;"
        "max-width:70rem;padding:0 1rem}"
        "input[type=url]{box-sizing:border-box;max-width:100%;width:36rem}"
        ".bucket{border:1px solid #bbb;border-radius:.4rem;margin:1rem 0;"
        "padding:.75rem}"
        ".chain{align-items:center;display:flex;flex-wrap:wrap;gap:.5rem}"
        ".node{border:1px solid #777;border-radius:.4rem;padding:.75rem;"
        "overflow-wrap:anywhere}"
        ".node-value{display:block}"
        ".arrow{font-weight:bold}"
        "details{margin-top:.5rem}"
        "code{overflow-wrap:anywhere}"
        "</style></head><body>"
        f"<h1>{html.escape(title)}</h1>{content}</body></html>"
    )


def _home_page() -> str:
    content = (
        '<form method="post" action="/shorten">'
        '<label for="url">줄일 URL</label><br>'
        '<input id="url" type="url" name="url" required maxlength="2048">'
        '<button type="submit">줄이기</button></form>'
        '<p><a href="/table">현재 해시 테이블 보기</a></p>'
    )
    return _page("URL 단축기", content)


def _result_page(short_link: str) -> str:
    escaped_link = html.escape(short_link, quote=True)
    content = (
        f'<p>짧은 링크: <a href="{escaped_link}">{escaped_link}</a></p>'
        '<p><a href="/">다른 URL 줄이기</a></p>'
    )
    return _page("단축 결과", content)


def _error_page(message: str) -> str:
    content = (
        f"<p>{html.escape(message)}</p>"
        '<p><a href="/">돌아가기</a></p>'
    )
    return _page("요청 오류", content)


def _request_host(handler: BaseHTTPRequestHandler) -> str:
    host = handler.headers.get("X-Forwarded-Host") or handler.headers.get("Host")
    return host or "localhost:8000"


def _request_scheme(handler: BaseHTTPRequestHandler) -> str:
    return handler.headers.get("X-Forwarded-Proto") or "http"


def _short_link(host: str, code: str, scheme: str) -> str:
    return f"{scheme}://{host}/{code}"


def _horner_steps(key: str, bucket_count: int) -> list[str]:
    steps = ["h_0 = 0"]
    current_value = 0
    for position, character in enumerate(key, start=1):
        next_value = (current_value * 31 + ord(character)) % bucket_count
        steps.append(
            f"h_{position} = ({current_value} * 31 + "
            f"ord({character!r})) % {bucket_count} = {next_value}"
        )
        current_value = next_value
    return steps


def _probe_path(
    table: LinearProbingTable[str], first_bucket: int, actual_bucket: int
) -> list[int]:
    path = []
    bucket = first_bucket
    for _ in range(table.bucket_count):
        path.append(bucket)
        if bucket == actual_bucket:
            return path
        bucket = (bucket + 1) % table.bucket_count
    raise RuntimeError("stored key is not reachable from its initial bucket")


def _table_entry(
    url: str,
    code: str,
    host: str,
    scheme: str,
    bucket_count: int,
    first_bucket: int | None = None,
    actual_bucket: int | None = None,
    probe_path: list[int] | None = None,
) -> str:
    escaped_url = html.escape(url, quote=True)
    link = _short_link(host, code, scheme)
    escaped_link = html.escape(link, quote=True)
    entry = [
        '<article class="node">',
        f'<span class="node-value">URL 키: {escaped_url}</span>',
        '<span class="arrow">→</span>',
        f'<span class="node-value">짧은 코드: {html.escape(code)}</span>',
        '<span class="arrow">→</span>',
        f'<a class="node-value" href="{escaped_link}">'
        f"짧은 링크: {escaped_link}</a>",
    ]
    if first_bucket is not None and actual_bucket is not None:
        entry.extend(
            (
                f'<span class="node-value">처음 해시된 칸: {first_bucket}</span>',
                f'<span class="node-value">실제로 들어간 칸: {actual_bucket}</span>',
                '<span class="node-value">들여다본 칸: '
                f'{" → ".join(str(bucket) for bucket in probe_path or [])}</span>',
            )
        )
    entry.append("<details><summary>호너 해시 계산 보기</summary><ol>")
    entry.extend(
        f"<li><code>{html.escape(step)}</code></li>"
        for step in _horner_steps(url, bucket_count)
    )
    entry.extend(("</ol></details></article>",))
    return "".join(entry)


def _table_page(shortener: Shortener, host: str, scheme: str) -> str:
    table = shortener._url_to_code
    is_linear = isinstance(table, LinearProbingTable)
    table_kind = "선형 탐지" if is_linear else "체이닝"
    empty_count = sum(entry is None for entry in table._buckets)
    content = [
        f"<p>테이블 종류: {table_kind} · 버킷 수: {table.bucket_count} · "
        f"비어 있는 칸 수: {empty_count} · 노드 구조: "
        "URL 키 → 짧은 코드 → 짧은 링크</p>"
    ]

    if is_linear:
        for bucket_number, entry in enumerate(table._buckets):
            if entry is None:
                continue
            url, code = entry
            first_bucket = table.bucket_index(url)
            path = _probe_path(table, first_bucket, bucket_number)
            content.append(
                f'<section class="bucket" id="bucket-{bucket_number}">'
                f"<h2>칸 {bucket_number}</h2><div class=\"chain\">"
                + _table_entry(
                    url,
                    code,
                    host,
                    scheme,
                    table.bucket_count,
                    first_bucket,
                    bucket_number,
                    path,
                )
                + "</div></section>"
            )
    else:
        for bucket_number, first_node in enumerate(table._buckets):
            if first_node is None:
                continue
            content.append(
                f'<section class="bucket" id="bucket-{bucket_number}">'
                f"<h2>칸 {bucket_number}</h2><div class=\"chain\">"
            )
            node = first_node
            while node is not None:
                content.append(
                    _table_entry(
                        node.key, node.value, host, scheme, table.bucket_count
                    )
                )
                if node.next is not None:
                    content.append('<span class="arrow">→</span>')
                node = node.next
            content.append("</div></section>")

    return _page("현재 URL 해시 테이블", "".join(content))


class ShortenerHTTPServer(HTTPServer):
    shortener: Shortener

    def __init__(
        self,
        address: tuple[str, int],
        shortener: Shortener | None = None,
        table: str = "chaining",
    ) -> None:
        self.shortener = (
            shortener if shortener is not None else Shortener(table=table)
        )
        super().__init__(address, ShortenerRequestHandler)


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    def _shortener(self) -> Shortener:
        return cast(ShortenerHTTPServer, self.server).shortener

    def _send_html(self, status: int, body: str) -> None:
        encoded_body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded_body)))
        self.end_headers()
        self.wfile.write(encoded_body)

    def _not_found(self) -> None:
        self._send_html(404, _error_page("페이지를 찾을 수 없습니다."))

    def _bad_request(self, message: str) -> None:
        self._send_html(400, _error_page(message))

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send_html(200, _home_page())
            return
        if path == "/table":
            self._send_html(
                200,
                _table_page(
                    self._shortener(),
                    _request_host(self),
                    _request_scheme(self),
                ),
            )
            return
        if path.startswith("/") and "/" not in path[1:]:
            url = self._shortener().expand(path[1:])
            if url is not None:
                self.send_response(302)
                self.send_header("Location", url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        self._not_found()

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/shorten":
            self._not_found()
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._bad_request("잘못된 요청입니다.")
            return
        if content_length < 0:
            self._bad_request("잘못된 요청입니다.")
            return

        try:
            form_data = self.rfile.read(content_length).decode("utf-8")
        except UnicodeDecodeError:
            self._bad_request("요청을 읽을 수 없습니다.")
            return

        url = ""
        for field_name, field_value in parse_qsl(form_data, keep_blank_values=True):
            if field_name == "url":
                url = field_value
                break

        try:
            code = self._shortener().shorten(url)
        except ValueError:
            self._bad_request("잘못된 URL입니다. HTTP 또는 HTTPS URL을 입력하세요.")
            return

        link = _short_link(_request_host(self), code, _request_scheme(self))
        self._send_html(200, _result_page(link))

    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        if code == 501:
            code = 404
            message = "Not Found"
            explain = None
        super().send_error(code, message, explain)


def create_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    shortener: Shortener | None = None,
    table: str = "chaining",
) -> ShortenerHTTPServer:
    return ShortenerHTTPServer((host, port), shortener, table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--table", choices=("chaining", "linear"), default="chaining"
    )
    arguments = parser.parse_args()

    server = create_server(
        arguments.host, arguments.port, table=arguments.table
    )
    print(f"Serving on http://{arguments.host}:{arguments.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
