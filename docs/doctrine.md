# personal-ops doctrine (v0)

Status: accepted
Date: 2026-09-21

## Why this exists

Hermes/Tom already tracks days, habits, and coaching. That is not the gap.
The gap is compounding **attempts** against yearly objectives: what we tried,
what evidence we have, what we learned, and the next real-world move.

Tracking is not the constraint. Overthinking, too many simultaneous objects,
and loops that close on research instead of contact with the world are.

## North star

Objectives are the North Star. Initiatives are the finite strategies. Moves
are the atomic execution unit. Evidence proves execution. Agents help
research, create, reason, and propose. Deterministic personal-ops code owns
state.

```text
Objective
  └── Initiative
        ├── Move
        ├── Move
        └── Move
```

Evidence attaches to a Move. Insight is a learning on the Initiative.
Harnesses are machinery, not domain objects.

## Progress, not activity

Personal Ops optimizes for **objective progress**, not system activity.

A week with 40 Moves and no dates or social interactions is worse than a week
with one Move that results in an actual date.

```text
10 property analyses ≠ progress
1 property viewing = potentially progress

20 volunteering searches ≠ progress
1 application / attendance = progress

5 training-plan analyses ≠ progress
completed training = progress
```

Research that does not produce a contracted output, and experiments that
never leave the notebook, are activity. They do not count as the initiative
advancing.

## Architectural split

| System | Owns | Must not |
|---|---|---|
| **fin-ops** | Financial truth and evidence | Coach, nag, or be duplicated here |
| **Tom-Hagen** | Conversation, memory, one-off execution | Be a second source of truth for objectives |
| **personal-ops** | Objective state, initiatives, moves, learnings | Become a notes folder or a habit tracker |

Tom may read personal-ops and speak it. Tom must not write SQLite or JSON.
personal-ops must still work if Telegram is ignored for a week.

## Domain objects

### Objective

Stable yearly objective. Human-owned. Agents cannot create or modify these.

v0 seed (titles only; live history stays in private runtime):

1. `relationship` — Build a relationship and move toward family
2. `physical` — Build physical confidence and health
3. `money-property` — Personal finances and property: track the money, grow it, buy a place
4. `discipline` — Build discipline, focus, and discomfort tolerance
5. `social-volunteer` — Live a more social, engaged, outdoor life (events, volunteering, outdoors)

Work/career is not an objective here. That is the area that already consumes
the days.

### Initiative

A finite effort intended to materially advance **one** objective.

Examples:

- Relationship → Improve online dating
- Relationship → Increase offline social opportunities
- Money/property → Find a property to buy
- Physical → Improve triathlon performance

Status: `active` | `paused` | `completed` | `killed`.

An initiative is **advancing** only when a non-research Move has closed with
execution evidence. Research-only work cannot mark it advancing.

### Move

The smallest executable unit that can change real-world state.

`kind` is a type, not a layer: `action` | `experiment` | `research`.

Examples: publish Hinge profile v1; replace photo #2; register for event X;
contact an estate agent; complete a specific training session.

## WIP constraint

This must not become another life backlog.

v0 caps:

- At most **3** `active` initiatives. **`paused` does not count as WIP.**
  Pause exists so history can wait without being killed to free a slot.
- At most **1** unclosed `experiment` Move per initiative
- Creating past the cap is rejected. Complete, kill, or pause. No override
  flag in v0.

The engine prefers finishing or killing existing initiatives over creating
new ones. Pause is the way to park work without erasing it. Agents must do
the same.

## Experiment closure (dating slice)

Research and profile generation are not success.

An experiment Move is closed only when it has reached the real world:

```text
Hypothesis → Baseline+variant recorded → Prepare → Deploy → Observe → Evidence → Decide → Learning
```

Baseline must be captured **before** deploy, even when evidence will be weak:

```text
baseline:
  profile_version: hinge-v0
  observation_window: ...
  metrics: ...
variant:
  profile_version: hinge-v1
decision: keep | revert | iterate
causal_confidence: weak
```

Without that, "variant B worked better" has no record of what B was better
than.

- **Prepare** (generate/select photo set B) does not close the experiment.
- **Deploy** (publish B on the platform) is execution; the experiment stays open.
- **Observe** for a predefined window or until captured evidence exists.
- **Decide** `keep` | `revert` | `iterate`.
- **Learning** is stored on the initiative, pointing at the move.

Sequential experiments on platforms without clean A/B or impressions must
record `causal_confidence: weak` rather than fake statistical cleanliness.

The first live profile is an **action**, not an experiment. There is nothing
to experiment against until a baseline is deployed in the real world.

### Dating funnel

Likes/matches are diagnostic. They must not be treated as the objective.

Primary downstream outcomes, in order:

```text
quality conversation
  → moved off app / meaningful interaction
  → date arranged
  → date happened
```

An initiative can be advancing (we published, observed, decided) and still
have zero dates. That is honest. Vanity metrics must not be optimized at the
expense of the relationship objective.

### Research Moves

Allowed when research is actually required. It must not be open-ended.

```text
question: "Which 6 photos should form Hinge baseline v1?"
output: ranked_selection
done_when: baseline photo set is chosen
```

Closing a research Move requires producing that output. It must never set
`advancing`. `"Research dating best practices"` with no contracted artifact
is rejected at create.

## State, evidence, privacy

The Git repository is **not** the runtime database. The GitHub remote is
public. Even if it later becomes private, operational data must not enter
Git history.

**Never in Git:**

- dating photos, profiles, matches, conversations
- calendar details, emails, contacts
- private financial state
- raw health/activity data
- credentials/tokens
- detailed objective history

**Git contains:** code, schemas, harnesses, prompts, migrations, tests,
sanitized examples, methodology.

**Runtime (default `~/.personal-ops/`):**

```text
~/.personal-ops/
├── personal-ops.db
├── artifacts/
├── cache/
└── config/
```

Override with `PERSONAL_OPS_HOME` or `--home`. The directory must live
outside this repository.

### Mutation path

```text
agent proposes
      ↓
personal-ops domain API validates
      ↓
deterministic code writes state
```

Agents must not edit SQLite or JSON state directly.

### Evidence records

Typed rows attached to a Move:

- `source`
- `timestamp`
- `move_id`
- `evidence_type`
- `external_reference`
- `metadata`
- `artifact_reference`

Reference an external source of truth instead of duplicating it:

- **fin-ops** for financial evidence
- **calendar** for scheduled/attended events
- dating platforms via manual capture/import until a real adapter exists
- **manual** confirmation when nothing machine-verifiable exists

`source=agent` is not evidence of execution.

## What v0 is not

- Not a habit tracker, fasting tracker, or work tracker (those stay in Tom)
- Not a second finance ledger
- Not an orchestrator of Cursor/Codex/ChatGPT/Tom
- Not a generic plugin engine
- Not a notes wiki

Build the three objects, the state boundary, and one end-to-end dating
initiative. Add abstractions only when that slice proves they are missing.

## Alternatives rejected

- Seven-layer tree (Objective → Initiative → Project → Experiment → Task →
  Evidence → Insight): classification becomes the product; this is the
  overthinking failure mode.
- Sheets-plus-cron as system of record: already failed as a closed loop.
- Agents writing files/SQLite: non-deterministic corruption, undebuggable
  history, easy to leak secrets into Git.
- Runtime data in the repo: public remote + irreversible Git history.
