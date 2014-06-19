#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose   Gets status-data from wlc and parses it to a json script
#           which can be later visualized by a javascript

import testcore.control.ssh
import os
import sys
import json

if len(sys.argv) < 3:
    print("Usage: python AutoWDSstatus.py <wlc-address> <wlc-username> <wlc_password>")
    exit(1)

wlc_address = sys.argv[1]
wlc_username = sys.argv[2]
wlc_password = sys.argv[3]


# Returns list of lists with tabledata from wlc for a given tablename, else empty table
def get_table_data(tablename, hostname, username, password):
    connection = testcore.control.ssh.SSH(host=hostname, username=username, password=password)
    return connection.runquery_table(tablename)


# Check if wlc is up
def wlc_is_up(hostname):
    if not os.system("ping -c 1 " + hostname + " > /dev/null") == 0:
        print(hostname + " is down!")
        return False
    else:
        return True

if not wlc_is_up(wlc_address):
    exit(1)

Active_Radios = get_table_data("/status/wlan-management/ap-status/active-radios", wlc_address, wlc_username, wlc_password)
Accesspoints = get_table_data("/Status/WLAN-Management/AP-Configuration/Accesspoints/", wlc_address, wlc_username, wlc_password)
Intra_Wlan_Discovery = get_table_data("/status/wlan-management/intra-wlan-discovery", wlc_address, wlc_username, wlc_password)
Autowds_Profile = get_table_data("/status/wlan-management/ap-configuration/autowds-profile/", wlc_address, wlc_username, wlc_password)
Autowds_topology = get_table_data("/status/wlan-management/ap-configuration/autowds-topology", wlc_address, wlc_username, wlc_password)
Autowds_auto_topology = get_table_data("/status/wlan-management/ap-configuration/autowds-auto-topology", wlc_address, wlc_username, wlc_password)

devices = set()
modules = set()
# Aufbau: device[lan_mac][ifc_id][wlan_mac] (Dient als lookuptable/dict)
device_modules = dict()
nodes = dict()
links = dict()

# Fill nodes from active radios
for line in Active_Radios:
    devices.add(line[0])
    modules.add(line[5])
    if not line[0] in device_modules.keys():
        device_modules[line[0]] = dict()

    if line[1] == '0':
        device_modules[line[0]][0] = line[5]
    else:
        device_modules[line[0]][1] = line[5]

    if not line[0] in nodes:
        d = dict()
        d["label"] = line[3]
        d["type"] = "AP"
        d["channel"] = ""
        d["mac"] = line[0]
        d["connectiontype"] = line[27]
        nodes[line[0]] = d

    if not line[5] in nodes:
        d = dict()
        d["label"] = "WLAN-" + str(int(line[1]) + 1)
        d["type"] = "IFC"
        d["id"] = int(line[1])
        d["mac"] = line[5]
        d["connectiontype"] = line[27]
        nodes[line[5]] = d


# Fill nodes channel data from accespoints
for line in Accesspoints:
    if not line[0] in device_modules.keys():
        continue
    wlan_mac_ifc0 = device_modules[line[0]][0]
    wlan_mac_ifc1 = device_modules[line[0]][1]
    wlan_channel_ifc0 = line[12]
    wlan_channel_ifc1 = line[17]
    nodes[wlan_mac_ifc0]["channel"] = wlan_channel_ifc0
    nodes[wlan_mac_ifc1]["channel"] = wlan_channel_ifc1

# Fill links
modus = Autowds_Profile[0][6]
Autowds_table = []
if modus == "Automatic":
    # Consider only data from Autowds_auto_topology
    Autowds_table = Autowds_auto_topology
elif modus == "Manual":
    # Consider only data from Autowds_topology
    Autowds_table = Autowds_topology
else:
    print("Modus is neither Automatic nor Manual => probably Semi -> Don't know what to do.")
    exit(1)

# Go Through autowds-connections
source_target = set()
for line in Autowds_table:
    if line[4] not in nodes:
        # Node is in autowds_(auto)_topology but not in nodes => would cause errors
        continue
    links[line[4]] = dict()
    links[line[4]][line[7]] = dict()
    links[line[4]][line[7]]["state"] = line[15]
    links[line[4]][line[7]]["connectiontype"] = "real"
    links[line[4]][line[7]]["sourcemac"] = line[4]
    links[line[4]][line[7]]["targetmac"] = line[7]
    links[line[4]][line[7]]["sourcestrength"] = ""
    links[line[4]][line[7]]["sourcechannel"] = ""
    links[line[4]][line[7]]["sourceage"] = ""
    links[line[4]][line[7]]["targetstrength"] = ""
    links[line[4]][line[7]]["targetchannel"] = ""
    links[line[4]][line[7]]["targetage"] = ""
    #links[line[4]][line[7]]["channel"] = ""

    source_target.add((line[4], line[7]))

