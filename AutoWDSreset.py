#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose This script resets the connections the CAA.py created at the wlc through ssh

import testcore.control.ssh
import os
import sys

if len(sys.argv) < 3:
    print("Usage: python AutoWDSreset.py <wlc-address> <wlc-username> <wlc_password>")
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


lcos_script = list()

# Delete all the configured links
lcos_script.append('rm /Setup/WLAN-Management/AP-Configuration/AutoWDS-Topology/*')

# Set the Topology management back to Auto(=0) mode
lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/AutoWDS-Profiles/AUTOWDS_PROFILE {Topology-Management} 0')

# Reset the radioprofile to default
lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/WLAN-Modul-1-default 2.4G')
lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/WLAN-Modul-2-default 2.4G')
lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/Radioprofiles/RADIO_PROF {Channel-List} 13')

# Get the table: /Setup/WLAN-Management/AP-Configuration/Accesspoints and from it the mac addresses of the wlan-modules
mac_list = list()
for line in get_table_data("/Setup/WLAN-Management/AP-Configuration/Accesspoints", wlc_address, wlc_username, wlc_password):
    if not line[0] is "ffffffffffff":
        mac_list.append(str(line[0]))

# Generate the module/channel reset commands
for entry in mac_list:
    lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/Accesspoints/' + entry + ' {WLAN-Module-1} default {Module-1-Channel-List} "" {WLAN-Module-2} default {Module-2-Channel-List} ""')

# Execute the script on the wlc if wlc is up
if wlc_is_up(wlc_address):
    wlc_connection = testcore.control.ssh.SSH(host=wlc_address, username=wlc_username, password=wlc_password)
    wlc_connection.runscript(lcos_script)
    print("Done")
