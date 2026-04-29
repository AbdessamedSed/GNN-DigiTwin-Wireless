package src;

import inet.mobility.contract.IMobility;

simple DTConnector
{
    parameters:
        int numMobilityModules;
        string mobilityModulePaths; 
        double samplingInterval @unit(s) = default(0.001s);
        

}
