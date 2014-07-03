#!/usr/bin/python
# Date 26.06.2014
# Purpose Draws the graphs for the main report files

import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.legend as lg


for reportfile in ["rx_crc_errors", "rx_errors", "tx_errors", "retries", "multiple_retries", "rx_packets", "tx_packets", "rx_bytes", "tx_bytes", "modem_load", "noise"]:
    f = open(reportfile, "r")
    filestring = f.read()
    f.close()
    masterlist = list()
    linesstring = filestring.splitlines()
    for entry in linesstring[0].split():
        masterlist.append(list())

    for line in linesstring:
        splitline = line.split()
        i = 0
        for entry in splitline:
            masterlist[i].append(entry)
            i += 1

    plt.figure(figsize=(7, 4))

    if reportfile == "rx_crc_errors":
        plt.title("Receive CRC-Error Rate")
        plt.ylabel("Receive CRC-Errors / 7s")
    elif reportfile == "rx_errors":
        plt.title("Receive Error Rate")
        plt.ylabel("Receive Errors / 7s")
    elif reportfile == "tx_errors":
        plt.title("Transmit Error Rate")
        plt.ylabel("Transmit Errors / 7s")
    elif reportfile == "retries":
        plt.title("Send Packet Retries")
        plt.ylabel("Retries / 7s")
    elif reportfile == "multiple_retries":
        plt.title("Multiple Send Packet Retries")
        plt.ylabel("Send Packet Retries")
    elif reportfile == "rx_packets":
        plt.title("Received Packet Rate ")
        plt.ylabel("Received Packets / 7s")
    elif reportfile == "tx_packets":
        plt.title("Transmit Packet Rate")
        plt.ylabel("Trasnmitted Packets / 7s")
    elif reportfile == "rx_bytes":
        plt.title("Received Byte Rate")
        plt.ylabel("Bytes Received / 7s")
    elif reportfile == "tx_bytes":
        plt.title("Transmit Byte Rate")
        plt.ylabel("Transmitted Bytes / 7s")
    elif reportfile == "modem_load":
        plt.title("Modem Load")
    elif reportfile == "noise":
        plt.title("Noise Level")
        plt.ylabel("dBm")
    else:
        print("Error: unknown reportfile")
        exit(1)

    for listentry in masterlist:
        plt.plot(listentry[1:], label=listentry[0])

    lg = plt.legend(loc=2, prop={"size": 10}, bbox_to_anchor=(1.05, 0.7), borderaxespad=0.)
    plt.grid(True)
    plt.xlabel("Time")
    plt.savefig(reportfile + ".svg", bbox_inches='tight')
    plt.close()


