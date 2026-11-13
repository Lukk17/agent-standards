#!/usr/bin/env python3
"""Serve local git repositories over the smart HTTP protocol, for the marketplace install test.

Claude Code adds a marketplace from a git URL and installs each relative-path
plugin from a clone of it. It refuses a file:// URL, and git's dumb HTTP
protocol cannot answer the shallow, sparse fetch an install makes, so the
install test needs a real smart HTTP server. This module hands every request
to `git http-backend`, the CGI program git ships for exactly that
(https://git-scm.com/docs/git-http-backend), and serves nothing else.

It binds 127.0.0.1 only and exports every repository under its root, so point
it at a scratch directory that holds nothing but the repositories under test.

Usage:
  python tools/git_http.py <root> [--port N]    serve <root>, print the port, run until killed
"""
from __future__ import annotations

import argparse
import http.server
import os
import pathlib
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager

BIND_ADDRESS = "127.0.0.1"
CGI_TIMEOUT_SECONDS = 120


def backend_environment(root: pathlib.Path, method: str, raw_path: str, headers: dict[str, str], length: int) -> dict[str, str]:
    """The CGI environment `git http-backend` reads for one request."""
    path, _, query = raw_path.partition("?")
    return {
        **os.environ,
        "GIT_PROJECT_ROOT": str(root),
        "GIT_HTTP_EXPORT_ALL": "1",
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_TYPE": headers.get("Content-Type", ""),
        "CONTENT_LENGTH": str(length),
        "GIT_PROTOCOL": headers.get("Git-Protocol", ""),
        "HTTP_CONTENT_ENCODING": headers.get("Content-Encoding", ""),
        "REMOTE_ADDR": BIND_ADDRESS,
    }


def parse_cgi_response(output: bytes) -> tuple[int, list[tuple[str, str]], bytes]:
    """Split CGI output into the status, the headers and the body.

    A CGI program names its status in a `Status:` header and defaults to 200.
    """
    head, _, body = output.partition(b"\r\n\r\n")
    status = 200
    headers: list[tuple[str, str]] = []
    for line in head.split(b"\r\n"):
        name, _, value = line.decode("latin-1").partition(":")
        if name.lower() == "status":
            status = int(value.split()[0])
        elif name:
            headers.append((name, value.strip()))
    return status, headers, body


def handler_for(root: pathlib.Path) -> type[http.server.BaseHTTPRequestHandler]:
    class GitHandler(http.server.BaseHTTPRequestHandler):
        def _serve(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            environment = backend_environment(root, self.command, self.path, dict(self.headers), length)
            result = subprocess.run(
                ["git", "http-backend"], input=body, env=environment, capture_output=True, timeout=CGI_TIMEOUT_SECONDS
            )
            status, headers, payload = parse_cgi_response(result.stdout)
            self.send_response(status)
            for name, value in headers:
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = _serve
        do_POST = _serve

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - the base class names it
            sys.stderr.write(f"{self.requestline}\n")

    return GitHandler


@contextmanager
def serving(root: pathlib.Path, port: int = 0) -> Iterator[str]:
    """Serve every repository under root for the duration of the block and yield the base URL."""
    server = http.server.ThreadingHTTPServer((BIND_ADDRESS, port), handler_for(root.resolve()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{BIND_ADDRESS}:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve local git repositories over smart HTTP.")
    parser.add_argument("root", type=pathlib.Path, help="directory whose repositories are served")
    parser.add_argument("--port", type=int, default=0, help="port to bind, default any free port")
    args = parser.parse_args(argv)
    server = http.server.ThreadingHTTPServer((BIND_ADDRESS, args.port), handler_for(args.root.resolve()))
    print(server.server_address[1], flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
