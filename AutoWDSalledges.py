#!/usr/bin/python
# author:       Konstantin Manna
# date:         05.03.2014
# purpose:      This script gets data from WLC per snmp and displays all possible paths from node to node

import pydot
import netsnmp
import sys
import datetime
import time

debug = True
wlc_address = sys.argv[1]
snmp_community = "public"
snmp_session = netsnmp.Session(DestHost=wlc_address, Version=2, Community=snmp_community)

#initial empty graph
graph = pydot.Dot(graph_type='graph',layout="fdp")
graph.write("all_edges.svg", format="svg")


#get data from device per snmp
def update_from_device():
        global graph
        graph = pydot.Dot(graph_type='graph',layout="circo")
        scan_results_ap_name = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.2'))
        scan_results_ap_mac = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.4'))
        scan_results_seen_bssid = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.1'))
        scan_results_channel = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.9'))
        scan_results_signal_strengh = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.11'))
        scan_results = zip(scan_results_ap_name, scan_results_ap_mac, scan_results_seen_bssid, scan_results_channel, scan_results_signal_strengh)

        active_radios_ap_name = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.3'))
        active_radios_ap_lan_mac = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.1'))
        active_radios_ap_bssid_mac = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.6'))
        active_radios = zip(active_radios_ap_name, active_radios_ap_lan_mac, active_radios_ap_bssid_mac)

        slave_aps = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.2.13.1.3'))
        master_aps = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.2.13.1.6'))
        connection_status = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.2.13.1.18'))
        established_connections = zip(slave_aps, master_aps, connection_status)

        aps_really_active = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.3'))
        aps_want_in = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.1.2.1'))
        aps_should_be_in = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.1.1.3'))

        #add all possible links
        for ap_name, ap_lan_mac, dest_ap_bssid, channel, signal_strength in scan_results:
                #create this node
                graph.add_node(pydot.Node(ap_name))

                #get ap name for the bssid: (and then only consider first match)
                list_of_ap_names_of_seen_node = [name for name, lan_mac, wlan_mac in active_radios if wlan_mac == dest_ap_bssid]
                if list_of_ap_names_of_seen_node:
                        if len(list_of_ap_names_of_seen_node) > 1:
                                if debug:
                                        print "warning: multiple matches in active_radios found for ssid: " + str(dest_ap_bssid)

                        #create the node
                        graph.add_node(pydot.Node(list_of_ap_names_of_seen_node[0]))
                        #create the edge
                        graph.add_edge(pydot.Edge(ap_name, list_of_ap_names_of_seen_node[0], label=str(channel), fontsize="10", penwidth=str(int(signal_strength) / 22.0), color="grey81", weight=str(signal_strength)))

        #color the esablished connections
        for (slave, master, status) in established_connections:
                if slave in aps_really_active:
                        if master in aps_really_active:
                                if slave:
                                        if master:
                                                if slave != "None":
                                                        if master != "None":
                                                                if status == "1":
                                                                        if debug:
                                                                                print "connection (" + str(slave) + "," + str(master) + ") is active"
                                                                        graph.add_edge(pydot.Edge(slave, master, color="green", penwidth="3"))
                                                                else:
                                                                        if debug:
                                                                                print "connection (" + str(slave) + "," + str(master) + ") is not active"
                                                                        graph.add_edge(pydot.Edge(slave, master, color="red"))
                                                        else:
                                                                if debug:
                                                                        print "master was none" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                                                else:
                                                        if debug:
                                                                print "slave was None" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                                        else:
                                                if debug:
                                                        print "master was null" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                                else:
                                        if debug:
                                                print "slave was null" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                        else:
                                if debug:
                                        print "master was not active" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                else:
                        if debug:
                                print "slave was not active" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"

        #add the nodes who want in
        for ap in aps_want_in:
                if debug:
                        print "AP " + str(ap) + " wants in"
                graph.add_node(pydot.Node(ap, style="filled", fillcolor="green"))

        #add the nodes who should be in
        for ap in aps_should_be_in:
                if debug:
                        print "AP " + str(ap) + " should be in"
                graph.add_node(pydot.Node(ap, style="filled", fillcolor="red"))

        #write graph to file
        graph.write("all_edges.svg", format="svg")

while True:
        update_from_device()
        print "refresh: " + str(datetime.datetime.now())
        time.sleep(1)
