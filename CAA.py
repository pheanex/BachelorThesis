#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose This script colors a networkx graph (Lancom AutoWDS Channel assignment algorithm)

import networkx as nx
import collections
import random
import pydot

# Image-iterator for debugging
#Number = 0

# Factor for edge thickness, smaller value => smaller edges
Edge_Thickness = 9.0

# Graphlayout for graphviz (what style to use)(fdp,sfdp,dot,neato,twopi,circo)
Graph_Layout = "fdp"

# Generate a random graph
# For debugging purpose
RandomGraph = nx.fast_gnp_random_graph(30, 0.2)
for node in RandomGraph.nodes():
    RandomGraph.node[node]["modules"] = 2

# Set random weights on edges for mst
for (a,b) in RandomGraph.edges():
    RandomGraph[a][b]["weight"] = random.randrange(1, 20)

# List of edges which have been visited (empty at beginning)
Edges_Done = set()

# List of all channels/colors which can be used for assignment
Assignable_Colors = ["red", "green", "blue", "orange"]

# How often is each color used?
# Initially fill it with 0 for all colors
Overall_Color_Counter = collections.Counter()
for color in Assignable_Colors:
    Overall_Color_Counter[color] = 0

# counterlist = dictionary with colors and their number of occurences
# allowed_colors = list to pick colors from (because we might not be allowed to use all in a certain situation)
# Returns a list with elements that are in the allowed_colors list and are least commonly used
def get_least_used_elements_for_counter_dict(counterlist, allowed_colors):
    least_used_elements = list()

    # Create new restricted counterlist with only those elements in it, which are also in allowed_colors
    restricted_counterlist = collections.Counter()
    for element in counterlist:
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
        edge = graphname.get_edge_data(node_a, neighbor)
        if edge and "color" in edge.keys():
            edgecolor = edge["color"]
            if edgecolor:
                color_counter[edgecolor] += 1

    for neighbor in neighbors_of_b:
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
    for node in graphname.nodes():

        # Create new temp Graph to work with
        Work_Graph = graphname.copy()

        # Remove the node
        Work_Graph.remove_node(node)

        # Now calculate the mst on this new graph
        MST_Work_Graph = nx.minimum_spanning_tree(Work_Graph)

        # Add the now necessary edges to the resulting graph
        for From, To, Attributes in MST_Work_Graph.edges(data=True):
            MST_Graph.add_edge(From, To, weight=Attributes['weight'])

    return MST_Graph


# Returns list of colors which are used the least over all edges in the graph and are in the allowed_colors list
def get_least_used_colors_overall(allowed_colors):
    least_used_colors = get_least_used_elements_for_counter_dict(Overall_Color_Counter, allowed_colors)
    return least_used_colors


# colorset = list of colors we can chose from
# caluclates the optimal color from this set
# Returns the color to use
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
    print(str(node_a) + "," + str(node_b) + "=" + str(edgecolor))
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
    edge.set_color(edgecolor)
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


# Returns list of the colors which the two nodes already use for their edges
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
            edge = graphname.get_edge_data(node, neighbor)
            if edge and "color" in edge.keys() and edge["color"] == oldcolor:
                # Recolor that edge
                set_edge_color(graphname, newcolor, node, neighbor)

                # Add the destination node to nodes_todo
                nodes_todo.append(neighbor)

                # Adjust overall_color_counter
                Overall_Color_Counter[oldcolor] -= 1
                Overall_Color_Counter[newcolor] += 1


