#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose This script colors a networkx graph (Lancom AutoWDS Channel assignment algorithm)

import networkx as nx
import collections_enhanced
import random
import pydot
import netsnmp


# counterlist = dictionary with colors and their number of occurences
# allowed_colors = list to pick colors from (because we might not be allowed to use all in a certain situation)
# Returns a list with elements that are in the allowed_colors list and are least commonly used
def get_least_used_elements_for_counter_dict(counterlist, allowed_colors):
    # Create new restricted counterlist with only those elements in it, which are also in allowed_colors
    restricted_counterlist = collections_enhanced.Counter()
    for element in counterlist.keys():
        if element in allowed_colors:
            restricted_counterlist[element] = counterlist[element]

    # Get all the least common elements
    return restricted_counterlist.least_common_all()


# Get the parent node for a wlan modules
def get_node_for_module(graphname, module):
    return graphname.node[module]["module-of"]


# Returns counter with entries (like color : nr of occurences of this color in neighborhood of node_a and node_b)
# for two nodes/modules and a list of allowed colors
def get_used_colors_for_nodes(graphname, modula_a, module_b, allowed_colors):
    node_a = get_node_for_module(graphname, modula_a)
    node_b = get_node_for_module(graphname, module_b)
    common_color_counter = graphname.node[node_a]["used-colors"] + graphname.node[node_b]["used-colors"]

    #safetly check
    if not common_color_counter:
        print("Error here")
        common_color_counter = graphname.node[node_a]["used-colors"] + graphname.node[node_b]["used-colors"]
    #todo: see if the allowed colors if is still necessary later
    returncounter = collections_enhanced.Counter()
    for key in common_color_counter.keys():
        if key in allowed_colors:
            returncounter[key] = common_color_counter[key]

    return returncounter


# Checks if the module_a of an edge is already used for a connection
# Go through all neighbors, and if there is one neighbor, which is not reached over a real-connection, then this module is used
def module_is_used(mst_graphname, module):
    for neighbor in mst_graphname.neighbors(module):
        module_con = mst_graphname.edge[module][neighbor]["real-connection"]
        if module_con is True:
            return True
    return False


# Returns the number of non module connections for a module
def nr_of_non_module_connections(graphname, module):
    connection_counter = 0
    for neighbor in graphname.neighbors(module):
        if not graphname.edge[module][neighbor]["real-connection"]:
            connection_counter += 1
    return connection_counter


# Converts a given directed graph to a undirected graph
# At the moment we just take the average of both edges
# Todo: later improve this a bit
# Returns the undirected graph
def convert_to_undirected_graph(directed_graph):
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
                undirected_graph[a][b]["weight"] = (directed_graph.edge[a][b]["weight"] + directed_graph.edge[b][a]["weight"]) / 2.0
                undirected_graph[a][b]["real-connection"] = True
                undirected_graph[a][b]["color"] = None
            else:
                # Ignore this edge
                print("Warning: Onesided link deteced: " + a + "-" + b + " -> Can't use link for undirected graph ")
    return undirected_graph


# Calculates for a given graph the survival graph (2-connected graph) and returns it
def calculate_survival_graph(graphname, wlan_modules, lan_nodes):
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
    elif mst_mode == "edge":
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
    elif mst_mode == "single":
        #Just fall through, since we already calculated the plain mst
        pass
    elif mst_mode == "none":
        mst = graphname
    elif mst_mode == "equal_module":
        mst = nx.Graph()
        visited_nodes = set()
        # Edge list contains quadruple with (source,target,edgeweigth,real-connections)
        edge_list = list()
        all_nodes = set()

        # Copy nodes from graphname to mst and fill the set: all_nodes
        for node in graphname.nodes():
            all_nodes.add(node)
            mst.add_node(node)
            for key in graphname.node[node].keys():
                mst.node[node][key] = graphname.node[node][key]

        # Add the root node and initialize edge_list
        visited_nodes.add(root_node)
        for neighbor in graphname.neighbors(root_node):
            edge_weight = graphname.edge[root_node][neighbor]["weight"]
            module_con = graphname.edge[root_node][neighbor]["real-connection"]
            edge_list.append((root_node, neighbor, edge_weight, module_con))

        while True:
            # Debugging
            show_graph(mst, wlan_modules, lan_nodes)

            # Pick all edges from edge_list, which are real-connections
            for index, (a, b, weight, module_con) in enumerate(edge_list):
                if module_con:
                    # Mark node as visited
                    visited_nodes.add(b)

                    # Add module-edge to mst
                    mst.add_edge(a, b)
                    for key in graphname.edge[a][b].keys():
                        mst.edge[a][b][key] = graphname.edge[a][b][key]

                    # Add only new edges to edge_list
                    for neighbor in graphname.neighbors(b):
                        if neighbor not in visited_nodes:
                            edge_weight = graphname.edge[b][neighbor]["weight"]
                            module_con = graphname.edge[b][neighbor]["real-connection"]
                            edge_list.append((b, neighbor, edge_weight, module_con))

            # Debugging
            show_graph(mst, wlan_modules, lan_nodes)

            # Pick only those Modules, which see new nodes
            see_new_nodes = list()
            for (a, b, weight, module_con) in edge_list:
                if b not in visited_nodes:
                    see_new_nodes.append((a, b, weight, module_con))
            if see_new_nodes:
                # Pick the modules, which are used least (those that have 0 connections if possible)
                module_usage_counter = collections_enhanced.Counter()
                for (a, b, weight, module_con) in see_new_nodes:
                    module_usage_counter[a] = nr_of_non_module_connections(mst, a)

                # Get a list of the least used modules
                least_used_modules = set(module_usage_counter.least_common_all())

                # From the list of least used modules, take all edges
                least_used_modules_counter = collections_enhanced.Counter()
                for (a, b, weight, module_con) in see_new_nodes:
                    if a in least_used_modules:
                        least_used_modules_counter[(a, b)] = weight

                # Pick the edge with the least costs
                (least_cost_module_a, least_cost_module_b), least_cost_weight = least_used_modules_counter.least_common(1)[0]

                # Mark node as visited
                visited_nodes.add(least_cost_module_b)

                # Add the edge to mst
                mst.add_edge(least_cost_module_a, least_cost_module_b)
                for key in graphname.edge[least_cost_module_a][least_cost_module_b].keys():
                    mst.edge[least_cost_module_a][least_cost_module_b][key] = graphname.edge[least_cost_module_a][least_cost_module_b][key]

                # Add its edges to the edge_list
                for neighbor in graphname.neighbors(least_cost_module_b):
                    if neighbor not in visited_nodes:
                        edge_weight = graphname.edge[least_cost_module_b][neighbor]["weight"]
                        module_con = graphname.edge[least_cost_module_b][neighbor]["real-connection"]
                        edge_list.append((least_cost_module_b, neighbor, edge_weight, module_con))
            else:
                if len(visited_nodes) != graphname.number_of_nodes():
                    print("Error: Could not connect all nodes")
                    exit(1)
                else:
                    break
    else:
        print("Unknown Mode: Please Chose one out of 'node', 'edge' or 'single'")
        exit(1)
    return mst


