"""Tests for .metrics/tools/quality_loop/mutator_windows.py, the starter that gives mutator a process-group kill."""

import os
import signal

from tests.quality_loop_support import QUALITY_TOOLS  # noqa: F401  puts quality_loop on the path

from quality_loop import mutator_windows


def test_the_missing_names_are_added_as_a_tree_kill(monkeypatch):
    monkeypatch.delattr(os, "killpg", raising=False)
    monkeypatch.delattr(signal, "SIGKILL", raising=False)

    mutator_windows.add_process_group_kill()

    assert os.killpg is mutator_windows.kill_process_tree
    assert signal.SIGKILL == signal.SIGTERM


def test_a_platform_that_has_them_keeps_its_own(monkeypatch):
    own_kill = object()
    monkeypatch.setattr(os, "killpg", own_kill, raising=False)
    monkeypatch.setattr(signal, "SIGKILL", 9, raising=False)

    mutator_windows.add_process_group_kill()

    assert os.killpg is own_kill
    assert signal.SIGKILL == 9


def test_the_tree_kill_ends_the_process_and_everything_it_started(monkeypatch):
    calls = []
    monkeypatch.setattr(mutator_windows.subprocess, "run", lambda argv, **_kw: calls.append(argv))

    mutator_windows.kill_process_tree(4321, 9)

    assert calls == [["taskkill", "/T", "/F", "/PID", "4321"]]
