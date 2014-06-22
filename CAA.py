#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose Selects the best Topology and Channels for a Mesh network administered by a WLC (Lancom AutoWDS)

import random
import json
import copy
import os
import sys

import networkx as nx
import logging

import collections_enhanced
import testcore.control.ssh


# counterlist = dictionary with channels and their number of occurences
# allowed_channels = list to pick channels from (because we might not be allowed to use all in a certain situation)
# Returns a list with elements that are in the allowed_channels list and are least commonly used
def get_least_used_elements_for_counter_dict(counterlist, allowed_channels):
    # Create new restricted counterlist with only those elements in it, which are also in allowed_channels
    restricted_counterlist = collections_enhanced.Counter()
    for element in counterlist.keys():
        if element in allowed_channels:
            restricted_counterlist[element] = counterlist[element]

    # Get all the least common elements
    return restricted_counterlist.least_common_all()


# Get the parent node for a wlan modules
def get_node_for_module(graphname, module):
    return graphname.node[module]["module-of"]


# Returns counter with entries (like channel : nr of occurences of this channel in neighborhood of node_a and node_b)
# for two nodes/modules and a list of allowed channels
def get_used_channels_for_nodes(graphname, modula_a, module_b, allowed_channels):
    node_a = get_node_for_module(graphname, modula_a)
    node_b = get_node_for_module(graphname, module_b)
    common_channel_counter = graphname.node[node_a]["used-channels"] + graphname.node[node_b]["used-channels"]
    returncounter = collections_enhanced.Counter()
    for key in common_channel_counter.keys():
        if key in allowed_channels:
            returncounter[key] = common_channel_counter[key]

    return returncounter


# Checks if the module_a of an edge is already used for a connection
# Go through all neighbors, and if there is one neighbor, which is not reached over a real-connection, then this module is used
def module_is_used(mst_graphname, module):
    for neighbor in mst_graphname.neighbors(module):
        module_con = mst_graphname.edge[module][neighbor]["real-connection"]
        if module_con is True:
            return True
    return False


# Converts a given directed graph to a undirected graph
# At the moment we just take the average of both edges
# Returns the undirected graph
def convert_to_undirected_graph(directed_graph, middle="lower"):
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


# Calculate for a given module and graph the number of connected module-module edges
def count_connected_module_edges_for_module(graph, module, wlan_modules):
    connection_counter = 0
    edges_done = set()
    modules_todo = list()

    # Add initial node to be able to start from there
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


# Translates the given SNR to a bandwith, so we can use it for calculating the score
# Returns a bandwidth
def translate_snr_to_bw(snr_lancom_value):
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


# Get a list of module neighbors for a node in a given graph
# Returned list only has modules which are actually used in graph for a link
def get_used_module_neighbors(graph, basic_con_graph, node, wlan_modules):
    module_neighbors = list()
    for neighbor in basic_con_graph.neighbors(node):
        if neighbor in wlan_modules and neighbor is not node:
            module_neighbors.append(neighbor)
    # Return all neighbors of node in basic_con_graph which are actually used in graph
    return [i for i in module_neighbors if module_is_used(graph, i)]


# For a given module return the modules connected to this module over a module-module edge in graph
def get_connected_modules_for_module(graph, module, wlan_modules):
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


# Get a list of module neighbors for two nodes in a given graph, which are in the interference range of the two nodes
# Returns a list of nodes, that are in the interference range
def get_used_interference_modules_for_link(graph, basic_con_graph, node_a, node_b, wlan_modules):
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


# Calculate the score for an edge
# A higher score is better
def calculate_score_for_edge(graph, basic_con_graph, node_a, node_b, wlan_modules):
    # Check if we want to calc the score of a node-module edge
    if node_a not in wlan_modules or node_b not in wlan_modules:
        return edge_max_score

    node_a_connected_count = count_connected_module_edges_for_module(graph, node_a, wlan_modules)
    node_b_connected_count = count_connected_module_edges_for_module(graph, node_b, wlan_modules)
    sum_connected_count = node_a_connected_count + node_b_connected_count

    # We can take either the snr of node_a -> node_b or node_b, since we receive a undirected
    # basic connectivity graph => does not matter which direction, since the averaging has been done before
    average_snr = basic_con_graph.edge[node_a][node_b]["snr"]
    expected_bandwidth = translate_snr_to_bw(average_snr)

    interfering_modules = get_used_interference_modules_for_link(graph, basic_con_graph, node_a, node_b, wlan_modules)
    nr_interfering_modules = len(interfering_modules)

    # Divide expected bandwidth by the number of interfering channels, since we share the channel with those links
    if nr_interfering_modules != 0:
        shared_expected_bandwidth = expected_bandwidth / nr_interfering_modules
    else:
        shared_expected_bandwidth = expected_bandwidth

    if sum_connected_count != 0:
        score = shared_expected_bandwidth / sum_connected_count
    else:
        score = shared_expected_bandwidth
    return score


