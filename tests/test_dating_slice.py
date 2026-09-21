from __future__ import annotations

from pathlib import Path

import pytest

from personal_ops.errors import ConfigError, DomainError
from personal_ops.paths import require_runtime_outside_repo
from personal_ops.store import MAX_ACTIVE_INITIATIVES, PersonalOps


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "objectives.example.yaml"


@pytest.fixture
def ops(tmp_path: Path) -> PersonalOps:
    return PersonalOps.init(tmp_path / "home")


def _seed(ops: PersonalOps) -> None:
    ops.seed_objectives(EXAMPLE)


def _experiment(ops: PersonalOps, initiative_id: str, title: str, hypothesis: str):
    move = ops.create_move(initiative_id, kind="experiment", title=title, hypothesis=hypothesis)
    ops.set_experiment_frames(
        move.id,
        baseline={"profile_version": "hinge-v0", "observation_window": "7d"},
        variant={"profile_version": "hinge-v1"},
    )
    return ops.get_move(move.id)


def test_init_rejects_directory_inside_git_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    inside = repo / "data"
    with pytest.raises(ConfigError, match="outside the Git repository"):
        require_runtime_outside_repo(inside, start=repo)


def test_seed_objectives_are_human_owned(ops: PersonalOps) -> None:
    seeded = ops.seed_objectives(EXAMPLE)
    assert [o.slug for o in seeded] == [
        "relationship",
        "physical",
        "money-property",
        "discipline",
        "social-volunteer",
    ]
    with pytest.raises(DomainError, match="OBJECTIVES_ALREADY_SEEDED"):
        ops.seed_objectives(EXAMPLE)
    assert not hasattr(ops, "create_objective")
    assert not hasattr(ops, "update_objective")


def test_research_does_not_mark_initiative_advancing(ops: PersonalOps) -> None:
    _seed(ops)
    dating = ops.create_initiative("relationship", "Improve online dating")
    assert dating.advancing is False
    research = ops.create_move(
        dating.id,
        kind="research",
        title="Choose Hinge baseline photos",
        question="Which 6 photos should form Hinge baseline v1?",
        output="ranked_selection",
        done_when="baseline photo set is chosen",
    )
    with pytest.raises(DomainError, match="RESEARCH_OUTPUT_REQUIRED"):
        ops.close_move(research.id, learning="still browsing")
    closed = ops.close_move(
        research.id,
        learning="Six photos selected.",
        output_result="ranked_selection: photo-a, photo-b, photo-c, photo-d, photo-e, photo-f",
    )
    assert closed.status == "closed"
    assert closed.output_result is not None
    assert ops.get_initiative(dating.id).advancing is False


def test_research_requires_a_contract(ops: PersonalOps) -> None:
    _seed(ops)
    dating = ops.create_initiative("relationship", "Improve online dating")
    with pytest.raises(DomainError, match="RESEARCH_CONTRACT_REQUIRED"):
        ops.create_move(dating.id, kind="research", title="Read dating best practices")


def test_experiment_cannot_close_on_prepare(ops: PersonalOps) -> None:
    _seed(ops)
    dating = ops.create_initiative("relationship", "Improve online dating")
    move = ops.create_move(
        dating.id,
        kind="experiment",
        title="Publish photo set B",
        hypothesis="Set B yields more quality conversations than A.",
    )
    ops.prepare_move(move.id)
    with pytest.raises(DomainError, match="EXPERIMENT_NOT_DEPLOYED"):
        ops.decide_move(move.id, decision="keep", learning="not yet")


def test_experiment_closes_only_after_deploy_evidence_and_decision(ops: PersonalOps) -> None:
    _seed(ops)
    dating = ops.create_initiative("relationship", "Improve online dating")
    move = _experiment(
        ops,
        dating.id,
        "Publish photo set B",
        "Set B yields more quality conversations than A.",
    )
    assert move.baseline["profile_version"] == "hinge-v0"
    assert move.variant["profile_version"] == "hinge-v1"
    ops.prepare_move(move.id)
    ops.deploy_move(move.id)
    with pytest.raises(DomainError, match="EXPERIMENT_NO_EVIDENCE"):
        ops.decide_move(move.id, decision="iterate", learning="no data")

    ops.add_evidence(move.id, evidence_type="photo_published", source="manual")
    ops.add_evidence(
        move.id,
        evidence_type="platform_match",
        source="hinge",
        metadata={"count": 4},
    )
    ops.add_evidence(
        move.id,
        evidence_type="quality_conversation",
        source="manual",
        metadata={"count": 1},
    )
    closed = ops.decide_move(
        move.id,
        decision="iterate",
        learning="Matches rose; only one conversation. Next: tighter openers, keep set B.",
    )
    assert closed.status == "closed"
    assert closed.decision == "iterate"
    assert closed.causal_confidence == "weak"
    refreshed = ops.get_initiative(dating.id)
    assert refreshed.advancing is True
    learnings = ops.list_learnings(dating.id)
    assert len(learnings) == 1
    assert "openers" in learnings[0].body

    report = ops.status()
    dating_status = next(i for i in report["initiatives"] if i["id"] == dating.id)
    assert dating_status["funnel"]["platform_match"] == 1
    assert dating_status["funnel"]["quality_conversation"] == 1
    assert dating_status["funnel"]["date_happened"] == 0
    assert dating_status["primary_signal"] == "quality_conversation"


def test_second_open_experiment_is_rejected(ops: PersonalOps) -> None:
    _seed(ops)
    dating = ops.create_initiative("relationship", "Improve online dating")
    ops.create_move(
        dating.id,
        kind="experiment",
        title="Publish photo set B",
        hypothesis="B > A on conversations.",
    )
    with pytest.raises(DomainError, match="OPEN_EXPERIMENT_EXISTS"):
        ops.create_move(
            dating.id,
            kind="experiment",
            title="Publish photo set C",
            hypothesis="C > B",
        )


def test_wip_cap_rejects_fourth_initiative(ops: PersonalOps) -> None:
    _seed(ops)
    ops.create_initiative("relationship", "Improve online dating")
    ops.create_initiative("physical", "Improve triathlon performance")
    ops.create_initiative("money-property", "Find a property to buy")
    assert MAX_ACTIVE_INITIATIVES == 3
    with pytest.raises(DomainError, match="WIP_LIMIT"):
        ops.create_initiative("social-volunteer", "Join a weekly event")

    paused = ops.list_initiatives(status="active")[0]
    ops.pause_initiative(paused.id, reason="Blocked on a viewing.")
    fourth = ops.create_initiative("social-volunteer", "Join a weekly event")
    assert fourth.status == "active"
    assert ops.status()["active_initiatives"] == 3
    assert ops.status()["paused_initiatives"] == 1


def test_agent_source_is_not_execution_evidence(ops: PersonalOps) -> None:
    _seed(ops)
    dating = ops.create_initiative("relationship", "Improve online dating")
    move = _experiment(ops, dating.id, "Publish photo set B", "B > A")
    ops.prepare_move(move.id)
    ops.deploy_move(move.id)
    with pytest.raises(DomainError, match="INVALID_SOURCE"):
        ops.add_evidence(move.id, evidence_type="photo_published", source="agent")


def test_experiment_cannot_deploy_without_baseline(ops: PersonalOps) -> None:
    _seed(ops)
    dating = ops.create_initiative("relationship", "Improve online dating")
    move = ops.create_move(
        dating.id,
        kind="experiment",
        title="Publish photo set B",
        hypothesis="B > A",
    )
    with pytest.raises(DomainError, match="BASELINE_REQUIRED"):
        ops.deploy_move(move.id)
