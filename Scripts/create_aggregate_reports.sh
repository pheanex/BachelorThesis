#!/bin/bash
testdatadir="$1"

if [ ! -d "$testdatadir" ]
then
	echo "Error: ${testdatadir} is not a valid testdatadir" >&2
	exit 1
fi
curdir="$(pwd)"
cd "$testdatadir"

# Extract from the sums file of each datadir the overall reports files
for report in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise
do
	rm -f "$report"
	touch "$report"
	for datadir in $(find .  -maxdepth 1 -type d | tail -n +2)
	do
		cd "$datadir"
		sums_file="sums"
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
		echo "$description" > "${report}_column"

		# For noise and modem load divide by the nr of modules to get the average and not the sums values
		if [[ "$report" == "noise" ]] || [[ "$report" == "modem_load" ]]
		then
			if ! [ -f nr_modules ]
			then
				echo "Error: no nr_modules file found" >&2
				exit 1
			fi
			nr_modules=$(cat nr_modules)
			awk 'NR>1{print $"'$column_nr'"/"'$nr_modules'"}' "$sums_file" >> "${report}_column"
		else
			awk 'NR>1{print $"'$column_nr'"}' "$sums_file" >> "${report}_column"
		fi

		paste -d' ' "../${report}" "${report}_column" > "${report}_tmp"
		mv "${report}_tmp" "../${report}"

		if [ "$report" = "modem_load" ]
		then
			awk '{for (i=1;i<13;i++){if($i == 0){$i=last[i]};last[i]=$i};print $0}' "../${report}" | column -t > "${report}_tmp"
			mv "${report}_tmp" "../${report}"
		fi
		cd ..
	done
done

# Align the columns nicely
for report in rx_crc_errors rx_errors tx_errors retries multiple_retries rx_packets tx_packets rx_bytes tx_bytes modem_load noise
do
	column -t "$report" > "${report}_tmp"
	mv "${report}_tmp" "$report"
done

cd "$curdir"