# Calculates for a given graph the survival graph (2-connected graph) and returns it
# mst_mode is the variable for MST creation mode, it can have the following values:
# node = We expect a complete node to fail at a time (network still works, even if a whole node breaks)
# module_module_edge = We expect only a single edge from a module to antoher module to fail at a time (network still works, even if an edge breaks, less connetions though than "node")
# node_module_edge = We expect only a single edge from a node to a module to fail at a time (network still works, even if an edge breaks, less connetions though than "node")
# single = only calculate ordinary MST (no redundancy, one node or edge breakds => connectivity is gone, least number of connections)
# equal_module = equally distribute the
def calculate_mst(graphname, wlan_modules, lan_nodes, mst_mode="equal_module"):
    logger.info("Calculating MST on Graph...")
    mst = nx.minimum_spanning_tree(graphname).copy()
    if mst_mode == "node":
        for node in lan_nodes:

            # Create new temp Graph to work with
            work_graph = graphname.copy()

            # Remove the node
            work_graph.remove_node(node)

            # Now calculate the mst on this new graph
            mst_work_graph = nx.minimum_spanning_tree(work_graph)

            # Add the now necessary edges to the resulting graph
            for a, b in mst_work_graph.edges():
                if not mst.has_edge(a, b):
                    # Add module-edge to mst
                    mst.add_edge(a, b)
                    for key in graphname.edge[a][b].keys():
                        mst.edge[a][b][key] = graphname.edge[a][b][key]
    elif mst_mode == "module_module_edge":
        # We have to note here, that we still could get less edges in the end
        # (we get here more edges than necessary for a 2-connected graph), but you really may not only want to use
        # only the edges, which you get by constructing a 2-connected graph, since this would also depend on bad quality-
        # links (Like you could get from A to C over B with : A->(0.1)->B->(0.1)->C, but you would rather take an edge like
        # A->(0.5)->C instead
        for edge in graphname.edges():

            # Only consider cases, where real-connections are cut
            # Cutting module-node connections does not make sense, since a module can't live on its own ;-)
            if edge[0] in lan_nodes or edge[1] in lan_nodes:
                continue

            # Create new temp Graph to work with
            work_graph = graphname.copy()

            # Remove the edge
            work_graph.remove_edge(edge[0], edge[1])

            # Now calculate the mst on the workgraph
            mst_work_graph = nx.minimum_spanning_tree(work_graph)

            # Add all of the edges from the MST_Work_Graph of this round to the final Graph
            for a, b in mst_work_graph.edges():
                if not mst.has_edge(a, b):
                    # Add module-edge to mst
                    mst.add_edge(a, b)
                    for key in graphname.edge[a][b].keys():
                        mst.edge[a][b][key] = graphname.edge[a][b][key]
    elif mst_mode == "node_module_edge":
        # We have to note here, that we still could get less edges in the end
        # (we get here more edges than necessary for a 2-connected graph), but you really may not only want to use
        # only the edges, which you get by constructing a 2-connected graph, since this would also depend on bad quality-
        # links (Like you could get from A to C over B with : A->(0.1)->B->(0.1)->C, but you would rather take an edge like
        # A->(0.5)->C instead
        for edge in graphname.edges():

            # Only consider cases, where real-connections are cut
            # Cutting module-node connections does not make sense, since a module can't live on its own ;-)
            if not (edge[0] in lan_nodes or edge[1] in lan_nodes):
                continue

            # Create new temp Graph to work with
            work_graph = graphname.copy()

            # Remove the edge
            work_graph.remove_edge(edge[0], edge[1])

            # Now calculate the mst on the workgraph
            mst_work_graph = nx.minimum_spanning_tree(work_graph)

            # Add all of the edges from the MST_Work_Graph of this round to the final Graph
            for a, b in mst_work_graph.edges():
                if not mst.has_edge(a, b):
                    # Add module-edge to mst
                    mst.add_edge(a, b)
                    for key in graphname.edge[a][b].keys():
                        mst.edge[a][b][key] = graphname.edge[a][b][key]
    elif mst_mode == "single":
        #Just fall through, since we already calculated the plain mst
        pass
    elif mst_mode == "none":
        mst = graphname
    elif mst_mode == "equal_module":
        mst = nx.Graph()
        visited_nodes = set()
        # Edge list contains quadruple with (source,target,edgeweigth,real-connections)
        edge_list = collections_enhanced.Counter()
        all_nodes = set()

        # Copy nodes from graphname to mst and fill the set: all_nodes
        for node in graphname.nodes():
            all_nodes.add(node)
            mst.add_node(node)
            for key in graphname.node[node].keys():
                mst.node[node][key] = graphname.node[node][key]

        # Start with root node
        # Add the edges originating from root node to new nodes to edge_list
        visited_nodes.add(root_node)
        for neighbor in graphname.neighbors(root_node):
            edge_list[(root_node, neighbor, graphname.edge[root_node][neighbor]["real-connection"])] \
                = calculate_score_for_edge(mst, graphname, root_node, neighbor, wlan_modules)

        # Main loop
        # Always recalc the scores of corresponding edges if adding new ones
        while True:
            # Then remove all edges which do not see new nodes (IE keep only productive edges)
            removed_edge = True
            while removed_edge:
                removed_edge = False
                for (a, b, real_connection) in edge_list:
                    if a in visited_nodes and b in visited_nodes:
                        removed_edge = True
                        del edge_list[(a, b, real_connection)]
                        break

            # If the edge_list is empty after the removing of unproductive edges, check if we visited all nodes
            if len(edge_list) == 0:
                if len(visited_nodes) != graphname.number_of_nodes():
                    logger.error("Could not connect all nodes.")
                    logger.error("Graph / APs are separated, maybe wait some time until they can at least theoretically span a network.")
                    exit(1)
                else:
                    break

            # Now find the best new edge and add it to the mst
            # Therefore just take the edge with the highest score
            (bestedge_node_a, bestedge_node_b, real_connection), highest_score = edge_list.most_common(1)[0]

            # Mark node as visited
            visited_nodes.add(bestedge_node_b)

            # Add the edge to mst
            mst.add_edge(bestedge_node_a, bestedge_node_b)
            for key in graphname.edge[bestedge_node_a][bestedge_node_b].keys():
                mst.edge[bestedge_node_a][bestedge_node_b][key] = graphname.edge[bestedge_node_a][bestedge_node_b][key]

            # Add its edges to the edge_list
            for neighbor in graphname.neighbors(bestedge_node_b):
                if neighbor not in visited_nodes:
                    real_connection_neigh = graphname.edge[bestedge_node_b][neighbor]["real-connection"]
                    edge_list[(bestedge_node_b, neighbor, real_connection_neigh)] \
                        = calculate_score_for_edge(mst, graphname, bestedge_node_b, neighbor, wlan_modules)

            # Remove the edge from edgelist, to speed up things and since we dont need it any longer (since we are using it)
            del edge_list[(bestedge_node_a, bestedge_node_b, real_connection)]

            # Update the scores, because scores might change, since we added new edge => score of others could get decreased
            # Todo: this could be made more efficient, by just updating those edges, where sth has changed instead of all, find out if this is a performance killer first
            for (a, b, real_connection) in edge_list:
                if real_connection:
                    edge_list[(a, b, real_connection)] = calculate_score_for_edge(mst, graphname, a, b, wlan_modules)

    else:
        logger.error("Unknown MST mode: Please Chose one out of 'node', 'node_module_edge', 'module_module_edge, 'single', 'none', 'equal_module'")
        exit(1)
    return mst


