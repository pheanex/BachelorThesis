import json
import os
import logging

import networkx as nx

import collections_enhanced
import testcore.control.ssh

__author__ = 'kmanna'
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

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


def graph_is_valid(graphname, lan_nodes, wlan_modules, assignable_channels):
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
                    if graphname.edge[edge[0]][edge[1]]["channel"] not in assignable_channels:
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


def get_modules_of_graph(graphname):
    """ For a given graph return a list of nodes where the "isModule" flag is true
    """

    return [node for (node, attributes) in graphname.nodes(data=True) if attributes["isModule"]]


def write_json(graph, filename="graph.json"):
    """Writes the given graph to a json file in a format that can be read by AutoWDSstatus

     Keyword arguments:
        filename - String, name of the file where the json should be written to, defaultname is "graph.json"
    """

    wlan_modules = get_modules_of_graph(graph)
    i = 0
    nodes_dict_index = dict()
    nodes_dict_name = dict()
    for key in graph.nodes():
        nodes_dict_index[i] = key
        nodes_dict_name[key] = i
        i += 1

    connections = list()
    for (A, B) in graph.edges():
        if A in wlan_modules and B in wlan_modules:
            if "channel" in graph.edge[A][B]:
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

    json_dict = {"nodes": [{"index": index, "ip": "", "connectiontype": "WLAN-AutoWDS", "label": nodes_dict_index[index], "mac": "", "type": ""} for index in nodes_dict_index.keys()],
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


def get_basic_graph_from_wlc(hostname, username, password, assignable_channels):
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
        for channel in assignable_channels:
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
        for channel in assignable_channels:
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
    #    if channel in assignable_channels:
    #        basic_graph.node[wlan_mac]["seen_channels"][channel] += 1

    return basic_graph, wlan_modules, lan_nodes


def write_graph_to_wlc(wlan_modules, address, username, password, pmst_graph_with_channels_assigned, continuation_time):
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
        #if not wlc_connection.runscript(['set /Setup/WLAN-Management/AP-Configuration/AutoWDS-Topology/AUTOWDS_PROFILE 0 ' + module_a_device + ' ' + module_a + ' ' + module_b_device + ' '+module_b]):
        #    logger.error("Could not write a link to table")
        #    exit(1)
        lcos_script.append('add /Setup/WLAN-Management/AP-Configuration/AutoWDS-Topology/AUTOWDS_PROFILE {0} {1} {2} {3} {4} "12345678" 1 * * * {5}'
                           .format(prio_counter, module_a_device, module_a_interface_name, module_b_device, module_b_interface_name, continuation_time))
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

        lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/Accesspoints/{0} {{{1}}} {2} {{{3}}} {4}'
                           .format(corresponding_device_name, module_number_name, band, module_channel_list_name, channel))

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