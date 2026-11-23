# KDE Plasma 6 Administration Checklist

Run it before calling a Plasma change done.

- [ ] `MACHINE.md` read, and the live layout read before any panel change
- [ ] Config files copied and the layout dumped before the first write
- [ ] The live API used, or plasmashell stopped before a hand edit
- [ ] Nothing written under `/usr/share` or `/usr/lib`
- [ ] The change read back and reported
- [ ] The change and its undo recorded in the `MACHINE.md` change log
