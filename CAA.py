#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose This script colors a networkx graph (Lancom AutoWDS Channel assignment algorithm)

import networkx as nx
import collections
import random
import pydot

#Get here the 2-connected graph from the dijkstra algorithms:
Graph = nx.Graph()
#The following is just for debug, remove later
Graph.add_edge("A", "B")
Graph.add_edge("A", "C")
Graph.add_edge("A", "D")
Graph.add_edge("B", "E")
Graph.add_edge("C", "E")
Graph.add_edge("C", "F")
Graph.add_edge("D", "F")
Graph.add_edge("E", "G")
Graph.add_edge("F", "G")
Graph.add_node("A", modules=2)
Graph.add_node("B", modules=2)
Graph.add_node("C", modules=2)
Graph.add_node("D", modules=2)
Graph.add_node("E", modules=2)
Graph.add_node("F", modules=2)
Graph.add_node("G", modules=2)


#liste von kanten die bereits gefaebt wurden (Am Anfang leer)
edges_done = set()

#list of nodes to go
nodelist = list()

#Initially put one of the gatewaynode in the nodelist as the rootnode(could also be another node)
nodelist.append("A")

#how many times is every color used?
overall_color_usage = collections.Counter()

#list of all channels/colors which can be used for assignment
assignable_colors = ["red", "green", "blue"]


def get_least_used_elements_for_counter_dict(counterlist):
    minimal_colors = list()
    #get the least common element
    least_common_element = counterlist.most_common()[-1]
    least_common_occurence = least_common_element[1]
    for a, b in reversed(counterlist):
        if b == least_common_occurence:
            minimal_colors.append(a)
        else:
            break
    return minimal_colors


#Returns dictionary with entries (like color : nr of occurences of this color in neighborhood of node)
def get_least_used_colors_for_node(nodename):
    neighbors = Graph.neighbors(nodename)
    colorlist = list()
    counterlist = collections.Counter()
    for neighbor in neighbors:
        edgecolor = Graph.get_edge_data(nodename, neighbor)["color"]
        if edgecolor:
            #add color to list
            colorlist.add(edgecolor)
            counterlist[edgecolor] += 1
    return get_least_used_elements_for_counter_dict(counterlist)


#Returns dictionary with entries (like color : nr of occurences of this color in neighborhood of node_a and node_b)
def get_least_used_colors_for_nodes(node_a, node_b):
    colorlist = list()
    counterlist = collections.Counter()
    neighbors_of_a = Graph.neighbors(node_a)
    neighbors_of_b = Graph.neighbors(node_b)
    for neighbor in neighbors_of_a:
        edgecolor = Graph.get_edge_data(node_a, neighbor)["color"]
        if edgecolor:
            #add color to list
            colorlist.add(edgecolor)
            counterlist[edgecolor] += 1
    for neighbor in neighbors_of_b:
        # because we dont want to count the edge between node_a and node_b twice
        edgecolor = Graph.get_edge_data(node_b, neighbor)["color"]
        if edgecolor and not neighbor == node_a:
            #add color to list
            colorlist.add(edgecolor)
            counterlist[edgecolor] += 1
    return get_least_used_elements_for_counter_dict(counterlist)


#return list of colors which are used the least general
def get_least_used_colors_overall():
    return get_least_used_elements_for_counter_dict(overall_color_usage)


#Picks for a given list of colors the best color/channel
#Returns color
def get_best_color_in(colorset, node_a, node_b):
    if len(colorset) == 1:
        return colorset[0]
    else:
        # das hier ist auch noch total falsch, aber ich seh nicht warum:
        # Nutze die Farbe, welche bei A am wenigsten genutzt wurde
        least_used_colors_for_node_a = get_least_used_colors_for_node(node_a)
        if len(least_used_colors_for_node_a) == 1:
            return least_used_colors_for_node_a[0]
        else:
            least_used_colors_for_node_a_and_node_b = get_list_of_colors_for_nodes(node_a, node_b)
            if len(least_used_colors_for_node_a_and_node_b) == 1:
                return least_used_colors_for_node_a_and_node_b[0]
            else:
                least_used_colors_overall = get_least_used_colors_overall()
                if len(least_used_colors_overall) == 1:
                    return least_used_colors_overall[0]
                else:
                    #use random color for least used overall colors
                    return random.choice(least_used_colors_overall)


#set the color for a edge
def set_edge_color(edgecolor, node_a, node_b):
    Graph.add_edge(node_a, node_b, color=edgecolor)
    overall_color_usage[edgecolor] += 1
    edges_done.add(node_a, node_b)
    edges_done.add(node_b, node_a)
    #color in pydot for debugging, remove later
    pydotgraph.add_edge(pydot.Edge(node_a, node_b, color=edgecolor))


