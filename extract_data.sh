#!/bin/bash
# Date 26.06.2014
# Purpose takes the sums reports files for all dirs in this directory and creates single type reports for all tests

# Specify the directory the testsets are in and cd there
curdir="$(pwd)"
if [ ! -d "$1" ]
then
	echo "Error: ${1} is not a directory" >&2
	exit 1
else
	cd "$1"
fi

# For each testdatadir trigger the create_stat_reports script
for datadir in $(find . -maxdepth 1 -type d | tail -n +2)
do
	"${curdir}/create_stat_reports.sh" "$datadir"
done

"${curdir}/create_aggregate_reports.sh" "${curdir}/$1"

# Draw the svgs
python "${curdir}/draw_graph.py"

cd "$curdir"