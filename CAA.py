#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose This script colors a networkx graph (Lancom AutoWDS Channel assignment algorithm)

import networkx as nx
import collections
import random
import pydot
import netsnmp


# counterlist = dictionary with colors and their number of occurences
# allowed_colors = list to pick colors from (because we might not be allowed to use all in a certain situation)
# Returns a list with elements that are in the allowed_colors list and are least commonly used
def get_least_used_elements_for_counter_dict(counterlist, allowed_colors):
    least_used_elements = list()

    # Create new restricted counterlist with only those elements in it, which are also in allowed_colors
    restricted_counterlist = collections.Counter()
    for element in counterlist.keys():
        if element in allowed_colors:
            restricted_counterlist[element] = counterlist[element]

    # Get the least common element (the rightest, because its a sorted list)
    least_common_element = restricted_counterlist.most_common()[-1]
    nr_of_used_times_for_least_element = least_common_element[1]

    # Find all other elements that are used the same number of times like the least common element
    for element in restricted_counterlist.keys():
        if restricted_counterlist[element] == nr_of_used_times_for_least_element:
            least_used_elements.append(element)

    return least_used_elements


# Returns dictionary with entries (like color : nr of occurences of this color in neighborhood of node)
# for a given node and allowed list of colors
def get_least_used_colors_for_node(graphname, nodename, allowed_colors):
    neighbors = graphname.neighbors(nodename)
    color_counter = collections.Counter()

    # Initially set all colors used to 0
    for color in Assignable_Colors and allowed_colors:
        color_counter[color] = 0

    for neighbor in neighbors:
        if not neighbor in lan_nodes:
            edge = graphname.get_edge_data(nodename, neighbor)
            if edge and "color" in edge.keys():
                edgecolor = edge["color"]
                if edgecolor:
                    color_counter[edgecolor] += 1

    return get_least_used_elements_for_counter_dict(color_counter, allowed_colors)


# Returns dictionary with entries (like color : nr of occurences of this color in neighborhood of node_a and node_b)
# for two nodes and a list of allowed colors
def get_least_used_colors_for_nodes(graphname, node_a, node_b, allowed_colors):
    color_counter = collections.Counter()

    # Initially set all colors used to 0
    for color in Assignable_Colors and allowed_colors:
        color_counter[color] = 0

    neighbors_of_a = graphname.neighbors(node_a)
    neighbors_of_b = graphname.neighbors(node_b)

    for neighbor in neighbors_of_a:
        if not neighbor in lan_nodes:
            edge = graphname.get_edge_data(node_a, neighbor)
            if edge and "color" in edge.keys():
                edgecolor = edge["color"]
                if edgecolor:
                    color_counter[edgecolor] += 1

    for neighbor in neighbors_of_b:
        if not neighbor in lan_nodes:
            edge = graphname.get_edge_data(node_b, neighbor)
            if edge and "color" in edge.keys():
                edgecolor = edge["color"]
                # Do not count the edge between node_a and node_b twice
                if edgecolor and not neighbor == node_a:
                    color_counter[edgecolor] += 1

    return get_least_used_elements_for_counter_dict(color_counter, allowed_colors)


