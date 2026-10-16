# Preferences and the defaults Command

Read this before reading or changing an application or system preference. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Sources: the `defaults(1)` man page as shipped with Xcode 27.2 beta 2, read through `https://keith.github.io/xcode-man-pages/defaults.1.html` on 2026-10-13, and Apple's "macOS Library Directory Details" in the File System Programming Guide.

---

### Use defaults, not the plist file

Preferences are `.plist` files under `~/Library/Preferences`, but the system caches them in `cfprefsd`. Apple's File System Programming Guide says of that directory: "You should never create files in this directory yourself. To get or set preference values, you should always use the `NSUserDefaults` class or an equivalent system-provided interface." `defaults` is that interface from the shell. Editing the file directly can be overwritten from the cache, or ignored until the next login.

---

### Find the domain, read, then write

A domain is usually the application's bundle identifier. Find it with:

```bash
osascript -e 'id of app "<App Name>"'
```

```bash
defaults domains | tr ',' '\n' | grep -i <part of name>
```

Read the whole domain, and keep the output as the backup:

```bash
defaults read <domain> > "$HOME/defaults-backup-<domain>-$(date +%Y%m%d%H%M%S).txt"
```

Read one key and its type:

```bash
defaults read <domain> <key>
```

```bash
defaults read-type <domain> <key>
```

Write with an explicit type:

```bash
defaults write <domain> <key> -bool false
```

Delete a key to go back to the application's default:

```bash
defaults delete <domain> <key>
```

The global domain is `-g`. The man page: "'-g' and '-globalDomain' may be used as synonyms for NSGlobalDomain." Keys found there apply to every application that does not set its own.

---

### Making a change take effect

1. Quit the application before writing its preferences, because a running app can write its own copy back on exit.
2. Some system components read their preferences at start. Restart them by name, for example `killall Dock` or `killall Finder`, which the system relaunches. Tell the owner first, because the Dock and Finder briefly disappear.
3. Some keys need a logout. Say so rather than guessing.
4. Read the key back after the change.

---

### Things to know

1. Hidden settings found on the web are often for an older macOS and do nothing on a newer one. Read the key back and check the behaviour, and remove a key that had no effect.
2. Settings enforced by a configuration profile cannot be overridden with `defaults`. Check with `profiles status -type enrollment` and the Profiles pane in System Settings.
3. The man page warns: "The defaults command will be changed in an upcoming major release to only operate on preferences domains." For general plist editing use `plutil` or `/usr/libexec/PlistBuddy` on a file you own.
4. Record the domain, key, old value and new value in the `MACHINE.md` change log.
