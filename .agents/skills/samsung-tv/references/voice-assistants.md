# Voice assistants

Read this before writing the script a voice phrase runs to open a TV app, or before giving that script several phrases on Alexa, Google Assistant or Assist. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were read in the page named next to them, or in the Home Assistant core source at tag 2026.10.4 under https://github.com/home-assistant/core/tree/2026.10.4/homeassistant/components: `alexa/__init__.py`, `alexa/entities.py`, `alexa/capabilities.py`, `google_assistant/helpers.py` and `google_assistant/trait.py`. The pages were read on 2026-11-06.

---

### The pattern

1. One Home Assistant script per app is the single source. It launches the app as [home-assistant-control.md](home-assistant-control.md#launch-an-app) shows.
2. Alternative names go on that script as entity aliases. The first alias is the main name Alexa gets, Google Assistant and Assist get every alias.
3. Alexa routines exist only to add more Alexa phrases, and each one runs the script.
4. One Assist automation with a sentence trigger, such as `(open|start|watch) {app} [on [the] TV]`, calls the matching script.

Name the script so it works as a spoken phrase without "open" or "launch", for example "Disney on TV", and use phrases such as "watch Disney". The reason is under [Open and launch](#open-and-launch).

---

### Alexa gets one name per script

`alexa: smart_home: entity_config` has no alias option. `ALEXA_ENTITY_SCHEMA` in `alexa/__init__.py` holds only `description`, `display_categories` and `name`. VERIFIED.

Home Assistant sends Alexa exactly one name, in `friendly_name` of `alexa/entities.py`: the `entity_config` `name`, else the first entry of the script's alias list, else the entity name. The alias list keeps "the order set by the user", and the entity's own name can be one of its entries. VERIFIED. So put the main spoken name first and leave `entity_config` `name` unset, or the aliases never reach Alexa.

---

### Alexa runs a script, not an app name

Alexa cannot open a TV app by its name through the media player. Home Assistant's Alexa integration has no `Launcher` or `AppController` capability, and `AlexaInputController` accepts only a fixed map of input names, so an app name in `source_list` is dropped. VERIFIED in `alexa/capabilities.py`. The Alexa page says "Alexa only supports the following input names", a list of names such as HDMI ports. VERIFIED.

Alexa lists Home Assistant scripts as scenes. The Alexa page at https://www.home-assistant.io/integrations/alexa.smart_home/, under Script: "Run script with script name, or "turn on" utterance", for example "Alexa, Party Time" or "Alexa, turn on Party Time". It goes on: "Deactivate a running script with "turn off" utterance". VERIFIED. So "turn off" on a script stops the script, it does not turn the TV off.

The same page lists words Alexa does not allow as names, among them alarm, music, timer and volume. VERIFIED. Check a script name against that list before exposing it.

---

### More Alexa phrases

Each extra Alexa phrase is an Alexa routine in the Alexa app, started by "When you say" with the phrase, whose action runs the script's scene. A routine takes several phrases. The limit, often quoted as seven, is UNVERIFIED.

---

### Open and launch

"Open" is the word Alexa uses to start a custom skill, https://developer.amazon.com/en-US/docs/alexa/custom-skills/understanding-how-users-invoke-custom-skills.html, VERIFIED. Video apps are started with "launch" through the `Alexa.Launcher` interface, https://developer.amazon.com/en-US/docs/alexa/device-apis/alexa-launcher.html, VERIFIED.

Whether a routine phrase that starts with "open" wins over a skill or an app launch is UNVERIFIED. Turning off other skills does not remove that built-in handling, INFERRED, medium confidence, because skill launch is part of Alexa itself rather than of one skill. So keep "open" and "launch" out of script names and routine phrases.

Samsung TVs from 2020 on have Alexa built in, and through the TV remote "Alexa, open [app name]" opens the app with no Home Assistant at all, https://www.samsung.com/us/support/answer/ANS10005261/, VERIFIED. Whether the same phrase works from a separate Echo through the SmartThings skill is UNVERIFIED.

---

### Google Assistant

`google_assistant: entity_config` supports `aliases`, "Aliases that can also be used to refer to this entity", https://www.home-assistant.io/integrations/google_assistant/, VERIFIED. `google_assistant/helpers.py` sends as nicknames the name, the `entity_config` aliases and the entity registry aliases. VERIFIED. So aliases set on the script reach Google with no extra configuration.

Scripts go to Google as the `SCENE` type with the Scene trait. Google's grammar example is "Activate midnight scene", https://developers.home.google.com/cloud-to-cloud/traits/scene, VERIFIED. So say "Hey Google, activate Disney on TV". Whether "turn on Disney on TV" or the bare name also works is UNVERIFIED.

Home Assistant has no `AppSelector` trait, VERIFIED in `google_assistant/trait.py`, so Google cannot open an app by name on the media player. Its `InputSelector` sends every `source_list` entry as an input, so on a TV that lists apps in `source_list`, "change input to Netflix" might work. INFERRED, medium confidence, from `trait.py`, untested.

Google Home household routines take several voice starters, https://support.google.com/googlehome/answer/7029585, VERIFIED. No official limit was found, UNVERIFIED.

---

### Assist

Assist matches the entity name and every alias, https://www.home-assistant.io/voice_control/aliases/, VERIFIED. So "turn on" with any alias of the script already works.

A conversation trigger takes a list of sentences with `[optional]` words, `(a|b)` alternatives and `{wildcards}`, whose text lands in `trigger.slots`, https://www.home-assistant.io/triggers/conversation/, VERIFIED. One automation catches every phrase pattern and calls the matching script. The automation as a whole is UNVERIFIED until it was run once:

```yaml
alias: "TV app by voice"
mode: single
triggers:
  - trigger: conversation
    command:
      - "(open|start|watch) {app} [on [the] TV]"
actions:
  - variables:
      scripts:
        netflix: script.<netflix-script>
        disney: script.<disney-script>
  - condition: template
    value_template: "{{ (trigger.slots.app | lower) in scripts }}"
  - action: script.turn_on
    target:
      entity_id: "{{ scripts[trigger.slots.app | lower] }}"
```

The map holds only the words the sentence trigger hears, the aliases stay on the scripts. The page warns "Wildcards match greedily". VERIFIED. Whether `[on [the] TV]` stays out of `{app}` is UNVERIFIED, so test a sentence with and without the ending once.
