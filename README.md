
# Simulation Dataset for QoS Prediction in 5G Wireless Networks

## 1. Overview

This repository provides simulation-generated datasets from multiple 5G wireless network scenarios developed using **OMNeT++**, **INET**, and **Simu5G**.

The dataset is designed to support research on **Quality of Service (QoS) prediction**, machine learning, deep learning, and data-driven modeling of **Network Digital Twins (NDTs)**.

The scenarios explore different network configurations and operating conditions, including:

- Network topology and user density
- User mobility
- Application traffic characteristics
- Wireless channel conditions
- Scheduling algorithms
- Transmission power
- Queue and buffer configurations

The collected data characterize network behavior at different levels, including application flows, network queues, and wireless links.

The dataset can be used to develop, train, evaluate, and compare predictive models, including Graph Neural Networks (GNNs), for wireless network performance analysis.

**Data source:** 5G network simulations.

**Source code:** https://github.com/AbdessamedSed/GNN-DigiTwin-Wireless

**Dataset repository:** DOREL — Recherche Data Gouv, Université de Lorraine, CRAN.

**Dataset DOI:**

---

## 2. Dataset Organization

The repository contains eight scenario directories:

```text
GNN-DigiTwin-Wireless/
├── SC01/
├── SC02/
├── SC03/
├── SC04/
├── SC05/
├── SC06/
├── SC07/
├── src/
└── README.md
```

Each scenario represents a different network configuration or operating condition.

The `src/` directory contains the associated implementation and processing code.

Only completed and verified scenario data are intended for publication in the DOREL dataset.

---

## 3. Simulation Environment

The data were generated using the following simulation framework:

| Component | Technology |
|-----------|------------|
| Network simulator | OMNeT++ |
| Network framework | INET |
| 5G simulation framework | Simu5G |
| Network technology | 5G |
| Data generation | Network simulation |
| Application domain | QoS prediction and Network Digital Twins |

The simulated scenarios consider different combinations of network parameters and operating conditions.

Depending on the scenario, these include variations in network topology, mobility patterns, traffic configurations, scheduling strategies, transmission powers, and buffer sizes.

The exact experimental settings are defined in the corresponding scenario configurations.

---

## 4. Dataset Characteristics

The datasets capture network observations collected during simulation runs.

Depending on the available files, these observations describe different components of the wireless network.

### 4.1. Application Flows

Application-level observations include:

- Traffic characteristics
- Offered traffic
- Flow-related information
- Network performance measurements

### 4.2. Network Queues

Queue-level observations include:

- Queue occupancy
- Buffer configuration
- Queue-related traffic characteristics

### 4.3. Wireless Links

Wireless-link observations include:

- Radio conditions
- Link characteristics
- Transmission-related information

---

## 5. QoS Prediction

The dataset supports research on the prediction and analysis of Quality of Service metrics in wireless networks.

Potential research applications include:

- QoS prediction
- Network performance modeling
- Graph Neural Networks
- Deep learning and machine learning
- Network Digital Twins
- Network configuration analysis
- Predictive network management

The dataset is not restricted to a particular machine learning architecture.

Researchers can use the data to develop and compare different predictive approaches.

---

## 6. Dataset Usage

A typical workflow for using the dataset consists of the following steps:

1. Download the required scenario data.
2. Inspect the corresponding network configurations.
3. Load and preprocess the collected observations.
4. Select the relevant input features and QoS targets.
5. Construct the required model inputs.
6. Train and evaluate predictive models.
7. Compare model performance across network scenarios.

---

## 7. Source Code and Reproducibility

The associated source code is available at:

https://github.com/AbdessamedSed/GNN-DigiTwin-Wireless

The repository provides supporting materials for simulation, data preparation, and predictive modeling.

---

## 8. Data Availability

The dataset is available in **DOREL**, the research data repository of Université de Lorraine.

Repository:

https://entrepot.recherche.data.gouv.fr/dataverse/dorel-lorraine

The published dataset record will provide persistent access to the released data and associated documentation.

**DOI:** To be added after publication.

---

## 9. Limitations

The dataset is generated using network simulations rather than measurements from a deployed commercial 5G network.

Consequently, the results obtained using these data may not directly generalize to real-world wireless environments.

Researchers should verify the data characteristics and simulation configurations before using the dataset for a specific prediction task.

---

## 10. Related Publication

This dataset is associated with research on graph-based prediction of wireless network performance presented at **ACM MSWiM 2026**.

The complete bibliographic reference and DOI will be added once the publication becomes available.

---

## 11. Citation

If you use this dataset in your research, please cite the official DOREL dataset record once it is published.

The citation will include the dataset authors, title, publication year, repository, version, and DOI.

When referring to the associated prediction methodology, please also cite the corresponding research article.

---

## 12. License

The dataset is distributed under the license specified in its official DOREL record.

Users should consult the relevant repository information before redistributing or modifying the materials.

---

## 13. Authors and Contact

**Contact:** Abdessamed Seddiki

**Laboratory:** Centre de Recherche en Automatique de Nancy (CRAN, UMR 7039)

**Institution:** Université de Lorraine, CNRS

**Location:** Nancy, France

**Email:** abdessamed.seddiki@univ-lorraine.fr

The complete list of dataset creators and their affiliations will be provided in the DOREL metadata record.

---

## 14. Acknowledgments

This research was conducted within the Centre de Recherche en Automatique de Nancy (CRAN), Université de Lorraine, CNRS, France.
