#include <omnetpp.h>
#include "inet/applications/base/ApplicationBase.h"
#include "inet/applications/udpapp/UdpBasicApp.h"
#include "inet/networklayer/common/L3AddressResolver.h"

using namespace omnetpp;
using namespace inet;

class FiveGApp : public ApplicationBase
{
  protected:
    int localPort = -1;
    int destPort = -1;
    cMessage *sendTimer = nullptr;
    L3Address destAddr;

  protected:
    virtual void initialize(int stage) override;
    virtual void handleMessageWhenUp(cMessage *msg) override;
    virtual void handleStartOperation(LifecycleOperation *operation) override {}
    virtual void handleStopOperation(LifecycleOperation *operation) override {}
    virtual void handleCrashOperation(LifecycleOperation *operation) override {}
    void sendPacket();
  public:
    virtual ~FiveGApp();
};

Define_Module(FiveGApp);

void FiveGApp::initialize(int stage)
{
    ApplicationBase::initialize(stage);
    if (stage == INITSTAGE_LOCAL) {
        localPort = par("localPort");
        destPort = par("destPort");
        sendTimer = new cMessage("sendPacket");
    }
    else if (stage == INITSTAGE_APPLICATION_LAYER) {
        destAddr = L3AddressResolver().resolve("gnb");
        scheduleAt(simTime() + par("startDelay"), sendTimer);
    }
}

void FiveGApp::handleMessageWhenUp(cMessage *msg)
{
    if (msg == sendTimer) {
        sendPacket();
        scheduleAt(simTime() + par("sendInterval"), sendTimer);
    } else {
        EV << "Received packet: " << msg->getName() << endl;
        delete msg;
    }
}

void FiveGApp::sendPacket()
{
    cPacket *pkt = new cPacket("FiveGPacket");
    pkt->setByteLength(par("packetSize"));
    send(pkt, "udpOut");
    EV << "Sent packet to gNB" << endl;
}

FiveGApp::~FiveGApp() {
    cancelAndDelete(sendTimer);
}