# Returns list of colors which are used the least over all edges in the graph and are in the allowed_colors list
def get_least_used_colors_in_overall(allowed_colors, overall_color_counter):
    return list(get_least_used_elements_for_counter_dict(overall_color_counter, allowed_colors))


# Get the color/channel for an edge(pair of modules), which has the least interference from other (not our) devices/wlans
# That means take a look at seen colors for the two modules and for a given set to chose from(color_set), find the color, which
# is used the least in both wireless regions
# Returns a list
def get_least_actually_seen_colors_for_set(graphname, color_set, module_a, module_b):
    seen_channels_for_node_a = graphname.node[module_a]["seen_channels"]
    seen_channels_for_node_b = graphname.node[module_b]["seen_channels"]
    seen_channels_for_both_nodes = seen_channels_for_node_a + seen_channels_for_node_b
    return list(get_least_used_elements_for_counter_dict(seen_channels_for_both_nodes, color_set))


# Returns a dict of the form: color : nr_of_occurrences for two modules
def get_actually_seen_colors_for_modules(graphname, module_a, module_b):
    seen_channels_for_node_a = graphname.node[module_a]["seen_channels"]
    seen_channels_for_node_b = graphname.node[module_b]["seen_channels"]
    seen_channels_for_both_nodes = seen_channels_for_node_a + seen_channels_for_node_b
    return seen_channels_for_both_nodes


# colorset = list of colors we can chose from
# caluclates the optimal color from this set
# Returns the color to use (not a list of colors)
def get_best_color_in(graphname, overall_color_counter, colorset, module_a, module_b):
    # Speed up things if there is only one color to chose from
    if len(colorset) == 1:
        return colorset[0]
    else:
        used_colors_for_both = get_used_colors_for_nodes(graphname, module_a, module_b, colorset)
        seen_colors_for_both = get_actually_seen_colors_for_modules(graphname, module_a, module_b)

        # Take the colors from used_colors_for_both which are used the least,
        # if there is a tie, then take the one, which has a lower value in seen_colors_for_both
        least_used_colors = list(get_least_used_elements_for_counter_dict(used_colors_for_both, colorset))
        if len(least_used_colors) == 1:
            return least_used_colors[0]
        else:
            least_seen_colors = list(get_least_used_elements_for_counter_dict(seen_colors_for_both, least_used_colors))
            if len(least_seen_colors) == 1:
                return least_seen_colors[0]
            else:
                least_used_colors_overall = get_least_used_colors_in_overall(least_seen_colors, overall_color_counter)
                if len(least_used_colors_overall) == 1:
                    return least_used_colors_overall[0]
                else:
                    # Pick one at random
                    return random.choice(least_used_colors_overall)


# Sets the color for an edge
def set_edge_color(graphname, overall_color_counter, edgecolor, module_a, module_b):
    # Check if the edge had a color before,
    # so it would be recoloring and we have to adapt the counters correspondingly
    former_color = graphname.edge[module_a][module_b]["color"]
    node_of_module_a = get_node_for_module(graphname, module_a)
    node_of_module_b = get_node_for_module(graphname, module_b)
    if former_color is not None:
        # It had a color before => we do a recoloring
        # Decrease for overpainting the old color
        graphname.node[node_of_module_a]["used-colors"][former_color] -= 1
        graphname.node[node_of_module_b]["used-colors"][former_color] -= 1

        # Decrease also the overall colorcounters for the former color
        overall_color_counter[former_color] -= 1

    # Color the edge and the modules
    graphname.edge[module_a][module_b]["color"] = edgecolor
    graphname.node[module_a]["color"] = edgecolor
    graphname.node[module_b]["color"] = edgecolor

    # Increase the color counter at the respective nodes for these modules
    graphname.node[node_of_module_a]["used-colors"][edgecolor] += 1
    graphname.node[node_of_module_b]["used-colors"][edgecolor] += 1

    # Increase also the overall colorcounters
    overall_color_counter[edgecolor] += 1


# Returns the number of modules for a node
def get_modules_count_for_node(graphname, node):
    imodules = graphname.node[node]["modules"]
    if imodules:
        return imodules
    else:
        print "node " + str(node) + " has no modules field. This is an error and should not happen"
        exit(1)


# Returns set of colors for all edges of a node, colored so far
def get_colorset_used_for_node(graphname, node):
    return set(graphname.node[node]["used-colors"])


# Returns set of colors for the node this module belongs to
# This makes sense, since a module can always just have maximal 1 attached color/channel
def get_colorset_used_for_module(graphname, module):
    node = get_node_for_module(graphname, module)
    return set(graphname.node[node]["used-colors"])


