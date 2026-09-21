# Spec: personal-ops v0 (dating slice)

## Objective

A single-user CLI that stores yearly objectives, finite initiatives, and
real-world Moves in private SQLite, with evidence and learnings. The first
vertical slice is an online-dating initiative under the relationship
objective.

**User:** Hassen, operating locally (Windows) or later on the Hetzner host.
**Success:** the dating experiment protocol can be executed end-to-end through
the domain API/CLI, research cannot fake progress, and no operational data
lands in Git.

## Tech stack

- Python >= 3.11
- stdlib `sqlite3` (WAL)
- PyYAML only to seed the example objectives file
- pytest
- No web server, ORM, dashboard, or LLM in the write path

## Commands

```text
python -m pip install -e ".[dev]"
python -m pytest
personal-ops init
personal-ops seed-objectives examples/objectives.example.yaml
personal-ops status
personal-ops initiative-create --objective relationship --title "Improve online dating"
personal-ops move-create --initiative ID --kind action --title "Deploy baseline Hinge profile"
personal-ops move-create --initiative ID --kind research --title "..." --question "..." --output ranked_selection --done-when "..."
personal-ops move-create --initiative ID --kind experiment --title "..." --hypothesis "..."
personal-ops experiment-frames ID --baseline '{...}' --variant '{...}'
personal-ops move-prepare ID
personal-ops move-deploy ID [--until UTC]
personal-ops evidence-add --move ID --type TYPE --source SOURCE
personal-ops move-decide ID --decision keep|revert|iterate --learning "..."
personal-ops move-close ID --output "..."
```

`--home` or `PERSONAL_OPS_HOME` selects the runtime directory.

## Project structure

```text
docs/           doctrine + this spec
examples/       sanitized yaml/json only
harnesses/      dating operator notes, not a framework
src/personal_ops/
tests/
```

Runtime lives in `~/.personal-ops/` (never in this tree).

## Code style

Named functions, dataclasses, explicit error codes. One mutation API
(`PersonalOps`). CLI is a thin wrapper. Match fin-ops tone: deterministic,
stdlib-heavy, runtime-outside-repo.

```python
ops = PersonalOps.init(home)
ops.seed_objectives(example_yaml)
initv = ops.create_initiative("relationship", "Improve online dating")
move = ops.create_move(initv.id, kind="experiment", title="Publish photo set B",
                       hypothesis="Set B yields more quality conversations than A")
ops.set_experiment_frames(move.id, baseline={"profile_version": "hinge-v0"},
                          variant={"profile_version": "hinge-v1"})
ops.prepare_move(move.id)
ops.deploy_move(move.id)
ops.add_evidence(move.id, evidence_type="photo_published", source="manual")
ops.decide_move(move.id, decision="iterate", learning="...")
```

## Testing strategy

pytest, tests next to behaviour in `tests/`. Prefer the domain API over CLI
except one smoke test. Use temp `--home`. Synthetic dating data only
(`photo-set-b`, `platform-x`). No real names, photos, or conversations.

Must prove: WIP cap on **active** only (paused excluded), experiment
closure, research contract + output, baseline required before experiment
deploy, funnel types separate from likes/matches, init refuses a path
inside the Git repo.

## Boundaries

- **Always:** write through `PersonalOps`; keep runtime outside Git; run pytest
  before considering a slice done.
- **Ask first:** new evidence types, raising the WIP cap, adding dependencies,
  wiring Tom or fin-ops, storing or copying real artifacts.
- **Never:** commit `~/.personal-ops` contents, dating photos, tokens, live
  objective history; let agents execute raw SQL; treat likes/matches as
  success; close an experiment at prepare; mark an initiative advancing from
  research alone.

## Success criteria

- [ ] Three domain objects only: Objective, Initiative, Move
- [ ] Agents cannot create or modify objectives
- [ ] Active initiatives capped at 3; paused excluded from WIP
- [ ] One unclosed experiment per initiative
- [ ] Experiment requires hypothesis, baseline+variant, deploy, evidence, decide
- [ ] Research requires question/output/done_when and a produced output; close leaves `advancing` false
- [ ] Status lists funnel outcomes separately from platform likes/matches
- [ ] Sequential experiments default `causal_confidence=weak`
- [ ] Default home is `~/.personal-ops`; init fails inside this repo
- [ ] Example yaml contains no live evidence

## Open questions

- When Tom should read `status` (not in v0)
- Whether Hetzner uses `~/.personal-ops` or `/var/lib/personal-ops`
- Property/events slices: add evidence types only when those initiatives exist
