# Build and Dependency Management Checklist

Run it before calling a build or dependency change done.

- [ ] Every version lives in one catalog, and no module hardcodes a version string.
- [ ] Every managed family comes from an imported bill of materials, with no member pinned by hand.
- [ ] An application commits its lock file and builds reproducibly from a clean checkout, a library declares ranges.
- [ ] New versions wait out a release-age cooldown, and installs verify hashes from the lock file.
- [ ] Shared build configuration lives in one convention plugin or parent definition.
- [ ] Each new dependency has a stated purpose, a license check, and prior approval.
- [ ] No generated file is hand-edited, and any committed generated output is regenerated and diffed in CI.