# Returns the number of the (distinct) colors this node already uses
def get_number_of_colors_used_for_node(graphname, node):
    colors_used = get_colorset_used_for_node(graphname, node)
    return len(colors_used)


# Returns the number of modules for a node that are still free to use
# modules=number of wlan modules (probably 2 or 3 atm)
def modules_free_count_for_node(graphname, node):
    #free modules = number of modules of node minus number of channels already used on that node
    return get_modules_count_for_node(graphname, node) - get_number_of_colors_used_for_node(graphname, node)


# Returns True, if this module already uses a color
# Since a module is per definition only one, this just tells us whether this module already uses a color or not
def module_is_already_colored(graphname, module):
    if graphname.node[module]["color"] is None:
        return False
    else:
        return True


# Returns list of colors which either node a or node b uses
def get_colors_used_for_nodes(graphname, node_a, node_b):
    colors_used_by_node_a = get_colorset_used_for_node(graphname, node_a)
    colors_used_by_node_b = get_colorset_used_for_node(graphname, node_b)
    colors_used_by_either_node_a_or_node_b = set(colors_used_by_node_a.union(colors_used_by_node_b))
    return colors_used_by_either_node_a_or_node_b


# Returns a set of colors which are not used by the node
def get_colors_not_used_for_node(graphname, node):
    colors_used_by_node = get_colorset_used_for_node(graphname, node)
    colors_not_used = [i for i in Assignable_Colors if i not in colors_used_by_node]
    return set(colors_not_used)


# Check if edge has a color
def edge_has_color(graphname, node_a, node_b):
    if graphname.edge[node_a][node_b]["color"] is not None:
        return True
    else:
        return False


# Returns the number of connected occurences for a certain color at a module
# It counts all the connected edges of the same color (over multiple modules)
def get_connected_color_count_for_module(graphname, module, color, wlan_modules):
    occurences = 0
    edges_done = set()
    modules_todo = list()

    # Add initial node to be able to start from there
    modules_todo.append(module)

    for mod in modules_todo:
        neighbors = graphname.neighbors(mod)
        for neighbor in neighbors:
            if neighbor in wlan_modules:
                if graphname.edge[mod][neighbor]["color"] == color and (mod, neighbor) not in edges_done:
                    # Increase overall color counter
                    occurences += 1

                    # Add edge to done-list
                    edges_done.add((mod, neighbor))
                    edges_done.add((neighbor, mod))

                    # Add module to go if not already visited
                    if neighbor not in modules_todo:
                        modules_todo.append(neighbor)
    return occurences


# Returns a dictionary with number of connected colorusage for the module provided
def get_color_count_for_module(graphname, module, wlan_modules):
    color_counter = collections_enhanced.Counter()
    colors_of_node = get_colorset_used_for_node(graphname, module)
    for color in colors_of_node:
        color_counter[color] = 0

    for color in colors_of_node:
        edges_done = set()
        modules_todo = list()

        # Add initial node to be able to start from there
        modules_todo.append(module)

        for mod in modules_todo:
            neighbors = graphname.neighbors(mod)
            for neighbor in neighbors:
                if neighbor in wlan_modules:
                    edge = graphname.edge[mod][neighbor]
                    if edge and "color" in edge.keys() and edge["color"] == color and (mod, neighbor) not in edges_done:
                        # Increase overall color counter
                        color_counter[color] += 1

                        # Add edge to done-list
                        edges_done.add((mod, neighbor))
                        edges_done.add((neighbor, mod))

                        # Add module to go if not already visited
                        if neighbor not in modules_todo:
                            modules_todo.append(neighbor)
    return color_counter


# Recolors for a given module all connected edges of the same color (even over multiple modules)
def recolor_edges_for_module(graphname, overall_color_counter, module, oldcolor, newcolor, wlan_modules):
    # Speed up things if colors are equal
    if oldcolor == newcolor:
        # Nothing to do then
        print("Error: tried to overpaint " + str(oldcolor) + " with " + str(newcolor) + ". This does not make sense  and should not happen.")
        exit(1)

    # Add initial node to be able to start from there
    modules_todo = list()
    modules_todo.append(module)

    for mod in modules_todo:
        neighbors = graphname.neighbors(mod)
        for neighbor in neighbors:
            if neighbor in wlan_modules:
                edge = graphname.edge[mod][neighbor]
                if edge and "color" in edge.keys() and edge["color"] == oldcolor:
                    # Recolor that edge
                    set_edge_color(graphname, overall_color_counter, newcolor, mod, neighbor)

                    # Add the destination node to nodes_todo
                    modules_todo.append(neighbor)


def find_color_for_edge_without_tricky(graphname, overall_color_counter, module_a, module_b):
    if not module_is_already_colored(graphname, module_a):
        if not module_is_already_colored(graphname, module_b):
            set_edge_color(graphname, overall_color_counter, get_best_color_in(graphname, overall_color_counter, Assignable_Colors, module_a, module_b), module_a, module_b)
        else:
            # We have to take the color of module_b
            set_edge_color(graphname, overall_color_counter, graphname.node[module_b]["color"], module_a, module_b)

    else:
        # we have to take the color of module_a, lets see if this is a problem
        # and check if b is not colored, or we can use the color there
        color_of_module_a = graphname.node[module_a]["color"]
        if not module_is_already_colored(graphname, module_b):
            set_edge_color(graphname, overall_color_counter, color_of_module_a, module_a, module_b)

        else:
            # Now we have a problem if the colors are not by accident the same
            color_of_module_b = graphname.node[module_b]["color"]
            if color_of_module_a == color_of_module_b:
                # We are lucky, they are the same
                set_edge_color(graphname, overall_color_counter, color_of_module_a, module_a, module_b)
            else:
                # Tricky case
                return False
    return True