# Calculate the backup links for a given mst graph and basic connectivity graph
def calculate_backup_links(mst, basic_con_graph, wlan_modules):
    logger.info("Calculating Backup links for Graph...")
    mst_edges = copy.copy(mst.edges())
    for edge in mst_edges:
        # Simulate each edge failing
        if edge[0] in wlan_modules and edge[1] in wlan_modules:
            mst.remove_edge(edge[0], edge[1])
            # Check if we still have a path to get to edge[1] even if this edge has failed
            # If we have still a path to edge[1], then we are done
            # else select second highest rated edge to get there
            if not nx.has_path(mst, edge[0], edge[1]):
                edge_list = collections_enhanced.Counter()

                # Edges of node_A
                for neighbor in basic_con_graph.neighbors(edge[0]):
                    # Consider only edges, which are productive (with which we get a path to the other node)
                    if nx.has_path(mst, neighbor, edge[1]):
                        # Consider only those edges, which are not already used in the mst-graph and are no node-module connections
                        if (edge[0], neighbor) not in mst_edges and neighbor in wlan_modules and neighbor is not edge[1]:
                            edge_list[(edge[0], neighbor)] = calculate_score_for_edge(mst, basic_con_graph, edge[0], neighbor, wlan_modules)
                # Edges of node_B
                for neighbor in basic_con_graph.neighbors(edge[1]):
                    # Consider only edges, which are productive (with which we get a route to the other node)
                    if nx.has_path(mst, neighbor, edge[0]):
                        # Consider only those edges, which are not already used in the mst-graph and are no node-module connections
                        if (edge[1], neighbor) not in mst_edges and neighbor in wlan_modules and neighbor is not edge[0]:
                            edge_list[(edge[1], neighbor)] = calculate_score_for_edge(mst, basic_con_graph, edge[1], neighbor, wlan_modules)

                # Select the highest rated edge
                if edge_list:
                    (bestedge_node_a, bestedge_node_b), highest_score = edge_list.most_common(1)[0]
                    mst.add_edge(bestedge_node_a, bestedge_node_b)
                    mst.edge[bestedge_node_a][bestedge_node_b]["backup-link"] = True
                    for key in basic_con_graph.edge[bestedge_node_a][bestedge_node_b].keys():
                        mst.edge[bestedge_node_a][bestedge_node_b][key] = basic_con_graph.edge[bestedge_node_a][bestedge_node_b][key]

            # Add the removed edge again
            mst.add_edge(edge[0], edge[1])
            mst.edge[edge[0]][edge[1]]["backup-link"] = False
            for key in basic_con_graph.edge[edge[0]][edge[1]].keys():
                mst.edge[edge[0]][edge[1]][key] = basic_con_graph.edge[edge[0]][edge[1]][key]

    return mst


