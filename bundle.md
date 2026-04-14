---
bundle:
  name: reality-check
  version: 0.1.0
  description: Verifies that what was built actually matches what the user intended

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: reality-check:behaviors/reality-check
---
