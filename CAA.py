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


# Calculates for a given graph the survival graph (2-connected graph) and returns it
def calculate_survival_graph(graphname):
    mst_graph = nx.minimum_spanning_tree(graphname).copy()
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
                if not mst_graph.has_edge(From, To):
                    mst_graph.add_edge(From, To, weight=Attributes['weight'])
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
                if not mst_graph.has_edge(From, To):
                    mst_graph.add_edge(From, To, Attributes)
    elif mst_mode == "single":
        #Just fall through, since we already calculated the plain mst
        print()
    elif mst_mode == "none":
        mst_graph = graphname
    else:
        print("Unknown Mode: Please Chose one out of 'node', 'edge' or 'single'")
        exit(1)
    return mst_graph


# Returns list of colors which are used the least over all edges in the graph and are in the allowed_colors list
def get_least_used_colors_in_overall(allowed_colors):
    return list(get_least_used_elements_for_counter_dict(Overall_Color_Counter, allowed_colors))


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
def get_best_color_in(graphname, colorset, module_a, module_b):
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
                least_used_colors_overall = get_least_used_colors_in_overall(least_seen_colors)
                if len(least_used_colors_overall) == 1:
                    return least_used_colors_overall[0]
                else:
                    # Pick one at random
                    return random.choice(least_used_colors_overall)


# Sets the color for an edge
def set_edge_color(graphname, edgecolor, module_a, module_b):
    edge_data = graphname.edge[module_a][module_b]
    edge_weight = edge_data["weight"]

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
        Overall_Color_Counter[former_color] -= 1

    # Color the edge and the modules
    graphname.edge[module_a][module_b]["color"] = edgecolor
    graphname.node[module_a]["color"] = edgecolor
    graphname.node[module_b]["color"] = edgecolor

    # Increase the color counter at the respective nodes for these modules
    graphname.node[node_of_module_a]["used-colors"][edgecolor] += 1
    graphname.node[node_of_module_b]["used-colors"][edgecolor] += 1

    # Increase also the overall colorcounters
    Overall_Color_Counter[edgecolor] += 1


# Returns the number of modules for a node
def get_modules_count_for_node(graphname, node):
    modules = graphname.node[node]["modules"]
    if modules:
        return modules
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
def get_connected_color_count_for_module(graphname, module, color):
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
def get_color_count_for_module(graphname, module):
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
def recolor_edges_for_module(graphname, module, oldcolor, newcolor):
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
                    set_edge_color(graphname, newcolor, mod, neighbor)

                    # Add the destination node to nodes_todo
                    modules_todo.append(neighbor)


def find_color_for_edge_without_tricky(graphname, module_a, module_b):
    if not module_is_already_colored(graphname, module_a):
        if not module_is_already_colored(graphname, module_b):
            set_edge_color(graphname, get_best_color_in(graphname, Assignable_Colors, module_a, module_b), module_a, module_b)
        else:
            # We have to take the color of module_b
            set_edge_color(graphname, graphname.node[module_b]["color"], module_a, module_b)

    else:
        # we have to take the color of module_a, lets see if this is a problem
        # and check if b is not colored, or we can use the color there
        color_of_module_a = graphname.node[module_a]["color"]
        if not module_is_already_colored(graphname, module_b):
            set_edge_color(graphname, color_of_module_a, module_a, module_b)

        else:
            # Now we have a problem if the colors are not by accident the same
            color_of_module_b = graphname.node[module_b]["color"]
            if color_of_module_a != color_of_module_b:
                # We are lucky, they are the same
                set_edge_color(graphname, color_of_module_a, module_a, module_b)

            else:
                # Tricky case
                return False
    return True


# Find the best color for an edge
def find_color_for_edge(graphname, module_a, module_b):
    if not find_color_for_edge_without_tricky(graphname, module_a, module_b):
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
        nr_of_occurrences_for_color_at_module_a = get_connected_color_count_for_module(graphname, module_a, color_of_module_a)
        nr_of_occurrences_for_color_at_module_b = get_connected_color_count_for_module(graphname, module_b, color_of_module_b)

        if nr_of_occurrences_for_color_at_module_a > nr_of_occurrences_for_color_at_module_b:
            winning_color = nr_of_occurrences_for_color_at_module_a
            losing_color = nr_of_occurrences_for_color_at_module_b
        else:
            winning_color = nr_of_occurrences_for_color_at_module_b
            losing_color = nr_of_occurrences_for_color_at_module_a

        # Recolor all other connected edges for both modules
        recolor_edges_for_module(graphname, module_a, losing_color, winning_color)
        recolor_edges_for_module(graphname, module_b, losing_color, winning_color)

        # Color the edge from node_a to node_b with this the best color available at node a
        set_edge_color(graphname, winning_color, module_a, module_b)


