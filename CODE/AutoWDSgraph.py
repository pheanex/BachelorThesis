#!/usr/bin/python
# author:       Konstantin Manna
# date:         28.02.2014
# purpose:      This script get the AutoWDS data from a device
#               and displays it as a graph

import pydot
import netsnmp
import sys
import datetime
import time

debug = False
wlc_address = sys.argv[1]
snmp_community = "public"
snmp_session = netsnmp.Session(DestHost=wlc_address, Version=2, Community=snmp_community)

#initial empty graph
graph = pydot.Dot(graph_type='graph')
graph.write("graph.svg", format="svg")


#get data from device per snmp
def update_from_device():
        global graph
        graph = pydot.Dot(graph_type='graph')
        slave_aps = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.2.13.1.3'))
        master_aps = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.2.13.1.6'))
        connection_status = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.2.13.1.18'))
        aps_want_in = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.1.2.1'))
        aps_should_be_in = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.1.1.3'))
        aps_really_active = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.3'))
        table = zip(slave_aps, master_aps, connection_status)
        for (slave, master, status) in table:
                if slave in aps_really_active:
                        if master in aps_really_active:
                                if slave:
                                        if master:
                                                if slave != "None":
                                                        if master != "None":
                                                                if status == "1":
                                                                        if debug: print "connection (" + str(slave) + "," + str(master) + ") is active"
                                                                        graph.add_edge(pydot.Edge(slave, master, color="green"))
                                                                else:
                                                                        if debug: print "connection (" + str(slave) + "," + str(master) + ") is not active"
                                                                        graph.add_edge(pydot.Edge(slave, master, color="red"))
                                                        else:
                                                                if debug: print "master was none" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                                                else:
                                                        if debug: print "slave was None" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                                        else:
                                                if debug: print "master was null" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                                else:
                                        if debug: print "slave was null" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                        else:
                                if debug: print "master was not active" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"
                else:
                        if debug: print "slave was not active" + "(" + str(slave) + "," + str(master) + "," + str(status) + ")"

        for ap in aps_want_in:
                if debug: print "AP " + str(ap) + " wants in"
                graph.add_node(pydot.Node(ap, style="filled", fillcolor="green"))

        for ap in aps_should_be_in:
                if debug: print "AP " + str(ap) + " should be in"
                graph.add_node(pydot.Node(ap, style="filled", fillcolor="red"))

        #write graph to file
        graph.write("graph.svg", format="svg")

while True:
        update_from_device()
        print "refresh: " + str(datetime.datetime.now())
        time.sleep(1)