# Calculates for a given graph the survival graph (2-connected graph) and returns it
def calculate_survival_graph(graphname):
    MST_Graph = nx.minimum_spanning_tree(graphname).copy()
    if mst_mode == "node":
        for node in graphname.nodes():

            # Create new temp Graph to work with
            work_graph = graphname.copy()

            # Remove the node
            work_graph.remove_node(node)

            # Now calculate the mst on this new graph
            mst_work_graph = nx.minimum_spanning_tree(work_graph)

            # Add the now necessary edges to the resulting graph
            for From, To, Attributes in mst_work_graph.edges(data=True):
                if not MST_Graph.has_edge(From, To):
                    MST_Graph.add_edge(From, To, weight=Attributes['weight'])
    elif mst_mode == "edge":
        # We have to note here, that we still could get less edges in the end
        # (we get here more edges than necessary for a 2-connected graph), but you really may not only want to use
        # only the edges, which you get by constructing a 2-connected graph, since this would also depend on bad quality-
        # links (Like you could get from A to C over B with : A->(0.1)->B->(0.1)->C, but you would rather take an edge like
        # A->(0.5)->C instead
        for edge in graphname.edges():

            # Create new temp Graph to work with
            work_graph = graphname.copy()

            # Remove the edge
            work_graph.remove_edge(edge[0], edge[1])

            # Now calculate the mst on the workgraph
            mst_work_graph = nx.minimum_spanning_tree(work_graph)

            # Add all of the edges from the MST_Work_Graph of this round to the final Graph
            for From, To, Attributes in mst_work_graph.edges(data=True):
                if not MST_Graph.has_edge(From, To):
                    MST_Graph.add_edge(From, To, weight=Attributes['weight'])
    elif mst_mode == "single":
        #Just fall through, since we already calculated the plain mst
        print()
    elif mst_mode == "none":
        MST_Graph = graphname
    else:
        print("Unknown Mode: Please Chose one out of 'node', 'edge' or 'single'")
        exit(1)
    return MST_Graph


# Returns list of colors which are used the least over all edges in the graph and are in the allowed_colors list
def get_least_used_colors_overall(allowed_colors):
    least_used_colors = get_least_used_elements_for_counter_dict(Overall_Color_Counter, allowed_colors)
    return least_used_colors


# Get the color/channel for an edge, which has the least interference from other (not our) devices/wlans
# That means take a look at the two nodes and for a given set to chose from, find the color, which
# is used the least in their wireless region
# Returns a list
def get_least_actually_seen_colors_for_set(graphname, color_set, node_a, node_b):
    seen_channels_for_node_a = graphname.node[node_a]["seen_channels"]
    seen_channels_for_node_b = graphname.node[node_b]["seen_channels"]
    seen_channels_for_both_nodes = seen_channels_for_node_a + seen_channels_for_node_b
    least_seen_channels = get_least_used_elements_for_counter_dict(seen_channels_for_both_nodes, color_set)
    return least_seen_channels


# colorset = list of colors we can chose from
# caluclates the optimal color from this set
# Returns the color to use (not a list of colors)
def get_best_color_in(graphname, colorset, node_a, node_b):
    # Speed up things if there is only one color to chose from
    if len(colorset) == 1:
        return colorset[0]
    else:
        # Use only colors in colorset and then only those which have been used the least at A
        least_used_colors_for_node_a = get_least_used_colors_for_node(graphname, node_a, colorset)

        # Speed up things if there is only one color to chose from
        if len(least_used_colors_for_node_a) == 1:
            return least_used_colors_for_node_a[0]
        else:
            # If the former is a tie, then also look at the colors from node b
            least_used_colors_for_node_a_and_node_b = get_least_used_colors_for_nodes(graphname, node_a, node_b, colorset)

            # Speed up things if there is only one color to chose from
            if len(least_used_colors_for_node_a_and_node_b) == 1:
                return least_used_colors_for_node_a_and_node_b[0]
            else:
                #If there is again a tie,use the color which has the least actual interference an both nodes
                leas_actually_seen_color = get_least_actually_seen_colors_for_set(graphname, least_used_colors_for_node_a_and_node_b, node_a, node_b)

                # Speed up things if there is only one color to chose from
                if len(leas_actually_seen_color) == 1:
                    return leas_actually_seen_color[0]
                else:
                    # If there is again a tie, look also at the overall color assignments and take the rarest used one
                    least_used_colors_overall = get_least_used_colors_overall(colorset)

                    # Speed up things if there is only one color to chose from
                    if len(least_used_colors_overall) == 1:
                        return least_used_colors_overall[0]
                    else:
                        # All have been ties so far, now take one color at random
                        random_color = random.choice(colorset)
                        return random_color