# Check if the coloring is valid (does ever node only use a number of colors = his modules and Are all edges colored?)
def graph_is_valid(graphname):
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
def show_graph(networkxgraph):
    pydotgraphname = pydot.Dot(graph_type='graph', layout=Graph_Layout)
    edges_done = set()
    for (A, B) in networkxgraph.edges():
        if (A, B) not in edges_done:
            edge_data = networkxgraph.edge[A][B]
            edge_weight = edge_data["weight"]
            if A in lan_nodes or B in lan_nodes:
                edge_style = "solid"
                edge_color = "black"
                edge_penwidth = 2
            else:
                edge_penwidth = str(Edge_Thickness/edge_weight)
                edge_color = edge_data["color"]
                edge_style = "dotted"
                if edge_color is None:
                    edge_color = "grey"
                else:
                    edge_color = colortable[edge_color]

            pydotgraphname.add_edge(pydot.Edge(str(A), str(B), style=edge_style, penwidth=edge_penwidth, color=edge_color))

            edges_done.add((A, B))
    pydotgraphname.write("caa.svg", format="svg")


#translate a lan_mac + interface nr to wlan_mac
def translate_lan_mac_to_wlan_mac(lanmac, interfacenr, active_radios_table):
    # Interfacenr is of the form "WLAN-ID"
    #look for the combination lanmac + interfacenr in the table active radios and return the wlan_mac for it
    results = [i[2] for i in active_radios_table if i[1] == lanmac and i[3] == interfacenr]
    if len(results) != 1:
        print "Error: Could not find lanmac and interfacenr for " + str(lanmac) + "," + str(interfacenr) + " in active_radios"
        exit(1)
    else:
        return results[0]


# Configuration
Number = 0                                              # Image-iterator for debugging
Edge_Thickness = 9.0                                    # Factor for edge thickness, smaller value => smaller edges
Graph_Layout = "dot"                                    # Graphlayout for graphviz (what style to use)(fdp,sfdp,dot,neato,twopi,circo)
mst_mode = "edge"                                       # This variable sets the mode for the MST creation:
                                                        # node = We expect a complete node to fail at a time (network still works, even if a whole node breaks)
                                                        # edge = We expect only a single edge to fail at a time (network still works, even if an edge breaks, less connetions though than "node")
                                                        # single = only calculate ordinary MST (no redundancy, one node or edge breakds => connectivity is gone, least number of connections)
Assignable_Colors = ["1", "3", "6", "11"]               # List of all channels/colors which can be used for assignment
colortable = dict()
colortable["1"] = "red"
colortable["3"] = "green"
colortable["6"] = "blue"
colortable["11"] = "orange"

Edges_Done = set()                                      # List of edges which have been visited (empty at beginning)
Overall_Color_Counter = collections_enhanced.Counter()  # This counts how often each color has been used overall, initially fill with 0
for color in Assignable_Colors:
    Overall_Color_Counter[color] = 0

