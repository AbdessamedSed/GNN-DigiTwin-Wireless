import os
import json
import re
import subprocess
import matplotlib.pyplot as plt
import shutil
import time
import csv
import math
from datetime import datetime

# ===========================================================================
# 1. CONFIGURATION DES MÉTADONNÉES SC07
# ===========================================================================
def get_ue_metadata(ue_id_string):
    """
    Associe un type de trafic et de mobilité à chaque UE selon son index.
    Les labels restent compatibles avec la logique utilisée dans les autres scripts.
    """
    match = re.search(r'\d+', ue_id_string)
    if not match:
        return {"traffic_type": "Unknown", "mobility_type": "Unknown"}

    index = int(match.group())

    if 0 <= index <= 11:
        return {"traffic_type": "EXPONENTIAL", "mobility_type": "GaussMarkov"}

    elif 12 <= index <= 23:
        return {"traffic_type": "DETERMINISTIC", "mobility_type": "Linear"}

    elif 24 <= index <= 35:
        return {"traffic_type": "UNIFORM", "mobility_type": "Circle"}

    elif 36 <= index <= 47:
        return {"traffic_type": "ONOFF", "mobility_type": "GaussMarkov"}

    elif 48 <= index <= 59:
        return {"traffic_type": "PPBP", "mobility_type": "Linear"}

    else:
        return {"traffic_type": "Unknown", "mobility_type": "Unknown"}

# ===========================================================================
# 2. PARAMÈTRES DE VARIATION ET CHEMINS
# ===========================================================================
POWERS = ["0.01W", "0.1W", "0.5W", "2W"]
SCHEDULERS = ["PF", "MAXCI", "DRR", "QOS_PF", "MAXCI_MB", "ALLOCATOR_BESTFIT"]
QUEUE_SIZES = ["50 KiB", "100KiB", "2MiB", "10MiB"]

SCENARIO_PREFIX = "SC07"
INI_FILE = "omnetpp.ini"
CONFIG_NAME = "DT-Scenario"

PROJECT_BINARY = "../out/clang-release/FiveG_network"
NED_PATH = "../src:/home/abdessamedseddiki/omnet/simu5g-1.4.1/src:/home/abdessamedseddiki/omnet/inet4.5/src"
LIB_INET = "../../inet4.5/src/INET"
LIB_SIMU5G = "../../simu5g-1.4.1/src/simu5g"
RUNTIME_SUMMARY_CSV = "runtime_generation_summary.csv"

# Si True, le script saute les configurations qui ont déjà un data.json
SKIP_SUCCESS = True

# ===========================================================================
# 3. FONCTIONS DE TRAITEMENT ET NETTOYAGE DU JSON
# ===========================================================================
def decrement_gnb_name(name):
    """Transforme 'gnb1' en 'gnb0', 'gnb2' en 'gnb1', etc."""
    if not name or name.lower() == "none":
        return name
    match = re.match(r"([a-zA-Z]+)(\d+)", name)
    if match:
        return f"{match.group(1)}{max(0, int(match.group(2)) - 1)}"
    return name


def load_json_safely(input_path):
    """
    Charge le JSON OMNeT++ même s'il contient nan, inf, -inf, etc.
    Tous ces tokens invalides sont remplacés par 0.0 avant json.loads().
    """
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    pattern = re.compile(
        r'(?P<prefix>[:\[,]\s*)(?P<value>[+-]?(?:nan|inf|infinity))(?P<suffix>\s*[,}\]])',
        re.IGNORECASE
    )

    raw = pattern.sub(lambda m: m.group("prefix") + "0.0" + m.group("suffix"), raw)

    return json.loads(raw)


def sanitize_positive_numbers(obj):
    """
    Parcourt récursivement le JSON.
    Toute valeur numérique invalide, NaN, inf, -inf, ou négative devient 0.
    Les chaînes comme qsize, traffic_type, mobility_type ne sont pas modifiées.
    """
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


