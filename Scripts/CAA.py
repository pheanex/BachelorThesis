#!/usr/bin/python
# author Konstantin Manna
# date  31.07.2014
# purpose Selects the best Topology and Channels for a Mesh network administered by a WLC (Lancom AutoWDS)

import random
import json
import copy
import os
import sys
import logging

import networkx as nx

import collections_enhanced
import testcore.control.ssh


#
# Functions for Interaction with Outer World
#

def convert_to_undirected_graph(directed_graph, middle="lower"):
    """Converts a given directed NetwrokX graph to an undirected graph

    Keyword arguments:
    directed_graph -- NetworkX directed Graph
    middle -- The behaviour for merging two edges
              If there exists (a,b) and (b,a) then both have attributes like SNR
              this parameter specifies, how to calculate the resulting value for
              the edge in the undirected graph, possible values are "lower", "average", "upper"
    Returns a undirected networkX graph
    """

    logger.info("Converting directed Graph to undirected Graph")

    undirected_graph = nx.Graph()
    for node in directed_graph.nodes():
        undirected_graph.add_node(node)
        for key in directed_graph.node[node].keys():
            undirected_graph.node[node][key] = directed_graph.node[node][key]

    for a, b in directed_graph.edges():
        if not directed_graph.edge[a][b]["real-connection"]:
            # Its a node-module connections -> just add it
            undirected_graph.add_edge(a, b)
            for key in directed_graph.edge[a][b].keys():
                undirected_graph.edge[a][b][key] = directed_graph.edge[a][b][key]
        else:
            if directed_graph.has_edge(a, b) and directed_graph.has_edge(b, a):
                undirected_graph.add_edge(a, b)
                if middle == "average":
                    undirected_graph.edge[a][b]["snr"] = (directed_graph.edge[a][b]["snr"] + directed_graph.edge[b][a]["snr"]) / 2.0
                elif middle == "lower":
                    if directed_graph.edge[b][a]["snr"] < directed_graph.edge[a][b]["snr"]:
                        undirected_graph.edge[a][b]["snr"] = directed_graph.edge[b][a]["snr"]
                    else:
                        undirected_graph.edge[a][b]["snr"] = directed_graph.edge[a][b]["snr"]
                    if directed_graph.edge[a][b]["snr"] < directed_graph.edge[b][a]["snr"]:
                        undirected_graph.edge[a][b]["snr"] = directed_graph.edge[a][b]["snr"]
                    else:
                        undirected_graph.edge[a][b]["snr"] = directed_graph.edge[b][a]["snr"]
                elif middle == "upper":
                    if directed_graph.edge[b][a]["snr"] > directed_graph.edge[a][b]["snr"]:
                        undirected_graph.edge[a][b]["snr"] = directed_graph.edge[b][a]["snr"]
                    else:
                        undirected_graph.edge[a][b]["snr"] = directed_graph.edge[a][b]["snr"]
                    if directed_graph.edge[a][b]["snr"] > directed_graph.edge[b][a]["snr"]:
                        undirected_graph.edge[a][b]["snr"] = directed_graph.edge[a][b]["snr"]
                    else:
                        undirected_graph.edge[a][b]["snr"] = directed_graph.edge[b][a]["snr"]
                else:
                    logger.error("converting directed graph to undirected graph failed, because '" + str(middle) + "' is not a valid setting.")
                    exit(1)

                undirected_graph.edge[a][b]["real-connection"] = True
                undirected_graph.edge[a][b]["channel"] = None
            else:
                # Ignore this edge
                if directed_graph.has_edge(a, b):
                    logger.info("Info: Ignoring Onesided link: " + a + "(" + directed_graph.node[a]["module-of-name"] + ") -> " + b + "(" + directed_graph.node[b]["module-of-name"] + ")")
                else:
                    logger.info("Info: Ignoring Onesided link: " + b + "(" + undirected_graph.node[b]["module-of-name"] + ") -> " + a + "(" + undirected_graph.node[a]["module-of-name"] + ")")
    return undirected_graph


