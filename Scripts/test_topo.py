import networkx as nx
import tcca
import random
import webbrowser
import time
max_weight = 1000
g = nx.Graph()

for i in range(9):
    i = str(i)
    g.add_node(i, isModule=False)
    for j in range(2):
        j = str(j)
        module_name = i + "." + j
        g.add_node(module_name, isModule=True)
        g.add_edge(i, module_name)
        g.edge[i][module_name]["snr"] = max_weight

seen_links = {0: [0, 1, 3, 4],
              1: [0, 1, 2, 3, 4, 5],
              2: [1, 2, 4, 5],
              3: [0, 1, 3, 4, 6, 7],
              4: [0, 1, 2, 3, 4, 5, 6, 7, 8],
              5: [1, 2, 4, 5, 7, 8],
              6: [3, 4, 6, 7],
              7: [3, 4, 5, 6, 7, 8],
              8: [4, 5, 7, 8]}

for node_a in seen_links:
    for node_b in seen_links[node_a]:
        for i in range(2):
            i = str(i)
            for j in range(2):
                j = str(j)
                node_a = str(node_a)
                node_b = str(node_b)
                moda = node_a + "." + i
                modb = node_b + "." + j
                if moda == modb:
                    continue
                g.add_edge(moda, modb, snr=random.randint(30, 96))

tcca.write_json(g, "/home/kmanna/autowdsstatus/autowds-graph.json")
time.sleep(2)
webbrowser.open("file:///home/kmanna/autowdsstatus/autowds-graph.html")

mst_graph = tcca.calculate_st(g)
time.sleep(2)
tcca.write_json(mst_graph, "/home/kmanna/autowdsstatus/autowds-graph.json")
time.sleep(2)
webbrowser.open("file:///home/kmanna/autowdsstatus/autowds-graph.html")

robust_graph = tcca.calculate_survival_links(mst_graph, g)
time.sleep(2)
tcca.write_json(robust_graph, "/home/kmanna/autowdsstatus/autowds-graph.json")
time.sleep(2)
webbrowser.open("file:///home/kmanna/autowdsstatus/autowds-graph.html")

ca_mst_graph = tcca.calculate_ca(mst_graph, g, [1,6,11])
time.sleep(2)
tcca.write_json(ca_mst_graph, "/home/kmanna/autowdsstatus/autowds-graph.json")
time.sleep(2)
webbrowser.open("file:///home/kmanna/autowdsstatus/autowds-graph.html")

ca_robust_graph = tcca.calculate_ca(robust_graph, g, [1,6,11])
time.sleep(2)
tcca.write_json(ca_robust_graph, "/home/kmanna/autowdsstatus/autowds-graph.json")
time.sleep(2)
webbrowser.open("file:///home/kmanna/autowdsstatus/autowds-graph.html")
