import logging
import random
import copy
import networkx as nx
import collections_enhanced
import json

__author__ = 'kmanna'

edge_max_score = 1000  # The score for node-module connections, this has to be higher than any possible module-module connection
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def write_json(graph, filename="autowds-graph.json"):
    """Writes the given graph to a json file in a format that can be read by AutoWDSstatus

     Keyword arguments:
        filename - String, name of the file where the json should be written to, defaultname is "autowds-graph.json"
    """

    wlan_modules = get_modules_of_graph(graph)
    i = 0
    nodes_dict_index = dict()
    nodes_dict_name = dict()
    nodetype = dict()
    channel = dict()
    for key in graph.nodes():
        nodes_dict_index[i] = key
        nodes_dict_name[key] = i
        if key in wlan_modules:
            nodetype[i] = "IFC"
            if "channel" in graph.node[key]:
                channel[i] = graph.node[key]["channel"]
            else:
                channel[i] = ""
        else:
            nodetype[i] = "AP"
            channel[i] = ""
        i += 1

    connections = list()
    for (A, B) in graph.edges():
        if A in wlan_modules and B in wlan_modules:
            if "channel" in graph.edge[A][B]:
                connectiontype = "real"
                state = "Active"
            else:
                connectiontype = "seen"
                state = "possible"
            snr = graph.edge[A][B]["snr"]
        else:
            connectiontype = "fake"
            state = "Active"
            snr = 200
        connections.append((nodes_dict_name[A], nodes_dict_name[B], snr, connectiontype, state))

    json_dict = {"nodes": [{"index": index,
                            "ip": "",
                            "connectiontype": "WLAN-AutoWDS",
                            "label": nodes_dict_index[index],
                            "mac": "",
                            "type": nodetype[index],
                            "channel": channel[index]} for index in nodes_dict_index.keys()],
                 "links": [{"sourcenoise": "",
                            "sourcemac": "",
                            "source": source,
                            "sourceage": 0,
                            "sourcestrength": snr,
                            "targetage": 0,
                            "targetnoise": "",
                            "target": target,
                            "targetstrength": snr,
                            "targetmac": "",
                            "connectiontype": connectiontype,
                            "state": state} for source, target, snr, connectiontype, state in connections]}
    with open(filename, 'w') as outfile:
        json.dump(json_dict, outfile, indent=4)


def module_is_used(mst_graphname, module):
    """Check if module is used

     Go through all neighbors, and if there is one neighbor, which is not reached over a real-connection, then this module is used
    """
    for neighbor in mst_graphname.neighbors(module):
        if is_real_edge(mst_graphname, module, neighbor):
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

    if is_fake_edge(basic_con_graph, node_a, node_b):
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


def get_modules_of_graph(graphname):
    """ For a given graph return a list of nodes where the "isModule" flag is true
    """

    return [node for (node, attributes) in graphname.nodes(data=True) if attributes["isModule"]]


def calculate_st(graphname):
    """ Find the maximal spanning tree

    Keyword arguments:
    graphname -- undirected NetworkX Graph where
                    edges have attributes:
                        "snr" - Integer which indicates the Signal to Noise ratio for this edge.
                    nodes have attributes
                        "isModule" - True if node is a Module or False if not
    returns an undirected MST NetworkX Graph
    """

    logger.info("Calculating MST on Graph...")

    wlan_modules = get_modules_of_graph(graphname)

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
    not_wlan_modules = [node for node in graphname.nodes() if node not in wlan_modules]

    # Select random Device to start with
    start_node = random.choice(list(not_wlan_modules))

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
        # If there is a tie, select the edge with the best snr
        bestedges = edge_list.most_common_all()
        if len(bestedges) > 1:
            snrscore = collections_enhanced.Counter()
            for edge in bestedges:
                snrscore[edge] = graphname.edge[edge[0]][edge[1]]["snr"]
            bestedge = snrscore.most_common(1)[0]
            bestedge_node_a = bestedge[0][0]
            bestedge_node_b = bestedge[0][1]
            highest_score = bestedge[1]
        else:
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


