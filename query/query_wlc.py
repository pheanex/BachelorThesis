#!/usr/bin/python
# author Konstantin Manna
# date   21.06.2014
# queries a WLC for some tables and saves the data to file

import time
from testcore.parseoutput.lcos import *
from testcore.control.ssh import *

if len(sys.argv) < 3:
    print("Usage: python query_ap.py <address> <username> <password>")
    exit(1)

address = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

if not os.system("ping -c 1 " + address + " > /dev/null") == 0:
    print(address + " is down!")
    exit(1)

ssh_connection = SSH(host=address, username=username, password=password)

# for given raw table string, write pretty string to file
def write_pretty_to_file(table_string, tablename):
    writestring = str()
    for gen_row in table_string:
        for row in gen_row:
            for entry in row:
                writestring += str(entry) + "\t"
            writestring += "\n"
    fd = open(tablename + "_" + timestamp, "w")
    fd.write(writestring)
    fd.close()

timestamp = time.strftime("%Y.%m.%d_%H:%M:%S")

# Get the tables
autowds_auto_topology_raw = ssh_connection.runquery("ls /Status/WLAN-Management/AP-Configuration/AutoWDS-Auto-Topology/")
autowds_topology_raw= ssh_connection.runquery("ls /Status/WLAN-Management/AP-Configuration/AutoWDS-Topology/")

# Parse tables
autowds_auto_topology = parse_table(autowds_auto_topology_raw)
autowds_topology = parse_table(autowds_topology_raw)

#write pretty files
write_pretty_to_file(autowds_auto_topology, "autowds_auto_topology")
write_pretty_to_file(autowds_topology, "autowds_topology")

# Open/Create the raw files
autowds_auto_topology_raw_file = open("autowds_auto_topology_raw" + timestamp, "w")
autowds_topology_raw_file = open("autowds_topology_raw" + timestamp, "w")

# Write data to raw files
autowds_auto_topology_raw_file.write(autowds_auto_topology_raw)
autowds_topology_raw_file.write(autowds_topology_raw)

# Close the raw files
autowds_auto_topology_raw_file.close()
autowds_topology_raw_file.close()


