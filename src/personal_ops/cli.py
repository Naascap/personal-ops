from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .errors import ConfigError, DomainError
from .paths import default_home
from .store import PersonalOps


def _home(value: str | None) -> Path:
    return Path(value).expanduser() if value else default_home()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="personal-ops",
        description="Objective-aware execution store",
    )
    root.add_argument("--version", action="version", version=f"personal-ops {__version__}")
    root.add_argument("--home", help="runtime directory (must be outside the Git repository)")
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="create the private runtime directory")

    seed = commands.add_parser("seed-objectives", help="human-only: load objectives from yaml")
    seed.add_argument("path")

    status = commands.add_parser("status", help="show objectives, WIP, and dating funnel")
    status.add_argument("--format", choices=("text", "json"), default="text")

    icreate = commands.add_parser("initiative-create", help="open a finite initiative")
    icreate.add_argument("--objective", required=True)
    icreate.add_argument("--title", required=True)

    ikill = commands.add_parser("initiative-kill", help="kill an initiative to free WIP")
    ikill.add_argument("id")
    ikill.add_argument("--reason", required=True)

    icomplete = commands.add_parser("initiative-complete", help="mark an initiative completed")
    icomplete.add_argument("id")
    icomplete.add_argument("--reason", default="")

    ipause = commands.add_parser("initiative-pause", help="pause an initiative (does not consume WIP)")
    ipause.add_argument("id")
    ipause.add_argument("--reason", default="")

    iresume = commands.add_parser("initiative-resume", help="resume a paused initiative into WIP")
    iresume.add_argument("id")

    mcreate = commands.add_parser("move-create", help="create a move on an initiative")
    mcreate.add_argument("--initiative", required=True)
    mcreate.add_argument("--kind", required=True, choices=("action", "experiment", "research"))
    mcreate.add_argument("--title", required=True)
    mcreate.add_argument("--hypothesis")
    mcreate.add_argument("--question", help="research: the question being answered")
    mcreate.add_argument("--output", help="research: contracted output (e.g. ranked_selection)")
    mcreate.add_argument("--done-when", help="research: closure criterion")

    commands_with_id = (
        ("move-prepare", "mark experiment prepared (not closed)"),
        ("move-deploy", "publish/execute in the real world"),
        ("move-close", "close a research or action move"),
    )
    for name, help_text in commands_with_id:
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("id")
        if name == "move-deploy":
            sub.add_argument("--until", help="UTC observation end (experiments)")
        if name == "move-close":
            sub.add_argument("--learning")
            sub.add_argument("--output", help="research: the produced output/decision")

    evidence = commands.add_parser("evidence-add", help="attach typed evidence to a move")
    evidence.add_argument("--move", required=True)
    evidence.add_argument("--type", required=True)
    evidence.add_argument("--source", required=True)
    evidence.add_argument("--ref")
    evidence.add_argument("--artifact")
    evidence.add_argument("--metadata", help="JSON object")

    frames = commands.add_parser(
        "experiment-frames",
        help="record experiment baseline and variant before deploy",
    )
    frames.add_argument("id")
    frames.add_argument("--baseline", required=True, help="JSON object")
    frames.add_argument("--variant", required=True, help="JSON object")

    decide = commands.add_parser("move-decide", help="close an experiment: keep|revert|iterate")
    decide.add_argument("id")
    decide.add_argument("--decision", required=True, choices=("keep", "revert", "iterate"))
    decide.add_argument("--learning", required=True)
    decide.add_argument("--causal-confidence", default="weak")
    return root


def _ops(home: str | None) -> PersonalOps:
    return PersonalOps.init(_home(home))


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _status_text(report: dict[str, Any]) -> str:
    lines = [
        f"home: {report['home']}",
        f"objectives: {', '.join(report['objectives']) or '(unseeded)'}",
        f"WIP: {report['active_initiatives']}/{report['wip_cap']} active "
        f"({report['paused_initiatives']} paused, excluded)",
    ]
    if not report["initiatives"]:
        lines.append("no initiatives")
        return "\n".join(lines)
    for item in report["initiatives"]:
        flag = "advancing" if item["advancing"] else "not advancing"
        lines.append(
            f"- [{item['status']}] {item['objective']}: {item['title']} ({flag})"
        )
        lines.append(
            f"    funnel primary={item['primary_signal']} "
            f"conversations={item['funnel']['quality_conversation']} "
            f"dates={item['funnel']['date_happened']} "
            f"matches={item['funnel']['platform_match']} (diagnostic)"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            ops = _ops(args.home)
            print(f"initialized {ops.home}")
            return 0
        ops = _ops(args.home)
        if args.command == "seed-objectives":
            seeded = ops.seed_objectives(Path(args.path))
            print(f"seeded {len(seeded)} objectives")
            return 0
        if args.command == "status":
            report = ops.status()
            if args.format == "json":
                _print(report)
            else:
                print(_status_text(report))
            return 0
        if args.command == "initiative-create":
            initv = ops.create_initiative(args.objective, args.title)
            _print({"id": initv.id, "title": initv.title, "objective": initv.objective_slug})
            return 0
        if args.command == "initiative-kill":
            initv = ops.kill_initiative(args.id, args.reason)
            _print({"id": initv.id, "status": initv.status})
            return 0
        if args.command == "initiative-complete":
            initv = ops.complete_initiative(args.id, args.reason)
            _print({"id": initv.id, "status": initv.status})
            return 0
        if args.command == "initiative-pause":
            initv = ops.pause_initiative(args.id, args.reason)
            _print({"id": initv.id, "status": initv.status})
            return 0
        if args.command == "initiative-resume":
            initv = ops.resume_initiative(args.id)
            _print({"id": initv.id, "status": initv.status})
            return 0
        if args.command == "move-create":
            move = ops.create_move(
                args.initiative,
                kind=args.kind,
                title=args.title,
                hypothesis=args.hypothesis,
                question=args.question,
                output=args.output,
                done_when=args.done_when,
            )
            _print({"id": move.id, "kind": move.kind, "status": move.status})
            return 0
        if args.command == "move-prepare":
            move = ops.prepare_move(args.id)
            _print({"id": move.id, "status": move.status})
            return 0
        if args.command == "move-deploy":
            move = ops.deploy_move(args.id, observe_until=args.until)
            _print({"id": move.id, "status": move.status})
            return 0
        if args.command == "experiment-frames":
            move = ops.set_experiment_frames(
                args.id,
                baseline=json.loads(args.baseline),
                variant=json.loads(args.variant),
            )
            _print({"id": move.id, "baseline": move.baseline, "variant": move.variant})
            return 0
        if args.command == "evidence-add":
            metadata = json.loads(args.metadata) if args.metadata else None
            ev = ops.add_evidence(
                args.move,
                evidence_type=args.type,
                source=args.source,
                external_reference=args.ref,
                metadata=metadata,
                artifact_reference=args.artifact,
            )
            _print({"id": ev.id, "type": ev.evidence_type, "source": ev.source})
            return 0
        if args.command == "move-decide":
            move = ops.decide_move(
                args.id,
                decision=args.decision,
                learning=args.learning,
                causal_confidence=args.causal_confidence,
            )
            _print({"id": move.id, "status": move.status, "decision": move.decision})
            return 0
        if args.command == "move-close":
            move = ops.close_move(args.id, learning=args.learning, output_result=args.output)
            _print({"id": move.id, "status": move.status, "output": move.output_result})
            return 0
        raise AssertionError(args.command)
    except (ConfigError, DomainError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
