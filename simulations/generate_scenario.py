#!/usr/bin/env python3
"""Generate OMNeT++ INI config for 20 gNBs / 100 UEs scenario."""

lines = []
lines.append("")
lines.append("# ---------------------------------------------------------------------------")
lines.append("# SCENARIO 20 gNB / 100 UE  (généré automatiquement)")
lines.append("# ---------------------------------------------------------------------------")
lines.append("[Config Scenario-20gNB-100UE]")
lines.append("extends = Statistics")
lines.append("")
lines.append("*.numUe = 100")
lines.append("*.numGnb = 20")
lines.append("*.numBgCells = 0")
lines.append("")
lines.append("# --- Zone élargie 5000x4000 m ---")
lines.append("**.constraintAreaMaxX = 5000m")
lines.append("**.constraintAreaMaxY = 4000m")
lines.append("")

# --- gNB positions (5 cols x 4 rows) ---
lines.append("# --- Positions gNB (grille 5x4, espacement 1000m) ---")
lines.append("*.gnb[*].mobility.initialZ = 30m")
for i in range(20):
    col = i % 5
    row = i // 5
    x = 500 + col * 1000
    y = 500 + row * 1000
    lines.append(f"*.gnb[{i}].mobility.initialX = {x}m")
    lines.append(f"*.gnb[{i}].mobility.initialY = {y}m")
lines.append("")

# --- gNB cell IDs ---
lines.append("# --- IDs cellules gNB ---")
for i in range(20):
    cid = i + 1
    lines.append(f"*.gnb[{i}].macNodeId = {cid}")
    lines.append(f"*.gnb[{i}].macCellId = {cid}")
lines.append("")

# --- UE cell assignments (5 UEs per gNB) ---
lines.append("# --- Affectation UE -> gNB (5 UE par gNB) ---")
for g in range(20):
    s = g * 5
    e = s + 4
    cid = g + 1
    lines.append(f"*.ue[{s}..{e}].masterId = {cid}")
    lines.append(f"*.ue[{s}..{e}].macCellId = {cid}")
    lines.append(f"*.ue[{s}..{e}].nrMasterId = {cid}")
    lines.append(f"*.ue[{s}..{e}].nrMacCellId = {cid}")
lines.append("")

# --- UE mobility ---
lines.append("# --- Mobilité UE ---")
lines.append('*.ue[*].mobility.typename = "GaussMarkovMobility"')
lines.append("*.ue[*].mobility.speed = uniform(5mps, 25mps)")
lines.append("")

# --- UE initial positions (near their serving gNB) ---
lines.append("# --- Positions initiales UE (proches de leur gNB) ---")
import random
random.seed(42)
for g in range(20):
    col = g % 5
    row = g // 5
    gx = 500 + col * 1000
    gy = 500 + row * 1000
    for u in range(5):
        ue_idx = g * 5 + u
        # Place UEs within 400m of their gNB
        ox = (u - 2) * 150  # spread: -300, -150, 0, 150, 300
        oy = random.randint(-300, 300)
        ux = max(10, min(4990, gx + ox))
        uy = max(10, min(3990, gy + oy))
        lines.append(f"*.ue[{ue_idx}].mobility.initialX = {ux}m")
        lines.append(f"*.ue[{ue_idx}].mobility.initialY = {uy}m")
lines.append("")

# --- Traffic ---
lines.append("# --- Trafic (Serveur -> 100 UE en DL) ---")
lines.append("*.server.numApps = 100")
lines.append("*.ue[*].numApps = 1")
lines.append('*.ue[*].app[0].typename = "UdpSink"')
lines.append('*.server.app[*].typename = "UdpBasicApp"')
lines.append("**.destPort = 1000")
lines.append("")
lines.append("# Trafic eMBB standard (80 UEs)")
lines.append('*.server.app[0..79].destAddresses = "ue[" + string(ancestorIndex(0)) + "]"')
lines.append("*.server.app[0..79].messageLength = 1450B")
lines.append("*.server.app[0..79].sendInterval = uniform(0.001s, 0.005s)")
lines.append("")
lines.append("# Trafic URLLC (10 UEs)")
lines.append('*.server.app[80..89].destAddresses = "ue[" + string(ancestorIndex(0)) + "]"')
lines.append("*.server.app[80..89].messageLength = intuniform(200B, 400B)")
lines.append("*.server.app[80..89].sendInterval = 10ms")
lines.append("")
lines.append("# Trafic IoT léger (10 UEs)")
lines.append('*.server.app[90..99].destAddresses = "ue[" + string(ancestorIndex(0)) + "]"')
lines.append("*.server.app[90..99].messageLength = intuniform(50B, 100B)")
lines.append("*.server.app[90..99].sendInterval = 500ms")
lines.append("")

# --- DTConnector ---
mob_paths = []
for i in range(100):
    mob_paths.append(f"ue[{i}].mobility")
for i in range(20):
    mob_paths.append(f"gnb[{i}].mobility")
mob_str = ",".join(mob_paths)

lines.append(f"*.dtConnector.numMobilityModules = 120")
lines.append(f"*.dtConnector.samplingInterval = 0.5s")
lines.append(f'*.dtConnector.mobilityModulePaths = "{mob_str}"')
lines.append("")
lines.append("")

output = "\n".join(lines)
print(output)

# Write to file for easy copy
with open("scenario_20gnb_100ue.ini", "w") as f:
    f.write(output)

print("\n# Config written to scenario_20gnb_100ue.ini")
