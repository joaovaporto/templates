# templates

Project templates I reuse when starting new work. Each subdirectory is a self-contained
starting point — copy it out, rename, and go.

## Available templates

| Template | For | Highlights |
|----------|-----|-----------|
| [`python-hexagonal/`](python-hexagonal/) | Python projects | Hexagonal architecture with the dependency rule **machine-enforced** (import-linter + in-suite architecture tests), a typed composition root for DI, and clean `uv` dependency tiers (core / extras / dev). Ships a `CLAUDE.md` aligned with my global conventions. |

## Using a template

```bash
cp -r python-hexagonal ../my-new-project
cd ../my-new-project
# rename the placeholder package `app` — see the template's CLAUDE.md
uv sync
make check
```

Each template carries its own `README.md` (how it is laid out and why) and `CLAUDE.md`
(the rules an AI assistant must follow inside it).
