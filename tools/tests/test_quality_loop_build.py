"""Tests for .metrics/tools/quality_loop/build.py: the Java build and the Gradle JaCoCo report block."""

import pytest
from tests.quality_loop_support import write

from quality_loop import build
from quality_loop.host import Host

POSIX = Host(windows=False)
WINDOWS = Host(windows=True)


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (["pom.xml"], build.MAVEN),
        (["build.gradle"], build.GRADLE),
        (["settings.gradle.kts"], build.GRADLE),
        (["pom.xml", "build.gradle"], build.MAVEN),
        ([], None),
    ],
)
def test_the_java_build_is_read_from_the_project_root(tmp_path, files, expected):
    for name in files:
        write(tmp_path, name)

    assert build.java_build(tmp_path) == expected


@pytest.mark.parametrize(
    ("host", "wrapper", "expected"),
    [
        (POSIX, "gradlew", "./gradlew"),
        (WINDOWS, "gradlew.bat", "gradlew.bat"),
        (POSIX, None, "gradle"),
        (WINDOWS, "gradlew", "gradle"),
    ],
)
def test_gradle_runs_through_the_project_wrapper_for_this_system(tmp_path, host, wrapper, expected):
    if wrapper:
        write(tmp_path, wrapper)

    assert build.gradle_executable(tmp_path, host) == expected


@pytest.mark.parametrize(
    ("host", "wrapper", "expected"),
    [(POSIX, "mvnw", "./mvnw"), (WINDOWS, "mvnw.cmd", "mvnw.cmd"), (WINDOWS, None, "mvn")],
)
def test_maven_runs_through_the_project_wrapper_for_this_system(tmp_path, host, wrapper, expected):
    if wrapper:
        write(tmp_path, wrapper)

    assert build.maven_executable(tmp_path, host) == expected


def test_the_groovy_report_block_is_added_to_build_gradle_once(tmp_path):
    build_file = write(tmp_path, "build.gradle", "plugins {\n    id 'java'\n}\n")

    first = build.ensure_gradle_report(tmp_path)
    after_first = build_file.read_text(encoding="utf-8")
    second = build.ensure_gradle_report(tmp_path)

    assert first == build_file
    assert second is None
    assert build_file.read_text(encoding="utf-8") == after_first
    assert after_first.startswith("plugins {\n    id 'java'\n}\n")
    assert "xml.outputLocation = project.layout.projectDirectory.file('target/site/jacoco/jacoco.xml')" in after_first


def test_the_kotlin_report_block_goes_into_build_gradle_kts(tmp_path):
    build_file = write(tmp_path, "build.gradle.kts", "plugins {\n    java\n}")

    build.ensure_gradle_report(tmp_path)

    text = build_file.read_text(encoding="utf-8")
    assert "plugins {\n    java\n}\n\n// " + build.REPORT_MARKER in text
    assert 'tasks.named<JacocoReport>("jacocoTestReport")' in text
    assert "apply plugin:" not in text


def test_a_build_file_with_crlf_endings_keeps_them(tmp_path):
    build_file = tmp_path / "build.gradle"
    build_file.write_bytes(b"plugins {\r\n    id 'java'\r\n}\r\n")

    build.ensure_gradle_report(tmp_path)

    content = build_file.read_bytes()
    assert content.count(b"\n") == content.count(b"\r\n")


def test_a_kotlin_settings_file_alone_gets_a_new_kotlin_build_file(tmp_path):
    write(tmp_path, "settings.gradle.kts", 'rootProject.name = "x"\n')

    created = build.ensure_gradle_report(tmp_path)

    assert created == tmp_path / "build.gradle.kts"
    assert created.read_text(encoding="utf-8").startswith("\n// " + build.REPORT_MARKER)


def test_a_build_file_that_is_not_utf8_is_named_and_left_unchanged(tmp_path):
    build_file = tmp_path / "build.gradle"
    build_file.write_bytes(b"// caf\xe9\nplugins { id 'java' }\n")

    with pytest.raises(build.BuildFileError, match="build.gradle is not UTF-8"):
        build.ensure_gradle_report(tmp_path)

    assert build_file.read_bytes() == b"// caf\xe9\nplugins { id 'java' }\n"