# Sets the color for an edge
def set_edge_color(graphname, edgecolor, node_a, node_b):
    edge_data = graphname.get_edge_data(node_a, node_b)
    edge_weight = edge_data["weight"]

    # Color the edge
    graphname[node_a][node_b]["color"] = edgecolor

    # Increase the overall colorcounters
    Overall_Color_Counter[edgecolor] += 1

    # Mark edge as done
    Edges_Done.add((node_a, node_b))
    Edges_Done.add((node_b, node_a))

    # Color in pydot for debugging, remove later
    # TODO: (THIS SHOULD BE DONE SOMEWHERE ELSE LATER)
    edge = pydotgraph.get_edge(str(node_a), str(node_b))[0]
    edge.set_color(colortable[edgecolor])
    penwidth = str(Edge_Thickness/edge_weight)
    edge.set_penwidth(penwidth)
    edge.set_style("solid")


# Returns the number of modules for a node
def get_modules_count_for_node(graphname, nodename):
    modules = graphname.node[nodename]["modules"]
    if modules:
        return modules


# Returns set of colors for all edges of a node
def get_colors_used_for_node(graphname, nodename):
    colorset = set()
    neighbors = graphname.neighbors(nodename)
    for neighbor in neighbors:
        if not neighbor in lan_nodes:
            edge = graphname.get_edge_data(nodename, neighbor)
            if edge and "color" in edge.keys():
                edgecolor = edge["color"]
                colorset.add(edgecolor)
    return list(colorset)


# Returns the number of the (distinct) colors this node already uses
def get_number_of_colors_used_for_node(graphname, nodename):
    colors_used = get_colors_used_for_node(graphname, nodename)
    return len(colors_used)


# Returns the number of modules for a node that are still free to use
# modules=number of wlan modules (probably 2 or 3 atm)
def modules_free_count(graphname, nodename):
    #free modules = num of modules of node minus num of channels already used
    return get_modules_count_for_node(graphname, nodename) - get_number_of_colors_used_for_node(graphname, nodename)


# Returns list of the colors which the either node a or node b uses
def get_colors_used_for_nodes(graphname, node_a, node_b):
    colors_used_by_node_a = get_colors_used_for_node(graphname, node_a)
    colors_used_by_node_b = get_colors_used_for_node(graphname, node_b)
    colors_used_by_either_node_a_or_node_b = list(set(colors_used_by_node_a + colors_used_by_node_b))
    return colors_used_by_either_node_a_or_node_b


# Returns a list of colors which are not used by the node
def get_colors_not_used_for_node(graphname, nodename):
    colors_used_by_node = get_colors_used_for_node(graphname, nodename)
    colors_not_used = [i for i in Assignable_Colors if i not in colors_used_by_node]
    return colors_not_used


# Returns a dictionary with connected colorusage for the node provided
def get_color_count_for_node(graphname, nodename):
    color_counter = collections.Counter()
    colors_of_nodename = get_colors_used_for_node(graphname, nodename)
    for color in colors_of_nodename:
        color_counter[color] = 0

    for color in colors_of_nodename:
        edges_done = set()
        nodes_todo = list()

        # Add initial node to be able to start from there
        nodes_todo.append(nodename)

        for node in nodes_todo:
            neighbors = graphname.neighbors(node)
            for neighbor in neighbors:
                if not neighbor in lan_nodes:
                    edge = graphname.get_edge_data(node, neighbor)
                    if edge and "color" in edge.keys() and edge["color"] == color and (node, neighbor) not in edges_done:
                        # Add edge to done-list
                        edges_done.add((node, neighbor))
                        edges_done.add((neighbor, node))

                        # Increase overall color counter
                        color_counter[color] += 1

                        # Add node togo if not already visited
                        if neighbor not in nodes_todo:
                            nodes_todo.append(neighbor)

    return color_counter


