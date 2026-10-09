# codeupipe

Core, Compile and Config. Standard library only.

- **Core** (`codeupipe`, `codeupipe.core`): Payload, Filter, Pipeline, Valve, Tap, Hook, State.
- **Compile** (`python -m codeupipe.lower`): export a pipeline as plain Python with no framework import.
- **Config** (`codeupipe.config`): `cup.config.json`, read by Compile and by `codeupipe-lint`.

The linter is a separate package, `codeupipe-lint`. Documentation is in the
repository README.
