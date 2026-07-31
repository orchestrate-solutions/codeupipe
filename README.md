# codeupipe — public static site

Live at **https://orchestrate.solutions/codeupipe/** (also reachable at **https://orchestrate.solutions/cup/**).

This repo is the built static site for [codeupipe](https://orchestrate.solutions/codeupipe/) — a composable **Payload → Filter → Pipeline** framework. It is a publish target, not the source of truth. The source lives in the private `orchestrate-solutions/cup` repo and is mirrored here on release.

## What's here

- `index.html`, `styles.css`, `app.js` — the marketing / agent-entrypoint site
- `agent-context.json`, `AGENTS.md` — machine-readable brief for AI agents
- `v1/` — versioned agent context and manifests
- `docs/` — concept docs (Payload, Filter, Pipeline, Valve, Tap, Hook, State)
- `runtime/`, `cup-ui/` — runtime bundles and UI assets

## Feeding this to an agent

Point your agent at either of:

- https://orchestrate.solutions/cup/agent-context.json
- https://orchestrate.solutions/cup/AGENTS.md

## License

Source and site are licensed under [PolyForm Noncommercial 1.0.0](./LICENSE). Commercial use requires a separate license — see the main project for details.

## Links

- Project site: https://orchestrate.solutions/codeupipe/
- Docs: https://orchestrate.solutions/cup/docs/
- Framework (Python): `pip install codeupipe`
- [contact@orchestrate.solutions](mailto:contact@orchestrate.solutions)