def graph_is_valid(graphname, lan_nodes, wlan_modules):
    """Check if the Channel assignment is vald
    Returns True or False
    """
    logger.info("Checking the graph for validity")

    valid = True
    # First check if every edge has an assigned channel
    for edge in graphname.edges():
        if not edge[0] in lan_nodes and not edge[1] in lan_nodes:
            if not edge:
                logger.error(edge + " not valid")
                valid = False
                break
            else:
                if not graphname.edge[edge[0]][edge[1]]["channel"]:
                    logger.error("Edge has no channel: " + str(edge[0]) + "<->" + str(edge[1]))
                    valid = False
                    break
                else:
                    # Check if the channel is in one of the assignable channels
                    if graphname.edge[edge[0]][edge[1]]["channel"] not in Assignable_Channels:
                        logger.error("The channel for edge: " + str(edge[0]) + "," + str(edge[1]) + "is not an assignable channel.")
                        valid = False
                        break
                # Check if there are only connections between modules of different nodes
                if graphname.node[edge[0]]["module-of"] == graphname.node[edge[1]]["module-of"]:
                    logger.error("The modules " + str(edge[0]) + "," + str(edge[1]) + " are both connected to node " + graphname.node[edge[0]]["module-of"])
                    logger.error("This does not make sense, but means the modules see each other in the basic graph.")
                    valid = False
                    break

    for module in wlan_modules:
        corresponding_module = graphname.node[module]["module-of"]
        if not graphname.has_edge(corresponding_module, module):
            logger.error("Module " + module + " is attached to " + corresponding_module + " but, has no direct connection to it.")
            valid = False
            break

    # Now check if every node has only so many attached channels/channels as the number of modules it has
    for node in lan_nodes:
        nr_of_modules = graphname.node[node]["modules"]

        # Number of channels in the used-channels counter which have a value != 0
        nr_of_channels = 0
        for key in graphname.node[node]["used-channels"].keys():
            if graphname.node[node]["used-channels"][key] != 0:
                nr_of_channels += 1

        if nr_of_channels > nr_of_modules:
            logger.error("Node " + str(node) + " has more channels attached than it has modules:" + str(nr_of_channels) + " > " + str(nr_of_modules) + ")")
            logger.error(graphname.node[node]["used-channels"])
            valid = False
            break

    if valid:
        logger.info("Graph is valid")
    else:
        logger.error("Graph is NOT valid")

    return valid


def write_json(graph, lan_nodes, wlan_modules, filename="graph.json"):
    """ Write a given NetworkX graph to a json file"""
    i = 0
    nodes_dict_index = dict()
    nodes_dict_name = dict()
    for key in lan_nodes.union(wlan_modules):
        nodes_dict_index[i] = key
        nodes_dict_name[key] = i
        i += 1

    connections = list()
    for (A, B) in graph.edges():
        if A in wlan_modules and B in wlan_modules:
            if graph.edge[A][B]["channel"]:
                color = "green"
            else:
                color = "grey"
            snr = graph.edge[A][B]["snr"]
            dash = "5,5"
        else:
            dash = "0,0"
            snr = 200
            color = "black"
        connections.append((nodes_dict_name[A], nodes_dict_name[B], snr, color, dash))

    json_dict = {"nodes": [{'name': nodes_dict_index[index], "index": index, "channel": "black", "label": nodes_dict_index[index]} for index in nodes_dict_index.keys()],
                 "links": [{"source": source, "target": target, "value": value, "color": color, "dash": dash} for source, target, value, color, dash in connections]}
    with open(filename, 'w') as outfile:
        json.dump(json_dict, outfile, indent=4)


def translate_wlan_mac_to_interface_nr(module_wlan_mac):
    """Translate a wlan mac to an interface Number """
    for index in active_radios:
        if active_radios[index]["wlan_mac"] == module_wlan_mac:
            return active_radios[index]["ifc"]
    logger.error("Could not translate interface_wlan_mac to interface_nr. You are asking for a wrong module")
    exit(1)


def get_table_data(tablename, hostname, username, password):
    """Returns a list of lists with tabledata from wlc for a given tablename, else empty table """
    connection = testcore.control.ssh.SSH(host=hostname, username=username, password=password)
    return connection.runquery_table(tablename)


