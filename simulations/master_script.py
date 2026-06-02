import os
import json
import re
import subprocess
import matplotlib.pyplot as plt
import shutil
import time
import csv
from datetime import datetime

# ===========================================================================
# 1. CONFIGURATION DES MÉTADONNÉES
# ===========================================================================
def get_ue_metadata(ue_id_string):
    """
    Associe un type de trafic et de mobilité à chaque UE selon son index.
    Les UEs 0..14 suivent la logique originale.
    Les UEs 15..29 répètent exactement la même logique avec index % 15.
    """
    match = re.search(r'\d+', ue_id_string)
    if not match:
        return {"traffic_type": "Unknown", "mobility_type": "Unknown"}

    index = int(match.group())
    group = index % 15

    if 0 <= group <= 2:
        return {"traffic_type": "EXPONENTIAL", "mobility_type": "GaussMarkov"}

    elif 3 <= group <= 4:
        return {"traffic_type": "DETERMINISTIC", "mobility_type": "Linear"}

    elif 5 <= group <= 6:
        return {"traffic_type": "UNIFORM", "mobility_type": "Circle"}

    elif 7 <= group <= 8:
        return {"traffic_type": "DETERMINISTIC", "mobility_type": "Stationary"}

    elif group == 9:
        return {"traffic_type": "ONOFF", "mobility_type": "GaussMarkov"}

    elif 10 <= group <= 11:
        return {"traffic_type": "PPBP", "mobility_type": "Linear"}

    elif group == 12:
        return {"traffic_type": "DETERMINISTIC", "mobility_type": "Circle"}

    elif group == 13:
        return {"traffic_type": "DETERMINISTIC", "mobility_type": "Stationary"}

    elif group == 14:
        return {"traffic_type": "DETERMINISTIC", "mobility_type": "GaussMarkov"}

    else:
        return {"traffic_type": "DETERMINISTIC", "mobility_type": "Stationary"}

# ===========================================================================
# 2. PARAMÈTRES DE VARIATION ET CHEMINS
# ===========================================================================
POWERS = ["0.5W"]
SCHEDULERS = ["PF", "MAXCI", "DRR"]
QUEUE_SIZES = ["2MiB"]

SCENARIO_PREFIX = "test2_embb"
INI_FILE = "omnetpp.ini"
CONFIG_NAME = "DT-Scenario"

PROJECT_BINARY = "../out/clang-release/FiveG_network"
NED_PATH = "../src:../../Simu5G/src:../../inet4.5/src"
LIB_INET = "../../inet4.5/src/INET"
LIB_SIMU5G = "../../Simu5G/src/simu5g"

RUNTIME_SUMMARY_CSV = "runtime_generation_summary.csv"

# ===========================================================================
# 3. FONCTIONS DE TRAITEMENT ET NETTOYAGE DU JSON
# ===========================================================================
def decrement_gnb_name(name):
    """Transforme 'gnb1' en 'gnb0'."""
    if not name or name.lower() == "none":
        return name
    match = re.match(r"([a-zA-Z]+)(\d+)", name)
    if match:
        return f"{match.group(1)}{max(0, int(match.group(2)) - 1)}"
    return name


def process_simulation_json(input_path, output_path, power, sched, queue):
    """Nettoie le JSON brut et ajoute les attributs demandés."""
    if not os.path.exists(input_path):
        return False

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

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

    target_ues = ["ue0", "ue4", "ue8", "ue12", "ue14", "ue15", "ue19", "ue23", "ue27", "ue29"]
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