# Find the best color for an edge
def find_color_for_edge(graphname, overall_color_counter, module_a, module_b, wlan_modules):
    if not find_color_for_edge_without_tricky(graphname, overall_color_counter, module_a, module_b):
        # Module A and B are differently colored but we have to establish a link between them
        # This is the most costly case
        # The solution here is based on a paper called hycint-mcr2 and works like described in the following:
        # Take the color from module_a or module_b which occurs less at both sides (connected!) and repaint it with the other one
        #todo: here we could also look for another link outside the mst, instead of enforcing one color
        # Then replace the least connected colors at A and B with the newcolor and also use it for the edge
        # between A and B

        # Get the colorcounts for both nodes and combine them
        color_of_module_a = graphname.node[module_a]["color"]
        color_of_module_b = graphname.node[module_b]["color"]
        nr_of_occurrences_for_color_at_module_a = get_connected_color_count_for_module(graphname, module_a, color_of_module_a, wlan_modules)
        nr_of_occurrences_for_color_at_module_b = get_connected_color_count_for_module(graphname, module_b, color_of_module_b, wlan_modules)

        if nr_of_occurrences_for_color_at_module_a > nr_of_occurrences_for_color_at_module_b:
            winning_color = color_of_module_a
            losing_color = color_of_module_b
        else:
            winning_color = color_of_module_b
            losing_color = color_of_module_a

        # Recolor all other connected edges for both modules
        recolor_edges_for_module(graphname, overall_color_counter, module_a, losing_color, winning_color, wlan_modules)
        recolor_edges_for_module(graphname, overall_color_counter, module_b, losing_color, winning_color, wlan_modules)

        # Color the edge from node_a to node_b with this the best color available at node a
        set_edge_color(graphname, overall_color_counter, winning_color, module_a, module_b)


# Check if the coloring is valid (does ever node only use a number of colors = his modules and Are all edges colored?)
def graph_is_valid(graphname, lan_nodes, wlan_modules):
    print("Checking the graph for validity")

    # First check if every edge is colored
    for edge in graphname.edges():
        if not edge[0] in lan_nodes and not edge[1] in lan_nodes:
            if not edge:
                print(edge + " not valid")
                print("Graph is NOT valid")
                return False
            else:
                if not graphname.edge[edge[0]][edge[1]]["color"]:
                    print("Edge has no color: " + str(edge[0]) + "<->" + str(edge[1]))
                    print("Graph is NOT valid")
                    return False
                else:
                    # Check if the color is in one of the assignable colors
                    if graphname.edge[edge[0]][edge[1]]["color"] not in Assignable_Colors:
                        print("The color for edge: " + str(edge[0]) + "," + str(edge[1]) + "is not an assignable color.")
                        print("Graph is NOT valid")
                        return False
                # Check if there are only connections between modules of different nodes
                if graphname.node[edge[0]]["module-of"] == graphname.node[edge[1]]["module-of"]:
                    print("The modules " + str(edge[0]) + "," + str(edge[1]) + " are both connected to node " + graphname.node[edge[0]]["module-of"])
                    print("This does not make sense")
                    print("Graph is NOT valid")
                    return False

    for module in wlan_modules:
        corresponding_module = graphname.node[module]["module-of"]
        if not graphname.has_edge(corresponding_module, module):
            print("Module " + module + " is attached to " + corresponding_module + " but, has no direct connection to it.")
            print("Graph is NOT valid")
            return False


    # Now check if every node has only so many attached colors/channels as the number of modules it has
    for node in lan_nodes:
        nr_of_modules = graphname.node[node]["modules"]

        # Number of colors in the used-colors counter which have a value != 0
        nr_of_colors = 0
        for key in graphname.node[node]["used-colors"].keys():
            if graphname.node[node]["used-colors"][key] != 0:
                nr_of_colors += 1

        if nr_of_colors > nr_of_modules:
            print("Node " + str(node) + " has more colors attached than it has modules:" + str(nr_of_colors) + " > " + str(nr_of_modules) + ")")
            print(graphname.node[node]["used-colors"])
            print("Graph is NOT valid")
            return False
    print("Graph is valid")
    return True


# Transform networkxgraph to pydot graph, for displaying purposes
def show_graph(networkxgraph, wlan_modules, lan_nodes, filename="caa.svg"):
    pydotgraphname = pydot.Dot(graph_type='graph', layout=Graph_Layout)
    edges_done = set()
    for node in networkxgraph.nodes():
        node_shape = "oval"
        if node in lan_nodes:
            node_shape = "oval"
        elif node in wlan_modules:
            node_shape = "box"
        else:
            print("Error: Node " + str(node) + " is neither in lan_nodes nor in wlan_modules. It has to be in one of those.")
            exit(1)
        pydotgraphname.add_node(pydot.Node(node, shape=node_shape))
    for (A, B) in networkxgraph.edges():
        if (A, B) not in edges_done:
            edge_weight = networkxgraph.edge[A][B]["weight"]
            if A in lan_nodes or B in lan_nodes:
                edge_style = "solid"
                edge_color = "black"
                edge_penwidth = 2
            else:
                # For debugging set to std penwidth
                #edge_penwidth = str(Edge_Thickness/edge_weight)
                edge_penwidth = 3
                edge_color = networkxgraph.edge[A][B]["color"]
                edge_style = "dotted"
                if edge_color is None:
                    edge_color = "grey"
                else:
                    edge_color = colortable[edge_color]

            pydotgraphname.add_edge(pydot.Edge(str(A), str(B), style=edge_style, penwidth=edge_penwidth, color=edge_color))

            edges_done.add((A, B))
    pydotgraphname.write(filename, format="svg")


# Translate a lan_mac + interface nr to wlan_mac
# Returns the wlan_mac, or nothing if not found
def translate_lan_mac_to_wlan_mac(lanmac, interfacenr, active_radios_dict):
    # Interfacenr is of the form "WLAN-ID"
    # Look for the combination lanmac + interfacenr in the table active radios and return the wlan_mac for it
    for index in active_radios_dict.keys():
        if active_radios_dict[index]["lan_mac"] == lanmac and active_radios_dict[index]["interface_nr"] == interfacenr:
            return active_radios_dict[index]["bssid_mac"]
    print("Warning: Got inconsistent data from WLC")
    print("         Could not translate lanmac: " + str(lanmac) + " and interfacenr: " + str(interfacenr) + " to wlan_mac from Scanresults and Active Radios.")