def calculate_survival_links(mst_original, basic_con_graph):
    """ Finds the best backup links for a given mst graph

    Keyword arguments:
    mst -- undirected weighted NetworkX Maximal spanning tree we created in step 1
    basic_con_graph -- undirected NetworkX graph - the underlying connectivity graph
    returns a 2-edge-connected MST NetworkX graph
    """

    logger.info("Calculating Survival links for Graph...")

    wlan_modules = get_modules_of_graph(basic_con_graph)

    mst = copy.deepcopy(mst_original)

    mst_edges = copy.copy(mst.edges())
    for edge in mst_edges:

        # Simulate each edge failing
        if edge[0] in wlan_modules and edge[1] in wlan_modules:

            mst.remove_edge(edge[0], edge[1])
            # Check if there still is a path to get to edge[1] even if this edge has failed
            # If we have still a path to edge[1], then we are done
            # else select second highest rated edge to get there
            if not nx.has_path(mst, edge[0], edge[1]):
                logger.debug("Edge " + str(edge) + " has no backup, searching one")
                edge_list = collections_enhanced.Counter()

                connected_components = nx.connected_components(mst)
                if len(connected_components) != 2:
                    logger.error("Could not split graph into two groups")
                    return 1

                # Create Group A and B
                if edge[0] in connected_components[0]:
                    group0 = connected_components[0]
                    group1 = connected_components[1]
                else:
                    group0 = connected_components[1]
                    group1 = connected_components[0]

                # Find edges connecting Group A and B
                connecting_edges = list()
                for cedge in basic_con_graph.edges():
                    if cedge[0] in group0 and cedge[1] in group1 or cedge[0] in group1 and cedge[1] in group0:
                        if not ((cedge[0] == edge[0] and cedge[1] == edge[1]) or (cedge[1] == edge[0] and cedge[0] == edge[1])):
                            connecting_edges.append(cedge)

                # Calculate scores for those survival edges
                for con_edge in connecting_edges:
                    edge_list[(con_edge[0], con_edge[1])] = calculate_score_for_edge(mst, basic_con_graph, con_edge[0], con_edge[1], wlan_modules)

                # If there is no connection that reconnects the two groups, then we can't do anything about it
                if len(connecting_edges) == 0:
                    logger.warning("Could not find backup for edge " + str(edge))
                    continue

                # Add edges with higest score that connects those two groups to the graph
                (bestedge_node_a, bestedge_node_b), highest_score = edge_list.most_common(1)[0]

                logger.debug("The backup for edge " + str(edge) + " is: ('" + str(bestedge_node_a) + "', '" + str(bestedge_node_b) + "')")

                mst.add_edge(bestedge_node_a, bestedge_node_b)
                mst.edge[bestedge_node_a][bestedge_node_b]["backup-link"] = True
                for key in basic_con_graph.edge[bestedge_node_a][bestedge_node_b].keys():
                    mst.edge[bestedge_node_a][bestedge_node_b][key] = basic_con_graph.edge[bestedge_node_a][bestedge_node_b][key]
            else:
                logger.debug("Edge " + str(edge) + " already has backup, moving to next edge")

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
    modules_todo = list()
    if node_a in wlan_modules:
        modules_todo.append(node_a)
    if node_b in wlan_modules:
        modules_todo.append(node_b)

    channel_group.add((node_a, node_b))

    for module in modules_todo:
        neighbors = graphname.neighbors(module)
        for neighbor in neighbors:
            if neighbor in wlan_modules and neighbor not in modules_todo:
                modules_todo.append(neighbor)
                channel_group.add((module, neighbor))

    return channel_group


def count_local_interference(graphname, connectivity_graph, channel_group, wlan_modules):
    """ Counts which channels interfere for a given channel-group

    Keyword arguments:
    graphname --
    connectivity_graph -- A NetworkX Graph which represents the basic connectivity
    channel_group -- A List of tuples which represent links in a channel-group
    wlan_modules -- List of nodenames of graphname which are modules, the rest (all nodes - modules) are device nodes

    Requires the module-nodes of graphname to have the following attributes:
    "seen_channels"  which is a list of foreign wlans like [1,6,11,11,36]
    "channel" which is None if no channel is assigned to that node or the channel which has been assigned to that connection

    Returns two collections_enhanced.Counter with the number of internal interference counts for each channel and external interference
    """

    internal_channel_counter = collections_enhanced.Counter()
    external_channel_counter = collections_enhanced.Counter()
    modules = set()

    for (module_a, module_b) in channel_group:
        modules.add(module_a)
        modules.add(module_b)

    logger.debug("  Interferences for channel-group: " + str(channel_group))
    logger.debug("      Modules are: " + str(modules))

    for module in modules:

        neighbors = connectivity_graph.neighbors(module)

        for neighbor in neighbors:

            logger.debug("      Neigh for module: " + str(module) + ": " + str(neighbor))

            if neighbor in wlan_modules:

                # Internal Interference
                channel = graphname.node[neighbor]["channel"]
                if channel:
                    internal_channel_counter[channel] += 1
                    logger.debug("          For " + str(module) + " : " + str(neighbor) + " @Channel:" + str(channel))
                else:
                    logger.debug("          Ignoring neigh: " + str(neighbor) + "(no channel)")

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


