---
bundle:
  name: dot-docs
  version: 1.0.0
  description: DOT graph documentation generation recipes for Amplifier repositories

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-dot-graph@main
  - bundle: dot-docs:behaviors/dot-docs
---

# DOT Docs

@dot-docs:context/dot-docs-awareness.md