def get_basic_graph_from_wlc(hostname, username, password):
    """Get data from the WLC and return a networkx basic connectivity graph"""
    logger.info("Getting Data from WLC...")

    # First check if we get a connection to the wlc
    if not os.system("ping -c 1 " + hostname + " > /dev/null") == 0:
        print(hostname + " is down!")
        exit(1)

    # Create the dict of dicts for scan results
    # Example entry: scan_results[<index>][<name>]["lan_mac"] = <value>
    #                scan_results[<index>][<name>]["channel"] = <value>
    #                ...
    intra_wlan_discovery = dict()
    intra_wlan_discovery_index = 0
    for line in get_table_data("/Status/WLAN-Management/Intra-WLAN-Discovery", hostname, username, password):
        entry_dict = dict()
        entry_dict["source_mac"] = line[0]
        entry_dict["wlan_dest_mac"] = line[1]
        entry_dict["channel"] = line[2]
        entry_dict["signal_strength"] = line[3]
        entry_dict["noise_level"] = line[4]
        entry_dict["age"] = line[5]
        intra_wlan_discovery[intra_wlan_discovery_index] = entry_dict
        intra_wlan_discovery_index += 1

    # First create the interfaces-graph
    # That means we create a node for each WLAN-interface of a node
    # and connect each of those of a node with a link with quality 0(best)(so the MST takes this edge always)
    # Therefore we use the Status/WLAN-Management/AP-Status/Active-Radios/ Table of the WLC
    # This gives us the interfaces of each node (identified by the MACs (LAN/WLAN)
    # Create the dict of dicts for active radios
    # Example entry: active_radios[<index>][<name>]["lan_mac"] = <value>
    #                active_radios[<index>][<name>]["bssid_mac"] = <value>
    #                ...
    active_wlan_interfaces = set()
    global active_radios
    active_radios = dict()
    active_radios_index = 0
    for line in get_table_data("/Status/WLAN-Management/AP-Status/Active-Radios", hostname, username, password):
        entry_dict = dict()
        entry_dict["lan_mac"] = line[0]
        entry_dict["ifc"] = line[1]
        entry_dict["ip"] = line[2]
        entry_dict["name"] = line[3]
        if not line[3]:
            logger.error("Name for AP: " + str(line[0]) + " not set!")
            exit(1)
        entry_dict["location"] = line[4]
        entry_dict["wlan_mac"] = line[5]
        entry_dict["radio_band"] = line[6]
        entry_dict["channel"] = line[7]
        entry_dict["modem_load_min"] = line[8]
        entry_dict["modem_load_max"] = line[9]
        entry_dict["modem_load_avg"] = line[10]
        entry_dict["client_count"] = line[11]
        entry_dict["background_scan"] = line[12]
        entry_dict["card_id"] = line[13]
        entry_dict["fw_version"] = line[14]
        entry_dict["card_serial_nr"] = line[15]
        entry_dict["operating"] = line[16]
        entry_dict["transmit_power"] = line[17]
        entry_dict["eirp"] = line[18]
        entry_dict["exc_eirp"] = line[19]
        entry_dict["internal"] = line[20]
        entry_dict["nr_radios"] = line[21]
        entry_dict["module"] = line[22]
        entry_dict["serial_nr"] = line[23]
        entry_dict["version"] = line[24]
        entry_dict["card_state"] = line[25]
        entry_dict["field_optimization"] = line[26]
        entry_dict["ap-connections"] = line[27]
        entry_dict["groups"] = line[28]
        active_wlan_interfaces.add(line[5])
        active_radios[active_radios_index] = entry_dict
        active_radios_index += 1

    # Todo: Foreign table/ Seen-channels, but christoph has to implement this table first (probably wont happen anytime soon)
    # Separate our connections from foreigners
    #our_connections = dict()
    #foreign_connections = dict()
    #for index in scan_results.keys():
    #    if scan_results[index]["seen_bssid"] in active_radios_ap_bssid_mac:
    #        our_connections[index] = scan_results[index]
    #    else:
    #        foreign_connections[index] = scan_results[index]

    # Safety check
    if len(intra_wlan_discovery) == 0:
        logger.error("Our connection list is empty. The APs don't see each other")
        exit(1)

    # Todo: Foreign table/ Seen-channels, but christoph has to implement this table first (probably wont happen anytime soon)
    #if len(foreign_connections) == 0:
    #    logger.warning("Foreign connection list is empty. The APs don't show foreign networks.")
    #    logger.warning("         This is unlikely, except there are really no other wireless lan networks around")

    # Remove the inactive connections from scan results
    # Only consider those connections, which have a corresponding partner in the active radios table, since only those connections are really active
    for index in intra_wlan_discovery.keys():
        if not intra_wlan_discovery[index]["source_mac"] in active_wlan_interfaces or not intra_wlan_discovery[index]["wlan_dest_mac"] in active_wlan_interfaces:
            logger.info("Ignoring link {0},{1}, since at least one is not in active Radios.".format(str(intra_wlan_discovery[index]["source_mac"]),
                                                                                                    str(intra_wlan_discovery[index]["wlan_dest_mac"])))
            del intra_wlan_discovery[index]

    # Create set of nodes, which are modules
    wlan_modules = set()
    for index in active_radios.keys():
        wlan_modules.add(active_radios[index]["wlan_mac"])

    # Create set of nodes, which are not modules (=>actual devices)
    lan_nodes = set()
    for index in active_radios.keys():
        lan_nodes.add(active_radios[index]["lan_mac"])

    basic_graph = nx.DiGraph()

    #
    # Generate the basic graph from data
    #
    # Set default values for nodes
    for node in lan_nodes:
        # Add the node
        basic_graph.add_node(node)

        # Initialize used channels with 0
        used_channels = collections_enhanced.Counter()
        for channel in Assignable_Channels:
            used_channels[channel] = 0
        basic_graph.node[node]["used-channels"] = used_channels

        # Set number of modules initially to 0
        basic_graph.node[node]["modules"] = 0

    # Set default values for modules
    for module in wlan_modules:

        # Add the module-node
        basic_graph.add_node(module)

        # Set the default channel
        basic_graph.node[module]["channel"] = None

        # Initialize actually seen counters for wlan modules with 0
        actually_seen_channels = collections_enhanced.Counter()
        for channel in Assignable_Channels:
            actually_seen_channels[channel] = 0
        basic_graph.node[module]["seen_channels"] = actually_seen_channels

        # Initialize nr of modules for wlan module
        basic_graph.node[module]["modules"] = 1

    # Fill/Add node-module edges with data from wlc
    for index in active_radios.keys():
        lan_mac = active_radios[index]["lan_mac"]
        name = active_radios[index]["name"]
        wlan_mac = active_radios[index]["wlan_mac"]

        # Add the edge
        basic_graph.add_edge(lan_mac, wlan_mac)

        # Module-edge data
        basic_graph.edge[lan_mac][wlan_mac]["real-connection"] = False

        # Write all data also into graph
        basic_graph.node[wlan_mac]["module-of"] = lan_mac
        basic_graph.node[wlan_mac]["module-of-name"] = name
        for key in active_radios[index].keys():
            basic_graph.edge[lan_mac][wlan_mac][key] = active_radios[index][key]

        # Also count here the number of modules each node has
        basic_graph.node[lan_mac]["modules"] += 1

    # Add all possible module-module links
    for index in intra_wlan_discovery.keys():
        source_mac = intra_wlan_discovery[index]["source_mac"]
        wlan_dest_mac = intra_wlan_discovery[index]["wlan_dest_mac"]
        #channel = autowds_topology_scan_results[index]["channel"]
        signal_strength = int(intra_wlan_discovery[index]["signal_strength"])
        #noise_level = int(autowds_topology_scan_results[index]["noise_level"])
        #age = autowds_topology_scan_results[index]["age"]

        basic_graph.add_edge(source_mac, wlan_dest_mac)

        # Set the score of this edge
        # The following is done, since Alfred Arnold mentioned that the Signal-strength value in LCOS is already the SNR
        snr = signal_strength
        basic_graph.edge[source_mac][wlan_dest_mac]["snr"] = snr

        # Initialize each edge with empty channel
        basic_graph.edge[source_mac][wlan_dest_mac]["channel"] = None
        basic_graph.edge[source_mac][wlan_dest_mac]["real-connection"] = True

    # Todo: Foreign table/ Seen-channels, but christoph has to implement this table first (probably wont happen anytime soon)
    # Fill interference list
    #for index in foreign_connections.keys():
    #    channel = foreign_connections[index]["channel"]
    #    wlan_mac = foreign_connections[index]["wlan_mac"]
    #    # Add to interference list of this wlan module-node
    #    # Only consider the channels we have in Assignable channels, since the others are useless
    #    if channel in Assignable_channels:
    #        basic_graph.node[wlan_mac]["seen_channels"][channel] += 1

    return basic_graph, wlan_modules, lan_nodes


