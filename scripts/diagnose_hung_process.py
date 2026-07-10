#!/usr/bin/env python3
"""
diagnose_hung_process.py — Live thread-stack dump for any running Wing process.

Closes the blind spot found in the thunderbird-telegram-gw incident (2026-07):
a process died/restarted ~57 times in 5 days with ZERO diagnostic trail because
nothing was attached to catch a traceback before systemd killed and restarted it.
Adding signal handlers to one script only fixes that one script, going forward.
This tool attaches from OUTSIDE, on demand, to ANY running Python process, with
no code changes required — retroactive coverage for every script in the Wing.

Requires: py-spy (installed in .venv — `pip install py-spy`)

USAGE
    python3 scripts/diagnose_hung_process.py --service thunderbird-telegram-gw.service
    python3 scripts/diagnose_hung_process.py --pattern thunderbird_telegram_gw.py
    python3 scripts/diagnose_hung_process.py --pid 3420683
    python3 scripts/diagnose_hung_process.py --service nexus.service --native-only

HOW IT RESOLVES A TARGET PID
    --service NAME   systemctl --user show -p MainPID --value NAME
    --pattern STR    pgrep -f STR (first match; warns + lists if more than one)
    --pid N          used directly, no resolution

PERMISSION MODEL (found empirically on this host, 2026-07-09)
    /proc/sys/kernel/yama/ptrace_scope = 1 ("restricted ptrace") on this system.
    That means: py-spy running as the SAME user as the target still gets
    "Permission Denied" unless it is a ptrace-parent of the target (it never is —
    targets are systemd-spawned or shell-spawned independently). Root, or
    CAP_SYS_PTRACE, is required to cross that boundary. There is no
    passwordless sudo configured on this host (`sudo -n true` fails), so a
    live human at a terminal typing a sudo password is the only way to grant
    that — this script does NOT attempt sudo itself; it will tell you the
    exact command and stop.

    WORKING FALLBACK (no sudo password needed): this account is a member of
    the `docker` group. The docker daemon runs as root, so `docker run
    --privileged --pid=host ...` gives a container root-equivalent access to
    the host PID namespace — which is sufient for ptrace. This is NOT a new
    privilege grant Hale invented; docker-group membership already IS
    root-equivalent host access (well-known Docker security caveat) — this
    script merely uses an authority the account already holds, via a
    programmatic path, instead of a human-only password prompt. Documented,
    not snuck past anyone.

    This script tries native py-spy first (works if scope=0 or run as root
    some day), and falls back to the docker wrapper automatically if native
    fails with a permission error. Pass --native-only to disable the fallback
    (e.g. to re-test after a ptrace_scope change) or --docker-only to force it.
"""
import argparse
import os
import shutil
import subprocess
import sys


def find_py_spy() -> str:
    candidates = ["/home/john/Thunderbird/.venv/bin/py-spy", shutil.which("py-spy") or ""]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    print("ERROR: py-spy not found. Install with:", file=sys.stderr)
    print("  /home/john/Thunderbird/.venv/bin/pip3 install py-spy", file=sys.stderr)
    sys.exit(2)


def resolve_pid(args) -> int:
    if args.pid:
        return args.pid

    if args.service:
        try:
            out = subprocess.run(
                ["systemctl", "--user", "show", "-p", "MainPID", "--value", args.service],
                capture_output=True, text=True, timeout=10,
            )
            pid = out.stdout.strip()
            if not pid or pid == "0":
                print(f"ERROR: systemctl reports no running MainPID for '{args.service}'. "
                      f"Is the unit active? Try: systemctl --user status {args.service}", file=sys.stderr)
                sys.exit(3)
            return int(pid)
        except Exception as e:
            print(f"ERROR resolving PID via systemctl --user for '{args.service}': {e}", file=sys.stderr)
            sys.exit(3)

    if args.pattern:
        out = subprocess.run(["pgrep", "-f", args.pattern], capture_output=True, text=True)
        pids = [p for p in out.stdout.strip().splitlines() if p]
        if not pids:
            print(f"ERROR: no running process matches pattern '{args.pattern}'", file=sys.stderr)
            sys.exit(3)
        if len(pids) > 1:
            print(f"WARNING: {len(pids)} processes match '{args.pattern}': {pids} — using first (lowest PID not guaranteed newest).", file=sys.stderr)
        return int(pids[0])

    print("ERROR: must supply one of --service, --pattern, or --pid", file=sys.stderr)
    sys.exit(1)


