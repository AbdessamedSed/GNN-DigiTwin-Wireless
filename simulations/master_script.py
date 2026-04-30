import os
import json
import re
import subprocess
import matplotlib.pyplot as plt
import shutil

# ===========================================================================
# 1. CONFIGURATION DES MÉTADONNÉES (TRAFIC ET MOBILITÉ)
# ===========================================================================
def get_ue_metadata(ue_id_string):
    """
    Associe un type de trafic et de mobilité à chaque UE selon son index.
    """
    match = re.search(r'\d+', ue_id_string)
    if not match:
        return {"traffic_type": "Unknown", "mobility_type": "Unknown"}
    
    index = int(match.group())
    
    if 0 <= index <= 2:
        return {
            "traffic_type": "EXPONENTIAL",
            "mobility_type": "GaussMarkov"
        }
    
    # --- [DETERMINISTIC] : UEs 3, 4, 5 ---
    elif 3 <= index <= 5:
        return {
            "traffic_type": "DETERMINISTIC",
            "mobility_type": "Stationary"
        }
    
    # --- [UNIFORM] : UEs 6, 7, 8 ---
    elif 6 <= index <= 8:
        return {
            "traffic_type": "UNIFORM",
            "mobility_type": "Circle"
        }
    
    # --- [NORMAL] : UEs 9, 10, 11 ---
    elif 9 <= index <= 11:
        return {
            "traffic_type": "NORMAL",
            "mobility_type": "Linear"
        }
    
    # --- [ONOFF] : UEs 12, 13, 14 ---
    elif 12 <= index <= 14:
        return {
            "traffic_type": "ONOFF",
            "mobility_type": "GaussMarkov"
        }
    
    # --- [PPBP / PARETO] : UEs 15, 16, 17 ---
    elif 15 <= index <= 17:
        return {
            "traffic_type": "PPBP",
            "mobility_type": "Stationary"
        }
    
    # --- [AR1 / AUTOREGRESSIVE] : UEs 18, 19 ---
    elif 18 <= index <= 19:
        return {
            "traffic_type": "AR1",
            "mobility_type": "Linear"
        }
    
    # Cas par défaut
    else:
        return {
            "traffic_type": "DETERMINISTIC",
            "mobility_type": "Stationary"
        }

# ===========================================================================
# 2. PARAMÈTRES DE VARIATION ET CHEMINS
# ===========================================================================
# Valeurs pour la boucle d'automatisation
POWERS = ["0.01W", "0.1W", "0.5W", "2W"]
SCHEDULERS = ["PF", "MAXCI", "DRR",  "QOS_PF", "MAXCI_MB", "ALLOCATOR_BESTFIT"]
QUEUE_SIZES = ["50KiB", "100KiB", "2MiB", "10MiB"]

SCENARIO_PREFIX = "SC01"
INI_FILE = "omnetpp.ini"
CONFIG_NAME = "DT-Scenario"

# Chemins vers les outils OMNeT++ (Ajustez si nécessaire)
PROJECT_BINARY = "../out/clang-release/FiveG_network"
NED_PATH = "../src:../../Simu5G/src:../../inet4.5/src"
LIB_INET = "../../inet4.5/src/INET"
LIB_SIMU5G = "../../Simu5G/src/simu5g"

# ===========================================================================
# 3. FONCTIONS DE TRAITEMENT ET NETTOYAGE DU JSON
# ===========================================================================
def decrement_gnb_name(name):
    """Transforme 'gnb1' en 'gnb0'"""
    if not name or name.lower() == "none":
        return name
    match = re.match(r"([a-zA-Z]+)(\d+)", name)
    if match:
        return f"{match.group(1)}{max(0, int(match.group(2)) - 1)}"
    return name

