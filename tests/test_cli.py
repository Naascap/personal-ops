from __future__ import annotations

import json
from pathlib import Path

from personal_ops.cli import main
from personal_ops.store import PersonalOps


def test_cli_dating_slice_roundtrip(tmp_path: Path) -> None:
    home = tmp_path / "home"
    example = Path(__file__).resolve().parents[1] / "examples" / "objectives.example.yaml"

    assert main(["--home", str(home), "init"]) == 0
    assert main(["--home", str(home), "seed-objectives", str(example)]) == 0
    assert main(
        [
            "--home",
            str(home),
            "initiative-create",
            "--objective",
            "relationship",
            "--title",
            "Improve online dating",
        ]
    ) == 0

    ops = PersonalOps.init(home)
    dating_id = ops.list_initiatives()[0].id
    assert (
        main(
            [
                "--home",
                str(home),
                "move-create",
                "--initiative",
                dating_id,
                "--kind",
                "experiment",
                "--title",
                "Publish photo set B",
                "--hypothesis",
                "Set B yields more quality conversations than A.",
            ]
        )
        == 0
    )
    move_id = ops.list_moves(dating_id)[0].id
    assert (
        main(
            [
                "--home",
                str(home),
                "experiment-frames",
                move_id,
                "--baseline",
                json.dumps({"profile_version": "hinge-v0"}),
                "--variant",
                json.dumps({"profile_version": "hinge-v1"}),
            ]
        )
        == 0
    )
    assert main(["--home", str(home), "move-prepare", move_id]) == 0
    assert main(["--home", str(home), "move-deploy", move_id]) == 0
    assert (
        main(
            [
                "--home",
                str(home),
                "evidence-add",
                "--move",
                move_id,
                "--type",
                "date_arranged",
                "--source",
                "manual",
                "--metadata",
                json.dumps({"count": 1}),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "--home",
                str(home),
                "move-decide",
                move_id,
                "--decision",
                "keep",
                "--learning",
                "One date arranged. Keep set B.",
            ]
        )
        == 0
    )
    assert main(["--home", str(home), "status", "--format", "json"]) == 0
