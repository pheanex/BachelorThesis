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
filename = "AutoWDSstatus.json"


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


Active_Radios = get_table_data("/status/wlan-management/ap-status/active-radios", wlc_address, wlc_username, wlc_password)
Accesspoints = get_table_data("/Status/WLAN-Management/AP-Configuration/Accesspoints/", wlc_address, wlc_username, wlc_password)
Intra_Wlan_Discovery = get_table_data("/status/wlan-management/intra-wlan-discovery", wlc_address, wlc_username, wlc_password)
Autowds_Profile = get_table_data("/status/wlan-management/ap-configuration/autowds-profile/", wlc_address, wlc_username, wlc_password)
Autowds_topology = get_table_data("/status/wlan-management/ap-configuration/autowds-topology", wlc_address, wlc_username, wlc_password)
Autowds_auto_topology = get_table_data("/status/wlan-management/ap-configuration/autowds-auto-topology", wlc_address, wlc_username, wlc_password)

devices = set()
modules = set()
device_modules = list()
nodes = dict()
links = dict()
source_target = set()

# Fill nodes
for line in Active_Radios:
    devices.add(line[0])
    modules.add(line[6])
    device_modules.append((line[0], line[6]))
    if not line[0] in nodes:
        d = dict()
        d["label"] = line[4]
        d["type"] = "AP"
        d["channel"] = ""
        nodes[line[0]] = d

    if not line[6] in nodes:
        d = dict()
        d["label"] = "WLAN-" + str(int(line[1]) + 1)
        d["type"] = "IFC"
        d["id"] = int(line[1])
        nodes[line[6]] = d

for line in Accesspoints:
    if line[0] in nodes:
        if nodes[line[0]]["id"] == 0:
            nodes[line[0]]["channel"] = line[13]
        else:
            nodes[line[0]]["channel"] = line[18]

# Fill links
modus = Autowds_Profile[6]
if modus is "Automatic":
    # Consider only data from Autowds_topology
    for line in Autowds_topology:
        links[line[5]] = dict()
        links[line[5]][line[8]] = dict()
        links[line[5]][line[8]]["state"] = line[15]
        links[line[5]][line[8]]["state"]["connectiontype"] = "real"
        source_target.add((line[5], line[8]))
elif modus is "Manual":
    # Consider only data from Autowds_Auto_topology
    for line in Autowds_auto_topology:
        links[line[5]] = dict()
        links[line[5]][line[8]] = dict()
        links[line[5]][line[8]]["state"] = line[15]
        links[line[5]][line[8]]["state"]["connectiontype"] = "real"
        source_target.add((line[5], line[8]))
else:
    print("Modus is neither Automatic nor Manual => probably Semi -> Don't know what to do.")
    exit(1)

for line in Intra_Wlan_Discovery:
    if (line[0], line[1]) in source_target:
        links[line[0]][line[1]]["sourcestrength"] = line[3]
        links[line[0]][line[1]]["sourcechannel"] = line[2]
        links[line[0]][line[1]]["sourceage"] = line[5]
    if (line[1], line[0]) in source_target:
        links[line[0]][line[1]]["targetstrength"] = line[3]
        links[line[0]][line[1]]["targetchannel"] = line[2]
        links[line[0]][line[1]]["targetage"] = line[5]

for (source, target) in device_modules:
    links[source] = dict()
    links[source][target] = dict()
    links[source][target]["sourcemac"] = source
    links[source][target]["targetmac"] = target
    links[source][target]["sourcestrength"] = 9000
    links[source][target]["targetstrength"] = 9000
    links[source][target]["state"] = "Active"
    links[source][target]["connectiontype"] = "fake"
    links[source][target]["channel"] = ""

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
            links[source][target]["sourcestrength"], links[source][target]["targetstrength"],
            links[source][target]["state"],
            links[source][target]["channel"]))

json_dict = {"nodes": [{'index': index,
                        'label': nodes[nodes_dict_index[index]]["label"],
                        'mac': nodes[nodes_dict_index[index]]["label"],
                        'type': nodes[nodes_dict_index[index]]["type"],
                        'channel': nodes[nodes_dict_index[index]]["channel"]} for index in nodes_dict_index.keys()],
             "links": [{"source": source,
                        "target": target,
                        'sourcemac': sourcemac,
                        'targetmac': targetmac,
                        'sourcestrength': sourcestrength,
                        'targetstrength': targetstrength,
                        'state': state,
                        'channel': channel} for source,
                                                target,
                                                sourcemac,
                                                targetmac,
                                                sourcestrength,
                                                targetstrength,
                                                state,
                                                channel in keyed_links]}
with open(filename, 'w') as outfile:
    json.dump(json_dict, outfile, indent=4)