for line in Intra_Wlan_Discovery:
    if (line[0], line[1]) in source_target:
        links[line[0]][line[1]]["sourcestrength"] = line[3]
        links[line[0]][line[1]]["sourcechannel"] = line[2]
        links[line[0]][line[1]]["sourceage"] = line[5]
    elif (line[1], line[0]) in source_target:
        links[line[1]][line[0]]["targetstrength"] = line[3]
        links[line[1]][line[0]]["targetchannel"] = line[2]
        links[line[1]][line[0]]["targetage"] = line[5]
    else:
        # Ignore seen connections for nodes which are not in active radios
        if not (line[0] in nodes and line[1] in nodes):
            continue
        source_target.add((line[0], line[1]))
        if not line[0] in links:
            links[line[0]] = dict()
        links[line[0]][line[1]] = dict()
        links[line[0]][line[1]]["connectiontype"] = "seen"
        links[line[0]][line[1]]["sourcemac"] = line[0]
        links[line[0]][line[1]]["targetmac"] = line[1]
        links[line[0]][line[1]]["sourcestrength"] = line[3]
        links[line[0]][line[1]]["sourcechannel"] = line[2]
        links[line[0]][line[1]]["sourceage"] = line[5]
        links[line[0]][line[1]]["state"] = "possible"
        # preset targetstr to empty string since it may get never set (since the aps dont have to see each other necessarily)
        links[line[0]][line[1]]["targetstrength"] = ""
        links[line[0]][line[1]]["targetchannel"] = ""
        links[line[0]][line[1]]["targetage"] = ""


for lan_mac in device_modules.keys():
    wlan_module0 = device_modules[lan_mac][0]
    wlan_module1 = device_modules[lan_mac][1]
    links[lan_mac] = dict()
    links[lan_mac][wlan_module0] = dict()
    links[lan_mac][wlan_module0]["sourcemac"] = lan_mac
    links[lan_mac][wlan_module0]["targetmac"] = wlan_module0
    links[lan_mac][wlan_module0]["sourcestrength"] = ""
    links[lan_mac][wlan_module0]["targetstrength"] = ""
    links[lan_mac][wlan_module0]["state"] = "Active"
    links[lan_mac][wlan_module0]["connectiontype"] = "fake"
    links[lan_mac][wlan_module0]["channel"] = ""
    links[lan_mac][wlan_module0]["sourceage"] = ""
    links[lan_mac][wlan_module0]["targetage"] = ""
    links[lan_mac][wlan_module1] = dict()
    links[lan_mac][wlan_module1]["sourcemac"] = lan_mac
    links[lan_mac][wlan_module1]["targetmac"] = wlan_module1
    links[lan_mac][wlan_module1]["sourcestrength"] = ""
    links[lan_mac][wlan_module1]["targetstrength"] = ""
    links[lan_mac][wlan_module1]["state"] = "Active"
    links[lan_mac][wlan_module1]["connectiontype"] = "fake"
    links[lan_mac][wlan_module1]["channel"] = ""
    links[lan_mac][wlan_module1]["sourceage"] = ""
    links[lan_mac][wlan_module1]["targetage"] = ""

# Write stuff to json
i = 0
nodes_dict_index = dict()
nodes_dict_name = dict()
for key in nodes:
    nodes_dict_index[i] = key
    nodes_dict_name[key] = i
    i += 1

keyed_links = list()
for source in links:
    for target in links[source]:
        keyed_links.append((
            nodes_dict_name[links[source][target]["sourcemac"]],
            nodes_dict_name[links[source][target]["targetmac"]],
            links[source][target]["sourcemac"],
            links[source][target]["targetmac"],
            links[source][target]["sourcestrength"],
            links[source][target]["targetstrength"],
            links[source][target]["state"],
            links[source][target]["connectiontype"],
            links[source][target]["sourceage"],
            links[source][target]["targetage"]))

json_dict = {"nodes": [{'index': index,
                        'label': nodes[nodes_dict_index[index]]["label"],
                        'mac': nodes[nodes_dict_index[index]]["mac"],
                        'type': nodes[nodes_dict_index[index]]["type"],
                        'channel': nodes[nodes_dict_index[index]]["channel"],
                        'connectiontype': nodes[nodes_dict_index[index]]["connectiontype"]
                        } for index in nodes_dict_index.keys()],
             "links": [{"source": source,
                        "target": target,
                        'sourcemac': sourcemac,
                        'targetmac': targetmac,
                        'sourcestrength': sourcestrength,
                        'targetstrength': targetstrength,
                        'state': state,
                        'connectiontype': connectiontype,
                        'sourceage': sourceage,
                        'targetage': targetage
                        } for source, target, sourcemac, targetmac, sourcestrength, targetstrength, state, connectiontype, sourceage, targetage in keyed_links]}
filename = "autowds-graph.json"
with open(filename, 'w') as outfile:
    json.dump(json_dict, outfile, indent=4)
