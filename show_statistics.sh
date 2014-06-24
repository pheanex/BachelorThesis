#!/bin/bash
#usage: give directory with testdata in it
testdatadir="$1"

if [ ! -d "$testdatadir" ]
then
	echo "Error: ${testdatadir} is not a valid testdatadir" >&2
	exit 1
fi

cd "$testdatadir"

# $1 = outputfilename
# $2 = inputfilename
# $3 = columnnumber of inputfilename
create_stat_file()
{
	general_file="../${1}"
	ap_cur_file="${general_file}_ap_${apid}"
	ap_tmp_file="${ap_cur_file}_tmp"
	echo "AP-${apid}" >> "$ap_cur_file"
	for file in $(find . -type f -iname "${2}*" | sort)
	do
		ap_wlan1_data=$(grep WLAN-1 "$file" | awk '{print $"'$3'"}')
		ap_wlan2_data=$(grep WLAN-2 "$file" | awk '{print $"'$3'"}')
		ap_sum_data=$(echo "${ap_wlan1_data} + ${ap_wlan2_data}" | bc -l)
		echo "$ap_sum_data" >> "$ap_cur_file"
	done

	if ! [ -f "$general_file" ]
	then
		touch "$general_file"
	fi

	paste -d' ' "$general_file" "$ap_cur_file" > "$ap_tmp_file"
	rm "$ap_cur_file"
	mv "$ap_tmp_file" "$general_file"		
}

# Delete old files first
for stat_file in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise sums
do
	rm -f "$stat_file"*
done

for apid in {11..22}
do
	cd "$apid"

	# RC-CRC Errors
	create_stat_file rx_crc_errors errors_raw 17

	# RC Errors
	create_stat_file rx_errors errors_raw 3

	# TX Errors
	create_stat_file tx_errors errors_raw 2

	# Retries
	create_stat_file retries errors_raw 9

	# Multiple_retries
	create_stat_file multiple_retries errors_raw 10

	# RX Packets
	create_stat_file rx_packets packet_transport_table 2

	# TX Packets
	create_stat_file tx_packets packet_transport_table 3

	# RX Bytes
	create_stat_file rx_bytes byte_transport_raw 3

	# TX Bytes
	create_stat_file tx_bytes byte_transport_raw 2

	# Modem Load
	create_stat_file modem_load radios_table 9

	# Noise
	create_stat_file noise radios_table 8

	cd ..
done

# align the columns and cut away uncomplete lines
for stat_file in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise
do
	column -t "$stat_file" | awk '$12{print $0}' > "${stat_file}_tmp"
	mv "${stat_file}_tmp" "$stat_file"
done

# convert to delta values for certain tables
for table in multiple_retries retries rx_bytes rx_crc_errors rx_errors rx_packets tx_bytes tx_errors tx_packets
do
	head -n1 "$table" > "${table}_tmp"
	awk 'NR>1{print $1-prev1,$2-prev2,$3-prev3,$4-prev4,$5-prev5,$6-prev6,$7-prev7,$8-prev8,$9-prev9,$10-prev10,$11-prev11,$12-prev12; prev1=$1;prev2=$2;prev3=$3;prev4=$4;prev5=$5;prev6=$6;prev7=$7;prev8=$8;prev9=$9;prev10=$10;prev11=$11;prev12=$12}' "$table" | tail -n +3 >> "${table}_tmp"
	mv "${table}_tmp" "$table"
done

# append the sum for the main files
for file in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise
do
	echo "SUM" > "${file}_sum"
	awk 'NR>1{print sum=$1+$2+$3+$4+$5+$6+$7+$8+$9+$10+$11+$12}' "$file" >> "${file}_sum"
	paste -d' ' "$file" "${file}_sum" > "${file}_tmp"
	rm "${file}_sum"
	mv "${file}_tmp" "$file"
done

# Create the SUMs table
touch sums
for file in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise
do
	echo "$file" > sums_tmp
	awk 'NR>1{print $13}' "$file" >> sums_tmp 
	paste -d' ' sums sums_tmp > sums_tmp2
	rm sums_tmp
	mv sums_tmp2 sums
done

# align the columns again and cut away uncomplete lines
for stat_file in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise
do
	column -t "$stat_file" | awk '$12{print $0}' > "${stat_file}_tmp"
	mv "${stat_file}_tmp" "$stat_file"
done

# sums has only 11 columns aling it also and cut away uncomplete lines
column -t sums | awk '$11{print $0}' > sums_tmp
mv sums_tmp sums

cd ..
