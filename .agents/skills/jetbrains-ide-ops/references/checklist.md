# JetBrains IDE Ops Checklist

Run it before calling a change to `.run/` or `.idea/` done.

- [ ] Every option name in a run configuration was copied from a working file or from XML the IDE wrote
- [ ] Every path inside a run configuration uses `$PROJECT_DIR$`, never an absolute path, except `SDK_NAME`, which is
  the interpreter's registered name copied as the IDE wrote it, even when that name looks like a path
- [ ] `.idea/modules.xml` lists only modules whose `.iml` is committed beside it
- [ ] `git check-ignore -v` confirmed each `.idea/` path in both directions
- [ ] Every `<module name="...">` in a run configuration names a module the IDE currently shows
- [ ] IDE `imageTag` values match the Compose `image` lines for the same services
- [ ] The IDE was closed before `.idea/` was edited by hand, and reopened cold afterwards
- [ ] After a rename, every item on the checklist was walked in order and the misses were fixed
