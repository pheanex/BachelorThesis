#!/usr/bin/python
# author Konstantin Manna
# date   25.03.2014
# purpose   Sets the given data in the wlc for testing purpose

import testcore.control.ssh
import os
import sys

if len(sys.argv) < 5:
    print("Usage: python AutoWDSstatus.py <wlc-address> <wlc-username> <wlc_password> <BScan> <Channel>")
    exit(1)

wlc_address = sys.argv[1]
wlc_username = sys.argv[2]
wlc_password = sys.argv[3]
Background_scan_interval = sys.argv[4]
Channel = int(sys.argv[5])
lcos_script = list()


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

# Set Channel and BGscaninterval
lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/Radioprofiles/RADIO_PROF {Channel-List} ' + str(Channel) + ' {Background-Scan} ' + str(Background_scan_interval))

# Set default band and modules to default band
# default (0), 2.4GHz (1), 5GHz (2), Off (3), Auto (255)
if int(Channel) < 14:
    lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/WLAN-Modul-1-default 2.4G')
    lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/WLAN-Modul-2-default 2.4G')
else:
    lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/WLAN-Modul-1-default 5G')
    lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/WLAN-Modul-2-default 5G')

lcos_script.append('set /Setup/WLAN-Management/AP-Configuration/Radioprofiles/RADIO_PROF {Channel-List} ' + Channel)

# Execute the script on the wlc if wlc is up
if wlc_is_up(wlc_address):
    wlc_connection = testcore.control.ssh.SSH(host=wlc_address, username=wlc_username, password=wlc_password)
    wlc_connection.runscript(lcos_script)
    print("Done")
    exit(0)
else:
    exit(1)

