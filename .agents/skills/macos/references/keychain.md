# The Keychain and the security Tool

Read this before storing a secret a script needs, or before reaching for a password stored on the Mac. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Source: the `security(1)` man page as shipped with Xcode, read through `https://keith.github.io/xcode-man-pages/security.1.html`.

---

### Rules

1. The agent never prints a secret. A Keychain value never goes into the session, a log, a file or a commit.
2. A script that needs a secret reads it at run time inside a command substitution that passes it straight to the program that needs it, through the environment rather than the command line.
3. Unlocking a keychain and approving access is the owner's step. A prompt asking to allow access to an item appears in the owner's session, and the owner decides.

---

### Store a secret

The owner runs this, because `-w` given without a value makes `security` prompt for it, so the secret is never typed into the shell history:

```bash
security add-generic-password -a "$USER" -s <service name> -w
```

`-s` names the service and `-a` the account. Use a service name that says what the secret is for, and record the service name, never the value, in `MACHINE.md`.

---

### Read a secret inside a script

From the man page, `find-generic-password` matches by `-a account` and `-s service`, and `-w` will "Display the password(only) for the item found". Use it only inside a substitution that hands the value to the consumer:

```bash
API_TOKEN="$(security find-generic-password -a "$USER" -s <service name> -w)" <program>
```

Check that an item exists without revealing it, by leaving out `-w` and `-g`:

```bash
security find-generic-password -a "$USER" -s <service name> > /dev/null && echo present
```

---

### Other verbs

| Verb | Use |
|---|---|
| `security list-keychains` | which keychains are searched |
| `security delete-generic-password -a <account> -s <service>` | remove an item, with the owner's approval |
| `security find-internet-password` | the same lookup for internet password items |

Certificates and keys go through Keychain Access or the certificate verbs of `security`. Trusting a certificate system wide changes what the whole machine accepts and is the owner's decision.