# Returns list of channels which are used the least over all edges in the graph and are in the allowed_channels list
def get_least_used_channels_in_overall(allowed_channels, overall_channel_counter):
    return list(get_least_used_elements_for_counter_dict(overall_channel_counter, allowed_channels))


# Todo: Foreign table/ Seen-channels, but christoph has to implement this table first (probably wont happen anytime soon)
# Get the channel for an edge(pair of modules), which has the least interference from other (not our) devices/wlans
# That means take a look at seen channels for the two modules and for a given set to chose from(channel_set), find the channel, which
# is used the least in both wireless regions
# Returns a list
#def get_least_actually_seen_channels_for_set(graphname, channel_set, module_a, module_b):
#    seen_channels_for_node_a = graphname.node[module_a]["seen_channels"]
#    seen_channels_for_node_b = graphname.node[module_b]["seen_channels"]
#    seen_channels_for_both_nodes = seen_channels_for_node_a + seen_channels_for_node_b
#    return list(get_least_used_elements_for_counter_dict(seen_channels_for_both_nodes, channel_set))


# Returns a dict of the form: channel : nr_of_occurrences for two modules
def get_actually_seen_channels_for_modules(graphname, module_a, module_b):
    seen_channels_for_node_a = graphname.node[module_a]["seen_channels"]
    seen_channels_for_node_b = graphname.node[module_b]["seen_channels"]
    seen_channels_for_both_nodes = seen_channels_for_node_a + seen_channels_for_node_b
    return seen_channels_for_both_nodes


