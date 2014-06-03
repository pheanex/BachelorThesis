#!/bin/bash
# author konstantin manna konstantin.manna@lancom.de
# date 03.06.2014
# purpose This script flashes the given firmwares onto the devices of the AutoWDS-testsetup
# Warning: If you have changed sth in the Autowds Setup (especially the mapping of VM to AP)
# 	   then you have to adapt this script!

l322fw=$1
l452fw=$2
batfw=$3

if [[ ! -f "$l322fw" ]] || [[ ! -f "$l452fw" ]] || [[ ! -f "$batfw" ]]
then
        echo "Error: usage: $0 <L322 Firmware file> <L452 Firmware file> <BAT firmware file>" >&2
        exit 1
fi

for i in $(seq 11 22)
do
	case $i in
	"11")
		cp "$l322fw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $l322fw 172.16.40.121:firmware"
		vzctl exec "$i" "rm /root/$l322fw"
		;;
	"12")
		cp "$l322fw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $l322fw 172.16.40.122:firmware"
		vzctl exec "$i" "rm /root/$l322fw"
		;;
	"13")
		cp "$l322fw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $l322fw 172.16.40.123:firmware"
		vzctl exec "$i" "rm /root/$l322fw"
		;;
	"14")
		cp "$l452fw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $l452fw 172.16.40.111:firmware"
		vzctl exec "$i" "rm /root/$l452fw"
		;;
	"15")
		cp "$l452fw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $l452fw 172.16.40.112:firmware"
		vzctl exec "$i" "rm /root/$l452fw"
		;;
	"16")
		cp "$l452fw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $l452fw 172.16.40.113:firmware"
		vzctl exec "$i" "rm /root/$l452fw"
		;;
	"17")
		cp "$batfw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $batfw 172.16.40.101:firmware"
		vzctl exec "$i" "rm /root/$batfw"
		;;
	"18")
		cp "$batfw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $batfw 172.16.40.102:firmware"
		vzctl exec "$i" "rm /root/$batfw"
		;;
	"19")
		cp "$batfw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $batfw 172.16.40.103:firmware"
		vzctl exec "$i" "rm /root/$batfw"
		;;
	"20")
		cp "$batfw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $batfw 172.16.40.104:firmware"
		vzctl exec "$i" "rm /root/$batfw"
		;;
	"21")
		cp "$batfw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $batfw 172.16.40.105:firmware"
		vzctl exec "$i" "rm /root/$batfw"
		;;
	"22")
		cp "$batfw" "/var/lib/vz/root/${i}/root/"
		vzctl exec "$i" "scp -oStrictHostKeyChecking=no $batfw 172.16.40.106:firmware"
		vzctl exec "$i" "rm /root/$batfw"
		;;
	*)
		echo "Error: vm id not valid" >&2
		exit 1
		;;
	esac
done
echo "Done" >&2
