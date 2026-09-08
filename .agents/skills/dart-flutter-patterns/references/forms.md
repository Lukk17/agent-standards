# Forms and Validation

Building a `Form`, validating several fields together, gating the submit, and testing both branches of the gate.

---

### Form architecture

- Host the `Form` in a `StatefulWidget`. It owns state that survives rebuilds.
- Create `final _formKey = GlobalKey<FormState>();` exactly once in the `State` class. Creating it inside `build`
  is expensive and destroys the form's state on every rebuild.
- Pass the key to the `Form` widget's `key` property. That is what gives you `FormState` for validation and save.
- From a deep descendant where passing the key is impractical, reach the state with `Form.of(context)`.
- Create every `TextEditingController` and `FocusNode` in `initState` and dispose them in `dispose`. A leaked
  controller keeps the whole subtree alive.

---

### Field validation

`TextFormField` wraps a `TextField` in a `FormField` and drives validation for you.

- Give each field a `validator` callback. Return a `String` to show an error under the field, or `null` when the
  value is valid.
- Validator messages are user-facing. Route every one through `AppLocalizations`, never a literal. See
  [localization.md](localization.md).
- Set `autovalidateMode: AutovalidateMode.onUserInteraction` so a field only turns red after the user has touched
  it, rather than on first paint.
- Cross-field rules (confirm password, end date after start date) read the other field's controller inside the
  validator. Re-validate the dependent field when its partner changes, otherwise a stale error stays on screen.

---

### Submit gating

1. Call `_formKey.currentState?.validate() ?? false`. `!` is banned here, and the `false` fallback is correct when
   the form is not mounted.
2. On `true`, every validator returned `null`. Submit, and disable the button while the request is in flight so a
   double tap cannot send twice.
3. On `false`, `FormState` has already rebuilt the fields with their error text. There is nothing else to do.
4. Guard `context` after the `await`, because the user can leave the screen mid-request.

---

### A validated multi-field form

Registration with three interdependent fields, a localized error for each rule, and a submit that cannot fire
twice. The import is the generated localizations file inside the app package, because the `flutter_gen` synthetic
package no longer exists.

```dart
import 'package:flutter/material.dart';
import 'package:my_app/l10n/app_localizations.dart';

class RegistrationForm extends StatefulWidget {
  const RegistrationForm({super.key, required this.onRegister});
  final Future<void> Function(String email, String password) onRegister;

  @override
  State<RegistrationForm> createState() => _RegistrationFormState();
}

class _RegistrationFormState extends State<RegistrationForm> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _submitting = true);
    final messenger = ScaffoldMessenger.of(context);
    final l10n = AppLocalizations.of(context);
    try {
      await widget.onRegister(_email.text.trim(), _password.text);
      messenger.showSnackBar(SnackBar(content: Text(l10n.registrationSucceeded)));
    } on RegistrationException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.registrationFailed(e.reason))));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Form(
      key: _formKey,
      autovalidateMode: AutovalidateMode.onUserInteraction,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextFormField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            decoration: InputDecoration(labelText: l10n.emailLabel),
            validator: (value) {
              final email = value?.trim() ?? '';
              if (email.isEmpty) return l10n.emailRequired;
              if (!email.contains('@') || email.endsWith('@')) return l10n.emailMalformed;
              return null;
            },
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _password,
            obscureText: true,
            textInputAction: TextInputAction.next,
            decoration: InputDecoration(labelText: l10n.passwordLabel),
            onChanged: (_) => _formKey.currentState?.validate(),
            validator: (value) {
              final password = value ?? '';
              if (password.length < 12) return l10n.passwordTooShort(12);
              if (!password.contains(RegExp(r'\d'))) return l10n.passwordNeedsDigit;
              return null;
            },
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _confirm,
            obscureText: true,
            textInputAction: TextInputAction.done,
            decoration: InputDecoration(labelText: l10n.confirmPasswordLabel),
            onFieldSubmitted: (_) => _submit(),
            validator: (value) =>
                value == _password.text ? null : l10n.passwordsDoNotMatch,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _submitting ? null : _submit,
            child: _submitting
                ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator())
                : Text(l10n.registerAction),
          ),
        ],
      ),
    );
  }
}
```

Points worth copying: the confirm field validates against the password controller rather than a duplicated
variable, `onChanged` on the password re-runs validation so the confirm error clears as soon as it becomes wrong
or right again, `messenger` and `l10n` are captured before the `await`, and the button is null-disabled while the
request runs instead of guarded by a flag inside the handler.

---

### Testing a form

Cover both branches of the submit gate. Pump the form inside a `MaterialApp` carrying
`AppLocalizations.delegate`, so the localized validator messages resolve.

- Valid submit: fill every field with values that pass, tap the button, and assert the success message appears and
  no validator error is on screen.
- Invalid submit: leave one field empty or mismatched, tap the button, and assert the localized error appears and
  the success message does not.
- Cross-field rule: type a password, type a matching confirmation, change the password, and assert the mismatch
  error appears without a second tap.

See [testing.md](testing.md) for the pump and settle patterns.

---

### Checklist

- [ ] `GlobalKey<FormState>` is created once in the `State`, never in `build`.
- [ ] Every controller and focus node is disposed.
- [ ] Every validator message comes from `AppLocalizations`.
- [ ] The submit gate uses `?? false`, never `!`.
- [ ] The submit button is disabled while a request is in flight.
- [ ] `context` derived objects are captured before any `await` in the submit handler.
- [ ] Widget tests cover the valid path, the invalid path, and each cross-field rule.
