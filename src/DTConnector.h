#ifndef __SRC_DTCONNECTOR_H_
#define __SRC_DTCONNECTOR_H_

#include <omnetpp.h>
#include <inet/mobility/contract/IMobility.h>
#include <fstream>
#include <vector>
#include <string>
#include <map>
#include <simu5g/stack/phy/NrPhyUe.h>
#include <simu5g/stack/mac/NrMacUe.h>
#include "inet/common/ModuleAccess.h"


using namespace omnetpp;
using namespace inet;

namespace src {

class DTConnector : public cSimpleModule, public cListener
{

  protected:

  // struct GnbConfig {
  //       std::string sched;
  //       double qSize;
  //       double power;
  //   };
  //   std::map<std::string, GnbConfig> gnbConfigs; 

    cMessage *sampleTimer = nullptr;
    std::vector<IMobility*> mobilityModules;
    std::vector<omnetpp::cModule*> phyModules;
    std::ofstream outputFile;
    std::vector<std::string> hostNames;

    std::string currentSched;    // Ex: "PF", "MAXCI", "DRR"
    double currentQSize;         // Ex: 2097152 (2MiB en octets)
    double currentTxPower;       // Ex: 0.1



    double samplingInterval;
    std::vector<std::string> mobilityModulePaths; // 
    int numMobilityModules;
    
    
    omnetpp::simsignal_t sinrDlSignal;
    omnetpp::simsignal_t sinrUlSignal;
    omnetpp::simsignal_t measuredSinrDlSignal;
    omnetpp::simsignal_t measuredSinrUlSignal;
    omnetpp::simsignal_t rcvdSinrD2DSignal;
    std::vector<double> lastSinrDl;
    std::vector<double> lastSinrUl;
    std::vector<double> lastSinrD2D;

    /*
      pour le sinr toujours on s'intéresse à la destination pour savoir si le paquet a été bien reçu
      si uplink => le sinr_up qui est plus important, pcq le gnb écoute le ue src avec cette qualité
      si downlini => le sinr down est le plus important
      si sidelink => le sinr side , et le down peut aider à voir si le gnb a un effet sur la connextion D2D
      mais sinon dans le dernier cas, le sinr up et le sinr down existent toujours
    ------------------------------------------------------------------------------------------------------------------------------
    | Type de Flux     |	UE Principal (L'ancre)	   |      SINR_DL	           |     SINR_UL	                 |   SINR_D2D
    |-------------------------------------------------------------------------------------------------------------------------------
    |  DL	             |           UE_1              |    Mesuré par UE_1      |  Mesuré par gNB (pour UE_1)   |        -999
    |  UL	             |           UE_1	             |    Mesuré par UE_1	     |  Mesuré par gNB (pour UE_1)   |	      -999
    |  D2D	           |           UE_1 (Dest)       |    Mesuré par UE_1	     |  Mesuré par gNB (pour UE_1)	 |   Mesuré par UE_1
    ------------------------------------------------------------------------------------------------------------------------------
    */

    simsignal_t distanceSignal;
    simsignal_t servingCellSignal;
    std::vector<double> lastDistance;
    std::vector<long> lastServingCell;


    // --- MAC Layer Signals 
    simsignal_t macThrDlSignal;
    simsignal_t macThrUlSignal;
    simsignal_t macDelayDlSignal;
    simsignal_t macDelayUlSignal;
    std::vector<double> lastMacThrDl;
    std::vector<double> lastMacThrUl;
    std::vector<double> lastMacDelayDl;
    std::vector<double> lastMacDelayUl;


    // simsignal_t blerDlSignal;
    simsignal_t packetLossDlSignal;
    simsignal_t bufferOverflowDlSignal;

    simsignal_t blerUlSignal;
    simsignal_t packetLossUlSignal;
    simsignal_t bufferOverflowUlSignal;

    simsignal_t rlcDelayDl;
    simsignal_t rlcDelayUl;

    simsignal_t receivedPacketFromUpperLayerSignal;
    simsignal_t receivedPacketFromLowerLayerSignal;
    simsignal_t sentPacketToLowerLayerSignal;
    simsignal_t sentPacketToUpperLayerSignal;

    simsignal_t macBufferOverFlowDlSignal;
    simsignal_t macBufferOverFlowUlSignal;
    simsignal_t harqErrorRateDlSignal;
    simsignal_t harqErrorRateUlSignal;
    simsignal_t harqTxAttemptsDlSignal;
    simsignal_t harqTxAttemptsUlSignal;
    simsignal_t avgServedBlocksDlSignal;
    simsignal_t avgServedBlocksUlSignal;
    simsignal_t cqiDlSignal;
    simsignal_t cqiUlSignal;    
    simsignal_t endToEndDelaySignal;