def process_simulation_json(input_path, output_path, power, sched, queue):
    """Nettoie le JSON brut et ajoute les attributs demandés."""
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
                        "queue_size": queue
                    })
                    node.pop("sinr_dl", None)
                    node.pop("sinr_ul", None)

                elif node_id.startswith("ue"):
                    meta = get_ue_metadata(node_id)
                    node.update({
                        "qsize": queue,
                        "traffic_type": meta["traffic_type"],
                        "mobility_type": meta["mobility_type"]
                    })
                    node.pop("app", None)
                    node.pop("bler", None)

        if "flows" in entry:
            for flow in entry["flows"]:
                flow.pop("app", None)
                flow.pop("bler", None)
                flow.pop("endToEndDelay", None)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return True

# ===========================================================================
# 4. GÉNÉRATION DES GRAPHIQUES
# ===========================================================================
def generate_real_plots(json_path, output_folder):
    """Génère les graphiques en extrayant les données des nodes et des flows."""
    if not os.path.exists(json_path):
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    os.makedirs(output_folder, exist_ok=True)

    target_ues = ["ue0", "ue10", "ue12", "ue23", "ue24", "ue35", "ue36", "ue47", "ue48", "ue59"]
    metrics = ["throughput", "delay", "sinr_ul", "sinr_dl", "x", "y", "rlcDelay", "rlcThroughput"]

    for metric in metrics:
        plt.figure(figsize=(12, 6))
        any_data_for_metric = False

        for target_ue in target_ues:
            timestamps = []
            values = []

            ue_idx = re.search(r'\d+', target_ue).group()
            ue_flow_format = f"ue[{ue_idx}]"

            for entry in data:
                ts = entry["timestamp"]

                for node in entry.get("nodes", []):
                    if node["id"] == target_ue and metric in node:
                        timestamps.append(ts)
                        values.append(node[metric])

                for flow in entry.get("flows", []):
                    if flow.get("src") == ue_flow_format or flow.get("dst") == ue_flow_format:
                        if metric in flow:
                            timestamps.append(ts)
                            values.append(flow[metric])

            if timestamps:
                sorted_points = sorted(zip(timestamps, values))
                ts_sorted, val_sorted = zip(*sorted_points)

                label_meta = get_ue_metadata(target_ue)["traffic_type"]
                plt.plot(
                    ts_sorted,
                    val_sorted,
                    label=f"{target_ue} ({label_meta})",
                    linewidth=1.5,
                    marker='o',
                    markersize=2
                )
                any_data_for_metric = True

        if any_data_for_metric:
            plt.title(f"Évolution Métrique : {metric.upper()}")
            plt.xlabel("Temps (s)")
            plt.ylabel(metric)
            plt.grid(True, linestyle="--", alpha=0.6)
            plt.legend(loc="best")
            plt.savefig(os.path.join(output_folder, f"graph_{metric}.png"))

        plt.close()

# ===========================================================================
# 5. FONCTIONS POUR LE TEMPS RÉEL DE GÉNÉRATION
# ===========================================================================
def init_runtime_summary_csv():
    """Crée le fichier CSV global de runtime s'il n'existe pas."""
    if os.path.exists(RUNTIME_SUMMARY_CSV):
        return

    with open(RUNTIME_SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "iteration",
            "folder_name",
            "power",
            "scheduler",
            "queue_size",
            "status",
            "start_datetime",
            "end_datetime",
            "simulation_time_s",
            "processing_time_s",
            "total_pipeline_time_s",
            "num_snapshots",
            "error"
        ])


def count_snapshots(json_path):
    """Compte le nombre de snapshots dans data.json."""
    if not os.path.exists(json_path):
        return 0

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return len(data)
        return 0
    except Exception:
        return 0


def write_runtime_json(folder_name, runtime_info):
    """Écrit un runtime.json dans le dossier de la configuration."""
    runtime_path = os.path.join(folder_name, "runtime.json")
    with open(runtime_path, "w", encoding="utf-8") as f:
        json.dump(runtime_info, f, indent=2)


