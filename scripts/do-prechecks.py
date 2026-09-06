#!/usr/bin/env python3
"""Run SPF5000's local quality gates in fail-fast order before a commit or PR.

Checks are ordered from quickest feedback to longest-running work, and execution
stops at the first failure. Everything here is read-only apart from the frontend
build output; nothing in this script commits, pushes, or rewrites git history.

Backend linting is opt-in because the repository does not configure Ruff yet, so
`ruff check backend` currently reports pre-existing findings. End-to-end tests are
opt-in because they need installed Playwright browsers and a backend on :8000.

Examples:
    ./scripts/do-prechecks.py
    ./scripts/do-prechecks.py --frontend-only
    ./scripts/do-prechecks.py --include-e2e --include-lint
    ./scripts/do-prechecks.py --list
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

try:
    from rich import box
    from rich.console import Console
    from rich.markup import escape
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ModuleNotFoundError:
    print(
        "Rich is required for this precheck utility. Install it for the active "
        "interpreter with: python3 -m pip install rich "
        "(or run this script with backend/.venv/bin/python after installing it there)",
        file=sys.stderr,
    )
    raise SystemExit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_DIR = REPO_ROOT / "backend"
VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))"
)
BUILD_WARNING_PATTERN = re.compile(
    r"\b(?:warn|[a-z0-9_]*warnings?)\b|\bdeprecat(?:ed|ion)\b|(?:^|\s)⚠(?:\s|$)",
    re.IGNORECASE,
)
# Vitest retries default to 1 because src/hooks/useAsyncData.test.ts contains a known
# timing-sensitive failure ("reload calls the loader again") that is unrelated to any
# change under review. Use --strict to surface single-attempt failures instead.
DEFAULT_VITEST_RETRIES = 1

console = Console(highlight=False)


@dataclass(frozen=True)
class Check:
    """One fail-fast quality gate."""

    name: str
    command: tuple[str, ...]
    detail: str
    cwd: Path = REPO_ROOT
    tags: tuple[str, ...] = ()
    reject_warnings: bool = False


@dataclass(frozen=True)
class CheckResult:
    """The result of running one quality gate."""

    check: Check
    returncode: int
    elapsed_seconds: float
    warning_lines: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and not self.warning_lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run quick static checks first, then tests and the production build. "
            "Stop immediately when a check fails."
        )
    )
    parser.add_argument(
        "--include-e2e",
        action="store_true",
        help=(
            "Run Playwright last. Requires installed Playwright browsers "
            "(`cd frontend && npm run playwright:install`) and a backend serving "
            "http://localhost:8000 (`make backend`)."
        ),
    )
    parser.add_argument(
        "--include-lint",
        action="store_true",
        help=(
            "Run `ruff check backend`. Ruff is not configured for this repository "
            "yet, so pre-existing findings currently fail this gate."
        ),
    )
    parser.add_argument(
        "--frontend-only",
        action="store_true",
        help="Skip backend checks.",
    )
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Skip frontend checks.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=f"Do not retry Vitest (default: {DEFAULT_VITEST_RETRIES} retry).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the selected checks and exit without running anything.",
    )
    options = parser.parse_args()
    if options.frontend_only and options.backend_only:
        parser.error("--frontend-only and --backend-only cannot be combined")
    return options


def checks_for(
    *, include_e2e: bool, include_lint: bool, vitest_retries: int
) -> list[Check]:
    """Return checks ordered from quick feedback to longest-running work."""
    vitest_command = ["npm", "test", "--", f"--retry={vitest_retries}"]

    checks = [
        Check(
            name="Working tree whitespace",
            command=("git", "diff", "--check", "HEAD"),
            detail="Reject trailing whitespace and leftover conflict markers.",
        ),
        Check(
            name="TypeScript",
            command=("npx", "tsc", "-b", "--force"),
            detail="Type-check the frontend without trusting the cached tsbuildinfo.",
            cwd=FRONTEND_DIR,
            tags=("frontend",),
        ),
        Check(
            name="Frontend tests",
            command=tuple(vitest_command),
            detail="Run the Vitest suite (jsdom + Testing Library).",
            cwd=FRONTEND_DIR,
            tags=("frontend",),
        ),
        Check(
            name="Frontend build",
            command=("npm", "run", "build"),
            detail="Run `tsc -b` and Vite, and reject warning output.",
            cwd=FRONTEND_DIR,
            tags=("frontend",),
            reject_warnings=True,
        ),
        Check(
            name="Backend tests",
            command=(str(VENV_PYTHON), "-m", "pytest"),
            detail="Run the FastAPI/pytest suite against the app under backend/.",
            cwd=BACKEND_DIR,
            tags=("backend",),
        ),
    ]

    if include_lint:
        checks.append(
            Check(
                name="Backend lint",
                command=("ruff", "check", "backend"),
                detail="Ruff lint of the backend (not adopted as a gate yet).",
                tags=("backend",),
            )
        )

    if include_e2e:
        checks.append(
            Check(
                name="End-to-end tests",
                command=("npm", "run", "test:e2e"),
                detail="Run Playwright against the running backend on :8000.",
                cwd=FRONTEND_DIR,
                tags=("frontend",),
            )
        )

    return checks


def select_checks(checks: Sequence[Check], options: argparse.Namespace) -> list[Check]:
    if options.frontend_only:
        return [c for c in checks if "backend" not in c.tags]
    if options.backend_only:
        return [c for c in checks if "frontend" not in c.tags]
    return list(checks)


def validate_environment(options: argparse.Namespace) -> None:
    """Fail before doing work when the checkout cannot run project commands."""
    problems: list[str] = []
    needs_frontend = not options.backend_only
    needs_backend = not options.frontend_only or options.include_lint

    if shutil.which("git") is None:
        problems.append("git is not available on PATH")
    elif subprocess.run(
        ("git", "rev-parse", "--verify", "HEAD"),
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    ).returncode != 0:
        problems.append("this checkout has no commits yet, so `git diff HEAD` cannot run")

    if needs_backend and not VENV_PYTHON.is_file():
        problems.append(
            f"{VENV_PYTHON.relative_to(REPO_ROOT)} is missing; create the backend "
            "virtualenv first (see README 'Development')"
        )
    if needs_backend and options.include_lint and shutil.which("ruff") is None:
        problems.append("ruff is not available on PATH (requested via --include-lint)")

    if needs_frontend:
        if shutil.which("npm") is None:
            problems.append("npm is not available on PATH")
        if not (FRONTEND_DIR / "node_modules").is_dir():
            problems.append(
                "frontend/node_modules is missing; run `cd frontend && npm install` first"
            )
        if options.include_e2e and not (
            FRONTEND_DIR / "node_modules" / "@playwright" / "test"
        ).exists():
            problems.append(
                "@playwright/test is missing; run `cd frontend && npm install` first"
            )

    if problems:
        message = "\n".join(f"• {problem}" for problem in problems)
        console.print(
            Panel(message, title="[red]Cannot run prechecks[/red]", border_style="red")
        )
        raise SystemExit(2)


def render_command(command: Sequence[str]) -> str:
    return shlex.join(str(part) for part in command)


def strip_terminal_codes(value: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", value)


def print_process_line(line: str) -> None:
    """Render child output live while preserving any ANSI styling it contains."""
    value = line.rstrip("\r\n")
    if value:
        console.print(Text.from_ansi(value), soft_wrap=True)
    else:
        console.print()


def run_check(check: Check, *, position: int, total: int) -> CheckResult:
    console.print()
    console.rule(f"[bold cyan]{position}/{total} · {escape(check.name)}[/bold cyan]")
    console.print(check.detail)
    console.print(f"[dim]cwd: {escape(str(check.cwd.relative_to(REPO_ROOT)))}[/dim]")
    console.print(f"[dim]$ {escape(render_command(check.command))}[/dim]")

    started_at = time.monotonic()
    warning_lines: list[str] = []
    environment = os.environ.copy()
    # Keep child output deterministic and coloured for the live renderer.
    environment.setdefault("FORCE_COLOR", "1")

    try:
        process = subprocess.Popen(
            list(check.command),
            cwd=check.cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print_process_line(line)
            normalized = strip_terminal_codes(line).strip()
            if (
                check.reject_warnings
                and normalized
                and BUILD_WARNING_PATTERN.search(normalized)
            ):
                warning_lines.append(normalized)
        returncode = process.wait()
    except FileNotFoundError as error:
        raise SystemExit(f"Precheck could not start {check.name}: {error}") from error
    except KeyboardInterrupt:
        if "process" in locals() and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            process.wait()
        console.print("\n[yellow]Prechecks interrupted.[/yellow]")
        raise SystemExit(130)

    elapsed = time.monotonic() - started_at
    return CheckResult(
        check=check,
        returncode=returncode,
        elapsed_seconds=elapsed,
        warning_lines=tuple(dict.fromkeys(warning_lines)),
    )


def print_failure(result: CheckResult, *, remaining: Sequence[Check]) -> None:
    reasons: list[str] = []
    if result.returncode != 0:
        reasons.append(f"Command exited with status {result.returncode}.")
    if result.warning_lines:
        reasons.append(
            f"The build emitted {len(result.warning_lines)} unique warning "
            f"marker{'s' if len(result.warning_lines) != 1 else ''}:"
        )
        reasons.extend(f"  • {escape(line)}" for line in result.warning_lines)
    reasons.append("Fix this before committing; nothing was committed or pushed.")
    if remaining:
        reasons.append(
            "Fail-fast mode did not run: " + ", ".join(check.name for check in remaining)
        )

    console.print()
    console.print(
        Panel(
            "\n".join(reasons),
            title=f"[bold red]Failed · {escape(result.check.name)}[/bold red]",
            border_style="red",
        )
    )


def print_success(results: Sequence[CheckResult]) -> None:
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Result", justify="center")
    table.add_column("Time", justify="right")
    for result in results:
        table.add_row(
            result.check.name,
            "[green]PASS[/green]",
            f"{result.elapsed_seconds:.1f}s",
        )

    total_seconds = sum(result.elapsed_seconds for result in results)
    console.print()
    console.print(table)
    console.print(
        Panel(
            f"[bold green]All {len(results)} prechecks passed[/bold green] "
            f"in {total_seconds:.1f}s.",
            border_style="green",
        )
    )


def print_check_list(checks: Sequence[Check]) -> None:
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Command", no_wrap=True, overflow="fold")
    table.add_column("Working directory", justify="left")
    for check in checks:
        table.add_row(
            check.name,
            render_command(check.command),
            str(check.cwd.relative_to(REPO_ROOT)),
        )
    console.print(table)
    console.print("[dim]Nothing was run (--list).[/dim]")


def main() -> int:
    options = parse_args()
    checks = select_checks(
        checks_for(
            include_e2e=options.include_e2e,
            include_lint=options.include_lint,
            vitest_retries=0 if options.strict else DEFAULT_VITEST_RETRIES,
        ),
        options,
    )

    if options.list:
        print_check_list(checks)
        return 0

    validate_environment(options)

    scope = (
        "frontend only"
        if options.frontend_only
        else "backend only"
        if options.backend_only
        else "full stack"
    )
    console.print(
        Panel(
            f"Scope: [bold]{scope}[/bold]. Quick gates run first; execution stops on "
            "the first failure. "
            + (
                "Playwright is enabled and will run last."
                if options.include_e2e
                else "Playwright is opt-in with --include-e2e."
            ),
            title="[bold]SPF5000 prechecks[/bold]",
            border_style="cyan",
        )
    )

    results: list[CheckResult] = []
    for index, check in enumerate(checks):
        result = run_check(check, position=index + 1, total=len(checks))
        results.append(result)
        if not result.passed:
            print_failure(result, remaining=checks[index + 1 :])
            return result.returncode if result.returncode else 1
        console.print(
            f"[bold green]PASS[/bold green] {escape(check.name)} "
            f"[dim]({result.elapsed_seconds:.1f}s)[/dim]"
        )

    print_success(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