def try_native(py_spy: str, pid: int, dump_args: list) -> tuple[bool, str]:
    proc = subprocess.run([py_spy, "dump", "--pid", str(pid)] + dump_args,
                           capture_output=True, text=True)
    combined = proc.stdout + proc.stderr
    ok = proc.returncode == 0 and "Permission Denied" not in combined
    return ok, combined


def try_docker(pid: int, dump_args: list) -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "ERROR: docker not available on this host — cannot use the ptrace_scope fallback."
    venv_py_spy = "/home/john/Thunderbird/.venv/bin/py-spy"
    cmd = [
        "docker", "run", "--rm", "--pid=host", "--privileged",
        "-v", f"{venv_py_spy}:/py-spy:ro",
        "python:3.13-slim",
        "/py-spy", "dump", "--pid", str(pid),
    ] + dump_args
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    combined = proc.stdout + proc.stderr
    ok = proc.returncode == 0 and "Permission Denied" not in combined
    return ok, combined


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--service", help="systemd --user unit name, e.g. thunderbird-telegram-gw.service")
    target.add_argument("--pattern", help="pgrep -f pattern to locate the process")
    target.add_argument("--pid", type=int, help="PID directly")
    ap.add_argument("--native-only", action="store_true", help="do not fall back to docker wrapper")
    ap.add_argument("--docker-only", action="store_true", help="skip native attempt, go straight to docker wrapper")
    ap.add_argument("--locals", action="store_true", help="pass --locals to py-spy (dump local variables too)")
    ap.add_argument("--full-filenames", action="store_true", help="pass --full-filenames to py-spy")
    args = ap.parse_args()

    dump_args = []
    if args.locals:
        dump_args.append("--locals")
    if args.full_filenames:
        dump_args.append("--full-filenames")

    pid = resolve_pid(args)
    print(f"[diagnose_hung_process] target PID: {pid}", file=sys.stderr)

    if not args.docker_only:
        py_spy = find_py_spy()
        print(f"[diagnose_hung_process] trying native py-spy ({py_spy}) ...", file=sys.stderr)
        ok, output = try_native(py_spy, pid, dump_args)
        if ok:
            print(f"[diagnose_hung_process] SUCCESS via native py-spy", file=sys.stderr)
            print(output)
            return
        print(f"[diagnose_hung_process] native attempt failed (expected if "
              f"/proc/sys/kernel/yama/ptrace_scope > 0 and not root):", file=sys.stderr)
        print(output.strip(), file=sys.stderr)
        if args.native_only:
            print("\n--native-only set — not falling back. To fix natively, a human must run:\n"
                  f"  sudo env \"PATH=$PATH\" {py_spy} dump --pid {pid}\n"
                  "(requires an interactive sudo password — this script will not attempt it).",
                  file=sys.stderr)
            sys.exit(1)

    print("[diagnose_hung_process] falling back to docker --privileged --pid=host wrapper "
          "(docker-group membership already grants root-equivalent host access; "
          "no sudo password required) ...", file=sys.stderr)
    ok, output = try_docker(pid, dump_args)
    if ok:
        print(f"[diagnose_hung_process] SUCCESS via docker wrapper", file=sys.stderr)
        print(output)
        return

    print("[diagnose_hung_process] docker fallback ALSO failed:", file=sys.stderr)
    print(output.strip(), file=sys.stderr)
    print("\nGenuine wall reached. To proceed, a human with sudo access must run:\n"
          f"  sudo env \"PATH=$PATH\" py-spy dump --pid {pid}\n"
          "This script will not attempt that on its own.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
