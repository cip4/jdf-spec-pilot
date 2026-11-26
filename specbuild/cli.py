"""Command line entry point for the specification toolchain."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import build, model, reconcile as reconcile_mod, sync, xsd_emit, xsd_import

DEFAULT_XJDF = "import/xsd/xjdf/xjdf.xsd"


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="specbuild")
    parser.add_argument("--root", default=None, help="repository root (default: auto-detect)")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("check", help="validate the model and generated blocks")
    commands.add_parser("sync", help="regenerate generated blocks from the model")

    build_cmd = commands.add_parser("build", help="build HTML for one variant")
    build_cmd.add_argument("--variant", choices=["both", "jdf", "xjdf"], default="both")
    build_cmd.add_argument("--release", action="store_true", help="omit draft-only content")
    build_cmd.add_argument("--out", default="build/html")

    import_cmd = commands.add_parser("import-xsd", help="import an XSD into the model (staging)")
    import_cmd.add_argument("--variant", choices=["xjdf"], default="xjdf")
    import_cmd.add_argument("--xsd", default=DEFAULT_XJDF)
    import_cmd.add_argument("--out", default="import/xsd/xjdf")

    commands.add_parser("reconcile", help="compare the staged import with the model")

    roundtrip_cmd = commands.add_parser("roundtrip", help="model-level XSD round-trip proof")
    roundtrip_cmd.add_argument("--xsd", default=DEFAULT_XJDF)
    roundtrip_cmd.add_argument("--workdir", default="import/roundtrip")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else model.repo_root_default()

    if args.command == "check":
        errors = model.validate(root) + sync.check(root)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("OK: model valid, generated blocks up to date")
        return 0

    if args.command == "sync":
        changed = sync.sync(root)
        for path in changed:
            print(f"updated {path.relative_to(root)}")
        print(f"{len(changed)} file(s) updated")
        return 0

    if args.command == "build":
        target = build.build(root, args.variant, args.release, args.out)
        print(f"built {target.relative_to(root)}")
        return 0

    if args.command == "import-xsd":
        xsd = _resolve(root, args.xsd)
        out = _resolve(root, args.out)
        modelset = xsd_import.import_all(xsd)
        counts = xsd_import.write_staging(modelset, out, str(xsd.relative_to(root)))
        detail = ", ".join(f"{bucket} {count}" for bucket, count in counts.items())
        print(f"imported {xsd.relative_to(root)}: {detail}")
        return 0

    if args.command == "reconcile":
        report, summary = reconcile_mod.reconcile(root)
        print(f"wrote {report.relative_to(root)}")
        for bucket, data in summary.items():
            print(
                f"{bucket}: model {data['model']}, xsd {data['xsd']}, "
                f"common {data['common']}, model-only {len(data['model_only'])}"
            )
        return 0

    if args.command == "roundtrip":
        xsd = _resolve(root, args.xsd)
        workdir = _resolve(root, args.workdir)
        first, second, differences, generated = xsd_emit.roundtrip(xsd, workdir)
        report = workdir / "report.md"
        status = "PASS" if not differences else "FAIL"
        lines = [
            f"# Round-trip report: {status}",
            "",
            f"- source: `{xsd.relative_to(root)}`",
            f"- generated XSD: `{generated.relative_to(root)}`",
            "",
            "| Bucket | Imported | Re-imported |",
            "| --- | --- | --- |",
        ]
        for bucket in first:
            lines.append(f"| {bucket} | {len(first[bucket])} | {len(second[bucket])} |")
        if differences:
            lines += ["", "## Differences", ""] + [f"- {d}" for d in differences[:200]]
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"round-trip {status}: {report.relative_to(root)}")
        if differences:
            for difference in differences[:50]:
                print(f"DIFF: {difference}", file=sys.stderr)
            return 1
        return 0

    return 2
