#!/usr/bin/env python3
"""A7 OC capacity probe — instrumented.

Modes:
  serial  <model>...   run each model one at a time (N=1), measure peak RSS
  conc <N> <model>     run N identical tasks concurrently, measure

Every run uses the SAME known-answer, in-repo task. Read-only against the
repo; the only writes are this probe's own JSON inside .oc_probe/.
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
PROBE = ROOT / ".oc_probe"
OC = "/home/john/.opencode/bin/opencode"
DB = Path.home() / ".local/share/opencode/opencode.db"

TASK = (
    "Read the file scripts/oc_worker.py in the current directory. "
    "Find the variable DEFAULT_MODEL. "
    "Reply with ONLY its default string value and nothing else."
)
EXPECTED = "opencode/deepseek-v4-flash-free"
TIMEOUT = 300


def meminfo():
    d = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, _, v = line.partition(":")
        d[k] = int(v.split()[0]) // 1024  # MiB
    return d


def vmstat():
    d = {}
    for line in Path("/proc/vmstat").read_text().splitlines():
        k, _, v = line.partition(" ")
        d[k] = int(v)
    return d


def wal_mb():
    p = DB.with_name(DB.name + "-wal")
    return round(p.stat().st_size / 1e6, 1) if p.exists() else 0.0


class Sampler(threading.Thread):
    """System-wide pressure sampler."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop = threading.Event()
        self.min_avail = 10**9
        self.samples = 0

    def run(self):
        while not self.stop.wait(1.0):
            self.min_avail = min(self.min_avail, meminfo()["MemAvailable"])
            self.samples += 1


def run_one(model, tag):
    tf = PROBE / f"time_{tag}.txt"
    t0 = time.time()
    rec = {"model": model, "tag": tag}
    try:
        p = subprocess.run(
            ["/usr/bin/time", "-v", "-o", str(tf), OC, "run", "--model", model, TASK],
            capture_output=True, text=True, timeout=TIMEOUT, cwd=str(ROOT),
        )
        out = (p.stdout or "").strip()
        rec.update(rc=p.returncode, secs=round(time.time() - t0, 1),
                   stdout_len=len(out), correct=EXPECTED in out,
                   tail=out[-200:], stderr=(p.stderr or "")[-200:])
    except subprocess.TimeoutExpired:
        rec.update(rc="TIMEOUT", secs=round(time.time() - t0, 1),
                   stdout_len=0, correct=False, tail="", stderr="timeout")
    except Exception as e:  # noqa: BLE001
        rec.update(rc="ERROR", secs=round(time.time() - t0, 1),
                   stdout_len=0, correct=False, tail="", stderr=str(e)[:200])
    if tf.exists():
        for line in tf.read_text(errors="replace").splitlines():
            if "Maximum resident set size" in line:
                rec["peak_rss_mb"] = round(int(line.split(":")[-1].strip()) / 1024, 1)
            elif "Elapsed (wall clock)" in line:
                rec["wall"] = line.split(": ", 1)[-1].strip()
    return rec


def instrument(fn, label, out_path):
    s = Sampler()
    before = {"mem": meminfo(), "vm": vmstat(), "wal": wal_mb(), "t": time.time()}
    s.start()
    results = fn()
    s.stop.set()
    s.join(timeout=3)
    after = {"mem": meminfo(), "vm": vmstat(), "wal": wal_mb(), "t": time.time()}
    payload = {
        "label": label,
        "elapsed_s": round(after["t"] - before["t"], 1),
        "mem_avail_before_mb": before["mem"]["MemAvailable"],
        "mem_avail_min_mb": s.min_avail,
        "mem_avail_after_mb": after["mem"]["MemAvailable"],
        "swap_free_before_mb": before["mem"]["SwapFree"],
        "swap_free_after_mb": after["mem"]["SwapFree"],
        "pswpin_delta": after["vm"]["pswpin"] - before["vm"]["pswpin"],
        "pswpout_delta": after["vm"]["pswpout"] - before["vm"]["pswpout"],
        "wal_mb_before": before["wal"],
        "wal_mb_after": after["wal"],
        "runs": results,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "runs"}, indent=1))
    for r in results:
        print(f"  {r['tag']:12s} {r['model']:34s} rc={r['rc']} {r['secs']:>6}s "
              f"rss={r.get('peak_rss_mb','?')}MB correct={r['correct']} "
              f"len={r['stdout_len']}", flush=True)
    return payload


def main():
    mode = sys.argv[1]
    if mode == "serial":
        models = sys.argv[2:]

        def go():
            return [run_one(m, f"s{i}") for i, m in enumerate(models)]

        instrument(go, "serial", PROBE / "result_serial.json")
    elif mode == "conc":
        n = int(sys.argv[2])
        model = sys.argv[3]
        out = [None] * n

        def go():
            ths = []
            for i in range(n):
                def w(i=i):
                    out[i] = run_one(model, f"c{i}")
                t = threading.Thread(target=w)
                t.start()
                ths.append(t)
            for t in ths:
                t.join()
            return out

        instrument(go, f"concurrent_n{n}", PROBE / f"result_conc{n}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