# Recolors for a given node all connected edges
def recolor_edges_for_node(graphname, nodename, oldcolor, newcolor):
    # Speed up things if colors are equal
    if oldcolor == newcolor:
        # Nothing to do then
        return

    nodes_todo = list()

    # Add initial node to be able to start from there
    nodes_todo.append(nodename)

    for node in nodes_todo:
        neighbors = graphname.neighbors(node)
        for neighbor in neighbors:
            if not neighbor in lan_nodes:
                edge = graphname.get_edge_data(node, neighbor)
                if edge and "color" in edge.keys() and edge["color"] == oldcolor:
                    # Recolor that edge
                    set_edge_color(graphname, newcolor, node, neighbor)

                    # Add the destination node to nodes_todo
                    nodes_todo.append(neighbor)

                    # Adjust overall_color_counter
                    Overall_Color_Counter[oldcolor] -= 1
                    Overall_Color_Counter[newcolor] += 1


def find_color_for_edge_without_tricky(graphname, node_a, node_b):
    if modules_free_count(graphname, node_a) > 0:
        if modules_free_count(graphname, node_b) > 0:
            # Is there a color used by neither node_a nor node_b?
            colors_not_used_by_node_a = get_colors_not_used_for_node(graphname, node_a)
            colors_not_used_by_node_b = get_colors_not_used_for_node(graphname, node_b)
            colors_unused_by_both = [i for i in colors_not_used_by_node_a if i in colors_not_used_by_node_b]
            if colors_unused_by_both:
                best_color = get_best_color_in(graphname, colors_unused_by_both, node_a, node_b)
                set_edge_color(graphname, best_color, node_a, node_b)
            else:
                # Is there a color, which has at least not been used by one of the two nodes?
                colors_not_used_by_either_node_a_or_node_b = list(set(colors_not_used_by_node_a + colors_not_used_by_node_b))
                if colors_not_used_by_either_node_a_or_node_b:
                    best_color = get_best_color_in(graphname, colors_not_used_by_either_node_a_or_node_b, node_a, node_b)
                    set_edge_color(graphname, best_color, node_a, node_b)
                else:
                    # Pick the best one in the already used ones by the nodes
                    colors_used_by_either_node_a_or_node_b = get_colors_used_for_nodes(graphname, node_a, node_b)
                    if colors_used_by_either_node_a_or_node_b:
                        best_color = get_best_color_in(graphname, colors_used_by_either_node_a_or_node_b, node_a, node_b)
                        set_edge_color(graphname, best_color, node_a, node_b)
                    else:
                        # Pick the best color of all general available colors
                        best_color = get_best_color_in(graphname, Assignable_Colors, node_a, node_b)
                        set_edge_color(graphname, best_color, node_a, node_b)
    else:
        if modules_free_count(graphname, node_b) > 0:
            # Use one of A's colors, which has been used the least there
            # This works, since we have still unused modules at A
            colors_used_for_node_a = get_colors_used_for_node(graphname, node_a)
            best_color = get_best_color_in(graphname, colors_used_for_node_a, node_a, node_b)
            set_edge_color(graphname, best_color, node_a, node_b)
        else:
            # We dont have any free modules at A or B
            # Is there an intersection of colors which A and B already use? => Use one of those
            colors_used_by_node_a = get_colors_used_for_node(graphname, node_a)
            colors_used_by_node_b = get_colors_used_for_node(graphname, node_b)
            colors_used_by_both = [i for i in colors_used_by_node_a if i in colors_used_by_node_b]
            if colors_used_by_both:
                # Chose the best from them
                best_color = get_best_color_in(graphname, colors_used_by_both, node_a, node_b)
                set_edge_color(graphname, best_color, node_a, node_b)
            else:
                return False
    return True


