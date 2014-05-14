#!/usr/bin/python
#author:	Konstantin Manna @ Lancom Systems
#date:		03.03.2014
#purpose:	Finds the minimum spanning tree for a graph with survival paths (backup routes)

import mst
import networkx as nx
import matplotlib.pyplot as plt

#Create the graph
Graph = nx.Graph()

#Add nodes
Graph.add_node("A")
Graph.add_node("B")
Graph.add_node("C")
Graph.add_node("D")
Graph.add_node("E")
Graph.add_node("F")

#Add edges with weight
Graph.add_edge("A", "B", weight=12)
Graph.add_edge("A", "C", weight=4)
Graph.add_edge("A", "D", weight=5)
Graph.add_edge("A", "E", weight=1)
Graph.add_edge("A", "F", weight=8)
Graph.add_edge("B", "C", weight=5)
Graph.add_edge("B", "D", weight=2)
Graph.add_edge("B", "E", weight=3)
Graph.add_edge("B", "F", weight=4)
#Graph.add_edge("C", "D", weight=4)
Graph.add_edge("C", "E", weight=2)
Graph.add_edge("C", "F", weight=13)
Graph.add_edge("D", "E", weight=14)
Graph.add_edge("D", "F", weight=15)
Graph.add_edge("E", "F", weight=16)

#Calculate MST (This will also be the resulting graph)
MST_Graph = nx.minimum_spanning_tree(Graph).copy()

#Now calculate backup mst in case of node failure (survival path)
for node in Graph.nodes():

	#Create new temp Graph to work with
	Work_Graph = Graph.copy()

	#Remove the node
	Work_Graph.remove_node(node)

	#Now calculate mst on this new graph
	MST_Work_Graph = nx.minimum_spanning_tree(Work_Graph)

	#Add the now necessary edges to the resulting graph
	for From,To,Attributes in MST_Work_Graph.edges(data=True):
			MST_Graph.add_edge(From, To, weight=Attributes['weight'])

#color edges
#edgecolors=list()
#for From,To in Graph.edges():
#	if (From,To) in MST_Graph.edges():
#		edgecolors.append('0.89')
#	else:
#		edgecolors.append('0.01')

plt.figure(1)
#nx.draw_networkx(Graph, nx.fruchterman_reingold_layout(Graph),edge_color=edgecolors)
#plt.figure(2)
nx.draw(MST_Graph)
plt.show()