def write_graph_to_wlc(wlan_modules, address, username, password, pmst_graph_with_channels_assigned):
    """ Write the given NetworkX graph back to the WLC, so it can reconfigure the Accesspoints"""
    logger.info("Writing Data to WLC")
    lcos_script = list()

    # Set the configuration delay to a good value (5Seconds is enough in our case)
    lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/Commonprofiles/WLAN_PROF {Configuration-Delay} 3')

    # Tell the WLC to use the connections we give them for the APs
    lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/AutoWDS-Profiles/AUTOWDS_PROFILE {Topology-Management} 2')

    # Delete the old connection-table
    lcos_script.append('rm /Setup/WLAN-Management/AP-Configuration/AutoWDS-Topology/*')

    # Add the links for the connection
    prio_counter = 1000  # Magic hidden value in LCOS (implemented by Christoph)
    for a, b in pmst_graph_with_channels_assigned.edges():
        if not a in wlan_modules or not b in wlan_modules:
            continue

        module_a = str(a)
        module_b = str(b)
        module_a_device = str(pmst_graph_with_channels_assigned.node[module_a]["module-of-name"])
        module_b_device = str(pmst_graph_with_channels_assigned.node[module_b]["module-of-name"])
        module_a_interface_nr = int(translate_wlan_mac_to_interface_nr(module_a)) + 1
        module_b_interface_nr = int(translate_wlan_mac_to_interface_nr(module_b)) + 1
        module_a_interface_name = "WLAN-" + str(module_a_interface_nr)
        module_b_interface_name = "WLAN-" + str(module_b_interface_nr)

        # Form: AUTOWDS_PROFILE 0 AP1 IFC1 AP2 IFC2
        #if not wlc_connection.runscript(['set /Setup/WLAN-Management/AP-Configuration/AutoWDS-Topology/AUTOWDS_PROFILE 0 ' + module_a_device + ' ' + module_a + ' ' + module_b_device + ' ' + module_b]):
        #    logger.error("Could not write a link to table")
        #    exit(1)
        lcos_script.append('add /Setup/WLAN-Management/AP-Configuration/AutoWDS-Topology/AUTOWDS_PROFILE {0} {1} {2} {3} {4} "12345678" 1 * * * {5}'.format(prio_counter, module_a_device, module_a_interface_name, module_b_device, module_b_interface_name, continuation_time))
        prio_counter += 1

    # Assign channels to the modules
    module_channel_assignment = dict()
    for module in wlan_modules:
        if module not in module_channel_assignment:
            module_channel_assignment[module] = pmst_graph_with_channels_assigned.node[module]["channel"]
        else:
            # Check if it has the same channel like the entry in the dictionary
            # (since it has to be consistent, else this is a fatal error and sth is wrong with the algorithm)
            if not module_channel_assignment[module] == pmst_graph_with_channels_assigned.node[module]["channel"]:
                logger.error("Interface-Channel assignment problem.")
                exit(1)
    for element in module_channel_assignment:
        module_name = str(element)
        channel = str(module_channel_assignment[element])

        # Check if we use this module, if not the channel is still None
        if module_channel_assignment[element] is None:
            continue

        module_number = int(translate_wlan_mac_to_interface_nr(module_name)) + 1
        module_number_name = "WLAN-Module-" + str(module_number)
        module_channel_list_name = "Module-" + str(module_number) + "-Channel-List"
        # Set the band
        # Excerpt from LCOS : :default (0), 2.4GHz (1), 5GHz (2), Off (3), Auto (255)
        if int(module_channel_assignment[element]) <= 14:  # set to 2,4GHz
            band = "1"
        else:  # set to 5GHz
            band = "2"
        corresponding_device_name = pmst_graph_with_channels_assigned.node[module_name]["module-of"]

        lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/Accesspoints/{0} {{{1}}} {2} {{{3}}} {4}'.format(corresponding_device_name, module_number_name, band, module_channel_list_name, channel))

    # Really write it now
    for line in lcos_script:
        logger.debug(line)
    answer = raw_input("Really write this to the WLC? [yN]:")
    if answer and len(answer) > 0:
        if answer[0] == "y" or answer[0] == "Y":
            wlc_connection = testcore.control.ssh.SSH(host=address, username=username, password=password)
            wlc_connection.runscript(lcos_script)
            print("Successfully written data to WLC")
            return
    print("Nothing written to WLC")


