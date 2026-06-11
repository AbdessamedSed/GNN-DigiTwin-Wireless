#!/usr/bin/env python3
import re
import json
import csv
import statistics
from pathlib import Path
from datetime import datetime

ROOT = Path(".").resolve()

pattern = re.compile(
    r"^\d+\)LAT-S(?P<S>\d+)-U=(?P<U>\d+)-G=(?P<G>\d+)-P=(?P<P>[^-]+)-S=(?P<SCHED>[^-]+)-Q=(?P<Q>[^-]+)-R=(?P<R>\d+)$"
)

def flatten_json(obj, prefix=""):
    out = {}

    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten_json(v, key))

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            out.update(flatten_json(v, key))

    else:
        out[prefix] = obj

    return out

def parse_time_string(value):
    """
    Accepts examples:
    - "12.45"
    - "12.45s"
    - "3.2 sec"
    - "2 min"
    - "00:03:21"
    - "1:02:03"
    """
    if not isinstance(value, str):
        return None

    s = value.strip().lower()

    # plain number in string
    try:
        return float(s)
    except Exception:
        pass

    # seconds
    m = re.match(r"^([0-9.]+)\s*(s|sec|secs|second|seconds)$", s)
    if m:
        return float(m.group(1))

    # minutes
    m = re.match(r"^([0-9.]+)\s*(m|min|mins|minute|minutes)$", s)
    if m:
        return float(m.group(1)) * 60.0

    # hours
    m = re.match(r"^([0-9.]+)\s*(h|hr|hrs|hour|hours)$", s)
    if m:
        return float(m.group(1)) * 3600.0

    # HH:MM:SS or MM:SS
    if re.match(r"^\d+:\d+(:\d+)?$", s):
        parts = [float(x) for x in s.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]

    return None

def parse_datetime(value):
    if not isinstance(value, str):
        return None

    candidates = [
        value,
        value.replace("Z", "+00:00"),
        value.replace(" ", "T"),
    ]

    for c in candidates:
        try:
            return datetime.fromisoformat(c)
        except Exception:
            pass

    return None

