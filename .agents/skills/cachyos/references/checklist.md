# CachyOS Administration Checklist

Run it before calling a CachyOS kernel, driver, repository or boot change done.

- [ ] `MACHINE.md` read, and the CPU ISA level, GPU, kernels and bootloader discovered or confirmed
- [ ] A snapshot taken before any kernel, driver, bootloader or initramfs change
- [ ] Kernel, headers and module package installed or removed as one flavor set
- [ ] A fallback kernel still installed and listed in the boot menu
- [ ] No hand-installed DKMS driver on top of a prebuilt module
- [ ] Boot options changed in `/etc/default/limine`, never in the generated `limine.conf`
- [ ] The change and its undo recorded in the `MACHINE.md` change log