def wlc_is_up(hostname):
    """Check if the WLC is up and running"""
    if not os.system("ping -c 1 " + hostname + " > /dev/null") == 0:
        return False
    else:
        return True


#
# Functions for Solving the Theoretical Problem
#

def module_is_used(mst_graphname, module):
    """Check if module is used

     Go through all neighbors, and if there is one neighbor, which is not reached over a real-connection, then this module is used
    """
    for neighbor in mst_graphname.neighbors(module):
        module_con = mst_graphname.edge[module][neighbor]["real-connection"]
        if module_con is True:
            return True
    return False


def count_connected_module_edges_for_module(graph, module, wlan_modules):
    """Count number of connected module-module edges

    For a given module and a graph counts the module edges we can reach by stepping over only other module edges.

    Returns number of modules as integer
    """
    connection_counter = 0
    edges_done = set()
    modules_todo = list()

    # Start with initial module node
    modules_todo.append(module)

    for mod in modules_todo:
        for neighbor in graph.neighbors(mod):
            if neighbor in wlan_modules:
                if (mod, neighbor) not in edges_done:
                    # Increase connection counter
                    connection_counter += 1

                    # Add edge to done-list
                    edges_done.add((mod, neighbor))
                    edges_done.add((neighbor, mod))

                    # Add module to go if not already visited
                    if neighbor not in modules_todo:
                        modules_todo.append(neighbor)
    return connection_counter


def translate_snr_to_bw(snr_lancom_value):
    """Translate the signal to noise ratio to an expected bandwidth

    Simulates a function
    Returns an integer which is an indicator for the expected bandwidh, higher is better
    """
    signal_to_noise = snr_lancom_value / 100.0 * 46.0
    if signal_to_noise <= 0:
        return 0
    elif 0 < signal_to_noise <= 10:
        return signal_to_noise
    elif 10 < signal_to_noise <= 20:
        return 2 * signal_to_noise - 10
    elif 20 < signal_to_noise <= 25:
        return 3 * signal_to_noise - 30
    elif 25 < signal_to_noise <= 30:
        return 2 * signal_to_noise - 5
    else:
        return 56


def get_used_module_neighbors(graph, basic_con_graph, node, wlan_modules):
    """ Get a list of active module neighbors for a node
    Returns a list with modules
    """
    module_neighbors = list()
    for neighbor in basic_con_graph.neighbors(node):
        if neighbor in wlan_modules and neighbor is not node:
            module_neighbors.append(neighbor)
    # Return all neighbors of node in basic_con_graph which are actually used in graph
    return [i for i in module_neighbors if module_is_used(graph, i)]


def get_connected_modules_for_module(graph, module, wlan_modules):
    """ Get modules which are connected to this module

    For a given module return the modules connected to this module over a module-module edge in graph

    Returns a list with modules
    """
    connected_modules = list()
    edges_done = set()
    modules_todo = list()

    # Add initial node to be able to start from there
    modules_todo.append(module)

    for mod in modules_todo:
        for neighbor in graph.neighbors(mod):
            if neighbor in wlan_modules and (mod, neighbor) not in edges_done:
                connected_modules.append(neighbor)

                # Add edge to done-list
                edges_done.add((mod, neighbor))
                edges_done.add((neighbor, mod))

                # Add module to go if not already visited
                if neighbor not in modules_todo:
                    modules_todo.append(neighbor)
    return connected_modules