def is_fake_edge(graphname, node_a, node_b):
    """ Returns True if one of the nodes A or B has its flag "isModule" set to False, which makes this connection a fake connection
    """
    if graphname.node[node_a]["isModule"] and graphname.node[node_b]["isModule"]:
        return False
    else:
        return True


def is_real_edge(graphname, node_a, node_b):
    """ Returns True if both nodes A and B have its flag "isModule" set to True, which makes this connection a real connection
    """
    if is_fake_edge(graphname, node_a, node_b):
        return False
    else:
        return True


def has_channel_assigned(graph, node_a, node_b):
    """ Returns True if the given edge already has a channel assigned, False if not
    """

    if graph.edge[node_a][node_b]["channel"]:
        return True
    else:
        return False


def calculate_ca(graphname, basic_con_graph, allowed_channel_list):
    """ Assigns channel fro the allowed_channel_list to the edges of the graphname graph

    Keyword arguments:
    graphname -- undirected weighted NetworkX graph
    basic_con_graph -- undirected NetworkX graph - the underlying connectivity graph
    returns a colored/channel assigned networkx graph
    """

    logger.info("Calculating channel assignment for graph...")

    wlan_modules = get_modules_of_graph(basic_con_graph)

    overall_channel_counter = collections_enhanced.Counter()
    for channel in allowed_channel_list:
        overall_channel_counter[channel] = 0

    # Initialize the edge- and node-channels
    for edge in graphname.edges():
        if is_real_edge(graphname, edge[0], edge[1]):
            graphname.edge[edge[0]][edge[1]]["channel"] = None
    for node in graphname.nodes():
        if node in wlan_modules:
            graphname.node[node]["channel"] = None
            graphname.node[node]["seen_channels"] = []

    # Iterate over all Edges
    for edge in graphname.edges():

        # Only assign channel to real connections
        if is_fake_edge(graphname, edge[0], edge[1]):
            continue

        # Skip this channel group if it already has a channel assigned
        if has_channel_assigned(graphname, edge[0], edge[1]):
            continue

        # Get the channel group for this edge
        channel_group = get_connected_channels_for_edge(graphname, edge[0], edge[1], wlan_modules)

        logger.debug("Coloring Channel-Group: " + str(channel_group))

        # For each module in channel group, count the channel usages
        internal_interference, external_interference = count_local_interference(graphname, basic_con_graph, channel_group, wlan_modules)
        logger.debug("  Internal-Interference: " + str(internal_interference))
        logger.debug("  External-Interference: " + str(external_interference))

        election_counter = collections_enhanced.Counter()
        for channel in allowed_channel_list:
            election_counter[channel] = 0

        # Respect internal interference
        for channel in internal_interference:
            if channel in election_counter:
                election_counter[channel] += internal_interference[channel]

        # Respect external interference
        for channel in external_interference:
            if channel in election_counter:
                election_counter[channel] += external_interference[channel]

        logger.debug("  Election-Counter: " + str(election_counter))

        # Select the channel that would cause the least local interference
        best_channels = election_counter.least_common_all().keys()
        if len(best_channels) == 1:
            best_channel = best_channels[0]
        else:

            # Tie occurred, which channel has been overall used the least?
            second_election = collections_enhanced.Counter()
            for channel in best_channels:
                second_election[channel] = overall_channel_counter[channel]

            logger.debug("  Overall-Channel-Counter: " + str(overall_channel_counter))
            logger.debug("  Second-Election-Counter because of tie: " + str(second_election))

            best_channels = second_election.least_common_all().keys()
            if len(best_channels) == 1:
                best_channel = best_channels[0]
            else:

                logger.debug("  Random-Pick because of tie")

                best_channel = random.choice(best_channels)

        logger.debug("  Using channel " + str(best_channel) + " for channel-group")

        # Assign the best channel to the channel group
        assign_channel_to_channel_group(best_channel, channel_group, graphname, overall_channel_counter)

    return graphname