#returns the number of modules for a node
def get_modules_count_for_node(nodename):
    modules = Graph.node[nodename]["modules"]
    if modules:
        return modules


#returns the number of channels this node already uses
def get_number_of_colors_used_for_node(nodename):
    return Graph.degree(nodename)


#returns the number of modules for a node that are still free to use
#modules=number of wlan modules (probably 2 or 3 atm)
def modules_free_count(nodename):
    #free modules = num of modules of node minus num of channels already used
    return get_modules_count_for_node(nodename) - get_number_of_colors_used_for_node(nodename)


#returns the colors which two nodes already use
def get_colors_used_for_nodes(node_a, node_b):
    return [i for i in get_colors_used_for_node(node_a) or get_colors_used_for_node(node_b)]


#returns the colors which a node already uses
def get_colors_used_for_node(nodename):
    colors_used = set()
    neighbors = Graph.neighbors(nodename)
    for neighbor in neighbors:
        edgecolor = Graph.get_edge_data(nodename, neighbor)["color"]
        if edgecolor:
            #add color to list
            colors_used.add(edgecolor)
    return list(colors_used)


#returns a list of colors which are not used by the node
def get_colors_not_used_for_node(nodename):
    return [i for i in assignable_colors if i not in get_colors_used_for_node(nodename)]


#Color a edge
def color_edge(node_a, node_b):
    if modules_free_count(node_a) > 0:
        if modules_free_count(node_b) > 0:
            #Is there a color used by neither node_a or node_b?
            channellist = [i for i in get_colors_not_used_for_node(node_a) if i in get_colors_not_used_for_node(node_b)]
            if channellist:
                set_edge_color(get_best_color_in(channellist, node_a, node_b), node_a, node_b)
            else:
                #Kann ich eine Farbe nutzen, die bei einem von beiden noch nicht genutzt wurde?
                #ist dasselbe wie unten, ich versteh den fall nicht mehr => grafisch nachbessern
                channellist = [i for i in get_colors_used_for_nodes(node_a, node_b)]
                if channellist:
                    set_edge_color(get_best_color_in(channellist, node_a, node_b))
                else:
                    channellist = [i for i in get_colors_used_for_nodes(node_a, node_b)]
                    if channellist:
                        set_edge_color(get_best_color_in(channellist, node_a, node_b))
#       else:
#           Verwende eine von B bereits genutzten Farben, die bei B noch weniger genutzt wurde,
#           Alternativ: Eine Farbe die in der Umgebung von A und B am wenigsten genutzt wurde
#           Alternativ: Eine Farbe die Global am wenigsten genutzt wurde
#           Alternativ: eine nicht zuletzt gewaehlt
#           #Dieser Fall funktioniert, da ich ja bei A noch freie module habe
#   else:
#       Habe ich noch Module bei B frei?
#           Ja:
#               Verwende eine von A bereits genutzten Farben, die bei A noch weniger genutzt wurde,
#               Alternativ: Eine Farbe die in der Umgebung von A und B am wenigsten genutzt wurde
#               Alternativ: Eine Farbe die Global am wenigsten genutzt wurde
#               Alternativ: eine nicht zuletzt gewaehlt
#               #Dieser Fall funktioniert, da ich ja bei B noch freie module habe
#           Nein:
#               #Ich habe also gar keine module mehr frei
#               Gibt es eine Schnittmenge der Farben, die A und B bereits nutzen?
#                   Ja:
#                       Nutze eine Farbe davon, die bei A am wenigsten genutzt wurde
#                       Alternativ: ...
#                   Nein:
#                       #bad case
#                       #loesung von hycint-mcr2
#                       nimmt von allen hier verwendeten farben die, welche die am kuerzesten zusammenhaengende strecke hat (incl einem farbwechsel) am wenigsten auftritt / verlaengerung) und ersetze sie mir einer von den bereits verwendeten

#convert data to paydot for drawing
pydotgraph = pydot.Dot(graph_type='graph', layout="fdp")
#transform from networkx to pydot
for (A, B) in Graph.edges():
    pydotgraph.add_edge(pydot.Edge(A, B))
pydotgraph.write("caa.svg", format="svg")

#Hauptschleife:
for node in nodelist:
    neighbors = Graph.neighbors(node)
    for neighbor in neighbors:
        if (node, neighbor) not in edges_done:
            color_edge(node, neighbor)
            nodelist.append(neighbor)
            pydotgraph.write("caa.svg", format="svg")
