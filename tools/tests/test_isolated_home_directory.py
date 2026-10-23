"""Tests for the isolated_home_directory fixture in conftest.py, which every test gets without asking.

A test that inherited the real HOME or CODEX_HOME linked skills into the
user's real ~/.config/codex/skills, so these cases fail the run the moment the
fixture stops covering a variable.
"""

import os
from pathlib import Path

import pytest

from tests.conftest import RELOCATING_VARIABLES


def test_home_is_a_fresh_folder_under_the_pytest_temp_root(tmp_path_factory):
    # Given the pytest temp root
    base = tmp_path_factory.getbasetemp().resolve()

    # When
    home = Path.home().resolve()

    # Then
    assert home.is_relative_to(base)
    assert os.environ["USERPROFILE"] == os.environ["HOME"]
    assert list(home.iterdir()) == []


@pytest.mark.parametrize("name", RELOCATING_VARIABLES)
def test_no_variable_that_moves_an_agent_home_reaches_a_test(name):
    assert name not in os.environ
