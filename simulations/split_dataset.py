import os
import json
from copy import deepcopy

BASE_DIR = "/home/abdessamedseddiki/omnet/FiveG_network/simulations"

def split_list(lst):
    mid = len(lst) // 2
    return lst[:mid], lst[mid:]

for folder_name in os.listdir(BASE_DIR):

    folder_path = os.path.join(BASE_DIR, folder_name)

    if not os.path.isdir(folder_path):
        continue

    data_file = os.path.join(folder_path, "data.json")

    if not os.path.isfile(data_file):
        print(f"[SKIP] Pas de data.json dans : {folder_name}")
        continue

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # =========================
        # CAS 1 : JSON = LISTE
        # =========================
        if isinstance(data, list):

            part1, part2 = split_list(data)

            out1 = os.path.join(folder_path, "data_part1.json")
            out2 = os.path.join(folder_path, "data_part2.json")

            with open(out1, "w", encoding="utf-8") as f:
                json.dump(part1, f, indent=2)

            with open(out2, "w", encoding="utf-8") as f:
                json.dump(part2, f, indent=2)

            print(f"[OK-LIST] {folder_name}")

        # =========================
        # CAS 2 : JSON = DICT
        # =========================
        elif isinstance(data, dict):

            data_part1 = deepcopy(data)
            data_part2 = deepcopy(data)

            nodes = data.get("nodes", [])
            flows = data.get("flows", [])

            nodes_1, nodes_2 = split_list(nodes)
            flows_1, flows_2 = split_list(flows)

            data_part1["nodes"] = nodes_1
            data_part1["flows"] = flows_1

            data_part2["nodes"] = nodes_2
            data_part2["flows"] = flows_2

            out1 = os.path.join(folder_path, "data_part1.json")
            out2 = os.path.join(folder_path, "data_part2.json")

            with open(out1, "w", encoding="utf-8") as f:
                json.dump(data_part1, f, indent=2)

            with open(out2, "w", encoding="utf-8") as f:
                json.dump(data_part2, f, indent=2)

            print(f"[OK-DICT] {folder_name}")

        else:
            print(f"[UNKNOWN FORMAT] {folder_name}")

    except Exception as e:
        print(f"[ERROR] {folder_name} -> {e}")