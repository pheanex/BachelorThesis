#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose   Check if the given number of aps are really active
#           that means if their status is running in /status/wlan-Management/AP-connections/

import testcore.control.ssh
import os
import sys

if len(sys.argv) < 4:
    print("Usage: python AutoWDSstatus.py <wlc-address> <wlc-username> <wlc_password> <nr_aps>")
    exit(1)

wlc_address = sys.argv[1]
wlc_username = sys.argv[2]
wlc_password = sys.argv[3]
nr_aps = int(sys.argv[4])


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
    print("WLC is down")
    exit(1)

ap_list = get_table_data("/Status/WLAN-Management/AP-Connections", wlc_address, wlc_username, wlc_password)

# Check if aps are in table (the right number of aps)
if ap_list is None:
    print("Error: Could not get data from WLC")
    exit(1)
if len(ap_list) < nr_aps:
    print(str(len(ap_list)) + " != " + str(nr_aps))
    exit(1)
else:  # Check if their status is also running
    for line in ap_list:
        if line[4] != "Run":
            print(str(line))
            exit(1)