# channelset = list of channels we can chose from
# calculates the optimal channel from this set
# Returns the channel to use (not a list of channels)
def get_best_channel_in(graphname, overall_channel_counter, channelset, module_a, module_b):
    # Speed up things if there is only one channel to chose from
    if len(channelset) == 1:
        return channelset[0]
    else:
        used_channels_for_both_nodes = get_used_channels_for_nodes(graphname, module_a, module_b, channelset)
        seen_channels_for_both_nodes = get_actually_seen_channels_for_modules(graphname, module_a, module_b)

        # Take the channels from used_channels_for_both which are used the least,
        # if there is a tie, then take the one, which has a lower value in seen_channels_for_both
        least_used_channels = list(get_least_used_elements_for_counter_dict(used_channels_for_both_nodes, channelset))
        if len(least_used_channels) == 1:
            return least_used_channels[0]
        else:
            least_seen_channels = list(get_least_used_elements_for_counter_dict(seen_channels_for_both_nodes, least_used_channels))
            if len(least_seen_channels) == 1:
                return least_seen_channels[0]
            else:
                least_used_channels_overall = get_least_used_channels_in_overall(least_seen_channels, overall_channel_counter)
                if len(least_used_channels_overall) == 1:
                    return least_used_channels_overall[0]
                else:
                    # Pick one at random
                    return random.choice(least_used_channels_overall)


# Sets the channel for an edge
def set_edge_channel(graphname, overall_channel_counter, edgechannel, module_a, module_b):
    # Check if the edge had a channel before,
    # so it would be a reassigning and we have to adapt the counters correspondingly
    former_channel = graphname.edge[module_a][module_b]["channel"]
    node_of_module_a = get_node_for_module(graphname, module_a)
    node_of_module_b = get_node_for_module(graphname, module_b)
    if former_channel is not None:
        # It had a channel before => we do a reassignment
        # Decrease for overpainting the old channel
        graphname.node[node_of_module_a]["used-channels"][former_channel] -= 1
        graphname.node[node_of_module_b]["used-channels"][former_channel] -= 1

        # Decrease also the overall channelcounters for the former channel
        overall_channel_counter[former_channel] -= 1

    # Assign channels to the edge and the modules
    graphname.edge[module_a][module_b]["channel"] = edgechannel
    graphname.node[module_a]["channel"] = edgechannel
    graphname.node[module_b]["channel"] = edgechannel

    # Increase the channel counter at the respective nodes for these modules
    graphname.node[node_of_module_a]["used-channels"][edgechannel] += 1
    graphname.node[node_of_module_b]["used-channels"][edgechannel] += 1

    # Increase also the overall channelcounters
    overall_channel_counter[edgechannel] += 1


# Returns set of channels for all edges of a node
def get_channelset_used_for_node(graphname, node):
    return set(graphname.node[node]["used-channels"])


# Returns True, if this module already uses a channel
# Since a module is per definition only one, this just tells us whether this module already uses a channel or not
def module_has_channel(graphname, module):
    if graphname.node[module]["channel"] is None:
        return False
    else:
        return True


# Check if edge has a channel
def edge_has_channel(graphname, node_a, node_b):
    if graphname.edge[node_a][node_b]["channel"] is None:
        return False
    else:
        return True


# Returns the number of connected occurences for a certain channel at a module
# It counts all the connected edges of the same channel (over multiple modules)
def get_connected_channel_count_for_module(graphname, module, channel, wlan_modules):
    occurences = 0
    edges_done = set()
    modules_todo = list()

    # Add initial node to be able to start from there
    modules_todo.append(module)

    for mod in modules_todo:
        neighbors = graphname.neighbors(mod)
        for neighbor in neighbors:
            if neighbor in wlan_modules:
                if graphname.edge[mod][neighbor]["channel"] == channel and (mod, neighbor) not in edges_done:
                    # Increase overall channel counter
                    occurences += 1

                    # Add edge to done-list
                    edges_done.add((mod, neighbor))
                    edges_done.add((neighbor, mod))

                    # Add module to go if not already visited
                    if neighbor not in modules_todo:
                        modules_todo.append(neighbor)
    return occurences


