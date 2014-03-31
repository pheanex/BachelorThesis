#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose This script colors a networkx graph (Lancom AutoWDS Channel assignment algorithm)

import networkx as nx
import collections
import random
import pydot

#imageiterator, for debugging remove later
number = 0

#Get here the 2-connected graph from the dijkstra algorithms:
Graph = nx.fast_gnp_random_graph(25, 0.5)
for node in Graph.nodes():
    Graph.node[node]["modules"] = 2

#set random weights on edges for mst
for (a,b) in Graph.edges():
    Graph[a][b]["weight"] = random.randrange(1,20)

#The following is just for debug, remove later
#Graph.add_edge("A", "B")
#Graph.add_edge("A", "C")
#Graph.add_edge("A", "D")
#Graph.add_edge("B", "E")
#Graph.add_edge("C", "E")
#Graph.add_edge("C", "F")
#Graph.add_edge("D", "F")
#Graph.add_edge("E", "G")
#Graph.add_edge("F", "G")
#Graph.add_node("A", modules=2)
#Graph.add_node("B", modules=2)
#Graph.add_node("C", modules=2)
#Graph.add_node("D", modules=2)
#Graph.add_node("E", modules=2)
#Graph.add_node("F", modules=2)
#Graph.add_node("G", modules=2)


#liste von kanten die bereits gefaebt wurden (Am Anfang leer)
edges_done = set()

#list of nodes to go
nodelist = list()

#Initially put one of the gatewaynode in the nodelist as the rootnode(could also be another node)
nodelist.append(0)

#list of all channels/colors which can be used for assignment
assignable_colors = ["red", "green", "blue"]

#how many times is every color used? initially fill it with 0 for all colors
overall_color_usage = collections.Counter()
for color in assignable_colors:
    overall_color_usage[color] = 0


# counterlist = dictionary with colors and their number of occurences
# allowed_colors = list to pick colors from (because we might not be allowed to use all in a certain situation)
# returns a list with elements that are in the allowed_colors list and are least commonly used
def get_least_used_elements_for_counter_dict(counterlist, allowed_colors):
    least_used_elements = list()

    # create new counter with only elements in it that are also in allowed_colors
    restricted_counterlist = collections.Counter()

    #create new counterlist with elements contained in both counterlist and allowed_colors
    for element in counterlist:
        if element in allowed_colors:
            restricted_counterlist[element] = counterlist[element]

    #get the least common element (the rightest, because its a sorted list)
    least_common_element = restricted_counterlist.most_common()[-1]
    nr_of_used_times_for_least_element = least_common_element[1]
    #find all other elements that are used the same number of times like the least
    for element in restricted_counterlist.keys():
        if restricted_counterlist[element] == nr_of_used_times_for_least_element:
            least_used_elements.append(element)
    return least_used_elements


# Returns dictionary with entries (like color : nr of occurences of this color in neighborhood of node)
# for a given node and allowed list of colors
def get_least_used_colors_for_node(nodename, allowed_colors):
    neighbors = Graph.neighbors(nodename)
    color_counter = collections.Counter()

    #initially set all colors used to 0
    for color in assignable_colors and allowed_colors:
        color_counter[color] = 0

    for neighbor in neighbors:
        edge = Graph.get_edge_data(nodename, neighbor)
        if edge and "color" in edge.keys():
            edgecolor = edge["color"]
            if edgecolor:
                color_counter[edgecolor] += 1
    return get_least_used_elements_for_counter_dict(color_counter, allowed_colors)


# Returns dictionary with entries (like color : nr of occurences of this color in neighborhood of node_a and node_b)
# for two nodes and a list of allowed colors
def get_least_used_colors_for_nodes(node_a, node_b, allowed_colors):
    color_counter = collections.Counter()

    #initially set all colors used to 0
    for color in assignable_colors and allowed_colors:
        color_counter[color] = 0

    neighbors_of_a = Graph.neighbors(node_a)
    neighbors_of_b = Graph.neighbors(node_b)

    for neighbor in neighbors_of_a:
        edge = Graph.get_edge_data(node_a, neighbor)
        if edge and "color" in edge.keys():
            edgecolor = edge["color"]
            if edgecolor:
                color_counter[edgecolor] += 1

    for neighbor in neighbors_of_b:
        edge = Graph.get_edge_data(node_b, neighbor)
        if edge and "color" in edge.keys():
            edgecolor = edge["color"]
            # because we dont want to count the edge between node_a and node_b twice
            if edgecolor and not neighbor == node_a:
                color_counter[edgecolor] += 1

    return get_least_used_elements_for_counter_dict(color_counter, allowed_colors)


