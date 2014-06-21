#!/bin/bash
#author kmanna
#date 21.06.2014
#purpose starts the autowds traffic test

wlc_address="172.16.40.100"
wlc_username="admin"
test_duration="$1"
traffic_bw="$2"

if [[ -z "$test_duration" ]] || [[ -z "$traffic_bw" ]]
then
        echo "Error: usage: $0 <Testduration in seconds> <Traffic in Mbit/s>"
        exit 1
fi

# Ask user for Testnotes
read -p "Notizen zum Test:" notes

#Reminder continuation time
read -p "Continuation time auf > ${test_duration} gestellt?" answer
if ! [ "$answer" = "yes" ]
then
	echo "Please type 'yes'" >&2
	exit 1
fi

# Check if APs are stable in 15s
for i in $(seq 1 3)
do
        sleep 5
        if ! python AutoWDScheckAPs.py 172.16.40.100 admin private $(seq $VM_start $VM_end | wc -l)
        then
		echo "Error: APs are not stabilized yet, please take a look at this"
		exit 1
        fi
done
echo "All APs are stable" >&2

echo "Update scripts in vms" >&2
for i in $(seq $VM_start $VM_end)
do
        cp iperf-parallel-servers iperf-multiple-clients /var/lib/vz/root/$i/root/
	cp -R ../query "/var/lib/vz/root/${i}/root"
done

# Get wlc config
scp "${wlc_username}@${wlc_address}:config" wlc_config

# Start AP queries
vzctl exec 11 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.122 root private $test_duration &"
vzctl exec 12 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.104 admin private $test_duration &"
vzctl exec 13 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.123 root private $test_duration &"
vzctl exec 14 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.121 root private $test_duration &"
vzctl exec 15 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.105 admin private $test_duration &"
vzctl exec 16 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.111 root private $test_duration &"
vzctl exec 17 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.113 root private $test_duration &"
vzctl exec 18 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.101 admin private $test_duration &"
vzctl exec 19 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.102 admin private $test_duration &"
vzctl exec 20 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.112 root private $test_duration &"
vzctl exec 21 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.103 admin private $test_duration &"
vzctl exec 22 "cd /root/query; rm -rf testdata; mkdir testdata; python query_ap.py 172.16.40.106 admin private $test_duration &"

echo "Starting parallel iperf listeners in vms" >&2
for i in $(seq $VM_start $VM_end)
do
        vzctl exec $i "cd /root; ./iperf-parallel-servers $VM_start $VM_end $i"
done

echo "Starting traffic throughput test in vms" >&2
for i in $(seq $VM_start $VM_end)
do
        vzctl exec $i "sleep 0.$RANDOM; cd /root; ./iperf-multiple-clients $VM_start $VM_end $i $NR_SECS $bw"
done

echo "Wait for test to finish about (${test_duration}s)" >&2
sleep $test_duration
sleep 5

echo "Stopping parallel iperf listeners in vms" >62
for i in $(seq $VM_start $VM_end)
do
        vzctl exec $i "killall iperf"
done

echo "Copying data from vms to archive" >&2
testarchive="$Testdata_${DATE}_${test_duration}_${traffic_bw}"
mkdir "$testarchive"
cd "$testarchive"
for i in $(seq $VM_start $VM_end)
do
        mkdir $i
        cd $i
        cp -R /var/lib/vz/root/${i}/root/query/testdata/* .
        cd ..
done

# Write notes from start
echo "$notes" > notes

cd ..
