
#include "DTConnector.h"
#include <inet/common/ModuleAccess.h>
#include <inet/mobility/contract/IMobility.h>
#include <simu5g/stack/phy/NrPhyUe.h>
#include <simu5g/stack/phy/LtePhyUe.h>
#include <omnetpp/cstringtokenizer.h> 
#include <simu5g/common/binder/Binder.h>
#include <simu5g/stack/mac/NrMacUe.h>
#include <simu5g/stack/mac/LteMacBase.h>
#include "simu5g/common/LteCommon.h"
#include "simu5g/stack/mac/LteMacBase.h"
#include "simu5g/stack/rlc/um/LteRlcUm.h"
#include "simu5g/stack/mac/LteMacBase.h"
#include "simu5g/stack/mac/LteMacEnb.h"
#include "inet/applications/udpapp/UdpSink.h"
#include "simu5g/stack/rlc/am/LteRlcAm.h"
#include "inet/common/packet/Packet.h" 
#include "inet/networklayer/common/L3AddressTag_m.h" // Pour identifier l'émetteur en UL
#include <iostream>
#include <sstream>
#include <cmath> 

using namespace omnetpp;
using namespace inet;
using namespace simu5g;

namespace src {

Define_Module(DTConnector);

// int DTConnector::numInitStages() const {
//     return 1; // On garde 2 stages pour que le réseau soit bien prêt
// }

void DTConnector::initialize()
{


    // 1. Enregistrement Signaux
    sinrDlSignal = registerSignal("rcvdSinrDl");
    sinrUlSignal = registerSignal("rcvdSinrUl");
    measuredSinrDlSignal = registerSignal("measuredSinrDl");
    measuredSinrUlSignal = registerSignal("measuredSinrUl");
    rcvdSinrD2DSignal = registerSignal("rcvdSinrD2D");


    distanceSignal = registerSignal("distance");
    servingCellSignal = registerSignal("servingCell");

    macThrDlSignal = registerSignal("macThroughputDl");
    macThrUlSignal = registerSignal("macThroughputUl");
    macDelayDlSignal = registerSignal("macDelayDl");
    macDelayUlSignal = registerSignal("macDelayUl");

    
    packetLossDlSignal = registerSignal("macPacketLossDl");
    packetLossUlSignal = registerSignal("macPacketLossUl");

    rlcDelayDl = registerSignal("rlcDelayDl");
    rlcDelayUl = registerSignal("rlcDelayUl");

    receivedPacketFromUpperLayerSignal = registerSignal("receivedPacketFromUpperLayer");
    receivedPacketFromLowerLayerSignal = registerSignal("receivedPacketFromLowerLayer");
    sentPacketToLowerLayerSignal = registerSignal("sentPacketToLowerLayer");
    sentPacketToUpperLayerSignal = registerSignal("sentPacketToUpperLayer");

    macBufferOverFlowDlSignal = registerSignal("macBufferOverFlowDl");
    macBufferOverFlowUlSignal = registerSignal("macBufferOverFlowUlS");
    harqErrorRateDlSignal = registerSignal("harqErrorRateDl");
    harqErrorRateUlSignal = registerSignal("harqErrorRateUl");
    harqTxAttemptsDlSignal = registerSignal("harqTxAttemptsDl");
    harqTxAttemptsUlSignal = registerSignal("harqTxAttemptsUl");
    avgServedBlocksDlSignal = registerSignal("avgServedBlocksDl");
    avgServedBlocksUlSignal = registerSignal("avgServedBlocksUl");
   

    endToEndDelaySignal = registerSignal("endToEndDelay");

    rlcThroughputDlSignal = registerSignal("rlcThroughputDl");
    rlcThroughputUlSignal = registerSignal("rlcThroughputUl");
    rlcPacketLossDlSignal = registerSignal("rlcPacketLossDl");
    rlcPacketLossUlSignal = registerSignal("rlcPacketLossUl");

    rlcCellPacketLossDlSignal = registerSignal("rlcCellPacketLossDl");
    rlcCellPacketLossUlSignal = registerSignal("rlcCellPacketLossUl");
    rlcCellThroughputDlSignal = registerSignal("rlcCellThroughputDl");
    rlcCellThroughputUlSignal = registerSignal("rlcCellThroughputUl");

    packetReceivedSignal = registerSignal("packetReceived");


    // 2. Init Paramètres
    samplingInterval = par("samplingInterval").doubleValue();
    std::string pathsStr = par("mobilityModulePaths").stdstringValue();
    cStringTokenizer tokenizer(pathsStr.c_str(), ",");

    while (tokenizer.hasMoreTokens()) {
        mobilityModulePaths.push_back(tokenizer.nextToken());
    }

    int n = mobilityModulePaths.size();
    
    // Init Vecteurs
    lastSinrDl.assign(n, 999.0); 
    lastSinrUl.assign(n, 999.0);
    lastSinrD2D.assign(n, 999.0);

    lastMacThrDl.assign(n, 0.0);
    lastMacThrUl.assign(n, 0.0);
    lastMacDelayDl.assign(n, 0.0);
    lastMacDelayUl.assign(n, 0.0);

    lastDistance.assign(n, 0.0);
    lastServingCell.assign(n, 0);

    lastBlerDl.assign(n, 0.0);
    lastBlerUl.assign(n, 0.0);
    lastPacketLossDl.assign(n, 0.0);
    lastPacketLossUl.assign(n, 0.0);

    lastRlcDelayDl.assign(n , 0.0);
    lastRlcDelayUl.assign(n , 0.0);
    lastReceivedPacketFromUpperLayer.assign(n, 0.0);
    lastReceivedPacketFromLowerLayer.assign(n , 0.0);
    lastSentPacketToLowerLayer.assign(n , 0.0);
    lastSentPacketToUpperLayer.assign(n , 0.0);

    lastMacBufferOverFlowDl.assign(n , 0.0);
    lastMacBufferOverFlowUl.assign(n , 0.0);
    lastHarqErrorRateDl.assign(n , 0.0);
    lastHarqErrorRateUl.assign(n , 0.0);
    lastHarqTxAttemptsDl.assign(n , 0.0);
    lastHarqTxAttemptsUl.assign(n , 0.0);
    lastAvgServedBlocksDl.assign(n , 0.0);
    lastAvgServedBlocksUl.assign(n , 0.0);


    lastRlcThroughputDl.assign(n , 0.0);
    lastRlcThroughputUl.assign(n , 0.0);
    lastRlcPacketLossDl.assign(n , 0.0);
    lastRlcPacketLossUl.assign(n , 0.0);
    lastRlcCellPacketLossDl.assign(n , 0.0);
    lastRlcCellPacketLossUl.assign(n , 0.0);
    lastRlcCellThroughputDl.assign(n , 0.0);
    lastRlcCellThroughputUl.assign(n , 0.0);

    lastEndToEndDelay.assign(n , 0.0);
    

    hostNames.clear();
    mobilityModules.clear();

    for (int i = 0; i < n; ++i) {
        cModule *mobModule = getModuleByPath(mobilityModulePaths[i].c_str());
        if (!mobModule) {
            EV << "DTConnector: [WARNING] Module " << mobilityModulePaths[i] << " introuvable." << endl;
            mobilityModules.push_back(nullptr);
            hostNames.push_back("unknown");
            continue;
        }
        mobilityModules.push_back(check_and_cast<inet::IMobility *>(mobModule));
        cModule *host = mobModule->getParentModule();
        hostNames.push_back(host->getFullName());
    }

    // Abonnements aux signaux
    cModule *sys = getSimulation()->getSystemModule();
    sys->subscribe(sinrDlSignal, this);
    sys->subscribe(sinrUlSignal, this);
    sys->subscribe(measuredSinrDlSignal, this);
    sys->subscribe(measuredSinrUlSignal, this);
    sys->subscribe(rcvdSinrD2DSignal, this);

    sys->subscribe(distanceSignal, this);     
    sys->subscribe(servingCellSignal, this);

    sys->subscribe(macThrDlSignal, this);
    sys->subscribe(macThrUlSignal, this);
    sys->subscribe(macDelayDlSignal, this);
    sys->subscribe(macDelayUlSignal, this);

    // sys->subscribe(blerDlSignal, this);
    // sys->subscribe(blerUlSignal, this);
    sys->subscribe(packetLossDlSignal, this);
    sys->subscribe(packetLossUlSignal, this);
    
    sys->subscribe(rlcDelayDl, this);
    sys->subscribe(rlcDelayUl, this);

    sys->subscribe(receivedPacketFromUpperLayerSignal, this);
    sys->subscribe(receivedPacketFromLowerLayerSignal, this);
    sys->subscribe(sentPacketToLowerLayerSignal, this);
    sys->subscribe(sentPacketToUpperLayerSignal, this);

    sys->subscribe(macBufferOverFlowDlSignal, this);
    sys->subscribe(macBufferOverFlowUlSignal, this);
    sys->subscribe(harqErrorRateDlSignal, this);
    sys->subscribe(harqErrorRateUlSignal, this);
    sys->subscribe(harqTxAttemptsDlSignal, this);
    sys->subscribe(harqTxAttemptsUlSignal, this);
    sys->subscribe(avgServedBlocksDlSignal, this);
    sys->subscribe(avgServedBlocksUlSignal, this);
 
    sys->subscribe(endToEndDelaySignal, this);

    sys->subscribe(rlcThroughputDlSignal, this);
    sys->subscribe(rlcThroughputUlSignal, this);
    sys->subscribe(rlcPacketLossDlSignal, this);
    sys->subscribe(rlcPacketLossUlSignal, this);
    sys->subscribe(rlcCellPacketLossDlSignal, this);
    sys->subscribe(rlcCellPacketLossUlSignal, this);
    sys->subscribe(rlcCellThroughputDlSignal, this);
    sys->subscribe(rlcCellThroughputUlSignal, this);

    sys->subscribe(packetReceivedSignal, this);


    

    // Init CSV
    csvFile.open(std::string(getFullName()) + "_Links.csv", std::ios::trunc);
    if (csvFile.is_open()) {
        csvFile << "timestamp,src,dest,speed_src,speed_dest,"
            << "posx_src,posy_src,posz_src,posx_dest,posy_dest,posz_dest,"
            << "traffic_type,packet_size,interval,"
            << "serving_gnb,distance,"
            << "sinr_dl,sinr_ul"
            << "mac_thr_dl,mac_thr_ul,mac_delay_dl,mac_delay_ul,blerDlSignal,blerUlSignal,packetLossDlSignal,packetLossUlSignal,"
            // << "bufferOverflowDlSignal,bufferOverflowUlSignal"
            << "\n";
    csvFile.flush();

    }

    // Init JSON
    jsonFile.open("network_state.json", std::ios::trunc);
    if (jsonFile.is_open()) {
        jsonFile << "[\n]"; 
        jsonFile.flush();
    }
    firstJsonEntry = true;

    // Timer
    sampleTimer = new cMessage("sampleTimer");
    scheduleAt(simTime() + samplingInterval, sampleTimer);
}

// --- Helpers ---
int DTConnector::findNodeIndexByName(const std::string& name) {
    for(size_t i=0; i<hostNames.size(); ++i) {
        if(hostNames[i] == name) return i;
    }
    // Recherche partielle pour gérer "ue0" vs "ue[0]"
    std::string clean = name;
    size_t b = clean.find("[");
    if(b != std::string::npos) clean = clean.substr(0, b);

    for(size_t i=0; i<hostNames.size(); ++i) {
        std::string h = hostNames[i];
        size_t bh = h.find("[");
        if(bh != std::string::npos) h = h.substr(0, bh);
        
        if (h == clean) {
            // Si on a un index, vérifions le
            if (name.find_first_of("0123456789") != std::string::npos) {
                if (hostNames[i].find(name.substr(name.find_first_of("0123456789"))) != std::string::npos)
                    return i;
            } else {
                return i; // Cas gnb sans index
            }
        }
    }
    return -1;
}

double DTConnector::getSpeed(int index) {
    if (index < 0 || index >= (int)mobilityModules.size() || !mobilityModules[index]) return 0.0;
    return mobilityModules[index]->getCurrentVelocity().length();
}

std::string DTConnector::getServingGnbId(const std::string& nodeName) {
    cModule* host = getModuleByPath(nodeName.c_str());
    if (!host) {
        int idx = findNodeIndexByName(nodeName);
        if (idx >= 0) host = getModuleByPath(mobilityModulePaths[idx].c_str())->getParentModule();
    }
    if (!host) return "unknown";

    cModule* nic = host->getSubmodule("cellularNic");
    if (!nic) return "unknown";

    cModule* macModule = nullptr;
    if (nic->getSubmodule("nrMac")) macModule = nic->getSubmodule("nrMac");
    else if (nic->getSubmodule("mac")) macModule = nic->getSubmodule("mac");

    if (macModule) {
        auto* macBase = dynamic_cast<simu5g::LteMacBase*>(macModule);
        if (macBase) return "gnb" + std::to_string((unsigned int)macBase->getMacCellId());
    }
    return "unknown";
}

// --- Traitement Signaux ---

// void DTConnector::receiveSignal(cComponent *source, simsignal_t signalID, long value, cObject *details) {
//     processIncomingSignal(source, signalID, (double)value);
// }

void DTConnector::receiveSignal(cComponent *source, simsignal_t signalID, cObject *obj, cObject *details) {
    
   if (signalID == packetReceivedSignal) {
        inet::Packet *pkt = dynamic_cast<inet::Packet *>(obj);
        if (pkt != nullptr) {
            simtime_t delay = simTime() - pkt->getCreationTime();
            std::string srcPath = source->getFullPath();
            std::string pktName = pkt->getName();

            // --- LOG DE DEBUG : À regarder dans la console OMNeT++ ---
            // EV << "SIGNAL REÇU ! Source: " << srcPath << " | Paquet: " << pktName << " | Delay: " << delay << endl;

            // 1. CAS DOWNLINK (L'UE reçoit)
            if (srcPath.find("ue") != std::string::npos) {
                for (size_t i = 0; i < hostNames.size(); ++i) {
                    if (srcPath.find(hostNames[i]) != std::string::npos) {
                        lastEndToEndDelay[i] = delay.dbl();
                        break;
                    }
                }
            }
            // 2. CAS UPLINK (Le Serveur reçoit)
            else if (srcPath.find("server") != std::string::npos) {
                // ASTUCE : On cherche l'ID de l'émetteur qui est souvent 
                // caché dans les métadonnées ou le nom simplifié.
                for (size_t i = 0; i < hostNames.size(); ++i) {
                    // On teste si le nom de l'UE (ex: "ue0") est dans le nom du paquet
                    // ou si c'est l'application correspondante
                    if (pktName.find(hostNames[i]) != std::string::npos || 
                        pktName.find("ue") != std::string::npos) { // Test large
                        
                        lastEndToEndDelay[i] = delay.dbl();
                        // EV << "UL Match trouvé pour " << hostNames[i] << endl;
                    }
                }
            }
            
            double bytes = (double)pkt->getByteLength();
            processIncomingSignal(source, signalID, bytes);
            return;
        }
    }

    // --- Reste du code pour les autres signaux ---
    cPacket *pkt = dynamic_cast<cPacket *>(obj);
    if (pkt != nullptr) {
        double bytes = (double)pkt->getByteLength(); 
        processIncomingSignal(source, signalID, bytes);
    }
}


void DTConnector::receiveSignal(cComponent *source, simsignal_t signalID, double value, cObject *details) {
    processIncomingSignal(source, signalID, value);
}

void DTConnector::receiveSignal(cComponent *source, simsignal_t signalID, uintval_t value, cObject *details)
{
    processIncomingSignal(source, signalID, (double)value);
}

void DTConnector::receiveSignal(cComponent *source, simsignal_t signalID, long value, cObject *details) {
    std::string srcPath = source->getFullPath();
    for (size_t i = 0; i < hostNames.size(); ++i) {
        if (srcPath.find(hostNames[i]) != std::string::npos) {
            if (signalID == servingCellSignal) {
                lastServingCell[i] = value;
            }
            
        }
    }

    processIncomingSignal(source, signalID, (double)value);
}



void DTConnector::processIncomingSignal(cComponent *source, simsignal_t signalID, double value) 
{
    std::string srcPath = source->getFullPath();
    for (size_t i = 0; i < hostNames.size(); ++i) {
        if (srcPath.find(hostNames[i]) != std::string::npos) {
            
            // SINR
            if (signalID == sinrDlSignal || signalID == measuredSinrDlSignal) lastSinrDl[i] = 10.0 * log10(value);
            else if (signalID == sinrUlSignal || signalID == measuredSinrUlSignal) lastSinrUl[i] = value;
            else if (signalID == rcvdSinrD2DSignal) lastSinrD2D[i] = 10.0 * log10(value);

            else if (signalID == macThrDlSignal) lastMacThrDl[i] = value;
            else if (signalID == macThrUlSignal) lastMacThrUl[i] = value;
            else if (signalID == macDelayDlSignal) lastMacDelayDl[i] = value;
            else if (signalID == macDelayUlSignal) lastMacDelayUl[i] = value;

            else if (signalID == distanceSignal) lastDistance[i] = value; 

            // else if (signalID == blerDlSignal) lastBlerDl[i] = value;
            // else if (signalID == blerUlSignal) lastBlerUl[i] = value;
            else if (signalID == packetLossDlSignal) lastPacketLossDl[i] = value;
            else if (signalID == packetLossUlSignal) lastPacketLossUl[i] = value;

            else if (signalID == rlcDelayDl) lastRlcDelayDl[i] = value;
            else if (signalID == rlcDelayUl) lastRlcDelayUl[i] = value;

            else if (signalID == receivedPacketFromUpperLayerSignal) lastReceivedPacketFromUpperLayer[i] = value;
            else if (signalID == receivedPacketFromLowerLayerSignal) lastReceivedPacketFromLowerLayer[i] = value;
            else if (signalID == sentPacketToLowerLayerSignal) lastSentPacketToLowerLayer[i] = value;
            else if (signalID == sentPacketToUpperLayerSignal) lastSentPacketToUpperLayer[i] = value;

            else if (signalID == macBufferOverFlowDlSignal) lastMacBufferOverFlowDl[i] = value;
            else if (signalID == macBufferOverFlowUlSignal) lastMacBufferOverFlowUl[i] = value;
            
            else if (signalID == harqErrorRateDlSignal) lastHarqErrorRateDl[i] = value;
            else if (signalID == harqErrorRateUlSignal) lastHarqErrorRateUl[i] = value;
            
            else if (signalID == harqTxAttemptsDlSignal) lastHarqTxAttemptsDl[i] = value;
            else if (signalID == harqTxAttemptsUlSignal) lastHarqTxAttemptsUl[i] = value;

            
            else if (signalID == rlcThroughputDlSignal) lastRlcThroughputDl[i] = value;
            else if (signalID == rlcThroughputUlSignal) lastRlcThroughputUl[i] = value;
            else if (signalID == rlcPacketLossDlSignal) lastRlcPacketLossDl[i] = value;
            else if (signalID == rlcPacketLossUlSignal) lastRlcPacketLossUl[i] = value;
            else if (signalID == rlcCellPacketLossDlSignal) lastRlcCellPacketLossDl[i] = value;
            else if (signalID == rlcCellPacketLossUlSignal) lastRlcCellPacketLossUl[i] = value;
            else if (signalID == rlcCellThroughputDlSignal) lastRlcCellThroughputDl[i] = value;
            else if (signalID == rlcCellThroughputUlSignal) lastRlcCellThroughputUl[i] = value;

            
            else if (signalID == avgServedBlocksDlSignal) lastAvgServedBlocksDl[i] = value;
            else if (signalID == avgServedBlocksUlSignal) lastAvgServedBlocksUl[i] = value;
            
            return;
        }
    }
}


void DTConnector::handleMessage(cMessage *msg)
{
    if (msg == sampleTimer) {        

        exportData(); 
        scheduleAt(simTime() + samplingInterval, sampleTimer);
    } else delete msg;
}


// --- Exportation ---
void DTConnector::exportData()
{
    double now = simTime().dbl();
    if (!jsonFile.is_open()) return;

    // =======================================================================
    // PARTIE 1 : PRÉPARATION ET RECALAGE JSON
    // =======================================================================
    
    // On recule de 2 caractères pour effacer le "\n]" écrit au tour précédent
    // Cela permet de rester à l'intérieur du tableau principal [ ... ]
    jsonFile.seekp(-2, std::ios::end);

    if (!firstJsonEntry) { 
        jsonFile << ",\n"; // Ajoute une virgule entre les blocs de timestamp
    }
    firstJsonEntry = false;

    jsonFile << "  {\n";
    jsonFile << "    \"timestamp\": " << now << ",\n";
    
    // =======================================================================
    // PARTIE 2 : JSON - NODES (L'état physique brut de chaque UE)
    // =======================================================================
    jsonFile << "    \"nodes\": [\n";
    bool isFirstNode = true;

    for (size_t i = 0; i < hostNames.size(); ++i) {
        if (!mobilityModules[i]) continue;

        // Gestion propre de la virgule (AVANT l'élément, sauf le premier)
        if (!isFirstNode) jsonFile << ",\n";
        isFirstNode = false;

        inet::Coord pos = mobilityModules[i]->getCurrentPosition();
        double speed = getSpeed(i);
        
        // Nettoyage ID : ue[0] -> ue0
        std::string rawName = hostNames[i];
        std::string cleanId = rawName;
        size_t b = cleanId.find("[");
        if (b != std::string::npos) {
             cleanId.erase(b, 1); 
             cleanId.erase(cleanId.find("]"), 1);
        }

        std::string servingGnb = (rawName.find("ue") != std::string::npos) ? getServingGnbId(rawName) : "none";

        jsonFile << "      { \"id\": \"" << cleanId << "\", ";

    if (hostNames[i].find("gnb") != std::string::npos) {
        // C'EST UN GNB : On met les métriques GLOBALES
        jsonFile << "\"type\": \"gnb\", "
                << "\"x\": " << pos.x << ", \"y\": " << pos.y << ", "
                 << "\"cell_loss_dl\": " << lastRlcCellPacketLossDl[i] << ", "
                 << "\"cell_loss_ul\": " << lastRlcCellPacketLossUl[i] << ", "
                 << "\"cell_thr_dl\": " << lastRlcCellThroughputDl[i] << ", "
                 << "\"cell_thr_ul\": " << lastRlcCellThroughputUl[i] << ", "
                 << "\"avg_avg_served_block_dl\" : " << lastAvgServedBlocksDl[i] << ", "
                 << "\"avg_avg_served_block_ul\" : " << lastAvgServedBlocksUl[i];

    } else {
        // C'EST UN UE : On met les métriques PHYSIQUES
        jsonFile << "\"type\": \"ue\", "
                 << "\"serving_gnb\": \"" << servingGnb << "\", "
                 << "\"x\": " << pos.x << ", \"y\": " << pos.y << ", "
                 << "\"speed\": " << speed << ", "
                 << "\"sinr_dl\": " << lastSinrDl[i] << ", "
                 << "\"sinr_ul\": " << lastSinrUl[i];
                
    }
    jsonFile << " }";


    }
    jsonFile << "\n    ],\n"; 

    // =======================================================================
    // PARTIE 3 : DÉTECTION DES FLUX ACTIFS (Logique de collecte)
    // =======================================================================
    std::vector<FlowInfo> activeFlows;

    // A. Flux DOWNLINK (Server -> gNB -> UE)
    cModule* sys = getSimulation()->getSystemModule();
    cModule* server = sys->getSubmodule("server");
    if (server) {
        int numApps = server->hasPar("numApps") ? server->par("numApps").intValue() : 0;
        for (int k = 0; k < numApps; k++) {
            cModule* app = server->getSubmodule("app", k);
            if (!app || !app->hasPar("destAddresses")) continue;

            
            if (now >= app->par("startTime").doubleValue()) {
                std::string dest = app->par("destAddresses").stdstringValue(); 
                int dstIdx = findNodeIndexByName(dest);
                
                FlowInfo f;
                f.srcName = "server"; f.dstName = dest;
                f.type = "DL";
                f.phySrc = "gnb"; 
                f.phyDst = dest;
                f.ueIndex = dstIdx; // Stats mesurées par le récepteur (UE)
                f.packetSize = app->par("messageLength").intValue();
                f.interval = app->par("sendInterval").doubleValue();
                activeFlows.push_back(f);
            }
        }
    }

    // B. Flux UPLINK & D2D (UE -> ...)
    for (size_t i = 0; i < hostNames.size(); ++i) {
        if (hostNames[i].find("gnb") != std::string::npos) continue; 
        cModule* host = getModuleByPath(mobilityModulePaths[i].c_str())->getParentModule();
        if(!host) continue;

        int numApps = host->hasPar("numApps") ? host->par("numApps").intValue() : 0;
        for (int k = 0; k < numApps; k++) {
            cModule* app = host->getSubmodule("app", k);
            if (!app || !app->hasPar("destAddresses")) continue;

            if (now >= app->par("startTime").doubleValue()) {
                std::string dest = app->par("destAddresses").stdstringValue();
                FlowInfo f;
                f.srcName = hostNames[i]; f.dstName = dest;
                f.packetSize = app->par("messageLength").intValue();
                f.interval = app->par("sendInterval").doubleValue();

                if (dest.find("server") != std::string::npos) {
                    f.type = "UL";
                    f.phySrc = hostNames[i]; f.phyDst = "gnb";
                    f.ueIndex = i; // Stats mesurées par gNB, attribuées à l'émetteur
                } else {
                    f.type = "D2D";
                    f.phySrc = hostNames[i]; f.phyDst = dest;
                    int dstIdx = findNodeIndexByName(dest);
                    f.ueIndex = dstIdx; // Stats mesurées par le récepteur D2D
                }
                activeFlows.push_back(f);
            }
        }
    }

    // =======================================================================
    // PARTIE 4 : JSON - FLOWS (Performance des flux)
    // =======================================================================
    jsonFile << "    \"flows\": [\n";
    bool isFirstFlow = true;

    for (size_t k = 0; k < activeFlows.size(); ++k) {
        int ueIdx = activeFlows[k].ueIndex;
        if (ueIdx < 0) continue;

        if (!isFirstFlow) jsonFile << ",\n";
        isFirstFlow = false;
        
        double  thr = 0, delay = 0, bler = 0, loss = 0 , rlcDelay = 0 , rcvUpper = 0 , 
                rcvLower = 0 , sentLower = 0 , sentUpper = 0, buffOverflow = 0, avgBlocks = 0,
                harqErr = 0, harqTx = 0 , endToEndDelay = 0 , 
                rlcThr = 0  , rlcLoss = 0;

        // Application de la philosophie : UL (émetteur) vs DL/D2D (récepteur)
        if (activeFlows[k].type == "UL") {
            thr = lastMacThrUl[ueIdx];
            delay = lastMacDelayUl[ueIdx];
            bler = lastBlerUl[ueIdx];
            loss = lastPacketLossUl[ueIdx];
            rlcDelay = lastRlcDelayUl[ueIdx];
            buffOverflow = lastMacBufferOverFlowUl[ueIdx];
            // avgBlocks = lastAvgServedBlocksUl[ueIdx];
            harqErr = lastHarqErrorRateUl[ueIdx];
            harqTx = lastHarqTxAttemptsUl[ueIdx];
            rlcThr = lastRlcThroughputUl[ueIdx];
            rlcLoss = lastRlcPacketLossUl[ueIdx];
            endToEndDelay = lastEndToEndDelay[ueIdx];
        } else {
            thr = lastMacThrDl[ueIdx];
            delay = lastMacDelayDl[ueIdx];
            bler = lastBlerDl[ueIdx];
            loss = lastPacketLossDl[ueIdx];
            rlcDelay = lastRlcDelayDl[ueIdx];
            buffOverflow = lastMacBufferOverFlowDl[ueIdx];
            // avgBlocks = lastAvgServedBlocksDl[ueIdx];
            harqErr = lastHarqErrorRateDl[ueIdx];
            harqTx = lastHarqTxAttemptsDl[ueIdx];
            rlcThr = lastRlcThroughputDl[ueIdx];
            rlcLoss = lastRlcPacketLossDl[ueIdx];
            endToEndDelay = lastEndToEndDelay[ueIdx];
        }

        rcvUpper = lastReceivedPacketFromUpperLayer[ueIdx];
        rcvLower = lastReceivedPacketFromLowerLayer[ueIdx];
        sentLower = lastSentPacketToLowerLayer[ueIdx];
        sentUpper = lastSentPacketToUpperLayer[ueIdx];

        jsonFile << "      { "
             << "\"type\": \"" << activeFlows[k].type << "\", "
             << "\"src\": \"" << activeFlows[k].srcName << "\", "
             << "\"dst\": \"" << activeFlows[k].dstName << "\", "
             << "\"app\": \"" << activeFlows[k].type << "\", " 
             << "\"packet_size\": " << activeFlows[k].packetSize << ", "
             << "\"interval\": " << activeFlows[k].interval << ", "
             << "\"throughput\": " << thr << ", "
             << "\"delay\": " << delay << ", "
             << "\"bler\": " << bler << ", "
             << "\"packet_loss\": " << loss << ", "
             << "\"rlcDelay\": " << rlcDelay << ", "
             << "\"macBufferOverflow\": " << buffOverflow << ", "
            //  << "\"avgServedBlocks\": " << avgBlocks << ", "
             << "\"harqErrorRate\": " << harqErr << ", "
             << "\"harqTxAttempts\": " << harqTx << ", "
             << "\"receivedPacketFromUpperLayer\": " << rcvUpper << ", "
             << "\"receivedPacketFromLowerLayer\": " << rcvLower << ", "
             << "\"sentPacketToLowerLayer\": " << sentLower << ", "
             << "\"sentPacketToUpperLayer\": " << sentUpper << ", "
             << "\"rlcThroughput\" : " << rlcThr << ", " 
             << "\"rlcPacketLoss\" : " << rlcLoss
            //  << "\"endToEndDelay\": " << endToEndDelay
             << " }";
    }

    // Fermeture propre du JSON pour validité immédiate
    jsonFile << "\n    ]\n"; 
    jsonFile << "  }\n]"; 
    jsonFile.flush();   

    // =======================================================================
    // PARTIE 5 : CSV - EXPORTATION DÉTAILLÉE
    // =======================================================================
    for (const auto& flow : activeFlows) {
        int srcIdx = findNodeIndexByName(flow.phySrc);
        int dstIdx = findNodeIndexByName(flow.phyDst);
        int ueIdx = flow.ueIndex;

        if (ueIdx < 0) continue;

        inet::Coord srcPos(0,0,0), dstPos(0,0,0);
        double srcSpeed = 0, dstSpeed = 0;

        if (srcIdx >= 0 && mobilityModules[srcIdx]) {
            srcPos = mobilityModules[srcIdx]->getCurrentPosition();
            srcSpeed = getSpeed(srcIdx);
        } else if (flow.phySrc == "gnb") {
            int gIdx = findNodeIndexByName("gnb");
            if (gIdx >= 0 && mobilityModules[gIdx]) srcPos = mobilityModules[gIdx]->getCurrentPosition();
        }

        if (dstIdx >= 0 && mobilityModules[dstIdx]) {
            dstPos = mobilityModules[dstIdx]->getCurrentPosition();
            dstSpeed = getSpeed(dstIdx);
        }

        csvFile << now << ","
                << flow.phySrc << "," << flow.phyDst << ","
                << srcSpeed << "," << dstSpeed << ","
                << srcPos.x << "," << srcPos.y << "," << srcPos.z << ","
                << dstPos.x << "," << dstPos.y << "," << dstPos.z << ","
                << flow.type << ","
                << flow.packetSize << ","
                << flow.interval << ","
                << lastServingCell[ueIdx] << ","
                << lastDistance[ueIdx] << ","
                << lastSinrDl[ueIdx] << ","              
                << lastSinrUl[ueIdx] << ","              
                // << lastSinrD2D[ueIdx] << ","
                << lastMacThrDl[ueIdx] << ","
                << lastMacThrUl[ueIdx] << ","
                << lastMacDelayDl[ueIdx] << ","
                << lastMacDelayUl[ueIdx] << ","
                << lastBlerDl[ueIdx] << ","
                << lastBlerUl[ueIdx] << ","
                << lastPacketLossDl[ueIdx] << ","
                << lastPacketLossUl[ueIdx] << "\n";
    }
    csvFile.flush();
}



void DTConnector::finish() {
    cancelAndDelete(sampleTimer);
    if (jsonFile.is_open()) {
        // jsonFile << "\n]"; 
        jsonFile.close();
    }
    if (csvFile.is_open()) csvFile.close();
}

} // namespace src