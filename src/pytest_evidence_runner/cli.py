from __future__ import annotations

import argparse
from pathlib import Path

from .comparison import Thresholds, compare_reports, save_baseline
from .docker import DEFAULT_IMAGE, build_docker_command, run_pytest_in_docker, shell_join
from .exporting import export_comparison, export_run
from .reporting import write_reports
from .runner import run_verification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pytest-evidence")
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    run_parser = subparsers.add_parser("run", help="Run pytest locally or inside Docker and write evidence reports.")
    run_parser.add_argument("--workdir", type=Path, help="Local working directory for non-Docker execution.")
    run_parser.add_argument("--project", type=Path, help="Project directory to test. Required for --docker.")
    run_parser.add_argument("--output-dir", default=Path("evidence/latest"), type=Path)
    run_parser.add_argument("--hash", action="append", default=[], dest="hash_patterns")
    run_parser.add_argument("--timeout-seconds", type=int, default=120)
    run_parser.add_argument("--docker", action="store_true", help="Execute pytest inside an isolated Docker container.")
    run_parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image to use for --docker.")
    run_parser.add_argument("--no-build", action="store_true", help="Do not build the default local Docker image.")
    run_parser.add_argument("command", nargs=argparse.REMAINDER)

    docker_parser = subparsers.add_parser("docker-command", help="Print an isolated Docker run command.")
    docker_parser.add_argument("--image", default="python:3.12-slim")
    docker_parser.add_argument("--project-path", required=True, type=Path)
    docker_parser.add_argument("--output-path", required=True, type=Path)
    docker_parser.add_argument("command", nargs=argparse.REMAINDER)

    baseline_parser = subparsers.add_parser("baseline", help="Save completed evidence reports as named baselines.")
    baseline_subparsers = baseline_parser.add_subparsers(dest="baseline_command", required=True)
    baseline_save = baseline_subparsers.add_parser("save", help="Save a report as a named baseline.")
    baseline_save.add_argument("--name", required=True)
    baseline_save.add_argument("--report", required=True, type=Path)
    baseline_save.add_argument("--baseline-dir", default=Path("baselines"), type=Path)

    compare_parser = subparsers.add_parser("compare", help="Compare two saved evidence reports.")
    compare_parser.add_argument("--baseline", required=True, type=Path)
    compare_parser.add_argument("--current", required=True, type=Path)
    compare_parser.add_argument("--output-dir", default=Path("comparison/latest"), type=Path)
    compare_parser.add_argument("--duration-threshold-seconds", type=float, default=0.25)
    compare_parser.add_argument("--duration-threshold-percent", type=float, default=50.0)

    export_parser = subparsers.add_parser("export", help="Export run or comparison evidence reports.")
    source = export_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run", type=Path, help="Directory containing report.json.")
    source.add_argument("--comparison", type=Path, help="Directory containing comparison.json.")
    export_parser.add_argument("--format", required=True, help="Comma-separated formats: pdf,html,json,md,zip")
    export_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args(argv)
    if hasattr(args, "command") and args.command and args.command[0] == "--":
        args.command = args.command[1:]

    if args.command_name == "run":
        if args.docker:
            if args.workdir and not args.project:
                args.project = args.workdir
            if not args.project:
                parser.error("--project is required when using --docker")
            report = run_pytest_in_docker(
                project_path=args.project,
                output_dir=args.output_dir,
                command=args.command or None,
                image=args.image,
                timeout_seconds=args.timeout_seconds,
                hash_patterns=args.hash_patterns,
                build_image=not args.no_build,
            )
        else:
            workdir = args.workdir or args.project
            if not workdir:
                parser.error("--workdir or --project is required for local execution")
            if not args.command:
                parser.error("local execution requires a command after --")
            report = run_verification(
                command=args.command,
                workdir=workdir,
                hash_patterns=args.hash_patterns,
                timeout_seconds=args.timeout_seconds,
            )
        json_path, md_path = write_reports(report, args.output_dir)
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")
        return report.exit_code

    if args.command_name == "docker-command":
        command = build_docker_command(args.image, args.project_path, args.output_path, args.command)
        print(shell_join(command))
        return 0

    if args.command_name == "baseline":
        report_path, metadata_path = save_baseline(args.name, args.report, args.baseline_dir)
        print(f"saved baseline report {report_path}")
        print(f"wrote baseline metadata {metadata_path}")
        return 0

    if args.command_name == "compare":
        thresholds = Thresholds(
            absolute_seconds=args.duration_threshold_seconds,
            relative_percent=args.duration_threshold_percent,
        )
        comparison, json_path, md_path = compare_reports(args.baseline, args.current, args.output_dir, thresholds)
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")
        return 1 if comparison["summary"]["introduced_regressions"] else 0

    if args.command_name == "export":
        formats = {item.strip().lower() for item in args.format.split(",") if item.strip()}
        allowed = {"pdf", "html", "json", "md", "zip"}
        unknown = sorted(formats - allowed)
        if unknown:
            parser.error(f"unknown export format(s): {', '.join(unknown)}")
        outputs = export_run(args.run, formats, args.output) if args.run else export_comparison(args.comparison, formats, args.output)
        for path in outputs:
            print(f"wrote {path}")
        return 0

    parser.error("unknown command")
    return 2