    simsignal_t rlcThroughputDlSignal;
    simsignal_t rlcThroughputUlSignal;
    simsignal_t rlcPacketLossDlSignal;
    simsignal_t rlcPacketLossUlSignal;
    simsignal_t rlcCellPacketLossDlSignal;
    simsignal_t rlcCellPacketLossUlSignal;
    simsignal_t rlcCellThroughputDlSignal;
    simsignal_t rlcCellThroughputUlSignal;

    simsignal_t packetReceivedSignal;

    std::vector<double> lastRlcThroughputDl;
    std::vector<double> lastRlcThroughputUl;
    std::vector<double> lastRlcPacketLossDl;
    std::vector<double> lastRlcPacketLossUl;
    std::vector<double> lastRlcCellPacketLossDl;
    std::vector<double> lastRlcCellPacketLossUl;
    std::vector<double> lastRlcCellThroughputDl;
    std::vector<double> lastRlcCellThroughputUl;

    std::vector<double> lastRlcDelayDl;
    std::vector<double> lastRlcDelayUl;

    std::vector<double> lastReceivedPacketFromUpperLayer;
    std::vector<double> lastReceivedPacketFromLowerLayer; 
    std::vector<double> lastSentPacketToLowerLayer;
    std::vector<double> lastSentPacketToUpperLayer;


    std::vector<double> lastBlerDl;
    std::vector<double> lastBlerUl;
    std::vector<double> lastPacketLossDl;
    std::vector<double> lastPacketLossUl;
    std::vector<double> lastBufferOverflowDl;
    std::vector<double> lastBufferOverflowUl;

    std::vector<double> lastMacBufferOverFlowDl;
    std::vector<double> lastMacBufferOverFlowUl;
    std::vector<double> lastHarqErrorRateDl;
    std::vector<double> lastHarqErrorRateUl;
    std::vector<double> lastHarqTxAttemptsDl;
    std::vector<double> lastHarqTxAttemptsUl;
    std::vector<double> lastAvgServedBlocksDl;
    std::vector<double> lastAvgServedBlocksUl;
    

    std::vector<double> lastEndToEndDelay;


    struct FlowInfo {
        std::string srcName;
        std::string dstName;
        std::string type; 
        std::string phySrc;
        std::string phyDst;
        int ueIndex;     // Index de l'UE concerné pour récupérer toutes ses stats
        int packetSize;
        double interval;

        double macThrDl;
        double macTheUl;
        double macDelayDl;
        double macDelayUl;
        double pathLossDl;
        double pathLossUl;
        double bufferOverFlowDl;
        double bufferOverFlowUl;
        double rlcDelayDl;
        double rlcDelayUl;

        /*
         Les données en dessous correspondent à de la couche RLC

        */
        double receivedPacketFromUpperLayer;
        double receivedPacketFromLowerLayer;
        double sentPacketToLowerLayer;
        double sentPacketToUpperLayer;

        double macBufferOverFlowDl;
        double macBufferOverFlowUl;
        double harqErrorRateDl;
        double harqErrorRateUl;
        double harqTxAttemptsDl;
        double harqTxAttemptsUl;
        

        double endToEndDelay;


    };


    std::ofstream csvFile;
    std::ofstream jsonFile;
    bool firstJsonEntry;



    

  public:
    // virtual int numInitStages() const override; 
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

    virtual void receiveSignal(omnetpp::cComponent *source, omnetpp::simsignal_t signalID, double value, omnetpp::cObject *details) override;
    virtual void receiveSignal(omnetpp::cComponent *source, omnetpp::simsignal_t signalID, long value, omnetpp::cObject *details) override;
    virtual void receiveSignal(cComponent *source, simsignal_t signalID, uintval_t value, cObject *details) override;
    virtual void receiveSignal(cComponent *source, simsignal_t signalID, cObject *obj, cObject *details) override;

    
    int findNodeIndexByName(const std::string& name);
    double getSpeed(int index);
    double getSinrForNode(int index, const std::string& type);
    
    void processIncomingSignal(cComponent *source, simsignal_t signalID, double value);
    void exportData();
    void writeJsonSnapshot(double timestamp);
    std::string getServingGnbId(const std::string& nodeName);

};

} // namespace src

#endif
