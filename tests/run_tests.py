#!/usr/bin/env python3
"""Tern test runner.

Each test is a .tn file under tests/cases/. Directives live in the leading
block of `//` comments; the header ends at the first line that isn't one.

    // args: --tokens {file}     arguments passed to the compiler
    //                           ({file} = path to this test; default: {file})
    // expect-exit: 1            expected exit code (default: 0)
    // expect-stdout:            following comment lines are the exact stdout
    // 42
    // expect-stderr:            following comment lines are the exact stderr
    // error: ...

stdout/stderr are only checked when the matching directive is present.

Usage: run_tests.py [--compiler PATH] [FILTER ...]
"""

import argparse
import difflib
import pathlib
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = ROOT / "tests" / "cases"
TIMEOUT = 10

COLOR = sys.stdout.isatty()
GREEN, RED, RESET = ("\033[32m", "\033[31m", "\033[0m") if COLOR else ("", "", "")


def parse_header(path):
    test = {"args": "{file}", "exit": 0, "stdout": None, "stderr": None}
    block = None
    for line in path.read_text().splitlines():
        if not line.startswith("//"):
            break
        body = line[2:]
        if body.startswith(" "):
            body = body[1:]

        key, sep, value = body.partition(":")
        if sep and key in ("args", "expect-exit", "expect-stdout", "expect-stderr"):
            block = None
            if key == "args":
                test["args"] = value.strip()
            elif key == "expect-exit":
                test["exit"] = int(value.strip())
            else:
                block = key.removeprefix("expect-")
                test[block] = []
        elif block:
            test[block].append(body)
    return test


def diff(expected, actual, name):
    return "".join(difflib.unified_diff(
        [l + "\n" for l in expected], [l + "\n" for l in actual],
        f"expected {name}", f"actual {name}"))


def run_test(compiler, path):
    test = parse_header(path)
    args = [str(path) if a == "{file}" else a for a in shlex.split(test["args"])]
    try:
        proc = subprocess.run([compiler, *args], capture_output=True,
                              text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return [f"timed out after {TIMEOUT}s"]

    failures = []
    if proc.returncode != test["exit"]:
        failures.append(f"exit code: expected {test['exit']}, got {proc.returncode}")
    for stream in ("stdout", "stderr"):
        expected = test[stream]
        actual = getattr(proc, stream).splitlines()
        if expected is not None and expected != actual:
            failures.append(diff(expected, actual, stream))
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", default=str(ROOT / "build" / "tern"))
    parser.add_argument("filters", nargs="*", help="only run tests whose path contains one of these")
    opts = parser.parse_args()

    tests = sorted(CASES.rglob("*.tn"))
    if opts.filters:
        tests = [t for t in tests if any(f in str(t) for f in opts.filters)]
    if not tests:
        print("no tests found", file=sys.stderr)
        return 1

    failed = 0
    for path in tests:
        name = path.relative_to(CASES)
        failures = run_test(opts.compiler, path)
        if failures:
            failed += 1
            print(f"{RED}FAIL{RESET} {name}")
            for f in failures:
                print("  " + f.replace("\n", "\n  ").rstrip())
        else:
            print(f"{GREEN}PASS{RESET} {name}")

    print(f"\n{len(tests) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