# Find the best color for an edge
def find_color_for_edge(graphname, node_a, node_b):
    if not find_color_for_edge_without_tricky(graphname, node_a, node_b):
        # There is also no intersection of colors in A and B
        # This is the most costly case
        # The solution here is based on a paper called hycint-mcr2 and works like described in the following:
        # Find the color which occurs the least connected at A and B,
        # then find the second least used color at A and B = newcolor
        # Then replace the least connected colors at A and B with the newcolor and also use it for the edge
        # between A and B

        # Get the colorcounts for both nodes and combine them
        combined_color_counter = get_color_count_for_node(graphname, node_a) + get_color_count_for_node(graphname, node_b)

        # Find the color which is the least common
        least_common_color = combined_color_counter.most_common()[-1][0]

        # Find the color we will use for this edge (This is then the second "best")
        # Replace the second rarest used color with the rarest used
        # Meaning we take all colors from both nodes A and B, in order to find the best in this set
        colors_used_by_node_a = get_colors_used_for_node(graphname, node_a)
        colors_used_by_node_b = get_colors_used_for_node(graphname, node_b)
        colors_used_by_either_node_a_or_node_b = list(set(colors_used_by_node_a + colors_used_by_node_b))

        # Remove the least common color from this set, because then this color would always be chosen,
        # because of its rare usage
        if least_common_color in colors_used_by_either_node_a_or_node_b:
            colors_used_by_either_node_a_or_node_b.remove(least_common_color)

        second_best_color = get_best_color_in(graphname, colors_used_by_either_node_a_or_node_b, node_a, node_b)

        # Recolor all other connected edges for both nodes, means recolor all second_best_colors with the least_common_color
        recolor_edges_for_node(graphname, node_a, second_best_color, least_common_color)
        recolor_edges_for_node(graphname, node_b, second_best_color, least_common_color)

        # Color the edge from node_a to node_b with this the best color available at node a
        # Now the tricky case is solved and continue with the normal procedure

        if not find_color_for_edge_without_tricky(graphname, node_a, node_b):
            print("ERROR: tricky case has not been solved correctly, could not assign color")
            exit(1)

# Check if the coloring is valid (does ever node only use a number of colors = his modules and Are all edges colored?)
def graph_is_valid(graphname):
    print("Checking the graph for validity")

    # First check if every edge has a color
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

    # Now check if every node has only so many attached colors/channels as the number of modules it has
    debug_sum_modules_used = 0
    debug_sum_modules_overall = 0
    for node in graphname.nodes():
        if node in wlan_modules:
            color_set = set()
            nr_of_modules = graphname.node[node]["modules"]
            for neighbor in graphname.neighbors(node):
                if not neighbor in lan_nodes:
                    color = graphname.edge[node][neighbor]["color"]
                    color_set.add(color)
            debug_sum_modules_used += len(color_set)
            debug_sum_modules_overall += nr_of_modules

            if len(color_set) > nr_of_modules:
                print("Node " + str(node) + " has more colors attached than it has modules:" + str(len(color_set)) + " > " + str(nr_of_modules) + ")")
                print(color_set)
                print("Graph is NOT valid")
                return False
        else:
            if not node in lan_nodes:
                print("something is wrong, node is neither lannode nor wlan module")
                return False


    print("Graph is valid with usage of: " + str(1.0*debug_sum_modules_used/debug_sum_modules_overall))
    return True


# Transform networkxgraph to pydot graph, for displaying purposes
def transform_graph(networkxgraph):
    for (A, B) in networkxgraph.edges():
        edge_data = networkxgraph.get_edge_data(A, B)
        edge_weight = edge_data["weight"]
        penwidth = str(Edge_Thickness/edge_weight)
        pydotgraph.add_edge(pydot.Edge(str(A), str(B), style="dotted", penwidth=penwidth))


# Writes the pydotgraph to file
def write_image():
    # Version wit slides
    #global Number
    #pydotgraph.write("caa_step_" + str(Number) + ".svg", format="svg")
    #Number += 1

    # Version without slides
    pydotgraph.write("caa.svg", format="svg")


#translate a lan_mac + interface nr to wlan_mac
def translate_lan_mac_to_wlan_mac(lanmac, interfacenr, active_radios_table):
    # Interfacenr is of the form "WLAN-ID"
    #look for the combination lanmac + interfacenr in the table active radios and return the wlan_mac for it
    results = [ i[2] for i in active_radios_table if i[1] == lanmac and i[3] == interfacenr]
    if len(results) != 1:
        print "Error: Could not find lanmac and interfacenr for " + str(lanmac) + "," + str(interfacenr) + " in active_radios"
        exit(1)
    else:
        return results[0]


