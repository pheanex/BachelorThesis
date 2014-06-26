#!/bin/bash
# Date 26.06.2014
# Purpose takes the sums reports files for all dirs in this directory and creates single type reports for all tests

# For each testdatadir trigger the create_stat_reports script
for datadir in $(find .  -maxdepth 1 -type d | tail -n +2)
do 
	./create_stat_reports.sh "$datadir"
done


# Extract from the sums file of each datadir the overall reports files
for report in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise
do
	rm -f "$report"
	touch "$report"
	for sums_file in $(find .  -maxdepth 1 -type d | tail -n +2)
	do
		cd "$sums_file"
		description=$(cat notes)
		case "$report" in
			rx_crc_errors)
				column_nr=1
				;;
			rx_errors)
				column_nr=2
				;;
			tx_errors)
				column_nr=3
				;;
			retries)
				column_nr=4
				;;
			multiple_retries)
				column_nr=5
				;;
			rx_packets)
				column_nr=6
				;;
			tx_packets)
				column_nr=7
				;;
			rx_bytes)
				column_nr=8
				;;
			tx_bytes)
				column_nr=9
				;;
			modem_load)
				column_nr=10
				;;
			noise)
				column_nr=11
				;;
			*)
				echo "Error: unknown report column/file" >&2
				exit 1
				;;
		esac
		
		awk 'NR>1{print $"'$column_nr'"}')	"$sums_file" > "${report}_column"
		paste -d' ' "$report" "${report}_column" > "${report}_tmp"
		mv "${report}_tmp" "$report"

		cd ..
	done
done

# Align the columns nicely 
for report in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise
do
	column -t "$report" > "${report}_tmp"
	mv "${report}_tmp" "$report"
done