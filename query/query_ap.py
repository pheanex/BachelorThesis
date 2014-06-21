#!/usr/bin/python
# author Konstantin Manna
# date   21.06.2014
# queries an AP for some tables and saves the data to file

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

timestamp = time.strftime("%Y.%m.%d_%H:%M:%S")

# Get the tables
byte_transport_table_raw = ssh_connection.runquery("ls /status/wlan/byte-transport")
errors_table_raw = ssh_connection.runquery("ls /status/wlan/errors")
packet_transport_table_raw = ssh_connection.runquery("ls /status/wlan/packet-transport")
radios_table_raw = ssh_connection.runquery("ls /status/wlan/radios")
accesspoints_list_table_raw = ssh_connection.runquery("ls /Status/WLAN/Interpoints/Accesspoint-List")

# Parse tables
byte_transport_table = parse_table(byte_transport_table_raw)
errors_table = parse_table(errors_table_raw)
packet_transport_table = parse_table(packet_transport_table_raw)
radios_table = parse_table(radios_table_raw)
accesspoints_list_table = parse_table(accesspoints_list_table_raw)

# Open/Create the files
byte_transport_file = open("byte_transport_" + timestamp, "w")
errors_file = open("errors_" + timestamp, "w")
packet_transport_file = open("packet_transport_" + timestamp, "w")
radios_file = open("radios_" + timestamp, "w")
accesspoints_list_file = open("accesspoints_list_" + timestamp, "w")
byte_transport_raw_file = open("byte_transport_raw_" + timestamp, "w")
errors_raw_file = open("errors_raw_" + timestamp, "w")
packet_transport_raw_file = open("packet_transport_raw_" + timestamp, "w")
radios_raw_file = open("radios_raw_" + timestamp, "w")
accesspoints_list_raw_file = open("accesspoints_list_raw_" + timestamp, "w")

# Write data to files
byte_transport_file.write(byte_transport_table)
errors_file.write(errors_table)
packet_transport_file.write(radios_table)
radios_file.write(radios_table)
accesspoints_list_file.write(accesspoints_list_table)

# write pretty/parsable stuff to file
string writestring
for bigrow in accesspoints_list_table:
	for row in accesspoints_list_table[1]:
		for e in row: s += str(e) + "\t"
		s += "\n"


byte_transport_raw_file.write(byte_transport_table)
errors_raw_file.write(errors_table)
packet_transport_raw_file.write(radios_table)
radios_raw_file.write(radios_table)
accesspoints_list_raw_file.write(accesspoints_list_table)

# Close the files
byte_transport_file.close()
errors_file.close()
packet_transport_file.close()
radios_file.close()
accesspoints_list_file.close()
byte_transport_raw_file.close()
errors_raw_file.close()
packet_transport_raw_file.close()
radios_raw_file.close()
accesspoints_list_raw_file.close()


