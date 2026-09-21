from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .db import connect
from .domain import (
    DECISIONS,
    DIAGNOSTIC_TYPES,
    EVIDENCE_TYPES,
    FUNNEL_ORDER,
    MOVE_KINDS,
    SOURCES,
    Evidence,
    Initiative,
    Learning,
    Move,
    Objective,
)
from .errors import DomainError
from .paths import require_runtime_outside_repo

MAX_ACTIVE_INITIATIVES = 3


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _id() -> str:
    return str(uuid.uuid4())


def _json_list(value: Any) -> list[str]:
    if not value:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DomainError("INVALID_CONSTRAINTS", "constraints must be a list of strings")
    return value


def _require_text(value: str | None, code: str, message: str) -> str:
    text = (value or "").strip()
    if not text:
        raise DomainError(code, message)
    return text


def _require_object(value: dict[str, Any] | None, code: str, message: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise DomainError(code, message)
    return value


def _parse_json_object(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    return json.loads(raw)


class PersonalOps:
    def __init__(self, home: Path, conn: sqlite3.Connection) -> None:
        self.home = home
        self._conn = conn

    @classmethod
    def init(cls, home: Path, *, start: Path | None = None) -> PersonalOps:
        home = Path(home).expanduser()
        require_runtime_outside_repo(home, start=start)
        (home / "artifacts").mkdir(parents=True, exist_ok=True)
        (home / "cache").mkdir(exist_ok=True)
        (home / "config").mkdir(exist_ok=True)
        conn = connect(home / "personal-ops.db")
        return cls(home, conn)

    def seed_objectives(self, path: Path) -> list[Objective]:
        existing = self._conn.execute("SELECT COUNT(*) AS n FROM objectives").fetchone()["n"]
        if existing:
            raise DomainError(
                "OBJECTIVES_ALREADY_SEEDED",
                "objectives are human-owned and already present; they cannot be re-seeded",
            )
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or "objectives" not in payload:
            raise DomainError("INVALID_SEED", "seed file must contain an objectives list")
        year = int(payload.get("year") or 0)
        created = _now()
        for raw in payload["objectives"]:
            slug = raw["slug"]
            self._conn.execute(
                """
                INSERT INTO objectives (id, slug, year, title, description, constraints_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _id(),
                    slug,
                    year,
                    raw["title"],
                    (raw.get("description") or "").strip(),
                    json.dumps(_json_list(raw.get("constraints")), ensure_ascii=True),
                    created,
                ),
            )
        self._conn.commit()
        return self.list_objectives()

    def list_objectives(self) -> list[Objective]:
        rows = self._conn.execute(
            "SELECT * FROM objectives ORDER BY rowid"
        ).fetchall()
        return [self._objective(row) for row in rows]

    def create_initiative(self, objective_slug: str, title: str) -> Initiative:
        title = title.strip()
        if not title:
            raise DomainError("INVALID_TITLE", "initiative title is required")
        objective = self._objective_by_slug(objective_slug)
        self._require_wip_slot()
        now = _now()
        ident = _id()
        self._conn.execute(
            """
            INSERT INTO initiatives (id, objective_id, title, status, advancing, created_at)
            VALUES (?, ?, ?, 'active', 0, ?)
            """,
            (ident, objective.id, title, now),
        )
        self._conn.commit()
        return self.get_initiative(ident)

    def get_initiative(self, initiative_id: str) -> Initiative:
        row = self._conn.execute(
            """
            SELECT i.*, o.slug AS objective_slug
            FROM initiatives i
            JOIN objectives o ON o.id = i.objective_id
            WHERE i.id = ?
            """,
            (initiative_id,),
        ).fetchone()
        if row is None:
            raise DomainError("NOT_FOUND", f"initiative {initiative_id} not found")
        return self._initiative(row)

    def list_initiatives(self, status: str | None = None) -> list[Initiative]:
        if status:
            rows = self._conn.execute(
                """
                SELECT i.*, o.slug AS objective_slug
                FROM initiatives i
                JOIN objectives o ON o.id = i.objective_id
                WHERE i.status = ?
                ORDER BY i.created_at
                """,
                (status,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT i.*, o.slug AS objective_slug
                FROM initiatives i
                JOIN objectives o ON o.id = i.objective_id
                ORDER BY i.created_at
                """
            ).fetchall()
        return [self._initiative(row) for row in rows]

    def kill_initiative(self, initiative_id: str, reason: str) -> Initiative:
        return self._close_initiative(initiative_id, "killed", reason)

    def complete_initiative(self, initiative_id: str, reason: str = "") -> Initiative:
        return self._close_initiative(initiative_id, "completed", reason)

    def pause_initiative(self, initiative_id: str, reason: str = "") -> Initiative:
        initiative = self.get_initiative(initiative_id)
        if initiative.status != "active":
            raise DomainError("INVALID_STATUS", f"cannot pause a {initiative.status} initiative")
        self._conn.execute(
            "UPDATE initiatives SET status = 'paused', close_reason = ? WHERE id = ?",
            (reason.strip() or None, initiative_id),
        )
        self._conn.commit()
        return self.get_initiative(initiative_id)

    def resume_initiative(self, initiative_id: str) -> Initiative:
        initiative = self.get_initiative(initiative_id)
        if initiative.status != "paused":
            raise DomainError("INVALID_STATUS", f"cannot resume a {initiative.status} initiative")
        self._require_wip_slot()
        self._conn.execute(
            "UPDATE initiatives SET status = 'active', close_reason = NULL WHERE id = ?",
            (initiative_id,),
        )
        self._conn.commit()
        return self.get_initiative(initiative_id)

    def create_move(
        self,
        initiative_id: str,
        *,
        kind: str,
        title: str,
        hypothesis: str | None = None,
        question: str | None = None,
        output: str | None = None,
        done_when: str | None = None,
    ) -> Move:
        if kind not in MOVE_KINDS:
            raise DomainError("INVALID_KIND", f"kind must be one of {MOVE_KINDS}")
        title = title.strip()
        if not title:
            raise DomainError("INVALID_TITLE", "move title is required")
        initiative = self.get_initiative(initiative_id)
        if initiative.status != "active":
            raise DomainError("INITIATIVE_NOT_ACTIVE", "moves can only be added to an active initiative")
        hypothesis_text = (hypothesis or "").strip() or None
        question_text = None
        output_contract = None
        done_when_text = None
        if kind == "experiment":
            hypothesis_text = _require_text(
                hypothesis, "HYPOTHESIS_REQUIRED", "experiment moves require a hypothesis"
            )
            open_exp = self._conn.execute(
                """
                SELECT COUNT(*) AS n FROM moves
                WHERE initiative_id = ? AND kind = 'experiment' AND status != 'closed'
                """,
                (initiative_id,),
            ).fetchone()["n"]
            if open_exp:
                raise DomainError(
                    "OPEN_EXPERIMENT_EXISTS",
                    "finish or kill the open experiment on this initiative first",
                )
        if kind == "research":
            question_text = _require_text(
                question,
                "RESEARCH_CONTRACT_REQUIRED",
                "research requires a question, output contract, and done_when",
            )
            output_contract = _require_text(
                output,
                "RESEARCH_CONTRACT_REQUIRED",
                "research requires a question, output contract, and done_when",
            )
            done_when_text = _require_text(
                done_when,
                "RESEARCH_CONTRACT_REQUIRED",
                "research requires a question, output contract, and done_when",
            )
        now = _now()
        ident = _id()
        confidence = "weak" if kind == "experiment" else None
        self._conn.execute(
            """
            INSERT INTO moves (
              id, initiative_id, kind, title, status, hypothesis,
              question, output_contract, done_when, causal_confidence, created_at
            ) VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
            """,
            (
                ident,
                initiative_id,
                kind,
                title,
                hypothesis_text,
                question_text,
                output_contract,
                done_when_text,
                confidence,
                now,
            ),
        )
        self._conn.commit()
        return self.get_move(ident)

    def list_moves(self, initiative_id: str) -> list[Move]:
        self.get_initiative(initiative_id)
        rows = self._conn.execute(
            "SELECT * FROM moves WHERE initiative_id = ? ORDER BY created_at",
            (initiative_id,),
        ).fetchall()
        return [self._move(row) for row in rows]

    def get_move(self, move_id: str) -> Move:
        row = self._conn.execute("SELECT * FROM moves WHERE id = ?", (move_id,)).fetchone()
        if row is None:
            raise DomainError("NOT_FOUND", f"move {move_id} not found")
        return self._move(row)

    def prepare_move(self, move_id: str) -> Move:
        move = self.get_move(move_id)
        if move.kind != "experiment":
            raise DomainError("NOT_AN_EXPERIMENT", "prepare applies to experiment moves")
        if move.status != "open":
            raise DomainError("INVALID_STATUS", f"cannot prepare a move in status {move.status}")
        now = _now()
        self._conn.execute(
            "UPDATE moves SET status = 'prepared', prepared_at = ? WHERE id = ?",
            (now, move_id),
        )
        self._conn.commit()
        return self.get_move(move_id)

    def set_experiment_frames(
        self,
        move_id: str,
        *,
        baseline: dict[str, Any],
        variant: dict[str, Any],
    ) -> Move:
        move = self.get_move(move_id)
        if move.kind != "experiment":
            raise DomainError("NOT_AN_EXPERIMENT", "baseline/variant frames apply to experiments")
        if move.status not in ("open", "prepared"):
            raise DomainError("INVALID_STATUS", f"cannot set frames on a {move.status} experiment")
        baseline = _require_object(
            baseline, "BASELINE_REQUIRED", "record what the variant will be compared against"
        )
        variant = _require_object(
            variant, "VARIANT_REQUIRED", "record what is changing versus the baseline"
        )
        self._conn.execute(
            "UPDATE moves SET baseline_json = ?, variant_json = ? WHERE id = ?",
            (
                json.dumps(baseline, ensure_ascii=True, sort_keys=True),
                json.dumps(variant, ensure_ascii=True, sort_keys=True),
                move_id,
            ),
        )
        self._conn.commit()
        return self.get_move(move_id)

    def deploy_move(self, move_id: str, *, observe_until: str | None = None) -> Move:
        move = self.get_move(move_id)
        if move.kind != "experiment" and move.kind != "action":
            raise DomainError("CANNOT_DEPLOY", "research moves are not deployed")
        if move.kind == "experiment" and move.status not in ("open", "prepared"):
            raise DomainError("INVALID_STATUS", f"cannot deploy a move in status {move.status}")
        if move.kind == "experiment" and (not move.baseline or not move.variant):
            raise DomainError(
                "BASELINE_REQUIRED",
                "record baseline and variant before deploying an experiment",
            )
        if move.kind == "action" and move.status != "open":
            raise DomainError("INVALID_STATUS", f"cannot deploy a move in status {move.status}")
        now = _now()
        status = "observing" if move.kind == "experiment" else "deployed"
        self._conn.execute(
            """
            UPDATE moves
            SET status = ?, deployed_at = ?, observing_until = ?
            WHERE id = ?
            """,
            (status, now, observe_until, move_id),
        )
        self._conn.commit()
        return self.get_move(move_id)

    def add_evidence(
        self,
        move_id: str,
        *,
        evidence_type: str,
        source: str,
        external_reference: str | None = None,
        metadata: dict[str, Any] | None = None,
        artifact_reference: str | None = None,
    ) -> Evidence:
        self.get_move(move_id)
        if source not in SOURCES:
            raise DomainError(
                "INVALID_SOURCE",
                f"source must be one of {SOURCES}; agent assertions are not execution evidence",
            )
        if evidence_type not in EVIDENCE_TYPES:
            raise DomainError("INVALID_EVIDENCE_TYPE", f"type must be one of {EVIDENCE_TYPES}")
        now = _now()
        ident = _id()
        payload = metadata or {}
        if not isinstance(payload, dict):
            raise DomainError("INVALID_METADATA", "metadata must be an object")
        self._conn.execute(
            """
            INSERT INTO evidence (
              id, move_id, source, recorded_at, evidence_type,
              external_reference, metadata_json, artifact_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ident,
                move_id,
                source,
                now,
                evidence_type,
                external_reference,
                json.dumps(payload, ensure_ascii=True, sort_keys=True),
                artifact_reference,
                now,
            ),
        )
        self._conn.commit()
        return self._evidence(
            self._conn.execute("SELECT * FROM evidence WHERE id = ?", (ident,)).fetchone()
        )

    def decide_move(
        self,
        move_id: str,
        *,
        decision: str,
        learning: str,
        causal_confidence: str = "weak",
    ) -> Move:
        move = self.get_move(move_id)
        if move.kind != "experiment":
            raise DomainError("NOT_AN_EXPERIMENT", "decide applies to experiment moves")
        if decision not in DECISIONS:
            raise DomainError("INVALID_DECISION", f"decision must be one of {DECISIONS}")
        learning = learning.strip()
        if not learning:
            raise DomainError("LEARNING_REQUIRED", "a closed experiment must record a learning")
        if move.status not in ("deployed", "observing"):
            raise DomainError(
                "EXPERIMENT_NOT_DEPLOYED",
                "publish the change in the real world before deciding; prepare is not closure",
            )
        if move.observing_until and move.observing_until > _now():
            raise DomainError(
                "EXPERIMENT_STILL_OBSERVING",
                f"observation window runs until {move.observing_until}",
            )
        count = self._conn.execute(
            "SELECT COUNT(*) AS n FROM evidence WHERE move_id = ?", (move_id,)
        ).fetchone()["n"]
        if not count:
            raise DomainError(
                "EXPERIMENT_NO_EVIDENCE",
                "capture at least one evidence record before deciding",
            )
        now = _now()
        self._conn.execute(
            """
            UPDATE moves
            SET status = 'closed', decision = ?, causal_confidence = ?, closed_at = ?
            WHERE id = ?
            """,
            (decision, causal_confidence, now, move_id),
        )
        self._conn.execute(
            """
            INSERT INTO learnings (id, initiative_id, move_id, body, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (_id(), move.initiative_id, move_id, learning, now),
        )
        self._conn.execute(
            "UPDATE initiatives SET advancing = 1 WHERE id = ?",
            (move.initiative_id,),
        )
        self._conn.commit()
        return self.get_move(move_id)

    def close_move(
        self,
        move_id: str,
        *,
        learning: str | None = None,
        output_result: str | None = None,
    ) -> Move:
        move = self.get_move(move_id)
        if move.kind == "experiment":
            raise DomainError(
                "USE_DECIDE",
                "experiments close via decide after deploy, evidence, and a keep/revert/iterate call",
            )
        if move.status == "closed":
            raise DomainError("ALREADY_CLOSED", "move is already closed")
        now = _now()
        result = None
        if move.kind == "research":
            result = _require_text(
                output_result,
                "RESEARCH_OUTPUT_REQUIRED",
                "research closes only when it produces the contracted output",
            )
            self._conn.execute(
                "UPDATE moves SET output_result = ? WHERE id = ?",
                (result, move_id),
            )
        if move.kind == "action":
            if move.status == "open":
                raise DomainError(
                    "ACTION_NOT_EXECUTED",
                    "deploy the action (real-world execution) before closing",
                )
            count = self._conn.execute(
                "SELECT COUNT(*) AS n FROM evidence WHERE move_id = ?", (move_id,)
            ).fetchone()["n"]
            if not count:
                raise DomainError(
                    "ACTION_NO_EVIDENCE",
                    "add execution evidence or a manual_confirmation before closing an action",
                )
            self._conn.execute(
                "UPDATE initiatives SET advancing = 1 WHERE id = ?",
                (move.initiative_id,),
            )
        self._conn.execute(
            "UPDATE moves SET status = 'closed', closed_at = ? WHERE id = ?",
            (now, move_id),
        )
        if learning and learning.strip():
            self._conn.execute(
                """
                INSERT INTO learnings (id, initiative_id, move_id, body, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (_id(), move.initiative_id, move_id, learning.strip(), now),
            )
        self._conn.commit()
        return self.get_move(move_id)

    def list_learnings(self, initiative_id: str) -> list[Learning]:
        rows = self._conn.execute(
            "SELECT * FROM learnings WHERE initiative_id = ? ORDER BY created_at",
            (initiative_id,),
        ).fetchall()
        return [self._learning(row) for row in rows]

    def status(self) -> dict[str, Any]:
        initiatives = []
        for initv in self.list_initiatives():
            funnel = {key: 0 for key in (*DIAGNOSTIC_TYPES, *FUNNEL_ORDER, "photo_published")}
            move_rows = self._conn.execute(
                "SELECT id FROM moves WHERE initiative_id = ?", (initv.id,)
            ).fetchall()
            for move in move_rows:
                for ev in self._conn.execute(
                    "SELECT evidence_type FROM evidence WHERE move_id = ?", (move["id"],)
                ):
                    if ev["evidence_type"] in funnel:
                        funnel[ev["evidence_type"]] += 1
            primary = "none"
            for key in reversed(FUNNEL_ORDER):
                if funnel[key]:
                    primary = key
                    break
            initiatives.append(
                {
                    "id": initv.id,
                    "objective": initv.objective_slug,
                    "title": initv.title,
                    "status": initv.status,
                    "advancing": initv.advancing,
                    "funnel": funnel,
                    "primary_signal": primary,
                    "open_experiments": self._conn.execute(
                        """
                        SELECT COUNT(*) AS n FROM moves
                        WHERE initiative_id = ? AND kind = 'experiment' AND status != 'closed'
                        """,
                        (initv.id,),
                    ).fetchone()["n"],
                }
            )
        return {
            "home": str(self.home),
            "objectives": [o.slug for o in self.list_objectives()],
            "active_initiatives": sum(1 for item in initiatives if item["status"] == "active"),
            "paused_initiatives": sum(1 for item in initiatives if item["status"] == "paused"),
            "wip_cap": MAX_ACTIVE_INITIATIVES,
            "initiatives": initiatives,
        }

    def _require_wip_slot(self) -> None:
        active = self._conn.execute(
            "SELECT COUNT(*) AS n FROM initiatives WHERE status = 'active'"
        ).fetchone()["n"]
        if active >= MAX_ACTIVE_INITIATIVES:
            raise DomainError(
                "WIP_LIMIT",
                "complete, kill, or pause an existing initiative before creating another "
                f"(cap {MAX_ACTIVE_INITIATIVES} active; paused does not count)",
            )

    def _close_initiative(self, initiative_id: str, status: str, reason: str) -> Initiative:
        initiative = self.get_initiative(initiative_id)
        if initiative.status not in ("active", "paused"):
            raise DomainError("ALREADY_CLOSED", f"initiative is already {initiative.status}")
        now = _now()
        self._conn.execute(
            "UPDATE initiatives SET status = ?, closed_at = ?, close_reason = ? WHERE id = ?",
            (status, now, reason.strip() or None, initiative_id),
        )
        self._conn.commit()
        return self.get_initiative(initiative_id)

    def _objective_by_slug(self, slug: str) -> Objective:
        row = self._conn.execute("SELECT * FROM objectives WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            raise DomainError("NOT_FOUND", f"objective {slug} not found")
        return self._objective(row)

    def _objective(self, row: sqlite3.Row) -> Objective:
        return Objective(
            id=row["id"],
            slug=row["slug"],
            year=row["year"],
            title=row["title"],
            description=row["description"],
            constraints=json.loads(row["constraints_json"]),
        )

    def _initiative(self, row: sqlite3.Row) -> Initiative:
        return Initiative(
            id=row["id"],
            objective_id=row["objective_id"],
            objective_slug=row["objective_slug"],
            title=row["title"],
            status=row["status"],
            advancing=bool(row["advancing"]),
            created_at=row["created_at"],
            closed_at=row["closed_at"],
            close_reason=row["close_reason"],
        )

    def _move(self, row: sqlite3.Row) -> Move:
        return Move(
            id=row["id"],
            initiative_id=row["initiative_id"],
            kind=row["kind"],
            title=row["title"],
            status=row["status"],
            hypothesis=row["hypothesis"],
            question=row["question"],
            output_contract=row["output_contract"],
            done_when=row["done_when"],
            output_result=row["output_result"],
            baseline=_parse_json_object(row["baseline_json"]),
            variant=_parse_json_object(row["variant_json"]),
            causal_confidence=row["causal_confidence"],
            decision=row["decision"],
            created_at=row["created_at"],
            prepared_at=row["prepared_at"],
            deployed_at=row["deployed_at"],
            observing_until=row["observing_until"],
            closed_at=row["closed_at"],
        )

    def _evidence(self, row: sqlite3.Row) -> Evidence:
        return Evidence(
            id=row["id"],
            move_id=row["move_id"],
            source=row["source"],
            recorded_at=row["recorded_at"],
            evidence_type=row["evidence_type"],
            external_reference=row["external_reference"],
            metadata=json.loads(row["metadata_json"]),
            artifact_reference=row["artifact_reference"],
        )

    def _learning(self, row: sqlite3.Row) -> Learning:
        return Learning(
            id=row["id"],
            initiative_id=row["initiative_id"],
            move_id=row["move_id"],
            body=row["body"],
            created_at=row["created_at"],
        )
