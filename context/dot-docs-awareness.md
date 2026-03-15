# DOT Docs

This bundle provides recipes for generating DOT graph documentation from Amplifier repositories.

## Available Recipes

Invoke these via the `recipes` tool:

- **dotfiles-discovery** (`dot-docs:recipes/dotfiles-discovery`) — Orchestrates the full discovery pipeline: scans repos, determines investigation tier, dispatches Parallax Discovery, synthesizes DOT output
- **dotfiles-prescan** (`dot-docs:recipes/dotfiles-prescan`) — Pre-scans repository architecture to determine which investigation topics are relevant
- **dotfiles-synthesis** (`dot-docs:recipes/dotfiles-synthesis`) — Synthesizes raw DOT investigation output from multiple agents into polished, canonical graph files with quality gate review loop

## When to Use

When asked to generate architectural documentation, create DOT graph diagrams, or document a repository's structure, invoke the dotfiles-discovery recipe to begin the pipeline. The recipes orchestrate multi-agent investigation — do not attempt to synthesize graphs manually.