def process_simulation_json(input_path, output_path, power, sched, queue):
    """Nettoie le JSON brut et ajoute les attributs demandés"""
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
                    node.update({"tx_power": power, "scheduling_discipline": sched, "queue_size": queue})
                    node.pop("sinr_dl", None)
                    node.pop("sinr_ul", None)
                elif node_id.startswith("ue"):
                    meta = get_ue_metadata(node_id)
                    node.update({"qsize": queue, "traffic_type": meta["traffic_type"], "mobility_type": meta["mobility_type"]})
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
# 4. GÉNÉRATION DES GRAPHIQUES (FIXED : THROUGHPUT & DELAY)
# ===========================================================================
def generate_real_plots(json_path, output_folder):
    """Génère les graphiques en extrayant les données des nodes et des flows"""
    if not os.path.exists(json_path):
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    os.makedirs(output_folder, exist_ok=True)
    target_ues = ["ue0", "ue4", "ue8", "ue12", "ue13", "ue14"]
    metrics = ["throughput", "delay", "sinr_ul", "sinr_dl", "x", "y" , "rlcDelay", "rlcThroughput"]

    for metric in metrics:
        plt.figure(figsize=(12, 6))
        any_data_for_metric = False
        
        for target_ue in target_ues:
            timestamps = []
            values = []
            # Format pour chercher dans les flows (ex: ue0 -> ue[0])
            ue_idx = re.search(r'\d+', target_ue).group()
            ue_flow_format = f"ue[{ue_idx}]"
            
            for entry in data:
                ts = entry["timestamp"]
                
                # A. Recherche dans NODES (pour sinr_dl, speed)
                for node in entry.get("nodes", []):
                    if node["id"] == target_ue and metric in node:
                        timestamps.append(ts)
                        values.append(node[metric])
                
                # B. Recherche dans FLOWS (pour throughput, delay)
                for flow in entry.get("flows", []):
                    # On vérifie si l'UE est la source ou la destination du flux
                    if flow.get("src") == ue_flow_format or flow.get("dst") == ue_flow_format:
                        if metric in flow:
                            timestamps.append(ts)
                            values.append(flow[metric])

            if timestamps:
                # Tri des données par temps pour un affichage correct
                sorted_points = sorted(zip(timestamps, values))
                ts_sorted, val_sorted = zip(*sorted_points)
                
                label_meta = get_ue_metadata(target_ue)["traffic_type"]
                plt.plot(ts_sorted, val_sorted, label=f"{target_ue} ({label_meta})", linewidth=1.5, marker='o', markersize=2)
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
# 5. BOUCLE PRINCIPALE D'AUTOMATISATION
# ===========================================================================
def run_all_scenarios():
    if not os.path.exists(PROJECT_BINARY):
        print(f"ERREUR : Binaire introuvable à {PROJECT_BINARY}")
        return

    iteration = 1
    for p in POWERS:
        for s in SCHEDULERS:
            for q in QUEUE_SIZES:
                # Création du nom de dossier propre
                folder_name = f"{iteration:02d}){SCENARIO_PREFIX}-P={p}-S={s}-Q={q}".replace(" ", "")
                print(f"\n🚀 SIMULATION {iteration}/27 : {folder_name}")
                os.makedirs(folder_name, exist_ok=True)

                # Construction de la commande (Ajout de -r 0 pour forcer un seul run à la fois)
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

                try:
                    # Lancement effectif de OMNeT++
                    subprocess.run(command, check=True)

                    # Gestion des fichiers après simulation
                    raw_json = "network_state.json"
                    output_json = os.path.join(folder_name, "data.json")
                    plots_dir = os.path.join(folder_name, "plots")

                    if process_simulation_json(raw_json, output_json, p, s, q):
                        print(f"   ✅ JSON traité.")
                        generate_real_plots(output_json, plots_dir)
                        print(f"   📈 Graphiques créés.")
                        shutil.copy(INI_FILE, os.path.join(folder_name, "omnetpp.ini"))
                        
                        # Nettoyage pour le prochain run
                        if os.path.exists(raw_json):
                            os.remove(raw_json)
                    else:
                        print(f"   ⚠️ Fichier {raw_json} non trouvé.")

                except subprocess.CalledProcessError as e:
                    print(f"   ❌ Erreur de simulation : {e}")
                except Exception as e:
                    print(f"   ⚠️ Erreur inattendue : {e}")

                iteration += 1

if __name__ == "__main__":
    run_all_scenarios()