# Find the best color for an edge
def find_color_for_edge(graphname, node_a, node_b):
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
                colors_not_used_by_node_a = get_colors_not_used_for_node(graphname, node_a)
                colors_not_used_by_node_b = get_colors_not_used_for_node(graphname, node_b)
                colors_not_used_by_either_node_a_or_node_b = list(set(colors_not_used_by_node_a + colors_not_used_by_node_b))
                if colors_not_used_by_either_node_a_or_node_b:
                    best_color = get_best_color_in(graphname, colors_not_used_by_either_node_a_or_node_b, node_a, node_b)
                    set_edge_color(graphname, best_color, node_a, node_b)
                else:
                    # There are no new colors anymore, pick the best one in the already used ones by the nodes
                    colors_used_by_both = get_colors_used_for_nodes(graphname, node_a, node_b)
                    if colors_used_by_both:
                        best_color = get_best_color_in(graphname, colors_used_by_both, node_a, node_b)
                        set_edge_color(graphname, best_color, node_a, node_b)
                    else:
                        # Use a color which is already used by B, which is used less there
                        # This works, since we still have free modules at A
                        colors_used_by_node_b = get_colors_used_for_node(graphname, node_b)
                        best_color = get_best_color_in(graphname, colors_used_by_node_b, node_a, node_b)
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
                # Meaning we take all colors from both nodes A and B, in order to find the best in this set
                colors_used_by_either_node_a_or_node_b = list(set(colors_used_by_node_a + colors_used_by_node_b))

                # Remove the least common color from this set, because then this color would always be cosen,
                # because of its rare usage
                if least_common_color in colors_used_by_either_node_a_or_node_b: colors_used_by_either_node_a_or_node_b.remove(least_common_color)
                best_color = get_best_color_in(graphname, colors_used_by_either_node_a_or_node_b, node_a, node_b)

                # Recolor all other connected edges for both nodes
                recolor_edges_for_node(graphname, node_a, least_common_color, best_color)
                recolor_edges_for_node(graphname, node_b, least_common_color, best_color)

                # Color the edge from node_a to node_b with this color
                set_edge_color(graphname, best_color, node_a, node_b)


# Check if the coloring is valid (does ever node only use a number of colors = his modules and Are all edges colored?)
def graph_is_valid(graphname):
    print("Checking the graph for validity")

    # First check if every edge has a color
    for edge in graphname.edges():
        if not edge:
            print(edge + " not valid")
            print("Graph is NOT valid")
            return
        else:
            if not graphname[edge[0]][edge[1]]["color"]:
                print("Edge has no color: " + str(edge[0]) + "<->" + str(edge[1]))
                print("Graph is NOT valid")
                return

    # Now check if every node has only so many attached colors/channels as the number of modules it has
    for node in graphname.nodes():
        color_set = set()
        nr_of_modules = graphname.node[node]["modules"]
        for neighbor in graphname.neighbors(node):
            color = graphname.edge[node][neighbor]["color"]
            color_set.add(color)
        if len(color_set) > nr_of_modules:
            print("Node " + str(node) + " has more colors attached than it has modules:" + str(len(color_set)) + " > " + str(nr_of_modules) + ")")
            print color_set
            print("Graph is NOT valid")
            return

    print("Graph is valid")


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


# Create pydotgraph (so we can draw it better)
pydotgraph = pydot.Dot(graph_type='graph', layout=Graph_Layout)

# Show basic Connectivity and channelquality
transform_graph(RandomGraph)
write_image()

# Calculate the Minimal Spanning Tree from the basic connectivity graph
del pydotgraph
pydotgraph = pydot.Dot(graph_type='graph', layout=Graph_Layout)
mst_graph = calculate_survival_graph(RandomGraph)
transform_graph(mst_graph)
write_image()

# This is the list of nodes over which we iterate
nodelist = list()

# Initially put only the gatewaynode in the nodelist (Could also be a different one)
nodelist.append(0)

# Find the best channels for every edge in the MST-Graph and assign them to the edges
for node in nodelist:
    neighbors = mst_graph.neighbors(node)
    for neighbor in neighbors:
        if (node, neighbor) not in Edges_Done:
            find_color_for_edge(mst_graph, node, neighbor)
            nodelist.append(neighbor)
            write_image()

# Finally check the graph for validity
graph_is_valid(mst_graph)
