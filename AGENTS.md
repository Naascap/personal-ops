# AGENTS.md

You are operating in `personal-ops`. Read `docs/doctrine.md` before proposing
any state change.

## What this is

Objective-aware execution store. Three objects: Objective → Initiative → Move.
Evidence hangs off a Move. Learnings hang off an Initiative. You propose;
the `personal-ops` CLI writes.

## Load this context

1. `docs/doctrine.md` — method
2. `docs/spec.md` — v0 slice
3. `personal-ops status` — live state (never invent it)
4. The **relevant** objective only. Do not dump all five into a prompt.

## Write path

```text
you propose → CLI/domain API validates → SQLite write
```

Never open `personal-ops.db`. Never edit JSON under `~/.personal-ops/`.
Never put runtime files in this repository.

## WIP

Prefer finishing or pausing an existing initiative over creating one.
Creation is rejected at 3 **active** initiatives. Paused does not count.
One unclosed experiment per initiative. There is no force flag.

## Dating slice

The first profile is an action (baseline in the real world), not an
experiment. Experiments record baseline and variant before deploy.

An experiment is not closed when a profile or photo set is generated.
It is closed when: deployed, observed, evidence captured, decision
recorded (`keep` | `revert` | `iterate`), learning stored.

Likes and matches are diagnostic. Optimize for quality conversation →
moved off app → date arranged → date happened.

Research Moves need `question`, `output`, and `done_when`, plus the
produced output on close. They cannot mark the initiative advancing.

If the platform has no impressions or A/B, say so and keep
`causal_confidence` weak.

Optimize for objective progress, not system activity.

## Never

- Track work, habits, or fasting here
- Duplicate fin-ops numbers; reference fin-ops
- Commit photos, profiles, messages, tokens, or live history
- Create new domain layers (Project, Task, Experiment-as-object)
- Build a generic harness engine because the next initiative might need it
