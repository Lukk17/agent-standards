"""Java build detection, and the JaCoCo report block a Gradle build needs for the tools to read its coverage.

crapper and mutator know Maven only. Both read JaCoCo XML from `target/site/jacoco/jacoco.xml` in the project
and in its modules one and two levels down, so a Gradle build gets one block, added once, that writes its report
there.
"""

from __future__ import annotations

from pathlib import Path

from quality_loop.host import Host

MAVEN = "maven"
GRADLE = "gradle"

GRADLE_BUILD_FILES = ("build.gradle.kts", "build.gradle")
GRADLE_SETTINGS_FILES = ("settings.gradle.kts", "settings.gradle")

# The block is found again by this line, so it is added once however often the wrapper runs.
REPORT_MARKER = "quality-loop: JaCoCo XML where crapper and mutator read it"

GROOVY_BLOCK = f"""
// {REPORT_MARKER}. Added once by .metrics/tools/run.
allprojects {{
    pluginManager.withPlugin('java') {{
        apply plugin: 'jacoco'
        tasks.named('jacocoTestReport') {{
            reports {{
                xml.required = true
                xml.outputLocation = project.layout.projectDirectory.file('target/site/jacoco/jacoco.xml')
            }}
        }}
    }}
}}
"""

KOTLIN_BLOCK = f"""
// {REPORT_MARKER}. Added once by .metrics/tools/run.
allprojects {{
    pluginManager.withPlugin("java") {{
        apply(plugin = "jacoco")
        tasks.named<JacocoReport>("jacocoTestReport") {{
            reports {{
                xml.required.set(true)
                xml.outputLocation.set(project.layout.projectDirectory.file("target/site/jacoco/jacoco.xml"))
            }}
        }}
    }}
}}
"""

class BuildFileError(Exception):
    """A Gradle build file the wrapper cannot read, so it cannot add the report block."""


# The coordinates crapper itself runs Maven with, so a Windows run measures the same way.
JACOCO_MAVEN_PLUGIN = "org.jacoco:jacoco-maven-plugin:0.8.12"


def java_build(root: Path) -> str | None:
    """MAVEN when the project root has a pom.xml, GRADLE when it has a Gradle build, None otherwise."""
    if (root / "pom.xml").is_file():
        return MAVEN
    if any((root / name).is_file() for name in GRADLE_BUILD_FILES + GRADLE_SETTINGS_FILES):
        return GRADLE
    return None


def gradle_executable(root: Path, host: Host) -> str:
    """The project's own Gradle wrapper when it has one, otherwise `gradle` from PATH."""
    if host.windows:
        return "gradlew.bat" if (root / "gradlew.bat").is_file() else "gradle"
    return "./gradlew" if (root / "gradlew").is_file() else "gradle"


def maven_executable(root: Path, host: Host) -> str:
    """The project's own Maven wrapper when it has one, otherwise `mvn` from PATH."""
    if host.windows:
        return "mvnw.cmd" if (root / "mvnw.cmd").is_file() else "mvn"
    return "./mvnw" if (root / "mvnw").is_file() else "mvn"


def gradle_build_file(root: Path) -> Path:
    """The root build file the report block belongs in, named for the project's DSL when there is none yet."""
    for name in GRADLE_BUILD_FILES:
        if (root / name).is_file():
            return root / name
    kotlin = (root / "settings.gradle.kts").is_file()
    return root / ("build.gradle.kts" if kotlin else "build.gradle")


def ensure_gradle_report(root: Path) -> Path | None:
    """Add the JaCoCo report block to the root Gradle build file once.

    Returns:
        The build file the block was written into, or None when it already holds the block.

    Raises:
        BuildFileError: the build file is not UTF-8. It is left unchanged.
    """
    build_file = gradle_build_file(root)
    try:
        text = build_file.read_bytes().decode("utf-8") if build_file.is_file() else ""
    except UnicodeDecodeError as exc:
        raise BuildFileError(
            f"{build_file.name} is not UTF-8 (byte {exc.start}: {exc.reason}), so the JaCoCo report block the tools "
            "need was not added."
        ) from exc
    if REPORT_MARKER in text:
        return None
    block = KOTLIN_BLOCK if build_file.suffix == ".kts" else GROOVY_BLOCK
    separator = "" if not text or text.endswith("\n") else "\n"
    combined = text + separator + block
    if "\r\n" in text:
        combined = text + (separator + block).replace("\n", "\r\n")
    build_file.write_bytes(combined.encode("utf-8"))
    return build_file