def get_used_interference_modules_for_link(graph, basic_con_graph, node_a, node_b, wlan_modules):
    """ Get a list of module neighbors for two nodes in a given graph, which are in the interference range of the two nodes

    Returns a list of modules which are in interference range
    """
    possibly_interfering_modules = list(set(get_used_module_neighbors(graph, basic_con_graph, node_a, wlan_modules) + get_used_module_neighbors(graph, basic_con_graph, node_b, wlan_modules)))
    # Remove our own modules (because the modules see each other)
    for module in [node_a, node_b]:
        if module in possibly_interfering_modules:
            possibly_interfering_modules.remove(module)
    # Take only those modules from this list, which actually interfere,
    # that means: only modules which use the same channel,
    # that means: those are connected(ie. those modules i can reach from a module using only module-module edges)
    actually_interfering_modules = get_connected_modules_for_module(graph, node_a, wlan_modules) + get_connected_modules_for_module(graph, node_b, wlan_modules)
    return [i for i in possibly_interfering_modules if i in actually_interfering_modules]


def calculate_score_for_edge(curr_mst_graph, basic_con_graph, node_a, node_b, wlan_modules):
    """ Calculate Edgescore for a given edge
    A higher score is better

    Keyword arguments:
    curr_mst_graph -- The MST NetworkX graph we created so far
    basic_con_graph -- The underlying networkX topology graph
                        This graphs read-edges have to have the attribute "snr"
    node_a -- name of the node of basic_con_graph for which we want to calculate the score
    node_b -- name of the node of basic_con_graph for which we want to calculate the score
    wlan_modules -- List with the names of modules of basic_con_graph
    returns score as float
    """

    if not basic_con_graph.edge[node_a][node_b]["real-connection"]:
        return edge_max_score

    node_a_connected_count = count_connected_module_edges_for_module(curr_mst_graph, node_a, wlan_modules)
    node_b_connected_count = count_connected_module_edges_for_module(curr_mst_graph, node_b, wlan_modules)
    sum_connected_count = node_a_connected_count + node_b_connected_count

    average_snr = basic_con_graph.edge[node_a][node_b]["snr"]
    expected_bandwidth = translate_snr_to_bw(average_snr)

    interfering_modules = get_used_interference_modules_for_link(curr_mst_graph, basic_con_graph, node_a, node_b, wlan_modules)
    nr_interfering_modules = len(interfering_modules)

    # Circumvent the division by zero case
    if nr_interfering_modules == 0:
        nr_interfering_modules = 1
    if sum_connected_count == 0:
        sum_connected_count = 1

    # Divide expected bandwidth by the number of interfering channels, since we share the channel with those links
    score = expected_bandwidth / (sum_connected_count * nr_interfering_modules)

    return score


def calculate_mst(graphname, wlan_modules):
    """ Find the maximal spanning tree

    Keyword arguments:
    graphname -- NetworkX Graph with edges that have the following attributes:
                "real-connection" - indicates whether this is a real connection as in module-module
                                    or an artificial connection like node-module
                "snr" - indicates the Signal to Noise ratio for this edge.
    wlan_modules -- List of nodenames of graphname which are modules, the rest (all nodes - modules) are device nodes
    returns a MST NetworkX Graph
    """

    logger.info("Calculating MST on Graph...")

    mst = nx.Graph()
    visited_nodes = set()
    edge_list = collections_enhanced.Counter()  # Edge list contains triple with (source,target,edge-weigth)
    all_nodes = set()

    # Copy nodes from graphname to mst and fill the set: all_nodes
    for node in graphname.nodes():
        all_nodes.add(node)
        mst.add_node(node)
        for key in graphname.node[node].keys():
            mst.node[node][key] = graphname.node[node][key]

    # Devices are all those nodes which are not modules
    devices = [node for node in graphname.nodes() if node not in wlan_modules]

    # Select random Device to start with
    start_node = random.choice(list(devices))

    # Add the edges originating from start node to edge_list
    visited_nodes.add(start_node)
    for neighbor in graphname.neighbors(start_node):
        edge_list[(start_node, neighbor)] = calculate_score_for_edge(mst, graphname, start_node, neighbor, wlan_modules)

    # Main loop
    while True:
        # Remove all edges which do not see new nodes (keep only productive edges)
        removed_edge = True
        while removed_edge:
            removed_edge = False
            for (a, b) in edge_list:
                if a in visited_nodes and b in visited_nodes:
                    removed_edge = True
                    del edge_list[(a, b)]
                    break

        # If the edge_list is empty after removing unproductive edges, check if we visited all nodes
        if len(edge_list) == 0:
            if len(visited_nodes) != graphname.number_of_nodes():
                logger.error("Could not connect all nodes.")
                logger.error("Graph / APs are separated, maybe wait some time until they can at least theoretically span a network.")
                exit(1)
            else:
                break

        # Find the best new edge and add it to the mst
        # Therefore just take the edge with the highest score
        (bestedge_node_a, bestedge_node_b), highest_score = edge_list.most_common(1)[0]

        # Mark node as visited
        visited_nodes.add(bestedge_node_b)

        # Add the edge to mst
        mst.add_edge(bestedge_node_a, bestedge_node_b)
        for key in graphname.edge[bestedge_node_a][bestedge_node_b].keys():
            mst.edge[bestedge_node_a][bestedge_node_b][key] = graphname.edge[bestedge_node_a][bestedge_node_b][key]

        # Add its edges to the edge_list
        for neighbor in graphname.neighbors(bestedge_node_b):
            if neighbor not in visited_nodes:
                edge_list[(bestedge_node_b, neighbor)] = calculate_score_for_edge(mst, graphname, bestedge_node_b, neighbor, wlan_modules)

        # Remove the edge from edgelist, to speed up things since we dont need it any longer (since we are using it)
        del edge_list[(bestedge_node_a, bestedge_node_b)]

        # Update the scores, because scores might change, since we added new edge => score of others could get decreased
        # Todo: this could be made more efficient, by just updating those edges, where sth has changed instead of all, find out if this would be a performance killer first
        for (a, b) in edge_list:
            edge_list[(a, b)] = calculate_score_for_edge(mst, graphname, a, b, wlan_modules)

    return mst