# Get the data from the wlc, returns a networkx basic graph
def get_basic_graph_from_wlc():
    #
    # Get data from WLC
    #
    snmp_session = netsnmp.Session(DestHost=wlc_address, Version=snmp_version, Community=snmp_community)

    # These are our intern connections
    AutoWDS_Topology_Scan_Results = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.122'))
    AutoWDS_Topology_Scan_Results_length = len(AutoWDS_Topology_Scan_Results) / 6
    AutoWDS_Topology_Scan_Results_target_wlan_mac_hex = AutoWDS_Topology_Scan_Results[0:AutoWDS_Topology_Scan_Results_length]
    AutoWDS_Topology_Scan_Results_target_wlan_mac = [i.encode("hex") for i in AutoWDS_Topology_Scan_Results_target_wlan_mac_hex]
    AutoWDS_Topology_Scan_Results_source_wlan_mac_hex = AutoWDS_Topology_Scan_Results[AutoWDS_Topology_Scan_Results_length:2*AutoWDS_Topology_Scan_Results_length]
    AutoWDS_Topology_Scan_Results_source_wlan_mac = [i.encode("hex") for i in AutoWDS_Topology_Scan_Results_source_wlan_mac_hex]
    AutoWDS_Topology_Scan_Results_radio_channel = AutoWDS_Topology_Scan_Results[2*AutoWDS_Topology_Scan_Results_length:3*AutoWDS_Topology_Scan_Results_length]
    AutoWDS_Topology_Scan_Results_phy_signal = AutoWDS_Topology_Scan_Results[3*AutoWDS_Topology_Scan_Results_length:4*AutoWDS_Topology_Scan_Results_length]
    AutoWDS_Topology_Scan_Results_noise_level = AutoWDS_Topology_Scan_Results[4*AutoWDS_Topology_Scan_Results_length:5*AutoWDS_Topology_Scan_Results_length]
    AutoWDS_Topology_Scan_Results_age = AutoWDS_Topology_Scan_Results[5*AutoWDS_Topology_Scan_Results_length:6*AutoWDS_Topology_Scan_Results_length]
    # Create the dict of dicts for scan results
    # Example entry: scan_results[<name>]["lan_mac"] = <value>
    #                scan_results[<name>]["channel"] = <value>
    #                ...
    AutoWDS_Topology_Scan_Results = dict()
    AutoWDS_Topology_Scan_Results_Index = 0
    for wlan_source_mac, wlan_dest_mac, channel, signal_strength, noise_level, age \
            in zip(AutoWDS_Topology_Scan_Results_source_wlan_mac, AutoWDS_Topology_Scan_Results_target_wlan_mac,
                   AutoWDS_Topology_Scan_Results_radio_channel, AutoWDS_Topology_Scan_Results_phy_signal,
                   AutoWDS_Topology_Scan_Results_noise_level, AutoWDS_Topology_Scan_Results_age):
        entry_dict = dict()
        entry_dict["source_mac"] = wlan_source_mac
        entry_dict["wlan_dest_mac"] = wlan_dest_mac
        entry_dict["channel"] = channel
        entry_dict["signal_strength"] = signal_strength
        entry_dict["noise_level"] = noise_level
        entry_dict["age"] = age
        AutoWDS_Topology_Scan_Results[AutoWDS_Topology_Scan_Results_Index] = entry_dict
        AutoWDS_Topology_Scan_Results_Index += 1

    del AutoWDS_Topology_Scan_Results_target_wlan_mac_hex, AutoWDS_Topology_Scan_Results_target_wlan_mac, \
        AutoWDS_Topology_Scan_Results_source_wlan_mac_hex, AutoWDS_Topology_Scan_Results_source_wlan_mac, \
        AutoWDS_Topology_Scan_Results_radio_channel, AutoWDS_Topology_Scan_Results_phy_signal, \
        AutoWDS_Topology_Scan_Results_noise_level, AutoWDS_Topology_Scan_Results_age, \
        AutoWDS_Topology_Scan_Results_length, AutoWDS_Topology_Scan_Results_Index

    # First create the interfaces-graph
    # That means we create a node for each WLAN-interface of a node
    # and connect each of those of a node with a link with quality 0(best)(so the MST takes this edge always)
    # Therefore we use the Status/WLAN-Management/AP-Status/Active-Radios/ Table of the WLC
    # This gives us the interfaces of each node (identified by the MACs (LAN/WLAN)
    Active_Radios = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1'))
    Active_Radios_length = len(Active_Radios) / 30
    Active_Radios_lan_mac_hex = Active_Radios[0:1*Active_Radios_length]
    Active_Radios_lan_mac = [j.encode("hex") for j in Active_Radios_lan_mac_hex]
    Active_Radios_ip = Active_Radios[1*Active_Radios_length:2*Active_Radios_length]
    Active_Radios_name = Active_Radios[2*Active_Radios_length:3*Active_Radios_length]
    Active_Radios_location = Active_Radios[3*Active_Radios_length:4*Active_Radios_length]
    Active_Radios_unknown5 = Active_Radios[4*Active_Radios_length:5*Active_Radios_length]
    Active_Radios_wlan_mac_hex = Active_Radios[5*Active_Radios_length:6*Active_Radios_length]
    Active_Radios_wlan_mac = [j.encode("hex") for j in Active_Radios_wlan_mac_hex]
    Active_Radios_ifc = Active_Radios[6*Active_Radios_length:7*Active_Radios_length]
    Active_Radios_radio_band = Active_Radios[7*Active_Radios_length:8*Active_Radios_length]
    Active_Radios_channel = Active_Radios[8*Active_Radios_length:9*Active_Radios_length]
    Active_Radios_client_count = Active_Radios[9*Active_Radios_length:10*Active_Radios_length]
    Active_Radios_background_scan = Active_Radios[10*Active_Radios_length:11*Active_Radios_length]
    Active_Radios_card_id = Active_Radios[11*Active_Radios_length:12*Active_Radios_length]
    Active_Radios_fw_version = Active_Radios[12*Active_Radios_length:13*Active_Radios_length]
    Active_Radios_card_serial_nr = Active_Radios[13*Active_Radios_length:14*Active_Radios_length]
    Active_Radios_operating = Active_Radios[14*Active_Radios_length:15*Active_Radios_length]
    Active_Radios_transmit_power = Active_Radios[15*Active_Radios_length:16*Active_Radios_length]
    Active_Radios_eirp = Active_Radios[16*Active_Radios_length:17*Active_Radios_length]
    Active_Radios_exc_eirp = Active_Radios[17*Active_Radios_length:18*Active_Radios_length]
    Active_Radios_internal = Active_Radios[18*Active_Radios_length:19*Active_Radios_length]
    Active_Radios_nr_radios = Active_Radios[19*Active_Radios_length:20*Active_Radios_length]
    Active_Radios_module = Active_Radios[20*Active_Radios_length:21*Active_Radios_length]
    Active_Radios_serial_nr = Active_Radios[21*Active_Radios_length:22*Active_Radios_length]
    Active_Radios_version = Active_Radios[22*Active_Radios_length:23*Active_Radios_length]
    Active_Radios_card_state = Active_Radios[23*Active_Radios_length:24*Active_Radios_length]
    Active_Radios_field_optimization = Active_Radios[24*Active_Radios_length:25*Active_Radios_length]
    Active_Radios_modem_load_min = Active_Radios[25*Active_Radios_length:26*Active_Radios_length]
    Active_Radios_modem_load_max = Active_Radios[26*Active_Radios_length:27*Active_Radios_length]
    Active_Radios_modem_load_avg = Active_Radios[27*Active_Radios_length:28*Active_Radios_length]
    Active_Radios_unknown29 = Active_Radios[28*Active_Radios_length:29*Active_Radios_length]
    Active_Radios_groups = Active_Radios[29*Active_Radios_length:30*Active_Radios_length]
    # Create the dict of dicts for active radios
    # Example entry: active_radios[<name>]["lan_mac"] = <value>
    #                active_radios[<name>]["bssid_mac"] = <value>
    #                ...
    Active_Radios = dict()
    Active_Radios_Index = 0
    for lan_mac, ip, name, location, unknown5, wlan_mac, ifc, radio_band, channel, client_count,\
        background_scan, card_id, fw_version, card_serial_nr, operating, transmit_power, eirp,\
        exc_eirp, internal, nr_radios, module, serial_nr, version, card_state, field_optimization,\
        modem_load_min, modem_load_max, modem_load_avg, unknown29, groups\
        in zip(Active_Radios_lan_mac, Active_Radios_ip, Active_Radios_name, Active_Radios_location,
               Active_Radios_unknown5, Active_Radios_wlan_mac, Active_Radios_ifc, Active_Radios_radio_band,
               Active_Radios_channel, Active_Radios_client_count, Active_Radios_background_scan,
               Active_Radios_card_id, Active_Radios_fw_version, Active_Radios_card_serial_nr, Active_Radios_operating,
               Active_Radios_transmit_power, Active_Radios_eirp, Active_Radios_exc_eirp, Active_Radios_internal,
               Active_Radios_nr_radios, Active_Radios_module, Active_Radios_serial_nr, Active_Radios_version,
               Active_Radios_card_state, Active_Radios_field_optimization, Active_Radios_modem_load_min,
               Active_Radios_modem_load_max, Active_Radios_modem_load_avg, Active_Radios_unknown29, Active_Radios_groups):
        entry_dict = dict()
        entry_dict["lan_mac"] = lan_mac
        entry_dict["ip"] = ip
        entry_dict["name"] = name
        entry_dict["location"] = location
        entry_dict["unknown5"] = unknown5
        entry_dict["wlan_mac"] = wlan_mac
        entry_dict["ifc"] = ifc
        entry_dict["radio_band"] = radio_band
        entry_dict["channel"] = channel
        entry_dict["client_count"] = client_count
        entry_dict["background_scan"] = background_scan
        entry_dict["card_id"] = card_id
        entry_dict["fw_version"] = fw_version
        entry_dict["card_serial_nr"] = card_serial_nr
        entry_dict["operating"] = operating
        entry_dict["transmit_power"] = transmit_power
        entry_dict["eirp"] = eirp
        entry_dict["exc_eirp"] = exc_eirp
        entry_dict["internal"] = internal
        entry_dict["nr_radios"] = nr_radios
        entry_dict["module"] = module
        entry_dict["serial_nr"] = serial_nr
        entry_dict["version"] = version
        entry_dict["card_state"] = card_state
        entry_dict["field_optimization"] = field_optimization
        entry_dict["modem_load_min"] = modem_load_min
        entry_dict["modem_load_max"] = modem_load_max
        entry_dict["modem_load_avg"] = modem_load_avg
        entry_dict["unknown29"] = unknown29
        entry_dict["groups"] = groups
        Active_Radios[Active_Radios_Index] = entry_dict
        Active_Radios_Index += 1

    del Active_Radios_lan_mac, Active_Radios_ip, Active_Radios_name, Active_Radios_location, Active_Radios_unknown5, \
        Active_Radios_wlan_mac, Active_Radios_ifc, Active_Radios_radio_band, Active_Radios_channel, Active_Radios_client_count, \
        Active_Radios_background_scan, Active_Radios_card_id, Active_Radios_fw_version, Active_Radios_card_serial_nr, \
        Active_Radios_operating, Active_Radios_transmit_power, Active_Radios_eirp, Active_Radios_exc_eirp, Active_Radios_internal, \
        Active_Radios_nr_radios, Active_Radios_module, Active_Radios_serial_nr, Active_Radios_version, Active_Radios_card_state, \
        Active_Radios_field_optimization, Active_Radios_modem_load_min, Active_Radios_modem_load_max, Active_Radios_modem_load_avg, \
        Active_Radios_unknown29, Active_Radios_groups, Active_Radios_lan_mac_hex, Active_Radios_wlan_mac_hex, Active_Radios_length, \
        Active_Radios_Index

    if len(Active_Radios) != len(AutoWDS_Topology_Scan_Results):
        print("Warning: Length of Active_Radios and AutoWDS_Topology_Scan_Results are different. Sth is probably wrong.")

    # Todo: Foreign table

    # Separate our connections from foreigners
    #our_connections = dict()
    #foreign_connections = dict()
    #for index in scan_results.keys():
    #    if scan_results[index]["seen_bssid"] in active_radios_ap_bssid_mac:
    #        our_connections[index] = scan_results[index]
    #    else:
    #        foreign_connections[index] = scan_results[index]

    # Safety check
    if len(AutoWDS_Topology_Scan_Results) == 0:
        print("Error: Our connection list is empty. The APs don't see each other")
        exit(1)
    #if len(foreign_connections) == 0:
    #    print("Warning: Foreign connection list is empty. The APs don't foreign networks.")
    #    print("         This is unlikely, except there are really no other wireless lan networks around")

    # Create set of nodes, which are modules
    wlan_modules = set()
    for index in Active_Radios.keys():
        wlan_modules.add(Active_Radios[index]["wlan_mac"])

    # Create set of nodes, which are not modules (=>actual devices)
    lan_nodes = set()
    for index in Active_Radios.keys():
        lan_nodes.add(Active_Radios[index]["lan_mac"])

    basic_graph = nx.DiGraph()

    #
    # Generate the basic graph from data
    #
    # Set default values for nodes
    for node in lan_nodes:
        # Add the node
        basic_graph.add_node(node)

        # Initialize used colors with 0
        used_colors = collections_enhanced.Counter()
        for color in Assignable_Colors:
            used_colors[color] = 0
        basic_graph.node[node]["used-colors"] = used_colors

        # Set number of modules initially to 0
        basic_graph.node[node]["modules"] = 0

    # Set default values for modules
    for module in wlan_modules:

        # Add the module-node
        basic_graph.add_node(module)

        # Set the default color
        basic_graph.node[module]["color"] = None

        # Initialize actually seen counters for wlan modules with 0
        #actually_seen_colors = collections_enhanced.Counter()
        #for color in Assignable_Colors:
        #    actually_seen_colors[color] = 0
        #basic_graph.node[module]["seen_channels"] = actually_seen_colors

        # Initialize nr of modules for wlan module
        basic_graph.node[module]["modules"] = 1

    # Fill/Add node-module edges with data from wlc
    for index in Active_Radios.keys():
        lan_mac = Active_Radios[index]["lan_mac"]
        wlan_mac = Active_Radios[index]["wlan_mac"]

        # Add the edge
        basic_graph.add_edge(lan_mac, wlan_mac)

        # Module-edge data
        basic_graph.edge[lan_mac][wlan_mac]["weight"] = 1
        basic_graph.edge[lan_mac][wlan_mac]["real-connection"] = False

        # Write all data also into graph
        basic_graph.node[wlan_mac]["module-of"] = lan_mac
        for key in Active_Radios[index].keys():
            basic_graph.edge[lan_mac][wlan_mac][key] = Active_Radios[index][key]

        # Also count here the number of modules each node has
        basic_graph.node[lan_mac]["modules"] += 1

    # Add all possible module-module links
    for index in AutoWDS_Topology_Scan_Results.keys():
        source_mac = AutoWDS_Topology_Scan_Results[index]["source_mac"]
        wlan_dest_mac = AutoWDS_Topology_Scan_Results[index]["wlan_dest_mac"]
        channel = AutoWDS_Topology_Scan_Results[index]["channel"]
        signal_strength = int(AutoWDS_Topology_Scan_Results[index]["signal_strength"])
        noise_level = int(AutoWDS_Topology_Scan_Results[index]["noise_level"])
        age = AutoWDS_Topology_Scan_Results[index]["age"]

        basic_graph.add_edge(source_mac, wlan_dest_mac)

        # Set the score of this edge
        # 1 + because the best edge has one (node to interfaces) a high signal-strength = good -> make inverse for MST-calculation
        # because lower values are better there
        SNR = signal_strength + noise_level
        basic_graph.edge[source_mac][wlan_dest_mac]["weight"] = 1 + 100.0 - SNR

        # Initialize each edge with empty color
        basic_graph.edge[source_mac][wlan_dest_mac]["color"] = None
        basic_graph.edge[source_mac][wlan_dest_mac]["real-connection"] = True

    # Fill interference list
    #for index in foreign_connections.keys():
    #    channel = foreign_connections[index]["channel"]
    #    wlan_mac = foreign_connections[index]["wlan_mac"]
    #    # Add to interference list of this wlan module-node
    #    # Only consider the channels we have in Assignable colors, since the others are useless
    #    if channel in Assignable_Colors:
    #        basic_graph.node[wlan_mac]["seen_channels"][channel] += 1

    return basic_graph, wlan_modules, lan_nodes