#calculates for a given graph the survival graph and returns it
def calculate_survival_graph(graphname):
    MST_Graph = nx.minimum_spanning_tree(graphname).copy()
    for node in graphname.nodes():

        # Create new temp Graph to work with
        Work_Graph = graphname.copy()

        #Remove the node
        Work_Graph.remove_node(node)

        #Now calculate mst on this new graph
        MST_Work_Graph = nx.minimum_spanning_tree(Work_Graph)

        #Add the now necessary edges to the resulting graph
        for From, To, Attributes in MST_Work_Graph.edges(data=True):
            MST_Graph.add_edge(From, To, weight=Attributes['weight'])
    return MST_Graph

#return list of colors which are used the least over all edges in the graph and are in the allowed_colors list
def get_least_used_colors_overall(allowed_colors):
    least_used_colors = get_least_used_elements_for_counter_dict(overall_color_usage, allowed_colors)
    return least_used_colors


# colorset = list of colors we can chose from
# caluclates the optimal color from this set
# Returns the color to use
def get_best_color_in(colorset, node_a, node_b):
    #make this faster if we can only chose from 1
    if len(colorset) == 1:
        return colorset[0]
    else:
        # Nutze die Farben, welche im colorset sind und bei A am wenigsten genutzt wurde
        least_used_colors_for_node_a = get_least_used_colors_for_node(node_a, colorset)
        #speed up things if there is only one color to chose from
        if len(least_used_colors_for_node_a) == 1:
            return least_used_colors_for_node_a[0]
        else:
            #if it is a tie, then also look at the colors from node b
            least_used_colors_for_node_a_and_node_b = get_least_used_colors_for_nodes(node_a, node_b, colorset)
            #speed up things if there is only one color to chose from
            if len(least_used_colors_for_node_a_and_node_b) == 1:
                return least_used_colors_for_node_a_and_node_b[0]
            else:
                #if there is still a tie, look also at the overall color assignments and take the rarest used one
                least_used_colors_overall = get_least_used_colors_overall(colorset)
                #speed up things if there is only one color to chose from
                if len(least_used_colors_overall) == 1:
                    return least_used_colors_overall[0]
                else:
                    #All have been ties so far, now take one color at random
                    random_color = random.choice(colorset)
                    return random_color


#set the color for a edge
def set_edge_color(edgecolor, node_a, node_b):
    edge_data = Graph.get_edge_data(node_a, node_b)
    edge_weight = edge_data["weight"]

    #color the edge
    Graph[node_a][node_b]["color"] = edgecolor

    #increase the overall colorcounters
    overall_color_usage[edgecolor] += 1

    #mark edge as done
    edges_done.add((node_a, node_b))
    edges_done.add((node_b, node_a))

    #color in pydot for debugging, remove later
    edge = pydotgraph.get_edge(str(node_a), str(node_b))[0]
    edge.set_color(edgecolor)
    penwidth = str(6.0/edge_weight)
    edge.set_penwidth(penwidth)
    edge.set_style("solid")


#returns the number of modules for a node
def get_modules_count_for_node(nodename):
    modules = Graph.node[nodename]["modules"]
    if modules:
        return modules


#returns set of colors for all edges of a node
def get_colors_used_for_node(nodename):
    colorset = set()
    neighbors = Graph.neighbors(nodename)
    for neighbor in neighbors:
        edge = Graph.get_edge_data(nodename, neighbor)
        if edge and "color" in edge.keys():
            edgecolor = edge["color"]
            colorset.add(edgecolor)
    return list(colorset)

#returns the number of the (distinct) colors this node already uses
def get_number_of_colors_used_for_node(nodename):
    colors_used = get_colors_used_for_node(nodename)
    return len(colors_used)


#returns the number of modules for a node that are still free to use
#modules=number of wlan modules (probably 2 or 3 atm)
def modules_free_count(nodename):
    #free modules = num of modules of node minus num of channels already used
    return get_modules_count_for_node(nodename) - get_number_of_colors_used_for_node(nodename)