def calculate_backup_links(mst, basic_con_graph, wlan_modules):
    """ Finds the best backup links for a given mst graph

    Keyword arguments:
    mst -- The NetworkX Maximal spanning tree we created in step 1
    basic_con_graph -- the underlying connectivity graph
    wlan_modules -- list of names of nodes of the basic_con_graph
    returns a 2-edge-connected MST NetworkX graph
    """

    logger.info("Calculating Backup links for Graph...")

    mst_edges = copy.copy(mst.edges())
    for edge in mst_edges:

        # Simulate each edge failing
        if edge[0] in wlan_modules and edge[1] in wlan_modules:

            mst.remove_edge(edge[0], edge[1])
            # Check if there still is a path to get to edge[1] even if this edge has failed
            # If we have still a path to edge[1], then we are done
            # else select second highest rated edge to get there
            if not nx.has_path(mst, edge[0], edge[1]):
                edge_list = collections_enhanced.Counter()

                connected_components = nx.connected_components(mst)
                if len(connected_components) != 2:
                    logger.error("Could not split graph into two groups")
                    exit(1)

                # Create Group A and B
                if edge[0] in connected_components[0]:
                    group0 = connected_components[0]
                    group1 = connected_components[1]
                else:
                    group0 = connected_components[1]
                    group1 = connected_components[0]

                # Find edges connecting Group A and B
                connecting_edges = list()
                for edge in mst.edges():
                    if edge[0] in group0 and edge[1] in group1 or edge[0] in group1 and edge[1] in group0:
                        connecting_edges.add(edge)

                # Calculate scores for those survival edges
                for con_edge in connecting_edges:
                    edge_list[(con_edge[0], con_edge[1])] = calculate_score_for_edge(mst, basic_con_graph, con_edge[0], con_edge[1], wlan_modules)

                # Add edges with higest score that connects those two groups to the graph
                (bestedge_node_a, bestedge_node_b), highest_score = edge_list.most_common(1)[0]
                mst.add_edge(bestedge_node_a, bestedge_node_b)
                mst.edge[bestedge_node_a][bestedge_node_b]["backup-link"] = True
                for key in basic_con_graph.edge[bestedge_node_a][bestedge_node_b].keys():
                    mst.edge[bestedge_node_a][bestedge_node_b][key] = basic_con_graph.edge[bestedge_node_a][bestedge_node_b][key]

            # Add the removed edge again
            mst.add_edge(edge[0], edge[1])
            for key in basic_con_graph.edge[edge[0]][edge[1]].keys():
                mst.edge[edge[0]][edge[1]][key] = basic_con_graph.edge[edge[0]][edge[1]][key]

    return mst


def get_connected_channels_for_edge(graphname, node_a, node_b, wlan_modules):
    """ Accumulate the channel group

    Returns the number of connected occurences for a certain channel at a module
    It counts all the connected edges of the same channel (over multiple modules)

    Keyword arguments:
    graphname -- NetworkX Graph which is to be channel assigned
    node_a, node_b -- The nodes of the edge we want to get the channelgroup for
    wlan_modules -- list of names of nodes of the basic_con_graph

    Returns a set of tuples, where each tuple represents a connection
    """

    channel_group = set()
    modules_done = set()
    modules_todo = set()
    if node_a in wlan_modules:
        modules_todo.add(node_a)
    if node_b in wlan_modules:
        modules_todo.add(node_b)

    channel_group.add((node_a, node_b))

    for module in modules_todo:
        neighbors = graphname.neighbors(module)
        for neighbor in neighbors:
            if neighbor in wlan_modules and neighbor not in modules_done:
                modules_todo.add(neighbor)
                channel_group.add((module, neighbor))

        modules_done.add(module)

    return channel_group