# Reassign channels for a given module all connected edges of the same channel (even over multiple modules)
def reassign_channel_to_edges_for_module(graphname, overall_channel_counter, module, oldchannel, newchannel, wlan_modules):
    # If channels are the same, something must be wrong
    if oldchannel == newchannel:
        # Nothing to do then
        logger.error("Error: tried to overpaint " + str(oldchannel) + " with " + str(newchannel) + ". This does not make sense and should not happen.")
        logger.error("This is an error in the Channel assignment algorithm.")
        exit(1)

    # Add initial node to be able to start from there
    modules_todo = list()
    modules_todo.append(module)

    for mod in modules_todo:
        neighbors = graphname.neighbors(mod)
        for neighbor in neighbors:
            if neighbor in wlan_modules:
                edge = graphname.edge[mod][neighbor]
                if edge and "channel" in edge.keys() and edge["channel"] == oldchannel:
                    # Reassign channel to that edge
                    set_edge_channel(graphname, overall_channel_counter, newchannel, mod, neighbor)

                    # Add the destination node to nodes_todo
                    modules_todo.append(neighbor)


# Find the best channel for an edge
def assign_channel_to_edge(graphname, overall_channel_counter, module_a, module_b, wlan_modules):
    if not module_has_channel(graphname, module_a):
        if not module_has_channel(graphname, module_b):
            set_edge_channel(graphname, overall_channel_counter, get_best_channel_in(graphname, overall_channel_counter, Assignable_Channels, module_a, module_b), module_a, module_b)
        else:
            # We have to take the channel of module_b
            set_edge_channel(graphname, overall_channel_counter, graphname.node[module_b]["channel"], module_a, module_b)
    else:
        # We have to take the channel of module_a, lets see if this is a problem.
        # Therefore check if b has a channel assigned, and if it has, check if its the same channel a has.
        channel_of_module_a = graphname.node[module_a]["channel"]
        if not module_has_channel(graphname, module_b):
            set_edge_channel(graphname, overall_channel_counter, channel_of_module_a, module_a, module_b)
        else:
            # Now we have a problem if the channels are not by accident the same
            channel_of_module_b = graphname.node[module_b]["channel"]
            if channel_of_module_a == channel_of_module_b:
                # We are lucky, they are the same
                set_edge_channel(graphname, overall_channel_counter, channel_of_module_a, module_a, module_b)
            else:
                # Channels are not the same, This means Module A and B have different channels assigned, but we have to establish a link between them
                # This is the most costly case (tricky case)
                # The solution here is based on a paper called hycint-mcr2 and works like described in the following:
                # Take the channel from module_a or module_b which occurs less at both sides (connected!) and repaint it with the other one
                # Then replace the least connected channels at A and B with the newchannel and also use it for the edge between A and B

                # Get the channelcounts for both nodes and combine them
                nr_of_occurrences_for_channel_at_module_a = get_connected_channel_count_for_module(graphname, module_a, channel_of_module_a, wlan_modules)
                nr_of_occurrences_for_channel_at_module_b = get_connected_channel_count_for_module(graphname, module_b, channel_of_module_b, wlan_modules)

                if nr_of_occurrences_for_channel_at_module_a > nr_of_occurrences_for_channel_at_module_b:
                    channel_with_more_occurrences = channel_of_module_a
                    channel_with_less_occurrences = channel_of_module_b
                else:
                    channel_with_more_occurrences = channel_of_module_b
                    channel_with_less_occurrences = channel_of_module_a

                # Reassign channels to all the other connected edges for both modules (overpaint channel_with_less_occurrences with channel_with_more_occurrences)
                reassign_channel_to_edges_for_module(graphname, overall_channel_counter, module_a, channel_with_less_occurrences, channel_with_more_occurrences, wlan_modules)
                reassign_channel_to_edges_for_module(graphname, overall_channel_counter, module_b, channel_with_less_occurrences, channel_with_more_occurrences, wlan_modules)

                # Assign a channel to the edge from node_a to node_b with this the best channel available at node a
                set_edge_channel(graphname, overall_channel_counter, channel_with_more_occurrences, module_a, module_b)


# Check if the CAA is valid
def graph_is_valid(graphname, lan_nodes, wlan_modules):
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


# Write the given graph to a json file
def write_json(graph, lan_nodes, wlan_modules, filename="graph.json"):
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


# Translate a wlan_ac into a interface_nr
def translate_wlan_mac_to_interface_nr(module_wlan_mac):
    for index in active_radios:
        if active_radios[index]["wlan_mac"] == module_wlan_mac:
            return active_radios[index]["ifc"]
    logger.error("Could not translate interface_wlan_mac to interface_nr. You are asking for a wrong module")
    exit(1)


