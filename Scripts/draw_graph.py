#!/usr/bin/python
# Date 26.06.2014
# Purpose Draws the graphs for the main report files

import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.legend as lg


for reportfile in ["rx_crc_errors", "rx_errors", "tx_errors", "retries", "multiple_retries", "rx_packets", "tx_packets", "rx_bytes", "tx_bytes", "modem_load", "noise", "tx_discard"]:
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
        plt.ylabel("Receive CRC-Errors/s")
    elif reportfile == "rx_errors":
        plt.title("Receive Error Rate")
        plt.ylabel("Receive Errors/s")
    elif reportfile == "tx_errors":
        plt.title("Transmit Error Rate")
        plt.ylabel("Transmit Errors/s")
    elif reportfile == "retries":
        plt.title("Send Packet Retries")
        plt.ylabel("Retries/s")
    elif reportfile == "multiple_retries":
        plt.title("Multiple Send Packet Retries")
        plt.ylabel("Send Packet Retries")
    elif reportfile == "rx_packets":
        plt.title("Received Packet Rate ")
        plt.ylabel("Received Packets/s")
    elif reportfile == "tx_packets":
        plt.title("Transmit Packet Rate")
        plt.ylabel("Transmitted Packets/s")
    elif reportfile == "rx_bytes":
        plt.title("Received Byte Rate")
        plt.ylabel("Bytes Received/s")
    elif reportfile == "tx_bytes":
        plt.title("Transmit Byte Rate")
        plt.ylabel("Transmitted Bytes/s")
    elif reportfile == "modem_load":
        plt.title("Modem Load")
    elif reportfile == "noise":
        plt.title("Noise Level")
        plt.ylabel("dBm")
    elif reportfile == "tx_discard":
	plt.title("Discarded Packets")
	plt.ylabel("Number of discarded Packets / s")
    else:
        print("Error: unknown reportfile")
        exit(1)

    sum7_divide_group = {"rx_crc_errors", "rx_errors", "tx_errors", "retries", "multiple_retries", "rx_packets", "tx_packets", "rx_bytes", "tx_bytes", "tx_discard"}

    if reportfile == "rx_packets":
        rx_packets = masterlist
    elif reportfile == "rx_errors":
        rx_errors = masterlist
    elif reportfile == "tx_packets":
        tx_packets = masterlist
    elif reportfile == "retries":
        retries = masterlist
    elif reportfile == "multiple_retries":
        multiple_retries = masterlist

    # Cycle through the data sets
    for listentry in masterlist:
        if reportfile in sum7_divide_group:
            seconds_list = [int(x)/7 for x in listentry[1:]]
            plt.plot(seconds_list, label=listentry[0])
        else:
            plt.plot(listentry[1:], label=listentry[0])

    lg = plt.legend(loc=2, prop={"size": 10}, bbox_to_anchor=(1.05, 0.7), borderaxespad=0.)
    plt.grid(True)
    plt.xlabel("Time")
    plt.savefig(reportfile + ".svg", bbox_inches='tight')
    plt.close()

# Create the extra graphs
# Cycle through the data sets
plt.title("Receive Error Rate / Received Packet Rate")
plt.ylabel("% Packet Errors of Received Packets")
for rx_errors_sublist, rxpackets_sublist in zip(rx_errors, rx_packets):
    divisionlist = [int(a) * 1.0 / int(b) for a, b in zip(rx_errors_sublist[1:], rxpackets_sublist[1:])]
    plt.plot(divisionlist, label=rx_errors_sublist[0])
lg = plt.legend(loc=2, prop={"size": 10}, bbox_to_anchor=(1.05, 0.7), borderaxespad=0.)
plt.grid(True)
plt.xlabel("Time")
plt.savefig("recpackerr.svg", bbox_inches='tight')
plt.close()

plt.title("Send Error Rate / Send Packet Rate")
plt.ylabel("% Packet Errors of Sent Packets")
for rx_errors_sublist, rxpackets_sublist in zip(retries, tx_packets):
    divisionlist = [int(a) * 1.0 / int(b) for a, b in zip(rx_errors_sublist[1:], rxpackets_sublist[1:])]
    plt.plot(divisionlist, label=rx_errors_sublist[0])
lg = plt.legend(loc=2, prop={"size": 10}, bbox_to_anchor=(1.05, 0.7), borderaxespad=0.)
plt.grid(True)
plt.xlabel("Time")
plt.savefig("sentpackerr.svg", bbox_inches='tight')
plt.close()

plt.title("Multiple Send Error Rate / Send Packet Rate")
plt.ylabel("% Multi Packet Errors of Sent Packets")
for rx_errors_sublist, rxpackets_sublist in zip(multiple_retries, tx_packets):
    divisionlist = [int(a) * 1.0 / int(b) for a, b in zip(rx_errors_sublist[1:], rxpackets_sublist[1:])]
    plt.plot(divisionlist, label=rx_errors_sublist[0])
lg = plt.legend(loc=2, prop={"size": 10}, bbox_to_anchor=(1.05, 0.7), borderaxespad=0.)
plt.grid(True)
plt.xlabel("Time")
plt.savefig("multisentpackerr.svg", bbox_inches='tight')
plt.close()