#
# Configuration
#
Number = 0                                              # Image-iterator for debugging
Edge_Thickness = 9.0                                    # Factor for edge thickness, smaller value => smaller edges
Graph_Layout = "dot"                                    # Graphlayout for graphviz (what style to use)(fdp,sfdp,dot,neato,twopi,circo)
mst_mode = "edge"                                       # This variable sets the mode for the MST creation:
                                                        # node = We expect a complete node to fail at a time (network still works, even if a whole node breaks)
                                                        # edge = We expect only a single edge to fail at a time (network still works, even if an edge breaks, less connetions though than "node")
                                                        # single = only calculate ordinary MST (no redundancy, one node or edge breakds => connectivity is gone, least number of connections)
Assignable_Colors = ["1", "3", "6", "11"]  # List of all channels/colors which can be used for assignment
colortable = dict()
colortable["1"] = "red"
colortable["3"] = "green"
colortable["6"] = "blue"
colortable["11"] = "orange"

#
# Generating Graphs for testing
#
#RandomGraph = nx.fast_gnp_random_graph(25, 0.3)           # Generate a random graph, for debugging, remove later
#for node in RandomGraph.nodes():
#    RandomGraph.node[node]["modules"] = 2
#    actually_seen_colors = collections.Counter()
#    for color in Assignable_Colors:
#        actually_seen_colors[color] = random.randrange(1, 15)
#    RandomGraph.node[node]["seen_channels"] = actually_seen_colors
#for (a, b) in RandomGraph.edges():                      # Set random weights on edges for mst
#    RandomGraph[a][b]["weight"] = random.randrange(1, 20)

#
# Getting Data from WLC per SNMP
#
wlc_address = "172.16.40.100"
snmp_community = "public"
snmp_session = netsnmp.Session(DestHost=wlc_address, Version=2, Community=snmp_community)
scan_results_ap_name = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.2'))
scan_results_ap_mac_hex = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.4'))
scan_results_ap_mac = [ i.encode("hex") for i in scan_results_ap_mac_hex]
scan_results_seen_bssid_hex = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.1'))
scan_results_seen_bssid = [ i.encode("hex") for i in scan_results_seen_bssid_hex]
scan_results_channel = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.9'))
scan_results_signal_strengh = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.11'))
scan_results_interface_nr = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.5'))

# First create the interfaces-graph
# That means we create a node for each WLAN-interface of a node
# and connect each of those of a node with a link with quality 0(best)(so the MST takes this edge always)
# Therefore we use the Status/WLAN-Management/AP-Status/Active-Radios/ Table of the WLC
# This gives us the interfaces of each node (identified by the MACs (LAN/WLAN)
active_radios_ap_name = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.3'))
active_radios_ap_lan_mac_hex = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.1'))
active_radios_ap_lan_mac = [ i.encode("hex") for i in active_radios_ap_lan_mac_hex]
active_radios_ap_bssid_mac_hex = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.6'))
active_radios_ap_bssid_mac = [ i.encode("hex") for i in active_radios_ap_bssid_mac_hex]
active_radios_interface_nr = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.7'))  # 0=1, 1=2, ...
active_radios = zip(active_radios_ap_name, active_radios_ap_lan_mac, active_radios_ap_bssid_mac, active_radios_interface_nr)
scan_results_wlan_mac = [ translate_lan_mac_to_wlan_mac(i[0], i[1], active_radios) for i in zip(scan_results_ap_mac, scan_results_interface_nr) ]
scan_results = zip(scan_results_ap_name, scan_results_ap_mac, scan_results_seen_bssid, scan_results_channel, scan_results_signal_strengh, scan_results_wlan_mac)

wlan_modules = set(active_radios_ap_bssid_mac)
lan_nodes = set(active_radios_ap_lan_mac)