# Create a random Graph for testing
def get_basic_random_graph(nr_of_nodes=10, max_nr_modules=3, max_nr_connections=4):
    basic_graph = nx.DiGraph()
    wlan_modules = set()
    lan_nodes = set()
    for nr in range(0, nr_of_nodes):
        nodename = "node_" + str(nr)
        lan_nodes.add(str(nodename))
        # Add the node
        basic_graph.add_node(nodename)

        # Initialize used colors with 0
        used_colors = collections_enhanced.Counter()
        for color in Assignable_Colors:
            used_colors[color] = 0
        basic_graph.node[nodename]["used-colors"] = used_colors

        # Set number of modules initially to 0
        basic_graph.node[nodename]["modules"] = 0
        for nr_mod in range(0, random.choice(range(1, max_nr_modules))):
            module = str(nr) + "_" + str(nr_mod)

            wlan_modules.add(module)

            # Add the module-node
            basic_graph.add_node(module)

            # Set the default color
            basic_graph.node[module]["color"] = None

            # Initialize actually seen counters for wlan modules with 0
            actually_seen_colors = collections_enhanced.Counter()
            for color in Assignable_Colors:
                actually_seen_colors[color] = 0
            basic_graph.node[module]["seen_channels"] = actually_seen_colors

            # Initialize nr of modules for wlan module
            basic_graph.node[module]["modules"] = 1

            basic_graph.node[module]["module-of"] = nodename

            basic_graph.add_edge(nodename, module)

             # Module-edge data
            basic_graph.edge[nodename][module]["weight"] = 1
            basic_graph.edge[nodename][module]["real-connection"] = False

            # Also count here the number of modules each node has
            basic_graph.node[nodename]["modules"] += 1

            for nr_con in range(0, random.choice(range(1,max_nr_connections))):
                random_module = random.choice(list(wlan_modules))
                if not random_module == module:
                    basic_graph.add_edge(module, random_module)
                    basic_graph.add_edge(random_module, module)
                    basic_graph.edge[module][random_module]["weight"] = 1 + 100.0 - random.choice(range(-20, 20))
                    basic_graph.edge[random_module][module]["weight"] = 1 + 100.0 - random.choice(range(-20, 20))

                    # Initialize each edge with empty color
                    basic_graph.edge[random_module][module]["color"] = None
                    basic_graph.edge[module][random_module]["color"] = None
                    basic_graph.edge[module][random_module]["real-connection"] = True
                    basic_graph.edge[random_module][module]["real-connection"] = True

    return basic_graph, wlan_modules, lan_nodes


