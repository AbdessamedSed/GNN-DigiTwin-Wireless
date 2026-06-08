#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automation for WirelessNet-GNN latency/speedup dataset generation.

Goal:
- Generate 5 controlled Simu5G scenarios with increasing UE counts.
- Keep power/scheduler/queue size fixed by default to isolate the effect of graph size.
- Preserve the same paths, config name, output file names, and JSON post-processing logic.
- Measure real wall-clock simulation time on the machine.

Run from the same simulations directory where your previous master_script.py works.
"""

import os
import json
import re
import subprocess
import shutil
import time
import csv
import math
from datetime import datetime
from pathlib import Path

# ===========================================================================
# 1. PATHS AND GLOBAL SETTINGS -- SAME LOGIC AS YOUR WORKING SCRIPT
# ===========================================================================
SCENARIO_PREFIX = "LAT"
CONFIG_NAME = "DT-Scenario"

PROJECT_BINARY = "../out/clang-release/FiveG_network"
NED_PATH = "../src:../../Simu5G/src:../../inet4.5/src"
LIB_INET = "../../inet4.5/src/INET"
LIB_SIMU5G = "../../Simu5G/src/simu5g"

RAW_JSON = "network_state.json"
RUNTIME_SUMMARY_CSV = "latency_scaling_runtime_summary.csv"
GENERATED_INI_DIR = "."

# Keep this True to avoid overwriting successful runs.
SKIP_SUCCESS = True

# Number of OMNeT++ repetitions per scenario size.
# For the paper, 3 is a good minimum; set 5 if you have time.
RUNS_PER_SCENARIO = 3

# We keep these fixed to isolate the impact of the number of UEs.
# They are all values already used in your existing omnetpp.ini.
DEFAULT_POWER = "0.5W"
DEFAULT_SCHEDULER = "PF"
DEFAULT_QUEUE_SIZE = "100KiB"

# Five controlled scaling points.
# For safety, the last two reuse the 4-gNB layout already present in your SC05 example.
SCENARIOS = [
    {"name": "S15",  "num_ue": 15,  "num_gnb": 1, "power": DEFAULT_POWER, "scheduler": DEFAULT_SCHEDULER, "queue_size": DEFAULT_QUEUE_SIZE},
    {"name": "S30",  "num_ue": 30,  "num_gnb": 2, "power": DEFAULT_POWER, "scheduler": DEFAULT_SCHEDULER, "queue_size": DEFAULT_QUEUE_SIZE},
    {"name": "S60",  "num_ue": 60,  "num_gnb": 4, "power": DEFAULT_POWER, "scheduler": DEFAULT_SCHEDULER, "queue_size": DEFAULT_QUEUE_SIZE},
    {"name": "S100", "num_ue": 100, "num_gnb": 4, "power": DEFAULT_POWER, "scheduler": DEFAULT_SCHEDULER, "queue_size": DEFAULT_QUEUE_SIZE},
    {"name": "S150", "num_ue": 150, "num_gnb": 4, "power": DEFAULT_POWER, "scheduler": DEFAULT_SCHEDULER, "queue_size": DEFAULT_QUEUE_SIZE},
]

# ===========================================================================
# 2. BASE INI TEMPLATE -- SAME GENERAL PARAMETERS AS YOUR EXAMPLE
# ===========================================================================
BASE_INI = r'''[General]
network = src.FiveGNetwork
sim-time-limit = 120s
#scheduler-class = "omnetpp::cRealTimeScheduler"

# --- Chemins ---
ned-path = ../src:../../Simu5G/src:../../inet4.5/src

# --- Config Réseau ---
*.configurator.typename = "Ipv4NetworkConfigurator"
*.configurator.addDefaultRoutes = true

# Désactiver les gros fichiers .vec/.sca OMNeT++
**.vector-recording = false
**.scalar-recording = false

# ---------------------------------------------------------------------------
# BLINDAGE TOTAL ANTI-DIALOGUE ET ANTI-PORT
# ---------------------------------------------------------------------------
**.masterId = 1
**.macCellId = 1
**.nrMasterId = 1
**.nrMacCellId = 1

# Délais de transmission
**.server.ppp[*].**.delay = 50ms
**.gnb[*].ppp[*].**.delay = 50ms

# Paramètres de Mobilité Globaux
**.initialZ = 0m
**.mobility.initFromDisplayString = false
**.mobility.updateInterval = 0.01s
**.constraintAreaMinX = 0m
**.constraintAreaMaxX = 1000m
**.constraintAreaMinY = 0m
**.constraintAreaMaxY = 1000m
**.constraintAreaMinZ = 0m
**.constraintAreaMaxZ = 100m
**.speedStdDev = 0mps
**.angleStdDev = 0deg
**.alpha = 0.5
**.margin = 10m

# --- CORRECTION DES PORTS ---
*.server.app[*].localPort = 1000 + ancestorIndex(0)
*.ue[*].app[0].localPort = 1000
**.startTime = 0.1s
**.stopTime = -1s

[Config Statistics]
**.channelModel = "UMA"
**.pathlossModel = "P3GPP38901"
**.transmitter.power = 0.01W
**.cellularNic.phy.receiver.noiseFigure = 5dB

# ---------------------------------------------------------------------------
# FIXED CONFIGURATION FOR LATENCY/SPEEDUP SCALING
# We do not sweep power/scheduler/queue size here, to isolate graph-size effect.
# ---------------------------------------------------------------------------
**.gnb[*].nic.phy.transmitter.power = {power}
**.gnb[*].cellularNic.mac.schedulingDisciplineDl = "{scheduler}"
**.gnb[*].cellularNic.mac.schedulingDisciplineUl = "{scheduler}"
**.gnb[*].cellularNic.numBands = 50

**.rlc.um.queueSize = {queue_size}
**.mac.queueSize = {queue_size}
'''

# Existing 4-gNB layout from your SC05 example.
GNB_POSITIONS = {
    0: (250, 250, 30),
    1: (750, 250, 30),
    2: (250, 750, 30),
    3: (750, 750, 30),
}

# Existing UE position ranges from your SC05 example, around each gNB quadrant.
CELL_BOUNDS = {
    0: (100, 400, 100, 400),
    1: (600, 900, 100, 400),
    2: (100, 400, 600, 900),
    3: (600, 900, 600, 900),
}

TRAFFIC_WEIGHTS = [
    ("EXPONENTIAL",   "GaussMarkov", 0.25),
    ("DETERMINISTIC", "Linear",      0.25),
    ("UNIFORM",       "Circle",      0.25),
    ("ONOFF",         "GaussMarkov", 0.125),
    ("PPBP",          "Linear",      0.125),
]

# ===========================================================================
# 3. SMALL HELPERS FOR INI GENERATION
# ===========================================================================
def range_expr(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}..{end}"


def split_evenly(total: int, groups: int):
    base = total // groups
    rem = total % groups
    counts = []
    start = 0
    for g in range(groups):
        count = base + (1 if g < rem else 0)
        end = start + count - 1
        counts.append((start, end, count))
        start = end + 1
    return counts


def traffic_counts_for_cell(k: int):
    raw = [(name, mob, k * w) for name, mob, w in TRAFFIC_WEIGHTS]
    floors = [(name, mob, int(math.floor(value)), value - math.floor(value)) for name, mob, value in raw]
    remaining = k - sum(item[2] for item in floors)
    order = sorted(range(len(floors)), key=lambda i: floors[i][3], reverse=True)
    counts = [item[2] for item in floors]
    for i in order[:remaining]:
        counts[i] += 1
    return [(TRAFFIC_WEIGHTS[i][0], TRAFFIC_WEIGHTS[i][1], counts[i]) for i in range(len(TRAFFIC_WEIGHTS)) if counts[i] > 0]


def mobility_paths(num_ue: int, num_gnb: int) -> str:
    ue_paths = [f"ue[{i}].mobility" for i in range(num_ue)]
    gnb_paths = [f"gnb[{i}].mobility" for i in range(num_gnb)]
    return ",".join(ue_paths + gnb_paths)


def gnb_config_lines(num_gnb: int):
    lines = []
    for g in range(num_gnb):
        x, y, z = GNB_POSITIONS[g]
        cell_id = g + 1
        lines += [
            f"*.gnb[{g}].mobility.typename = \"StationaryMobility\"",
            f"*.gnb[{g}].mobility.initialX = {x}m",
            f"*.gnb[{g}].mobility.initialY = {y}m",
            f"*.gnb[{g}].mobility.initialZ = {z}m",
            "",
            f"*.gnb[{g}].masterId = {cell_id}",
            f"*.gnb[{g}].macCellId = {cell_id}",
            f"*.gnb[{g}].nrMasterId = {cell_id}",
            f"*.gnb[{g}].nrMacCellId = {cell_id}",
            "",
        ]
    return lines


def association_lines(num_ue: int, num_gnb: int):
    lines = []
    cell_ranges = split_evenly(num_ue, num_gnb)
    for g, (start, end, count) in enumerate(cell_ranges):
        cell_id = g + 1
        r = range_expr(start, end)
        lines += [
            f"*.ue[{r}].masterId = {cell_id}",
            f"*.ue[{r}].macCellId = {cell_id}",
            f"*.ue[{r}].nrMasterId = {cell_id}",
            f"*.ue[{r}].nrMacCellId = {cell_id}",
            "",
        ]
    return lines, cell_ranges


def add_dl_app(lines, start, end, send_interval):
    r = range_expr(start, end)
    lines += [
        f"*.server.app[{r}].typename = \"UdpBasicApp\"",
        f"*.server.app[{r}].destAddresses = \"ue[\" + string(ancestorIndex(0)) + \"]\"",
        f"*.server.app[{r}].destPort = 1000",
        f"*.server.app[{r}].messageLength = 1450B",
        f"*.server.app[{r}].sendInterval = {send_interval}",
        f"*.ue[{r}].app[0].typename = \"UdpSink\"",
        "",
    ]


def add_ul_app(lines, start, end, send_interval):
    r = range_expr(start, end)
    lines += [
        f"*.ue[{r}].app[0].typename = \"UdpBasicApp\"",
        f"*.ue[{r}].app[0].destAddresses = \"server\"",
        f"*.ue[{r}].app[0].destPort = 1000 + ancestorIndex(1)",
        f"*.ue[{r}].app[0].messageLength = 1450B",
        f"*.ue[{r}].app[0].sendInterval = {send_interval}",
        f"*.server.app[{r}].typename = \"UdpSink\"",
        "",
    ]


def add_mobility(lines, start, end, mobility_type, gnb_index):
    r = range_expr(start, end)
    xmin, xmax, ymin, ymax = CELL_BOUNDS[gnb_index]
    cx, cy, _ = GNB_POSITIONS[gnb_index]

    if mobility_type == "GaussMarkov":
        # Speed range is set by traffic type after this function if needed.
        lines += [
            f"*.ue[{r}].mobility.typename = \"GaussMarkovMobility\"",
            f"*.ue[{r}].mobility.initialX = uniform({xmin}m, {xmax}m)",
            f"*.ue[{r}].mobility.initialY = uniform({ymin}m, {ymax}m)",
        ]
    elif mobility_type == "Linear":
        lines += [
            f"*.ue[{r}].mobility.typename = \"LinearMobility\"",
            f"*.ue[{r}].mobility.initialX = uniform({xmin}m, {xmax}m)",
            f"*.ue[{r}].mobility.initialY = uniform({ymin}m, {ymax}m)",
        ]
    elif mobility_type == "Circle":
        lines += [
            f"*.ue[{r}].mobility.typename = \"CircleMobility\"",
            f"*.ue[{r}].mobility.cx = {cx}m",
            f"*.ue[{r}].mobility.cy = {cy}m",
            f"*.ue[{r}].mobility.r = 180m",
            f"*.ue[{r}].mobility.speed = 25mps",
            "",
        ]


def traffic_and_mobility_lines(num_ue: int, num_gnb: int):
    lines = []
    metadata = {}
    _, cell_ranges = association_lines(num_ue, num_gnb)

    for gnb_index, (cell_start, cell_end, count) in enumerate(cell_ranges):
        cursor = cell_start
        for traffic_type, mobility_type, k in traffic_counts_for_cell(count):
            start = cursor
            end = cursor + k - 1
            cursor = end + 1
            r = range_expr(start, end)

            lines.append(f"# UEs {r}: {traffic_type} + {mobility_type} around gNB{gnb_index}")

            if traffic_type == "EXPONENTIAL":
                add_dl_app(lines, start, end, "exponential(0.001s)")
                add_mobility(lines, start, end, "GaussMarkov", gnb_index)
                lines += [f"*.ue[{r}].mobility.speed = uniform(20mps, 40mps)", ""]

            elif traffic_type == "DETERMINISTIC":
                add_ul_app(lines, start, end, "0.001s")
                add_mobility(lines, start, end, "Linear", gnb_index)
                lines += [
                    f"*.ue[{r}].mobility.speed = uniform(25mps, 45mps)",
                    f"*.ue[{r}].mobility.angle = uniform(0deg, 360deg)",
                    "",
                ]

            elif traffic_type == "UNIFORM":
                add_dl_app(lines, start, end, "uniform(0.001s, 0.005s)")
                add_mobility(lines, start, end, "Circle", gnb_index)

            elif traffic_type == "ONOFF":
                add_dl_app(lines, start, end, "uniform(0,1) < 0.8 ? 0.0002s : 0.4s")
                add_mobility(lines, start, end, "GaussMarkov", gnb_index)
                lines += [f"*.ue[{r}].mobility.speed = uniform(30mps, 60mps)", ""]

            elif traffic_type == "PPBP":
                add_dl_app(lines, start, end, "pareto(0.001s, 1.3)")
                add_mobility(lines, start, end, "Linear", gnb_index)
                lines += [
                    f"*.ue[{r}].mobility.speed = uniform(35mps, 70mps)",
                    f"*.ue[{r}].mobility.angle = uniform(0deg, 360deg)",
                    "",
                ]

            for ue in range(start, end + 1):
                metadata[f"ue{ue}"] = {"traffic_type": traffic_type, "mobility_type": mobility_type}

    return lines, metadata


def build_ini(scenario):
    num_ue = scenario["num_ue"]
    num_gnb = scenario["num_gnb"]

    if num_gnb > 4:
        raise ValueError("This script intentionally uses only the existing 4-gNB layout from SC05.")

    ini = BASE_INI.format(
        power=scenario["power"],
        scheduler=scenario["scheduler"],
        queue_size=scenario["queue_size"],
    )

    lines = [
        "",
        "# ---------------------------------------------------------------------------",
        f"# {scenario['name']} : {num_ue} UEs, {num_gnb} gNBs, latency/speedup scaling scenario",
        "# ---------------------------------------------------------------------------",
        "[Config DT-Scenario]",
        "extends = Statistics",
        "",
        f"*.numUe = {num_ue}",
        f"*.numGnb = {num_gnb}",
        f"*.server.numApps = {num_ue}",
        "*.ue[*].numApps = 1",
        "",
        f"*.dtConnector.numMobilityModules = {num_ue + num_gnb}",
        "*.dtConnector.samplingInterval = 0.1s",
        f"*.dtConnector.mobilityModulePaths = \"{mobility_paths(num_ue, num_gnb)}\"",
        "",
        "# gNB positions and cell identifiers",
    ]

    lines += gnb_config_lines(num_gnb)
    assoc, _ = association_lines(num_ue, num_gnb)
    lines += ["# UE-to-gNB associations"] + assoc

    tm_lines, metadata = traffic_and_mobility_lines(num_ue, num_gnb)
    lines += [
        "# Traffic and mobility patterns",
        "# Types conserved: EXPONENTIAL, DETERMINISTIC, UNIFORM, ONOFF, PPBP",
        "# Mobilities conserved: GaussMarkov, Linear, Circle",
        "",
    ] + tm_lines

    return ini + "\n".join(lines) + "\n", metadata

# ===========================================================================
# 4. JSON POST-PROCESSING -- SAME SPIRIT AS YOUR WORKING SCRIPT
# ===========================================================================
def decrement_gnb_name(name):
    if not name or str(name).lower() == "none":
        return name
    match = re.match(r"([a-zA-Z]+)(\d+)", str(name))
    if match:
        return f"{match.group(1)}{max(0, int(match.group(2)) - 1)}"
    return name


def load_json_safely(input_path):
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    pattern = re.compile(
        r'(?P<prefix>[:\[,]\s*)(?P<value>[+-]?(?:nan|inf|infinity))(?P<suffix>\s*[,}\]])',
        re.IGNORECASE,
    )
    raw = pattern.sub(lambda m: m.group("prefix") + "0.0" + m.group("suffix"), raw)
    return json.loads(raw)


def sanitize_positive_numbers(obj):
    if isinstance(obj, dict):
        return {k: sanitize_positive_numbers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_positive_numbers(v) for v in obj]
    if isinstance(obj, float):
        if not math.isfinite(obj) or obj < 0:
            return 0.0
        return obj
    if isinstance(obj, int):
        if obj < 0:
            return 0
        return obj
    return obj


def process_simulation_json(input_path, output_path, power, sched, queue, ue_metadata):
    if not os.path.exists(input_path):
        return False

    data = load_json_safely(input_path)
    data = sanitize_positive_numbers(data)

    for entry in data:
        if "nodes" in entry:
            for node in entry["nodes"]:
                node_id = node.get("id", "")

                if "serving_gnb" in node:
                    node["serving_gnb"] = decrement_gnb_name(node["serving_gnb"])

                if node_id.startswith("gnb"):
                    node.update({
                        "tx_power": power,
                        "scheduling_discipline": sched,
                        "queue_size": queue,
                    })
                    node.pop("sinr_dl", None)
                    node.pop("sinr_ul", None)

                elif node_id.startswith("ue"):
                    meta = ue_metadata.get(node_id, {"traffic_type": "Unknown", "mobility_type": "Unknown"})
                    node.update({
                        "qsize": queue,
                        "traffic_type": meta["traffic_type"],
                        "mobility_type": meta["mobility_type"],
                    })
                    node.pop("app", None)
                    node.pop("bler", None)

        if "flows" in entry:
            for flow in entry["flows"]:
                flow.pop("app", None)
                flow.pop("bler", None)
                flow.pop("endToEndDelay", None)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return True


def count_snapshots(json_path):
    if not os.path.exists(json_path):
        return 0
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0

# ===========================================================================
# 5. RUNTIME LOGGING
# ===========================================================================
def init_runtime_summary_csv():
    if os.path.exists(RUNTIME_SUMMARY_CSV):
        return
    with open(RUNTIME_SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "iteration", "scenario", "run", "folder_name",
            "num_ue", "num_gnb", "power", "scheduler", "queue_size",
            "status", "start_datetime", "end_datetime",
            "simulation_time_s", "processing_time_s", "total_pipeline_time_s",
            "num_snapshots", "error",
        ])


def write_runtime_json(folder_name, runtime_info):
    with open(os.path.join(folder_name, "runtime.json"), "w", encoding="utf-8") as f:
        json.dump(runtime_info, f, indent=2)


def append_runtime_summary(runtime_info):
    with open(RUNTIME_SUMMARY_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            runtime_info.get("iteration", ""),
            runtime_info.get("scenario", ""),
            runtime_info.get("run", ""),
            runtime_info.get("folder_name", ""),
            runtime_info.get("num_ue", ""),
            runtime_info.get("num_gnb", ""),
            runtime_info.get("power", ""),
            runtime_info.get("scheduler", ""),
            runtime_info.get("queue_size", ""),
            runtime_info.get("status", ""),
            runtime_info.get("start_datetime", ""),
            runtime_info.get("end_datetime", ""),
            runtime_info.get("simulation_time_s", ""),
            runtime_info.get("processing_time_s", ""),
            runtime_info.get("total_pipeline_time_s", ""),
            runtime_info.get("num_snapshots", ""),
            runtime_info.get("error", ""),
        ])

# ===========================================================================
# 6. MAIN AUTOMATION LOOP
# ===========================================================================
def run_all_scenarios():
    if not os.path.exists(PROJECT_BINARY):
        print(f"ERREUR : Binaire introuvable à {PROJECT_BINARY}")
        return

    Path(GENERATED_INI_DIR).mkdir(exist_ok=True)
    init_runtime_summary_csv()

    total = len(SCENARIOS) * RUNS_PER_SCENARIO
    iteration = 1

    for scenario in SCENARIOS:
        ini_text, ue_metadata = build_ini(scenario)

        for run_id in range(RUNS_PER_SCENARIO):
            folder_name = (
                f"{iteration:02d}){SCENARIO_PREFIX}-{scenario['name']}-"
                f"U={scenario['num_ue']}-G={scenario['num_gnb']}-"
                f"P={scenario['power']}-S={scenario['scheduler']}-Q={scenario['queue_size']}-R={run_id}"
            ).replace(" ", "")

            print(f"\n🚀 SIMULATION {iteration}/{total} : {folder_name}")
            os.makedirs(folder_name, exist_ok=True)

            output_json = os.path.join(folder_name, "data.json")
            if SKIP_SUCCESS and os.path.exists(output_json):
                print(f"   ⏭️ Déjà généré, skip : {folder_name}")
                iteration += 1
                continue

            ini_file = os.path.join(GENERATED_INI_DIR, f"omnetpp_{scenario['name']}_R{run_id}.ini")
            with open(ini_file, "w", encoding="utf-8") as f:
                f.write(ini_text)

            command = [
                PROJECT_BINARY, "-u", "Cmdenv", "-c", CONFIG_NAME, "-r", "0",
                "-n", NED_PATH, "-l", LIB_INET, "-l", LIB_SIMU5G, f"--seed-set={run_id}",
                f"--**.gnb[*].nic.phy.transmitter.power={scenario['power']}",
                f"--**.gnb[*].cellularNic.mac.schedulingDisciplineDl=\"{scenario['scheduler']}\"",
                f"--**.gnb[*].cellularNic.mac.schedulingDisciplineUl=\"{scenario['scheduler']}\"",
                f"--**.rlc.um.queueSize={scenario['queue_size']}",
                f"--**.mac.queueSize={scenario['queue_size']}",
                ini_file,
            ]

            start_datetime = datetime.now().isoformat(timespec="seconds")
            total_start = time.perf_counter()
            simulation_time_s = 0.0
            processing_time_s = 0.0
            num_snapshots = 0
            status = "FAILED"
            error_msg = ""

            try:
                # Clean stale raw JSON from a previous failed run.
                if os.path.exists(RAW_JSON):
                    os.remove(RAW_JSON)

                sim_start = time.perf_counter()
                subprocess.run(command, check=True)
                sim_end = time.perf_counter()
                simulation_time_s = sim_end - sim_start

                proc_start = time.perf_counter()
                if process_simulation_json(
                    RAW_JSON, output_json,
                    scenario["power"], scenario["scheduler"], scenario["queue_size"], ue_metadata,
                ):
                    shutil.copy(ini_file, os.path.join(folder_name, "omnetpp.ini"))
                    num_snapshots = count_snapshots(output_json)
                    if os.path.exists(RAW_JSON):
                        os.remove(RAW_JSON)
                    status = "SUCCESS"
                    print("   ✅ JSON traité.")
                else:
                    error_msg = f"Fichier {RAW_JSON} non trouvé."
                    print(f"   ⚠️ {error_msg}")
                proc_end = time.perf_counter()
                processing_time_s = proc_end - proc_start

            except subprocess.CalledProcessError as e:
                status = "FAILED_SIMULATION"
                error_msg = str(e)
                print(f"   ❌ Erreur de simulation : {e}")

            except Exception as e:
                status = "FAILED_OTHER"
                error_msg = str(e)
                print(f"   ⚠️ Erreur inattendue : {e}")

            finally:
                total_end = time.perf_counter()
                end_datetime = datetime.now().isoformat(timespec="seconds")

                runtime_info = {
                    "iteration": iteration,
                    "scenario": scenario["name"],
                    "run": run_id,
                    "folder_name": folder_name,
                    "num_ue": scenario["num_ue"],
                    "num_gnb": scenario["num_gnb"],
                    "power": scenario["power"],
                    "scheduler": scenario["scheduler"],
                    "queue_size": scenario["queue_size"],
                    "status": status,
                    "start_datetime": start_datetime,
                    "end_datetime": end_datetime,
                    "simulation_time_s": round(simulation_time_s, 6),
                    "processing_time_s": round(processing_time_s, 6),
                    "total_pipeline_time_s": round(total_end - total_start, 6),
                    "num_snapshots": num_snapshots,
                    "ini_file": ini_file,
                    "command": command,
                    "error": error_msg,
                }

                write_runtime_json(folder_name, runtime_info)
                append_runtime_summary(runtime_info)

                print(f"   ⏱️ Temps simulation : {runtime_info['simulation_time_s']} s")
                print(f"   ⏱️ Temps processing  : {runtime_info['processing_time_s']} s")
                print(f"   ⏱️ Temps total       : {runtime_info['total_pipeline_time_s']} s")
                print(f"   📸 Snapshots         : {runtime_info['num_snapshots']}")
                print(f"   📝 Runtime sauvé dans: {os.path.join(folder_name, 'runtime.json')}")

            iteration += 1


if __name__ == "__main__":
    run_all_scenarios()
