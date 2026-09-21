# Dating slice (v0)

Not a photo generator. Not a pickup optimizer. This folder documents the
operator loop that the CLI already enforces.

The first live profile is an **action**, not an experiment. You need a
baseline deployed in reality before you have anything to experiment against.

## First initiative

```text
Objective:  relationship
Initiative: Improve online dating
```

### Move 001 — action

Create and deploy a strong baseline Hinge profile.

Done when:

- profile is live
- selected photos are deployed
- prompts are deployed
- configuration/version is captured privately (not in Git)
- deployment timestamp is recorded

### Move 002 — action

Observe the baseline for N days / sufficient activity. Capture whatever
evidence is realistically available. Likes/matches are diagnostic.

### Move 003 — experiment

Test **one** profile change against the recorded baseline. Set frames
before deploy. Close only after observe + evidence + keep/revert/iterate.

## Loop after that

1. `personal-ops status` — read, do not invent.
2. If an experiment is open, finish it. Do not start another.
3. Research needs a question, output contract, and done_when. It cannot
   mark the initiative advancing.
4. `experiment-frames` before `move-deploy`.
5. Funnel: `quality_conversation` → `moved_off_app` → `date_arranged`
   → `date_happened`.
6. Sequential tests without impressions stay `causal_confidence=weak`.

## Allowed evidence types (this slice)

`photo_published`, `platform_like`, `platform_match`,
`quality_conversation`, `moved_off_app`, `date_arranged`,
`date_happened`, `manual_confirmation`.

## Out of scope

Tom's Adlerian activation coaching, scraping dating apps, storing photos
in Git, treating profile generation as a closed experiment, Hinge/Tom/MCP
integrations, a generic harness framework.
