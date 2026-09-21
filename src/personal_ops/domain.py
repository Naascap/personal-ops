from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ObjectiveSlug = str
InitiativeStatus = Literal["active", "paused", "completed", "killed"]
MoveKind = Literal["action", "experiment", "research"]
MoveStatus = Literal["open", "prepared", "deployed", "observing", "closed"]
Decision = Literal["keep", "revert", "iterate"]

MOVE_KINDS = ("action", "experiment", "research")
DECISIONS = ("keep", "revert", "iterate")
SOURCES = ("manual", "hinge", "calendar", "fin-ops", "file")
EVIDENCE_TYPES = (
    "photo_published",
    "platform_like",
    "platform_match",
    "quality_conversation",
    "moved_off_app",
    "date_arranged",
    "date_happened",
    "manual_confirmation",
)
FUNNEL_ORDER = (
    "quality_conversation",
    "moved_off_app",
    "date_arranged",
    "date_happened",
)
DIAGNOSTIC_TYPES = ("platform_like", "platform_match")


@dataclass(frozen=True)
class Objective:
    id: str
    slug: str
    year: int
    title: str
    description: str
    constraints: list[str]


@dataclass(frozen=True)
class Initiative:
    id: str
    objective_id: str
    objective_slug: str
    title: str
    status: str
    advancing: bool
    created_at: str
    closed_at: str | None
    close_reason: str | None


@dataclass(frozen=True)
class Move:
    id: str
    initiative_id: str
    kind: str
    title: str
    status: str
    hypothesis: str | None
    question: str | None
    output_contract: str | None
    done_when: str | None
    output_result: str | None
    baseline: dict[str, Any] | None
    variant: dict[str, Any] | None
    causal_confidence: str | None
    decision: str | None
    created_at: str
    prepared_at: str | None
    deployed_at: str | None
    observing_until: str | None
    closed_at: str | None


@dataclass(frozen=True)
class Evidence:
    id: str
    move_id: str
    source: str
    recorded_at: str
    evidence_type: str
    external_reference: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    artifact_reference: str | None = None


@dataclass(frozen=True)
class Learning:
    id: str
    initiative_id: str
    move_id: str | None
    body: str
    created_at: str