basic_connectivity_graph = nx.Graph()
#generate node to interface edges
for ap_name, ap_lan_mac, ap_wlan_interface_mac, ap_interface_nr in active_radios:
    basic_connectivity_graph.add_edge(ap_lan_mac, ap_wlan_interface_mac)
    basic_connectivity_graph[ap_lan_mac][ap_wlan_interface_mac]["weight"] = 1
    #initialize actually seen counters for wlan modules:
    actually_seen_colors = collections.Counter()
    for color in Assignable_Colors:
        actually_seen_colors[color] = 0
    basic_connectivity_graph.node[ap_wlan_interface_mac]["seen_channels"] = actually_seen_colors
    basic_connectivity_graph.node[ap_wlan_interface_mac]["interface-nr"] = ap_interface_nr
    basic_connectivity_graph.node[ap_wlan_interface_mac]["module-of"] = ap_name
    basic_connectivity_graph.node[ap_lan_mac]["name"] = ap_name
    #initialize nr of modules for wlan module
    basic_connectivity_graph.node[ap_wlan_interface_mac]["modules"] = 1
    #initialize nr of modules for lan_mac
    basic_connectivity_graph.node[ap_lan_mac]["modules"] = len(basic_connectivity_graph.neighbors(ap_lan_mac))


#add all possible links from scan-results-table (interface to interface)
for ap_name, ap_lan_mac, dest_wlan_mac, channel, signal_strength, ap_wlan_mac in scan_results:
    #check if we see one of our autowds aps or another wlan
    if dest_wlan_mac in active_radios_ap_bssid_mac:
        #its one of our connections in autowds
        basic_connectivity_graph.add_edge(ap_wlan_mac, dest_wlan_mac)

        # 1 + because the best edge has one (node to interfaces) a high signal-strength = good -> make inverse for MST-calculation
        # because lower values are better there
        basic_connectivity_graph[ap_wlan_mac][dest_wlan_mac]["weight"] = 1 + 100.0 / int(signal_strength)
    else:
        #its not one of our connections => add to interference list of this wlan module-node
        basic_connectivity_graph.node[ap_wlan_mac]["seen_channels"][channel] += 1

#
# Main function
#
Edges_Done = set()                                      # List of edges which have been visited (empty at beginning)
Overall_Color_Counter = collections.Counter()           # This counts how often each color has been used overall, initially fill with 0
for color in Assignable_Colors:
    Overall_Color_Counter[color] = 0

#pydotgraph = pydot.Dot(graph_type='graph', layout=Graph_Layout) # Create pydotgraph (so we can draw it better), remove the whole pydot stuff for final release
#transform_graph(RandomGraph)                            # Show basic Connectivity and channelquality
#write_image()

# First phase: Calculate the Minimal Spanning Tree from the basic connectivity graph
#del pydotgraph
pydotgraph = pydot.Dot(graph_type='graph', layout=Graph_Layout)
mst_graph = calculate_survival_graph(basic_connectivity_graph)
transform_graph(mst_graph)
write_image()

# Second Phase: Find the best channels for every edge in the MST-Graph and assign them to the edges
nodelist = list()   # This is the list of nodes over which we iterate
nodelist.append("ece555ffd63a")  # Initially put only the gatewaynode in the nodelist (Could also be a different one)
#todo: automate the line above

# Add all edges which have a lan node in them, so we dont try to color them
for From, To in mst_graph.edges():
    if From in lan_nodes or To in lan_nodes:
        Edges_Done.add((From, To))
        Edges_Done.add((To, From))

# Go through all nodes (main loop)
for node in nodelist:
    neighbors = mst_graph.neighbors(node)
    for neighbor in neighbors:
        if (node, neighbor) not in Edges_Done:
            find_color_for_edge(mst_graph, node, neighbor)
            nodelist.append(neighbor)
            #write_image()

write_image()
print(Overall_Color_Counter)

# Finally check the graph for validity
if not graph_is_valid(mst_graph):
    print("Found a bad one")
    exit(1)