def count_local_interference(graphname, connectivity_graph, channel_group, wlan_modules):
    """ Counts which channels interfere for a given channel-group

    Keyword arguments:
    graphname --
    connectivity_graph -- A NetworkX Graph which represents the basic connectivity
    channel_group -- A List of tuples which represent links in a channel-group
    wlan_modules -- List of nodenames of graphname which are modules, the rest (all nodes - modules) are device nodes

    Requires the nodes of graphname to have attributes: "seen_channels"  which is a list of foreign wlans
                                                        "channel" which is None if no channel is assigned to
                                                        that node or the channel which has been assigned to that connection

    Returns two collections_enhanced.Counter with the number of internal interference counts for each channel and external interference
    """

    internal_channel_counter = collections_enhanced.Counter()
    external_channel_counter = collections_enhanced.Counter()
    modules = set()

    for (module_a, module_b) in channel_group:
        modules.add(module_a)
        modules.add(module_b)

    for module in modules:
        neighbors = connectivity_graph.neighbors(module)
        for neighbor in neighbors:

            # Internal Interference
            channel = graphname.node[module_a]["channel"]
            if channel:
                internal_channel_counter[channel] += 1

        # External Interference
        for external_channel in graphname.node[module]["seen_channels"]:
            external_channel_counter[external_channel] += 1

    return internal_channel_counter, external_channel_counter


def assign_channel_to_channel_group(channel, channel_group, graphname, overall_channel_counter):
    """ Assigns channels to all members of this channel group"""
    for node_a, node_b in channel_group:
        graphname.node[node_a]["channel"] = channel
        graphname.node[node_b]["channel"] = channel
        graphname.edge[node_a][node_b]["channel"] = channel

    # Increase overall channel counter
    overall_channel_counter[channel] += 1


def calculate_caa_for_graph(graphname, connectivity_graph, wlan_modules, overall_channel_counter, Assignable_Channels):
    """ Calculate a Channel Assignment for a given NetworkX graph"""
    logger.info("Calculating channel assignment for graph...")

    # Iterate over all Edges
    for edge in graphname.edges():
        if graphname.edge[edge[0]][edge[1]]["real-connection"]:
            # Get the channel group for this edge
            channel_group = get_connected_channels_for_edge(graphname, edge[0], edge[1], wlan_modules)

            # For each module in channel group, count the channel usages
            internal_interference, external_interference = count_local_interference(graphname, connectivity_graph, wlan_modules)

            election_counter = collections_enhanced.Counter()
            for channel in Assignable_Channels:
                election_counter[channel] = 0

            # Respect internal interference
            for channel in internal_interference:
                if channel in election_counter:
                    election_counter[channel] += internal_interference[channel]

            # Respect external interference
            for channel in external_interference:
                if channel in election_counter:
                    election_counter[channel] += external_interference[channel]

            # Select the channel that has been used the least
            best_channels = election_counter.least_common_all()
            if len(best_channels) == 1:
                best_channel = best_channels[0]
            else:
                second_election = collections_enhanced.Counter()
                for channel in best_channels:
                    second_election[channel] = overall_channel_counter[channel]
                    best_channels = second_election.least_common_all()
                    if len(best_channels) == 1:
                        best_channel = best_channels[0]
                    else:
                        best_channel = random.choice(best_channels)

            # Assign the best channel to the channel group
            assign_channel_to_channel_group(best_channel, channel_group, graphname, overall_channel_counter)

    return graphname


# Configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
if len(sys.argv) < 6:
    sys.exit("Usage: python CAA.py <wlc-address> <wlc-username> <wlc_password> <usable-channels> <continuation_time in min>")
wlc_address = sys.argv[1]
wlc_username = sys.argv[2]
wlc_password = sys.argv[3]
Assignable_Channels = sys.argv[4].split(",")  # List of all channels which can be used for assignment
continuation_time = sys.argv[5]  # How long the APs should stay connected until going back to scanning mode

if not wlc_is_up(wlc_address):
    logger.error("WLC:" + str(wlc_address) + " seems to be offline.")
    exit(1)

edge_max_score = 1000  # The score for node-module connections, this has to be higher than any possible module-module connection
channel_counter = collections_enhanced.Counter()  # This counts how often each channel has been used overall, initially fill with 0
for channel_entry in Assignable_Channels:
    channel_counter[channel_entry] = 0

# Getting Data from WLC
basic_connectivity_graph_directed, modules, devices = get_basic_graph_from_wlc(wlc_address, wlc_username, wlc_password)

# Convert to undirected graph
basic_connectivity_graph = convert_to_undirected_graph(basic_connectivity_graph_directed)

# First phase: Calculate the Minimal Spanning Tree from the basic connectivity graph
mst_graph = calculate_mst(basic_connectivity_graph, modules)

# Assign channels to the mst
mst_graph_with_channels_assigned = calculate_caa_for_graph(mst_graph, basic_connectivity_graph, modules, channel_counter, Assignable_Channels)

# Finally check the graph for validity
if not graph_is_valid(mst_graph_with_channels_assigned, devices, modules):
    exit(1)

# Calculate the backup links for a given, CAAed mst
# Todo: create copy for mst_graph_with_channels_assigned because this variable is overwritten/modified
#robust_graph = calculate_backup_links(mst_graph_with_channels_assigned, basic_connectivity_graph, modules)
#show_graph(robust_graph, modules, devices, filename_svg='caa_robust.svg', filename_json="graph_robust.json")

# In the wlc set the links and channels
write_graph_to_wlc(modules, wlc_address, wlc_username, wlc_password, mst_graph_with_channels_assigned)
