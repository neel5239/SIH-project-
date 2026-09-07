# Question Flows

**The clinical logic of this product, as data.** A clinician can read these files; the team can
change the interview without touching Python.

```
flows/
├── chest_pain.yaml     ★ the hero flow — build this first and perfect it
├── fever.yaml
├── cough.yaml
├── abdominal_pain.yaml
├── headache.yaml
├── general.yaml        past illness · medicines · allergies · family · lifestyle
└── red_flags.yaml      ★ deterministic emergency rules
```

## Shape of a question

```yaml
- id: pain.radiation
  text: "Does the pain spread anywhere?"
  type: choose_many
  options:
    - { key: left_arm, label: "Left arm", icon: arm-left }
    - { key: jaw,      label: "Jaw",      icon: jaw }
    - { key: none,     label: "Nowhere",  icon: none }
  ask_if:
    - { answer: complaint.type, equals: pain }
  emergency_rules: [CP-001]
```

## Shape of an emergency rule

```yaml
- id: CP-001
  name: "Chest pain with breathlessness"
  all_of:
    - { answer: pain.site, in: [chest, centre_chest] }
    - any_of:
        - { answer: pain.radiation, in: [left_arm, jaw] }
        - { answer: associated, contains: breathlessness }
  action: flag_and_notify
  message: "Your symptoms may need urgent attention. Please go to the triage desk."
```

- [ ] **Five flows built and perfected.** Five good beats forty half-built.
- [ ] Every closed question has icon-able options — a non-reader must be able to tap
- [ ] `ask_if` is the branching. No question order is hardcoded in Python.
- [ ] **The emergency message never names a disease.** It describes the pattern and points at triage.
- [ ] **Get a doctor to read these files.** One hour, enormous credibility.
