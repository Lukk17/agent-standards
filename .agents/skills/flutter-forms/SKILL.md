---
name: flutter-forms
description: Builds Flutter forms with validation and user input handling. Use when creating login screens, data entry forms, or any multi-field user input.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Thu, 12 Mar 2026 22:15:24 GMT

---
# Building Validated Forms

---

### Contents
- [Form Architecture](#form-architecture)
- [Field Validation](#field-validation)
- [Workflow: Implementing a Validated Form](#workflow-implementing-a-validated-form)
- [Examples](#examples)

---

### Form Architecture

Implement forms using a `Form` widget to group and validate multiple input fields together. 

- Use a StatefulWidget: Always host your `Form` inside a `StatefulWidget`. 
- Persist the GlobalKey: Instantiate a `GlobalKey<FormState>` exactly once as a final variable within the `State` class.
  Do not generate a new `GlobalKey` inside the `build` method; doing so is resource-expensive and destroys the form's
  state on every rebuild.
- Bind the Key: Pass the `GlobalKey<FormState>` to the `key` property of the `Form` widget. This uniquely identifies the
  form and provides access to the `FormState` for validation and submission.
- Alternative Access: If dealing with highly complex widget trees where passing the key is impractical, use
  `Form.of(context)` to access the `FormState` from a descendant widget.

---

### Field Validation

Use `TextFormField` to render Material Design text inputs with built-in validation support. `TextFormField` is a
convenience widget that automatically wraps a standard `TextField` inside a `FormField`.

- Implement the Validator: Provide a `validator()` callback function to each `TextFormField`.
- Return Error Messages: If the user's input is invalid, return a `String` containing the specific error message. The
  `Form` will automatically rebuild to display this text below the field.
- Localize Validator Messages: Validator messages are user-facing strings. Never return hardcoded literals. Route every
  message through `AppLocalizations.of(context)` so error text is translated. See the flutter-localization skill.
- Return Null for Success: If the input passes validation, you must return `null`.

---

### Workflow: Implementing a Validated Form

Follow this sequential workflow to implement and validate a form. Copy the checklist to track your progress.

Task Progress:
- [ ] 1. Create a `StatefulWidget` and its corresponding `State` class.
- [ ] 2. Instantiate `final _formKey = GlobalKey<FormState>();` in the `State` class.
- [ ] 3. Return a `Form` widget in the `build` method and assign `key: _formKey`.
- [ ] 4. Add `TextFormField` widgets as descendants of the `Form`.
- [ ] 5. Write a `validator` function for each `TextFormField` (return `String` on error, `null` on success).
- [ ] 6. Add a submit button (e.g., `ElevatedButton`).
- [ ] 7. Implement the validation check in the button's `onPressed` callback using
  `_formKey.currentState?.validate() ?? false`.

#### Validation Decision Logic

When the user triggers the submit action, execute the following conditional logic:

1. Call `_formKey.currentState?.validate() ?? false`. The force-unwrap `!` is banned; the null-aware call with a `false`
   fallback is safe when the form is not yet mounted.
2. If `true` (Valid): All validators returned `null`. Proceed with form submission (e.g., save data, make API call) and
   display a success indicator (e.g., a `SnackBar`).
3. If `false` (Invalid): One or more validators returned an error string. The `FormState` automatically rebuilds the UI
   to display the error messages.
4. Feedback Loop: Run validator -> review errors -> fix. The user must adjust their input and resubmit until
   `validate()` returns `true`.

---

### Examples

#### Complete Validated Form Implementation

Use the following pattern to implement a robust, validated form.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

class UserRegistrationForm extends StatefulWidget {
  const UserRegistrationForm({super.key});

  @override
  State<UserRegistrationForm> createState() => _UserRegistrationFormState();
}

class _UserRegistrationFormState extends State<UserRegistrationForm> {
  // 1. Persist the GlobalKey in the State class
  final _formKey = GlobalKey<FormState>();

  @override
  Widget build(BuildContext context) {
    // 2. Bind the key to the Form
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 3. Add TextFormFields with validators
          TextFormField(
            decoration: const InputDecoration(
              labelText: 'Username',
              hintText: 'Enter your username',
            ),
            validator: (value) {
              final l10n = AppLocalizations.of(context)!;
              if (value == null || value.isEmpty) {
                return l10n.usernameRequired; // Error state (localized)
              }
              if (value.length < 4) {
                return l10n.usernameTooShort; // Error state (localized)
              }
              return null; // Valid state
            },
          ),
          const SizedBox(height: 16),
          // 4. Add the submit button
          ElevatedButton(
            onPressed: () {
              // 5. Trigger validation logic (no force-unwrap)
              if (_formKey.currentState?.validate() ?? false) {
                // Form is valid: Process data
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(AppLocalizations.of(context)!.processingData)),
                );
              } else {
                // Form is invalid: Errors are automatically displayed
                debugPrint('Form validation failed.');
              }
            },
            child: const Text('Submit'),
          ),
        ],
      ),
    );
  }
}
```

#### Widget Test Pointer

Cover both branches of the validation gate. Pump the form inside a `MaterialApp` with `AppLocalizations.delegate`
wired up, then assert the valid-submit and invalid-submit paths:

- Valid submit: enter a username of 4 or more characters, tap Submit, and assert the success `SnackBar` text appears
  (`find.text`) and no validator error is shown.
- Invalid submit: leave the field empty (or under 4 characters), tap Submit, and assert the localized validator error
  appears and the success `SnackBar` does not.

See the flutter-testing-apps skill for the Given/When/Then structure and the `pumpAndSettle` pattern.
