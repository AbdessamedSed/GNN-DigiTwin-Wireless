# Latency Scaling Dataset

This folder contains the simulation runs used to evaluate the scalability of the wireless network simulation pipeline.

## Objective

The goal is to measure how simulation runtime and generated data size evolve when increasing the network size.

## Dataset structure

The dataset contains 15 runs:

- 5 network sizes.
- 3 repetitions per size.
- Fixed configuration:
  - Power: 0.5 W.
  - Scheduler: PF.
  - Queue size: 100 KiB.

## Scenario sizes

| Scale | UEs | gNBs | Repetitions |
|---:|---:|---:|---:|
| S15 | 15 | 1 | 3 |
| S30 | 30 | 2 | 3 |
| S60 | 60 | 4 | 3 |
| S100 | 100 | 4 | 3 |
| S150 | 150 | 4 | 3 |

## Average simulation runtime

| Scale | Runs | Mean runtime |
|---:|---:|---:|
| S15 | 3 | 50.67 s |
| S30 | 3 | 1.78 min |
| S60 | 3 | 3.93 min |
| S100 | 3 | 6.73 min |
| S150 | 3 | 10.50 min |

## Files

Each run folder contains:

- `data.json`: generated simulation data.
- `runtime.json`: runtime metadata.
- `omnetpp.ini`: OMNeT++ configuration.

The file `scaling_simulation_times.csv` summarizes runtime and data size for all runs.