def append_runtime_summary(runtime_info):
    """Ajoute une ligne dans le CSV global."""
    with open(RUNTIME_SUMMARY_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            runtime_info.get("iteration", ""),
            runtime_info.get("folder_name", ""),
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
            runtime_info.get("error", "")
        ])

# ===========================================================================
# 6. BOUCLE PRINCIPALE D'AUTOMATISATION
# ===========================================================================
def run_all_scenarios():
    if not os.path.exists(PROJECT_BINARY):
        print(f"ERREUR : Binaire introuvable à {PROJECT_BINARY}")
        return

    init_runtime_summary_csv()

    total = len(POWERS) * len(SCHEDULERS) * len(QUEUE_SIZES)
    iteration = 1

    for p in POWERS:
        for s in SCHEDULERS:
            for q in QUEUE_SIZES:
                folder_name = f"{iteration:02d}){SCENARIO_PREFIX}-P={p}-S={s}-Q={q}".replace(" ", "")
                print(f"\n🚀 SIMULATION {iteration}/{total} : {folder_name}")

                os.makedirs(folder_name, exist_ok=True)

                output_json_existing = os.path.join(folder_name, "data.json")
                if SKIP_SUCCESS and os.path.exists(output_json_existing):
                    print(f"   ⏭️ Déjà généré, skip : {folder_name}")
                    iteration += 1
                    continue

                command = [
                    PROJECT_BINARY, "-u", "Cmdenv", "-c", CONFIG_NAME, "-r", "0",
                    "-n", NED_PATH, "-l", LIB_INET, "-l", LIB_SIMU5G,
                    f"--**.gnb[*].nic.phy.transmitter.power={p}",
                    f"--**.gnb[*].cellularNic.mac.schedulingDisciplineDl=\"{s}\"",
                    f"--**.gnb[*].cellularNic.mac.schedulingDisciplineUl=\"{s}\"",
                    f"--**.rlc.um.queueSize={q}",
                    f"--**.mac.queueSize={q}",
                    INI_FILE
                ]

                start_datetime = datetime.now().isoformat(timespec="seconds")
                total_start = time.perf_counter()

                simulation_time_s = 0.0
                processing_time_s = 0.0
                total_pipeline_time_s = 0.0
                num_snapshots = 0
                status = "FAILED"
                error_msg = ""

                try:
                    sim_start = time.perf_counter()
                    subprocess.run(command, check=True)
                    sim_end = time.perf_counter()
                    simulation_time_s = sim_end - sim_start

                    proc_start = time.perf_counter()

                    raw_json = "network_state.json"
                    output_json = os.path.join(folder_name, "data.json")
                    plots_dir = os.path.join(folder_name, "plots")

                    if process_simulation_json(raw_json, output_json, p, s, q):
                        print("   ✅ JSON traité.")
                        # generate_real_plots(output_json, plots_dir)
                        # print("   📈 Graphiques créés.")
                        shutil.copy(INI_FILE, os.path.join(folder_name, "omnetpp.ini"))

                        num_snapshots = count_snapshots(output_json)

                        if os.path.exists(raw_json):
                            os.remove(raw_json)

                        status = "SUCCESS"
                    else:
                        error_msg = f"Fichier {raw_json} non trouvé."
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
                    total_pipeline_time_s = total_end - total_start
                    end_datetime = datetime.now().isoformat(timespec="seconds")

                    runtime_info = {
                        "iteration": iteration,
                        "folder_name": folder_name,
                        "power": p,
                        "scheduler": s,
                        "queue_size": q,
                        "status": status,
                        "start_datetime": start_datetime,
                        "end_datetime": end_datetime,
                        "simulation_time_s": round(simulation_time_s, 6),
                        "processing_time_s": round(processing_time_s, 6),
                        "total_pipeline_time_s": round(total_pipeline_time_s, 6),
                        "num_snapshots": num_snapshots,
                        "command": command,
                        "error": error_msg
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