#returns list of the colors which the two nodes already use for their edges
def get_colors_used_for_nodes(node_a, node_b):
    colors_used_by_node_a = get_colors_used_for_node(node_a)
    colors_used_by_node_b = get_colors_used_for_node(node_b)
    colors_used_by_either_node_a_or_node_b = list(set(colors_used_by_node_a + colors_used_by_node_b))
    return colors_used_by_either_node_a_or_node_b


#returns a list of colors which are not used by the node
def get_colors_not_used_for_node(nodename):
    colors_used_by_node = get_colors_used_for_node(nodename)
    colors_not_used = [i for i in assignable_colors if i not in colors_used_by_node]
    return colors_not_used



# Returns a dictionary with connected colorusage for the node provided
def get_color_count_for_node(nodename):
    #initialize color counter
    color_counter = collections.Counter()
    colors_of_nodename = get_colors_used_for_node(nodename)
    for color in colors_of_nodename:
        color_counter[color] = 0

    for color in colors_of_nodename:
        edges_done = set()
        nodes_togo = list()

        #add initial node to be able to start from there
        nodes_togo.append(nodename)

        for node in nodes_togo:
            neighbors = Graph.neighbors(node)
            for neighbor in neighbors:
                edge = Graph.get_edge_data(node, neighbor)
                if edge and "color" in edge.keys() and edge["color"] == color and (node, neighbor) not in edges_done:
                    #add edge to done-list
                    edges_done.add((node, neighbor))
                    edges_done.add((neighbor, node))

                    #increase counter
                    color_counter[color] += 1

                    #add node togo if not already visited
                    if neighbor not in nodes_togo:
                        nodes_togo.append(neighbor)
    return color_counter


# Recolors for a given node all connected edges
def recolor_edges_for_node(nodename, oldcolor, newcolor):
    edges_done = set()
    nodes_togo = list()

    #add initial node to be able to start from there
    nodes_togo.append(nodename)

    for node in nodes_togo:
        neighbors = Graph.neighbors(node)
        for neighbor in neighbors:
            edge = Graph.get_edge_data(node, neighbor)
            if edge and "color" in edge.keys() and edge["color"] == oldcolor:
                #recolor that edge
                set_edge_color(newcolor, node, neighbor)

                #add the destination node to nodes_togo
                nodes_togo.append(neighbor)

#transform networkxgraph to pydot graph
def transform_graph(networkxgraph):
    for (A, B) in networkxgraph.edges():
        edge_data = networkxgraph.get_edge_data(A, B)
        edge_weight = edge_data["weight"]
        penwidth = str(6.0/edge_weight)
        pydotgraph.add_edge(pydot.Edge(str(A), str(B), style="dotted", penwidth=penwidth))


#writes the pydotgraph
def write_image():
    global number
    pydotgraph.write("caa_step_" + str(number) + ".svg", format="svg")
    number += 1

