# personal-ops

Objective-aware execution store for one life. Yearly objectives stay stable.
Initiatives are finite strategies. Moves are the unit that must change the
real world. Agents propose; deterministic code writes.

Tom (Hermes) remains the conversational surface. fin-ops remains financial
truth. This repository is not a habit tracker and not a notes folder.

Doctrine: [`docs/doctrine.md`](docs/doctrine.md).
Agent rules: [`AGENTS.md`](AGENTS.md).
v0 spec: [`docs/spec.md`](docs/spec.md).

## v0 slice

One dating initiative under the relationship objective, including experiment
closure that cannot succeed on research or unpublished profile work.

## Runtime

State lives **outside Git**, default `~/.personal-ops/`:

```text
~/.personal-ops/
├── personal-ops.db
├── artifacts/
├── cache/
└── config/
```

The public repo ships `examples/objectives.example.yaml`, not live config.

```powershell
cd C:\dev\personal-ops
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
personal-ops init
personal-ops seed-objectives examples/objectives.example.yaml
personal-ops status
```

Override the home directory with `--home` or `PERSONAL_OPS_HOME`.