# Returns list of lists with tabledata from wlc for a given tablename, else empty table
def get_table_data(tablename, hostname, username, password):
    connection = testcore.control.ssh.SSH(host=hostname, username=username, password=password)
    return connection.runquery_table(tablename)


# Get the data from the wlc, returns a networkx basic graph
def get_basic_graph_from_wlc(hostname, username, password):
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


# Caclulate a CAA for a given graph
def calculate_caa_for_graph(graphname, wlan_modules, overall_channel_counter):
    logger.info("Calculating CAA for Graph...")
    edges_done = set()  # List of edges which have been visited (empty at beginning)
    nodelist = list()  # This is the list of nodes over which we iterate
    nodelist.append(root_node)  # Initially put only the gatewaynode in the nodelist (Could also be a different one)

    # Iterate over all nodes in BFS-style
    for node in nodelist:
        neighbors = graphname.neighbors(node)
        for neighbor in neighbors:
            if (node, neighbor) not in edges_done and (neighbor, node) not in edges_done:
                # We just want to assign a channel to the module-edges and not
                # the edges between node and module, since they dont need a channels assigned
                if node in wlan_modules and neighbor in wlan_modules and not edge_has_channel(graphname, node, neighbor):
                    assign_channel_to_edge(graphname, overall_channel_counter, node, neighbor, wlan_modules)
                if not neighbor in nodelist:
                    nodelist.append(neighbor)
                # Mark edge as done
                edges_done.add((node, neighbor))
    return graphname


# Write the connections back to the WLC
def write_graph_to_wlc(wlan_modules, address, username, password, pmst_graph_with_channels_assigned):
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
        lcos_script.append('add /Setup/WLAN-Management/AP-Configuration/AutoWDS-Topology/AUTOWDS_PROFILE {0} {1} {2} {3} {4} "12345678" 1 * * * 11'.format(prio_counter, module_a_device, module_a_interface_name, module_b_device, module_b_interface_name))
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
     


# Check if wlc is up
def wlc_is_up(hostname):
    if not os.system("ping -c 1 " + hostname + " > /dev/null") == 0:
        return False
    else:
        return True


# Configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
if len(sys.argv) < 4:
    print("Usage: python CAA.py <wlc-address> <wlc-username> <wlc_password> <usable-channels>")
    exit(1)
wlc_address = sys.argv[1]
wlc_username = sys.argv[2]
wlc_password = sys.argv[3]
Assignable_Channels = sys.argv[4].split(",")  # List of all channels which can be used for assignment

if not wlc_is_up(wlc_address):
    logger.error("WLC:" + str(wlc_address) + " seems to be offline.")
    exit(1)

edge_max_score = 1000  # The score for node-module connections, this has to be higher than any possible module-module connection
channel_counter = collections_enhanced.Counter()  # This counts how often each channel has been used overall, initially fill with 0
for channel_entry in Assignable_Channels:
    channel_counter[channel_entry] = 0

# Getting Data from WLC per SNMP
basic_connectivity_graph_directed, modules, devices = get_basic_graph_from_wlc(wlc_address, wlc_username, wlc_password)

# Set the root node TODO: automate this further later
root_node = random.choice(list(devices))

# Convert to undirected graph
basic_connectivity_graph = convert_to_undirected_graph(basic_connectivity_graph_directed)

# First phase: Calculate the Minimal Spanning Tree from the basic connectivity graph
mst_graph = calculate_mst(basic_connectivity_graph, modules, devices, "equal_module")

# Assign channels to the mst
mst_graph_with_channels_assigned = calculate_caa_for_graph(mst_graph, modules, channel_counter)

# Finally check the graph for validity
if not graph_is_valid(mst_graph_with_channels_assigned, devices, modules):
    exit(1)

# Calculate the backup links for a given, CAAed mst
# Todo: create copy for mst_graph_with_channels_assigned because this variable is overwritten/modified
#robust_graph = calculate_backup_links(mst_graph_with_channels_assigned, basic_connectivity_graph, modules)
#show_graph(robust_graph, modules, devices, filename_svg='caa_robust.svg', filename_json="graph_robust.json")

# In the wlc set the links and channels
write_graph_to_wlc(modules, wlc_address, wlc_username, wlc_password, mst_graph_with_channels_assigned)
