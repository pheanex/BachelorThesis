#!/usr/bin/python
# author Konstantin Manna
# date   21.06.2014
# queries an AP for some tables and saves the data to file

import time
from testcore.parseoutput.lcos import *
from testcore.control.ssh import *
import datetime

if len(sys.argv) < 4:
    print("Usage: python query_ap.py <address> <username> <password> <duration>")
    exit(1)


address = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]
test_duration = int(sys.argv[4])

teststart = datetime.datetime.now()
testend = teststart + datetime.timedelta(0,test_duration)

if not os.system("ping -c 1 " + address + " > /dev/null") == 0:
    print(address + " is down!")
    exit(1)

ssh_connection = SSH(host=address, username=username, password=password)


# for given raw table string, write pretty string to file
def write_pretty_to_file(table_string, tablename, timestamp):
    writestring = str()

    # Title line
    for name in table_string[0]:
        writestring += name + "\t"
    writestring += "\n"

    # Start of data lines
    for row in table_string[1]:
        for entry in row:
            writestring += str(entry) + "\t"
        writestring += "\n"

    # Write stuff to files
    fd = open("testdata/" + tablename + "_" + timestamp, "w")
    fd.write(writestring)
    fd.close()


def get_data_and_write_to_file():
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

    #write pretty files
    write_pretty_to_file(byte_transport_table, "byte_transport_table", timestamp)
    write_pretty_to_file(errors_table, "errors_table", timestamp)
    write_pretty_to_file(packet_transport_table, "packet_transport_table", timestamp)
    write_pretty_to_file(radios_table, "radios_table", timestamp)
    write_pretty_to_file(accesspoints_list_table, "accesspoints_list_table", timestamp)

    # Open/Create the raw files
    byte_transport_raw_file = open("testdata/byte_transport_raw_" + timestamp, "w")
    errors_raw_file = open("testdata/errors_raw_" + timestamp, "w")
    packet_transport_raw_file = open("testdata/packet_transport_raw_" + timestamp, "w")
    radios_raw_file = open("testdata/radios_raw_" + timestamp, "w")
    accesspoints_list_raw_file = open("testdata/accesspoints_list_raw_" + timestamp, "w")

    # Write data to raw files
    byte_transport_raw_file.write(byte_transport_table_raw)
    errors_raw_file.write(errors_table_raw)
    packet_transport_raw_file.write(radios_table_raw)
    radios_raw_file.write(radios_table_raw)
    accesspoints_list_raw_file.write(accesspoints_list_table_raw)

    # Close the raw files
    byte_transport_raw_file.close()
    errors_raw_file.close()
    packet_transport_raw_file.close()
    radios_raw_file.close()
    accesspoints_list_raw_file.close()

while True:
    if datetime.datetime.now() < testend:
        get_data_and_write_to_file()
    else:
        exit(0)
    time.sleep(3)




