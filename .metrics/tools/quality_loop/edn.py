"""A reader for the part of EDN the three tools write: maps, vectors, lists, strings, numbers, keywords, nil.

A keyword reads as a `Keyword`, a `str` subclass, so `data["entries"]` finds the value under `:entries` and
`:survived` compares equal to `"survived"`.
"""

from __future__ import annotations

import re


class EdnError(ValueError):
    """The text is not EDN this reader understands."""


class Keyword(str):
    """An EDN keyword, held without its leading colon."""

    __slots__ = ()


_NUMBER = re.compile(r"[+-]?\d+(\.\d+)?([eE][+-]?\d+)?M?N?")
_TOKEN_END = re.compile(r"[\s,\[\]{}()\"]|$")
_ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}
_CLOSERS = {"{": "}", "[": "]", "(": ")"}
_SYMBOLS: dict[str, object] = {"nil": None, "true": True, "false": False}


class _Reader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.index = 0

    def skip(self) -> None:
        text = self.text
        while self.index < len(text):
            char = text[self.index]
            if char.isspace() or char == ",":
                self.index += 1
            elif char == ";":
                newline = text.find("\n", self.index)
                self.index = len(text) if newline < 0 else newline + 1
            else:
                return

    def value(self) -> object:
        self.skip()
        if self.index >= len(self.text):
            raise EdnError("unexpected end of input")
        char = self.text[self.index]
        if char in _CLOSERS:
            return self.collection(char)
        if char == '"':
            return self.string()
        if char == ":":
            return Keyword(self.token()[1:])
        return self.atom()

    def collection(self, opener: str) -> object:
        closer = _CLOSERS[opener]
        self.index += 1
        items: list[object] = []
        while True:
            self.skip()
            if self.index >= len(self.text):
                raise EdnError(f"missing {closer!r}")
            if self.text[self.index] == closer:
                self.index += 1
                break
            items.append(self.value())
        if opener != "{":
            return items
        if len(items) % 2:
            raise EdnError("a map needs an even number of forms")
        return {_hashable(items[i]): items[i + 1] for i in range(0, len(items), 2)}

    def string(self) -> str:
        self.index += 1
        parts: list[str] = []
        text = self.text
        while self.index < len(text):
            char = text[self.index]
            if char == '"':
                self.index += 1
                return "".join(parts)
            if char == "\\":
                escape = text[self.index + 1 : self.index + 2]
                if escape not in _ESCAPES:
                    raise EdnError(f"unknown string escape \\{escape}")
                parts.append(_ESCAPES[escape])
                self.index += 2
                continue
            parts.append(char)
            self.index += 1
        raise EdnError("unterminated string")

    def token(self) -> str:
        end = _TOKEN_END.search(self.text, self.index + 1)
        stop = end.start() if end else len(self.text)
        token = self.text[self.index : stop]
        self.index = stop
        return token

    def atom(self) -> object:
        token = self.token()
        if token in _SYMBOLS:
            return _SYMBOLS[token]
        if _NUMBER.fullmatch(token):
            number = token.rstrip("MN")
            return float(number) if any(mark in number for mark in ".eE") else int(number)
        raise EdnError(f"unsupported form {token!r}")


def _hashable(key: object) -> object:
    if isinstance(key, list):
        return tuple(key)
    return key


def loads(text: str) -> object:
    """Read exactly one EDN value from text."""
    reader = _Reader(text)
    value = reader.value()
    reader.skip()
    if reader.index != len(text):
        raise EdnError("more than one value")
    return value
