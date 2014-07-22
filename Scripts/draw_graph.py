#!/usr/bin/python
# Date 26.06.2014
# Purpose Draws the graphs for the main report files

import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.legend as lg
from operator import itemgetter
from pylab import *


# Create artificial graphs from data
def write_graph(title, ylabel, data1, data2, filename):
    plt.title(title)
    plt.ylabel(ylabel)
    linestyle_iterator = 1
    boxplotlist = list()
    namelist = list()
    for first_data, second_data in zip(data1, data2):
        divisionlist = [int(a) * 1.0 / (int(b) + int(a)) for a, b in zip(first_data[1:], second_data[1:])]
        data = divisionlist[:88]

        # Convert data from 0.9 in 90 (Because numpy does seem to have problems with float)
        rounded_data = [int(round(float(element) * 100)) for element in data]

        plt.plot(xscale, data, linestyle[linestyle_iterator], label=first_data[0])
        linestyle_iterator += 1
        namelist.append(first_data[0])
        boxplotlist.append(rounded_data)

    lg = plt.legend(loc=2, prop={"size": 10}, bbox_to_anchor=(1.05, 0.7), borderaxespad=0., title="Used Channels")
    plt.grid(True)
    plt.xlabel("Time in s")
    plt.xlim(0, 600)
    plt.savefig(filename + ".svg", bbox_inches='tight')
    plt.close()

    xticks([1, 2, 3, 4, 5], namelist)
    boxplot(boxplotlist)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel("Used Channels/Band")
    savefig(filename + "_boxplot.svg", bbox_inches='tight')
    clf()


linestyle_iterator = 1
linestyle = {1: "ob-", 2: "vg-", 3: "sr-", 4: "pc-", 5: "*m-"}
boxplotlist = list()
xscale = range(0, 614, 7)
for reportfile in ["rx_errors", "tx_errors", "retries", "rx_packets", "tx_packets", "rx_bytes", "tx_bytes", "modem_load", "noise", "multiple_retries"]:
    linestyle_iterator = 1
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

    # Reorder masterlist
    myorder = [3, 0, 4, 2, 1]
    masterlist = [masterlist[i] for i in myorder]

    plt.figure(figsize=(7, 4))

    if reportfile == "rx_crc_errors":
        title = "Packet Receive CRC-Error Rate/s"
        ylabel = "Receive CRC-Errors/s"
    elif reportfile == "rx_errors":
        title = "Received Packets with Errors/s"
        ylabel = "Packets/s"
    elif reportfile == "tx_errors":
        title = "Undeliverable Packets/s"
        ylabel = "Packet Transmit Errors/s"
    elif reportfile == "retries":
        title = "Successfully Transmitted Packets (One Retry)/s"
        ylabel = "Retries/s"
    elif reportfile == "multiple_retries":
        title = "Successfully Transmitted Packets (Multiple Retries)/s"
        ylabel = "Packets/s"
    elif reportfile == "rx_packets":
        title = "Successfully Received Packets/s"
        ylabel = "Packets/s"
    elif reportfile == "tx_packets":
        title = "Successfully Transmitted Packets/s"
        ylabel = "Packets/s"
    elif reportfile == "rx_bytes":
        title = "Successfully Received KBytes/s"
        ylabel = "KBytes/s"
    elif reportfile == "tx_bytes":
        title = "Successfully Transmitted KBytes/s"
        ylabel = "KBytes/s"
    elif reportfile == "modem_load":
        title = "Average Modem Load (Per AP)"
        ylabel = "% Medium used"
    elif reportfile == "noise":
        title = "Average Noise Level (Per AP)"
        ylabel = "dBm"
    elif reportfile == "tx_discard":
        title = "Discarded Packets/s"
        ylabel = "Packets/s"
    else:
        print("Error: unknown reportfile")
        exit(1)

    sum7_divide_group = {"rx_crc_errors", "rx_errors", "tx_errors", "retries", "rx_packets", "tx_packets", "rx_bytes", "tx_bytes", "tx_discard"}

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
    elif reportfile == "tx_errors":
        tx_errors = masterlist

    # Cycle through the data sets
    namelist = list()
    boxplot_data_list = list()
    for listentry in masterlist:

        # Limit plot to 600s (since the tests only ran that long and everything after that is garbage/artefacts)
        plt.xlim(0, 600)

        # Remove the title from data
        data = listentry[1:89]

        namelist.append(listentry[0])

        if reportfile in sum7_divide_group:
            # Divide data by 7 since we only have 7 seconds intervals
            data = [int(x)/7 for x in listentry[1:89]]
            if reportfile == "rx_bytes" or reportfile == "tx_bytes":
                # Divide by 1000 so we get KBytes instead of Bytes
                data = [x/(1000 * 1.0) for x in data]

        # Round data for boxplot
        rounded_data = [int(round(float(element))) for element in data]

        boxplot_data_list.append(rounded_data)
        plt.plot(xscale, data, linestyle[linestyle_iterator], label=listentry[0])
        linestyle_iterator += 1

    # Graph
    lg = plt.legend(loc=2, prop={"size": 10}, bbox_to_anchor=(1.05, 0.7), borderaxespad=0., title="Used Channels")
    plt.title(title)
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.xlabel("Time in s")
    plt.savefig(reportfile + ".svg", bbox_inches='tight')
    plt.close()

    # Boxplot
    xticks([1, 2, 3, 4, 5], namelist)
    boxplot(boxplot_data_list)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel("Used Channels/Band")
    savefig(reportfile + "_boxplot.svg", bbox_inches='tight')
    clf()

write_graph("Received Packets with Errors / All Received Packets", "%", rx_errors, rx_packets, "recpackerr")
write_graph("Packet Transmission Retries / All Transmitted Packets", "%", retries, tx_packets, "sentpackerr")
write_graph("Packet Transmission Retries (Multiple) / All Transmitted Packets", "%", multiple_retries, tx_packets, "multisentpackerr")