# Caclulate a coloring for a given graph
def calculate_colored_graph(graphname, wlan_modules):
    edges_done = set()                                      # List of edges which have been visited (empty at beginning)
    nodelist = list()                                       # This is the list of nodes over which we iterate
    nodelist.append(root_node)                              # Initially put only the gatewaynode in the nodelist (Could also be a different one)
    overall_color_counter = collections_enhanced.Counter()  # This counts how often each color has been used overall, initially fill with 0
    for color in Assignable_Colors:
        overall_color_counter[color] = 0

    # Go through all nodes (main loop)
    for node in nodelist:
        neighbors = graphname.neighbors(node)
        for neighbor in neighbors:
            if (node, neighbor) not in edges_done:
                # We just want to color the module-edges and not
                # the edges between node and module, since they dont need a coloring
                if node in wlan_modules and neighbor in wlan_modules and not edge_has_color(graphname, node, neighbor):
                    find_color_for_edge(graphname, overall_color_counter, node, neighbor, wlan_modules)
                if not neighbor in nodelist:
                    nodelist.append(neighbor)
                # Mark edge as done
                edges_done.add((node, neighbor))
                edges_done.add((neighbor, node))
    return graphname

#
# Configuration
#
Number = 0                                              # Image-iterator for debugging
Edge_Thickness = 9.0                                    # Factor for edge thickness, smaller value => smaller edges
Graph_Layout = "dot"                                    # Graphlayout for graphviz (what style to use)(fdp,sfdp,dot,neato,twopi,circo)
#mst_mode = "single"                                    # This variable sets the mode for the MST creation:
                                                        # node = We expect a complete node to fail at a time (network still works, even if a whole node breaks)
                                                        # edge = We expect only a single edge to fail at a time (network still works, even if an edge breaks, less connetions though than "node")
                                                        # single = only calculate ordinary MST (no redundancy, one node or edge breakds => connectivity is gone, least number of connections)
                                                        # equal_module = equally distribute the
