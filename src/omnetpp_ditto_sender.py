import socket
import json
import os
import time
import subprocess
import sys

# --- CONFIGURATION PAR DÉFAUT ---
DEFAULT_FREQ = 200
UDP_IP_DEST = "10.255.0.1"
UDP_IP_SRC = "10.255.0.1"
UDP_PORT = 9999
INTERFACE = "veth-sender"

# Configuration n°2 forcée (5G URLLC)
CONFIG_AUTO = {
    "desc": "5G URLLC", 
    "delay": "5ms", 
    "loss": "0.001%", 
    "rate": "500mbit", 
    "corrupt": "0.1%"
}

# Chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# On remonte d'un cran pour trouver network_state.json dans simulations/
JSON_PATH = os.path.join(SCRIPT_DIR, "..", "simulations", "network_state.json")
SENT_LOG_PATH = os.path.join(SCRIPT_DIR, "sent_packet_ids.txt")

def apply_network_conditions(config):
    """Applique la configuration TC sans demander à l'utilisateur."""
    print(f"\n[TC] Configuration automatique : {config['desc']}")
    # Nettoyage
    subprocess.run(f"sudo tc qdisc del dev {INTERFACE} root 2>/dev/null || true", shell=True)
    # Application des délais, pertes et débit
    cmd = f"sudo tc qdisc add dev {INTERFACE} root netem delay {config['delay']} loss {config['loss']} rate {config['rate']}"
    if config.get("corrupt") and config["corrupt"] != "0%":
        cmd += f" corrupt {config['corrupt']}"
    subprocess.run(cmd, shell=True)
    print(f"[TC] {config['desc']} appliqué avec succès.")

def main():
    # 1. Récupération de la fréquence via l'orchestrateur
    global_freq = DEFAULT_FREQ
    if len(sys.argv) > 1:
        try:
            global_freq = float(sys.argv[1])
        except ValueError:
            print(f"Usage: sudo python3 {sys.argv[0]} [frequency_hz]")
    
    if os.getuid() != 0:
        print("❌ Erreur: sudo requis pour TC et l'accès à l'interface réseau."); sys.exit(1)

    # 2. Application automatique de la Config n°2
    apply_network_conditions(CONFIG_AUTO)

    # Initialisation du log
    with open(SENT_LOG_PATH, "w") as f:
        f.write("SnapshotID\tTimestampMS\tSimTime\tStatus\n")

    print(f"\n🚀 SENDER AUTO - Fréquence : {global_freq} Hz")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP_SRC, 0))
    # Liaison à l'interface virtuelle
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, INTERFACE.encode())
    except Exception as e:
        print(f"⚠️ Warning: Liaison interface échouée ({e}), envoi via routage standard.")

    last_sent_t = -1.0
    snapshot_id = 0
    interval = 1.0 / global_freq

    try:
        while True:
            start_loop = time.time()
            
            if os.path.exists(JSON_PATH):
                try:
                    with open(JSON_PATH, "r") as f:
                        data = json.load(f)
                        last_state = data[-1] if isinstance(data, list) else data
                        
                        current_t = float(last_state.get("timestamp", 0))

                        # Envoi uniquement si nouveau timestamp simulation
                        if current_t > last_sent_t:
                            # Construction du paquet complet (Nodes + Flows)
                            nodes_lite = []
                            for n in last_state.get("nodes", []):
                                nodes_lite.append({
                                    "id": n["id"],
                                    "x": n["x"],
                                    "y": n["y"],
                                    "z": n.get("z", 1.5),
                                    "sinr_dl": n.get("sinr_dl", 0),
                                    "sinr_ul": n.get("sinr_ul", 0),
                                    "speed": n.get("speed", 0)
                                })

                            flows_lite = []
                            for f in last_state.get("flows", []):
                                flows_lite.append({
                                    "s": f["src"],
                                    "d": f["dst"],
                                    "thr": f.get("throughput", 0),
                                    "sz": f.get("packet_size", 1450),
                                    "i": f.get("interval", 0.001)
                                })

                            packet = {
                                "t": current_t,
                                "n": nodes_lite,
                                "f": flows_lite
                            }
                            
                            # Envoi UDP vers le Bridge
                            sock.sendto(json.dumps(packet).encode(), (UDP_IP_DEST, UDP_PORT))
                            
                            last_sent_t = current_t
                            snapshot_id += 1
                            
                            if snapshot_id % 20 == 0:
                                print(f" [TX] Snapshot t={current_t} envoyé.")

                except (json.JSONDecodeError, IndexError, KeyError, ValueError):
                    pass # Fichier en cours d'écriture

            # Contrôle précis de la fréquence
            elapsed = time.time() - start_loop
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n🛑 Arrêt Sender.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()