# Getting Data from WLC per SNMP
wlc_address = "172.16.40.100"
snmp_community = "public"
snmp_session = netsnmp.Session(DestHost=wlc_address, Version=2, Community=snmp_community)
scan_results_ap_name = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.2'))
scan_results_ap_mac_hex = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.4'))
scan_results_ap_mac = [i.encode("hex") for i in scan_results_ap_mac_hex]
scan_results_seen_bssid_hex = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.120.1.1'))
scan_results_seen_bssid = [i.encode("hex") for i in scan_results_seen_bssid_hex]
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
active_radios_ap_lan_mac = [i.encode("hex") for i in active_radios_ap_lan_mac_hex]
active_radios_ap_bssid_mac_hex = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.6'))
active_radios_ap_bssid_mac = [i.encode("hex") for i in active_radios_ap_bssid_mac_hex]
active_radios_interface_nr = snmp_session.walk(netsnmp.VarList('.1.3.6.1.4.1.248.32.18.1.73.9.2.1.7'))  # 0=1, 1=2, ...
active_radios = zip(active_radios_ap_name, active_radios_ap_lan_mac, active_radios_ap_bssid_mac, active_radios_interface_nr)
scan_results_wlan_mac = [translate_lan_mac_to_wlan_mac(i[0], i[1], active_radios) for i in zip(scan_results_ap_mac, scan_results_interface_nr)]
scan_results = zip(scan_results_ap_name, scan_results_ap_mac, scan_results_seen_bssid, scan_results_channel, scan_results_signal_strengh, scan_results_wlan_mac)
wlan_modules = set(active_radios_ap_bssid_mac)
lan_nodes = set(active_radios_ap_lan_mac)
basic_connectivity_graph = nx.Graph()
# Generate node to interface edges
for ap_name, ap_lan_mac, ap_wlan_interface_mac, ap_interface_nr in active_radios:
    basic_connectivity_graph.add_edge(ap_lan_mac, ap_wlan_interface_mac)
    basic_connectivity_graph.edge[ap_lan_mac][ap_wlan_interface_mac]["weight"] = 1
    #initialize actually seen counters for wlan modules:
    actually_seen_colors = collections_enhanced.Counter()
    for color in Assignable_Colors:
        actually_seen_colors[color] = 0
    basic_connectivity_graph.node[ap_wlan_interface_mac]["seen_channels"] = actually_seen_colors
    basic_connectivity_graph.node[ap_wlan_interface_mac]["interface-nr"] = ap_interface_nr
    basic_connectivity_graph.node[ap_wlan_interface_mac]["module-of"] = ap_lan_mac
    basic_connectivity_graph.node[ap_lan_mac]["name"] = ap_name
    basic_connectivity_graph.node[ap_wlan_interface_mac]["color"] = None
    #initialize nr of modules for wlan module
    basic_connectivity_graph.node[ap_wlan_interface_mac]["modules"] = 1
    #initialize nr of modules for lan_mac
    basic_connectivity_graph.node[ap_lan_mac]["modules"] = len(basic_connectivity_graph.neighbors(ap_lan_mac))
    #initialize empty counter "used colors" for node
    used_colors = collections_enhanced.Counter()
    for color in Assignable_Colors:
        used_colors[color] = 0
    basic_connectivity_graph.node[ap_lan_mac]["used-colors"] = used_colors
# Add all possible links from scan-results-table (module to module and seen-channels)
for ap_name, ap_lan_mac, dest_wlan_mac, channel, signal_strength, ap_wlan_mac in scan_results:
    #check if we see one of our autowds aps or another wlan
    if dest_wlan_mac in active_radios_ap_bssid_mac:
        #its one of our connections in autowds
        basic_connectivity_graph.add_edge(ap_wlan_mac, dest_wlan_mac)

        # 1 + because the best edge has one (node to interfaces) a high signal-strength = good -> make inverse for MST-calculation
        # because lower values are better there
        basic_connectivity_graph.edge[ap_wlan_mac][dest_wlan_mac]["weight"] = 1 + 100.0 / int(signal_strength)

        # Initialize each edge with empty color
        basic_connectivity_graph.edge[ap_wlan_mac][dest_wlan_mac]["color"] = None
    else:
        #its not one of our connections => add to interference list of this wlan module-node
        # Only consider the channels we have in Assignable colors, since the others are useless
        if channel in Assignable_Colors:
            basic_connectivity_graph.node[ap_wlan_mac]["seen_channels"][channel] += 1

# Show basic Connectivity and channelquality
show_graph(basic_connectivity_graph)

# First phase: Calculate the Minimal Spanning Tree from the basic connectivity graph
mst_graph = calculate_survival_graph(basic_connectivity_graph)
show_graph(mst_graph)

# Second Phase: Find the best channels for every edge in the MST-Graph and assign them to the edges
nodelist = list()   # This is the list of nodes over which we iterate
nodelist.append("ece555ffd63a")  # Initially put only the gatewaynode in the nodelist (Could also be a different one)
#todo: automate the line above

# Go through all nodes (main loop)
for node in nodelist:
    neighbors = mst_graph.neighbors(node)
    for neighbor in neighbors:
        if (node, neighbor) not in Edges_Done:
            # We just want to color the module-edges and not
            # the edges between node and module, since they dont need a coloring
            if node in wlan_modules and neighbor in wlan_modules and not edge_has_color(mst_graph, node, neighbor):
                find_color_for_edge(mst_graph, node, neighbor)
            if not neighbor in nodelist:
                nodelist.append(neighbor)
            # Mark edge as done
            Edges_Done.add((node, neighbor))
            Edges_Done.add((neighbor, node))

# Show the finished graph
show_graph(mst_graph)

# Finally check the graph for validity
if not graph_is_valid(mst_graph):
    exit(1)