Assignable_Colors = ["1", "3", "6", "11"]               # List of all channels/colors which can be used for assignment
colortable = dict()
colortable["1"] = "red"
colortable["3"] = "green"
colortable["6"] = "blue"
colortable["11"] = "orange"
wlc_address = "172.16.40.100"
snmp_community = "public"
snmp_version = 2

# Getting Data from WLC per SNMP
#basic_connectivity_graph_directed, modules, devices = get_basic_graph_from_wlc()
while True:
    # Alternatively for debugging/testing, generate Random Graph
    nr_nodes = random.choice(range(5, 25))
    nr_modules = random.choice(range(2, 5))
    nr_max_connections = random.choice(range(2, 6))
    basic_connectivity_graph_directed, modules, devices = get_basic_random_graph(nr_nodes, nr_modules, nr_max_connections)
    root_node = random.choice(list(devices))
    #mst_mode = random.choice(["node", "edge", "single", "equal_module"])
    #todo: for debugging used only equal remove later
    mst_mode = "equal_module"

    # Convert to undirected graph
    basic_connectivity_graph = convert_to_undirected_graph(basic_connectivity_graph_directed)

    # DEBUG: Show basic Connectivity and channelquality
    show_graph(basic_connectivity_graph, modules, devices)

    # First phase: Calculate the Minimal Spanning Tree from the basic connectivity graph
    mst_graph = calculate_survival_graph(basic_connectivity_graph, modules, devices)

    # DEBUG: Show Minimal Spanning Tree graph
    show_graph(mst_graph, modules, devices)

    # Second Phase: Find the best channels for every edge in the MST-Graph and assign them to the edges
    colored_graph = calculate_colored_graph(mst_graph, modules)

    # DEBUG: Show colored Graph
    show_graph(colored_graph, modules, devices)

    # Finally check the graph for validity
    if not graph_is_valid(colored_graph, devices):
        exit(1)