def extract_runtime_seconds(runtime_path):
    if not runtime_path.exists():
        return None, "missing runtime.json", {}

    try:
        with open(runtime_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return None, f"invalid runtime.json: {e}", {}

    flat = flatten_json(data)

    # 1) Direct numeric/string runtime keys
    good_keywords = [
        "wall_clock",
        "wallclock",
        "wall_time",
        "walltime",
        "elapsed",
        "runtime",
        "run_time",
        "execution_time",
        "exec_time",
        "duration",
        "total_time",
        "real_time",
        "time_seconds",
        "seconds",
    ]

    bad_keywords = [
        "simtime",
        "sim_time",
        "simulation_time",
        "sim-time",
        "start",
        "end",
        "timestamp",
        "date",
        "returncode",
        "exit",
        "pid",
    ]

    candidates = []

    for key, value in flat.items():
        kl = key.lower()

        if any(bad in kl for bad in bad_keywords):
            continue

        if any(good in kl for good in good_keywords):
            seconds = None

            if isinstance(value, (int, float)) and not isinstance(value, bool):
                seconds = float(value)

                # simple unit guessing from key
                if "minute" in kl or kl.endswith("_min") or ".min" in kl:
                    seconds *= 60.0
                elif "hour" in kl or kl.endswith("_h") or ".h" in kl:
                    seconds *= 3600.0

            elif isinstance(value, str):
                seconds = parse_time_string(value)

            if seconds is not None and seconds > 0:
                candidates.append((key, seconds))

    if candidates:
        # choose largest useful runtime candidate, avoids tiny internal values
        candidates.sort(key=lambda x: x[1], reverse=True)
        key, seconds = candidates[0]
        return seconds, f"from runtime.json key: {key}", flat

    # 2) Try start/end timestamps
    start_keys = []
    end_keys = []

    for key, value in flat.items():
        kl = key.lower()
        dt = parse_datetime(value)

        if dt is None:
            continue

        if "start" in kl or "begin" in kl:
            start_keys.append((key, dt))
        if "end" in kl or "finish" in kl or "stop" in kl:
            end_keys.append((key, dt))

    for sk, sdt in start_keys:
        for ek, edt in end_keys:
            delta = (edt - sdt).total_seconds()
            if delta > 0:
                return delta, f"computed from timestamps: {sk} -> {ek}", flat

    return None, "runtime value not found", flat

def fmt_time(seconds):
    if seconds is None:
        return "NA"

    seconds = float(seconds)

    if seconds < 60:
        return f"{seconds:.2f}s"
    if seconds < 3600:
        return f"{seconds / 60:.2f}min"

    return f"{seconds / 3600:.2f}h"

rows = []

for p in ROOT.iterdir():
    if not p.is_dir():
        continue

    m = pattern.match(p.name)
    if not m:
        continue

    info = m.groupdict()

    runtime_path = p / "runtime.json"
    data_path = p / "data.json"

    runtime_sec, source, flat = extract_runtime_seconds(runtime_path)

    rows.append({
        "folder": p.name,
        "S": int(info["S"]),
        "U": int(info["U"]),
        "G": int(info["G"]),
        "P": info["P"],
        "scheduler": info["SCHED"],
        "Q": info["Q"],
        "R": int(info["R"]),
        "runtime_sec": runtime_sec,
        "runtime_human": fmt_time(runtime_sec),
        "source": source,
        "has_data_json": data_path.exists(),
        "data_json_size_MB": round(data_path.stat().st_size / (1024 * 1024), 3) if data_path.exists() else None,
    })

rows.sort(key=lambda x: (x["S"], x["R"]))

print("\n================ SCALING SIMULATION TIMES ================\n")

header = f"{'S':>5} {'U':>5} {'G':>3} {'R':>3} {'Runtime':>12} {'Runtime(s)':>12} {'Data MB':>10}  Folder"
print(header)
print("-" * len(header))

for r in rows:
    sec_txt = "NA" if r["runtime_sec"] is None else f"{r['runtime_sec']:.2f}"
    print(
        f"{r['S']:>5} "
        f"{r['U']:>5} "
        f"{r['G']:>3} "
        f"{r['R']:>3} "
        f"{r['runtime_human']:>12} "
        f"{sec_txt:>12} "
        f"{str(r['data_json_size_MB']):>10}  "
        f"{r['folder']}"
    )

print("\n================ AVERAGE BY SCALE ================\n")

by_scale = {}
for r in rows:
    if r["runtime_sec"] is not None:
        by_scale.setdefault(r["S"], []).append(r["runtime_sec"])

header2 = f"{'S':>5} {'Runs':>5} {'Mean':>12} {'Min':>12} {'Max':>12}"
print(header2)
print("-" * len(header2))

for S in sorted(by_scale):
    vals = by_scale[S]
    print(
        f"{S:>5} "
        f"{len(vals):>5} "
        f"{fmt_time(statistics.mean(vals)):>12} "
        f"{fmt_time(min(vals)):>12} "
        f"{fmt_time(max(vals)):>12}"
    )

missing = [r for r in rows if r["runtime_sec"] is None]

if missing:
    print("\n================ WARNINGS ================\n")
    for r in missing:
        print(f"[WARNING] Runtime not found for {r['folder']} | {r['source']}")

    print("\nTo inspect the available keys, run:\n")
    print("python3 inspect_runtime_keys.py")

print("\n================ EXPORT ================\n")

out_csv = ROOT / "scaling_simulation_times.csv"
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "folder", "S", "U", "G", "P", "scheduler", "Q", "R",
        "runtime_sec", "runtime_human", "source",
        "has_data_json", "data_json_size_MB"
    ])
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved: {out_csv}")
print("\nDone.\n")