# Find the best color for an edge
def find_color_for_edge(node_a, node_b):
    if modules_free_count(node_a) > 0:
        if modules_free_count(node_b) > 0:
            #Is there a color used by neither node_a nor node_b?
            colors_not_used_by_node_a = get_colors_not_used_for_node(node_a)
            colors_not_used_by_node_b = get_colors_not_used_for_node(node_b)
            colors_unused_by_both = [i for i in colors_not_used_by_node_a if i in colors_not_used_by_node_b]
            if colors_unused_by_both:
                best_color = get_best_color_in(colors_unused_by_both, node_a, node_b)
                set_edge_color(best_color, node_a, node_b)
            else:
                # Kann ich eine Farbe nutzen, die zumindest bei einem von beiden noch nicht genutzt wurde?
                colors_not_used_by_node_a = get_colors_not_used_for_node(node_a)
                colors_not_used_by_node_b = get_colors_not_used_for_node(node_b)
                colors_not_used_by_either_node_a_or_node_b = list(set(colors_not_used_by_node_a + colors_not_used_by_node_b))
                if colors_not_used_by_either_node_a_or_node_b:
                    best_color = get_best_color_in(colors_not_used_by_either_node_a_or_node_b, node_a, node_b)
                    set_edge_color(best_color, node_a, node_b)
                else:
                    #es gibt keine neue farben mehr => muss eine der existierenden gewaelht werden (die node a und node b verwenden)
                    colors_used_by_both = get_colors_used_for_nodes(node_a, node_b)
                    if colors_used_by_both:
                        best_color = get_best_color_in(colors_used_by_both, node_a, node_b)
                        set_edge_color(best_color, node_a, node_b)
                    else:
                        # Verwende eine von B bereits genutzten Farben, die bei B noch weniger genutzt wurd
                        # Dieser Fall funktioniert, da ich ja bei A noch freie module habe
                        colors_used_by_node_b = get_colors_used_for_node(node_b)
                        best_color = get_best_color_in(colors_used_by_node_b, node_a, node_b)
                        set_edge_color(best_color, node_a, node_b)

    else:
        if modules_free_count(node_b) > 0:
            # Verwende eine von A bereits genutzten Farben, die bei A noch weniger genutzt wurde
            # Dieser Fall funktioniert, da ich ja bei B noch freie module habe
            colors_used_for_node_a = get_colors_used_for_node(node_a)
            best_color = get_best_color_in(colors_used_for_node_a, node_a, node_b)
            set_edge_color(best_color, node_a, node_b)
        else:
            #Ich habe also gar keine module mehr frei
            #Gibt es eine Schnittmenge der Farben, die A und B bereits nutzen?
            colors_used_by_node_a = get_colors_used_for_node(node_a)
            colors_used_by_node_b = get_colors_used_for_node(node_b)
            colors_used_by_both = [i for i in colors_used_by_node_a if i in colors_used_by_node_b]
            if colors_used_by_both:
                #Waehle die beste daraus
                best_color = get_best_color_in(colors_used_by_both, node_a, node_b)
                set_edge_color(best_color, node_a, node_b)
            else:
                # tricky case, loesung von hycint-mcr2
                # nimmt von allen hier verwendeten farben die, welche zusammenhaengend bei node a und node b am wenigsten vorkommt
                # (wir koennen diese dann am einfachsten ersetzen, ohne viel schaden anzurichten)
                # Ersetze diese mit einer von den bereits verwendeten

                #debug remove later:
                print("tricky case")

                #get the colorcounts for both nodes and combine them
                combined_color_counter = get_color_count_for_node(node_a) + get_color_count_for_node(node_b)

                # Find the color which is the least common
                least_common_color = combined_color_counter.most_common()[-1][0]

                # Find the color we will use for this dilemma
                colors_used_by_node_a = get_colors_used_for_node(node_a)
                colors_used_by_node_b = get_colors_used_for_node(node_b)
                colors_used_by_either_node_a_or_node_b = list(set(colors_used_by_node_a + colors_used_by_node_b))
                best_color = get_best_color_in(colors_used_by_either_node_a_or_node_b, node_a, node_b)

                # recolor all other connected edges for both nodes
                recolor_edges_for_node(node_a, least_common_color, best_color)
                recolor_edges_for_node(node_b, least_common_color, best_color)

                # color the edge from node_a to node_b with this color
                set_edge_color(best_color, node_a, node_b)


#create pydotgraph (so we can draw it better)
pydotgraph = pydot.Dot(graph_type='graph', layout="fdp")

#Show Connectivity
transform_graph(Graph)
write_image()

#Minimal Spanning Tree
pydotgraph = pydot.Dot(graph_type='graph', layout="fdp")
mst_graph = calculate_survival_graph(Graph)
transform_graph(mst_graph)
write_image()

#Channel assignment
for node in nodelist:
    neighbors = mst_graph.neighbors(node)
    for neighbor in neighbors:
        if (node, neighbor) not in edges_done:
            find_color_for_edge(node, neighbor)
            nodelist.append(neighbor)
            write_image()


#now add the nodes we didnt use due to mst optimization
#for (a, b) in Graph.edges():
#    if Graph.has_edge(a, b) and not mst_graph.has_edge(a, b):
#        edge_data = Graph.get_edge_data(a, b)
#        edge_weight = edge_data["weight"]
#        penwidth = str(6.0/edge_weight)
#        pydotgraph.add_edge(pydot.Edge(str(a), str(b), style="dotted", color="grey60", penwidth=penwidth))
#        write_image()

#Todo: check if the coloring is valid (does ever node only use a number of colors = his modules and Are all edges colored?)
