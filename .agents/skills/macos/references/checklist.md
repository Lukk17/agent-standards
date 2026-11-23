# macOS Administration Checklist

Run it before calling a change on a Mac done.

- [ ] `MACHINE.md` read, and `sw_vers` and `uname -m` checked
- [ ] Homebrew used first, formula for a command line tool and cask for a GUI app, no `sudo brew`
- [ ] The App Store or a vendor installer used only for software Homebrew does not carry
- [ ] launchd jobs loaded with `bootstrap` into the right domain, not the legacy `load`
- [ ] Old preference values recorded before any `defaults write`
- [ ] Quarantine cleared on one named item only, Gatekeeper and SIP left on
- [ ] No privacy permission granted and no secret printed by the agent
- [ ] Snapshot or backup confirmed before updates or changes under `/Library`
- [ ] The change and its undo recorded in the `MACHINE.md` change log
