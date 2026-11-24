"""Whether the command that starts an MCP server names one exact release.

A server started as `npx <package>@latest`, as `uvx <package>` with no
version, from an image with no tag, or with `docker run --pull=always` runs
whatever its registry serves on the day it starts. `floating` gives the reason
such a command floats, and None for a command that names an exact npm version,
an exact PyPI version, or an image by a version tag other than `latest`
together with the `@sha256:` digest of that tag. A tag alone can be pushed
again, and a digest alone names no release a reader can look up.

tools/plugin_map_rules.py refuses a plugin map with a floating server block,
and tools/tests/test_mcp_pins.py holds the five MCP files and the documents to
the same rule.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

__all__ = ["floating", "package"]

DOCKER = "docker"
NPX = "npx"
UVX = "uvx"

# The options of each launcher that take the next word as their value.
VALUE_OPTIONS: dict[str, frozenset[str]] = {
    NPX: frozenset({"-p", "--package", "-c", "--call"}),
    UVX: frozenset({"--from", "--with", "--env-file", "-p", "--python", "--index", "--default-index"}),
    DOCKER: frozenset({
        "-e", "--env", "--env-file", "-v", "--volume", "--mount", "--name", "--network", "-p", "--publish",
        "-u", "--user", "-w", "--workdir", "--entrypoint", "--platform", "--pull",
    }),
}
# The option of each launcher whose value names the package, ahead of the first plain word.
PACKAGE_OPTIONS: dict[str, frozenset[str]] = {
    NPX: frozenset({"-p", "--package"}),
    UVX: frozenset({"--from"}),
    DOCKER: frozenset(),
}

NPM_EXACT = re.compile(r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*@(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}", re.ASCII)
PYPI_EXACT = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?(?:==|@)[0-9]+(?:\.[0-9]+)*", re.ASCII)
IMAGE_DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$", re.ASCII)
PULL_ALWAYS = "always"
FLOATING_TAG = "latest"


def _words(command: Sequence[str]) -> tuple[list[str], dict[str, str]]:
    """The plain words after the launcher, and the value of each option that takes one."""
    launcher, arguments = command[0], list(command[1:])
    plain: list[str] = []
    values: dict[str, str] = {}
    index = 0
    while index < len(arguments):
        word = arguments[index]
        if word.startswith("-") and "=" in word:
            option, _, value = word.partition("=")
            values[option] = value
        elif word in VALUE_OPTIONS[launcher]:
            values[word] = arguments[index + 1] if index + 1 < len(arguments) else ""
            index += 1
        elif not word.startswith("-"):
            plain.append(word)
        index += 1
    return plain, values


def package(command: Sequence[str]) -> str | None:
    """The package or image a launcher command starts, as the command spells it, or None when it names none.

    Raises:
        ValueError: the command is empty or starts a launcher this module does not know.
    """
    if not command:
        raise ValueError("empty command")
    launcher = command[0]
    if launcher not in VALUE_OPTIONS:
        raise ValueError(f"unknown launcher {launcher!r}, teach tools/mcp_pins.py how it names its package")
    plain, values = _words(command)
    for option in PACKAGE_OPTIONS[launcher]:
        if values.get(option):
            return values[option]
    if launcher == DOCKER:
        plain = plain[1:] if plain[:1] == ["run"] else []
    return plain[0] if plain else None


def _image_floats(image: str) -> str | None:
    digest = IMAGE_DIGEST.search(image)
    tag = image.partition("@")[0].rsplit("/", 1)[-1].partition(":")[2]
    if not tag:
        return f"the image {image!r} names a digest but no version tag" if digest else f"the image {image!r} names no tag and no digest"
    if tag == FLOATING_TAG:
        return f"the image {image!r} names the moving tag {FLOATING_TAG}" if digest else f"the image {image!r} floats on the tag {FLOATING_TAG}"
    if not digest:
        return f"the image {image!r} names the tag {tag!r} but no digest"
    return None


def floating(command: Sequence[str]) -> str | None:
    """Why a server command does not name one exact release, or None when it does."""
    try:
        named = package(command)
    except ValueError as exc:
        return str(exc)
    launcher = command[0]
    if named is None:
        return f"the {launcher} command names no package"
    if launcher == DOCKER:
        if _words(command)[1].get("--pull") == PULL_ALWAYS:
            return "the docker command pulls the image on every start"
        return _image_floats(named)
    exact = NPM_EXACT if launcher == NPX else PYPI_EXACT
    return None if exact.fullmatch(named) else f"the {launcher} package {named!r} names no exact version"
