import sys
import os
import bttraffic
import csv
import glob
import logging
import time
import datetime

logger = logging.getLogger(__name__)

def parse_BTtraffic(inputpath, csvoutfile, unittag=None):
	"""
	combine all iperf result csv into one csv. returns list of textual results.
	"""

	unittags={
		'g':{'unit':1e9, 'unitstr':'GBit'},
		'G':{'unit':8e9, 'unitstr':'GByte'},
		'm':{'unit':1e6, 'unitstr':'MBit'},
		'M':{'unit':8e6, 'unitstr':'MByte'},
		'k':{'unit':1e3, 'unitstr':'KBit'},
		'K':{'unit':8e3, 'unitstr':'KByte'},
		'b':{'unit':1, 'unitstr':'Bit'},
		'B':{'unit':8, 'unitstr':'Byte'},
	}

	tcpsearchpath = os.path.join(inputpath,'*-TCP-?c*.csv') # CLIENT files
	udpsearchpath = os.path.join(inputpath,'*-UDP*-?s*.csv') # SERVER files
	resfile=os.path.join(inputpath,'spawn_result.txt')

	unit = 1e6
	unitstr = 'MBit'
	if unittag is not None:
		if unittags.has_key(unittag):
			unit = unittags[unittag]['unit']
			unitstr = unittags[unittag]['unitstr']
			
	output = []
	totalmedian = 0
	totalmean = 0
	totalstddev = 0
	totaldir =  [0, 0]
	csvfound = False
			
	with open(csvoutfile,'wb') as Fcsvout: 
		csvout=csv.writer(Fcsvout)
		csvout.writerow(['Flow', 'Median MBit/s', 'Mean MBit/s', 'StdDev MBit/s', 'A ratio', 'B ratio'])
		
		
		# Fres.write(' '.join(sys.argv))
		
		resultstcp = []
		resultsudp = []
		starttimes = []
		stoptimes = []
		
		# first get all data
		
		for csvfile in glob.iglob(tcpsearchpath):
			csvfound = True
			flow = csvfile[csvfile.rfind('-')+3:-4]
			type = csvfile[csvfile.rfind('-')+1]
			if type=="l":
				typestr = "local client vs. remote server"
				dir = 0
			else:
				typestr = "local server vs. remote client"
				dir = 1
			vectors = bttraffic.IperfCsv(csvfile)
			if len(vectors['timestamp'])>2:
				resultstcp.append((flow, typestr, vectors, dir))
				starttimes.append(vectors['timestamp'][0])
				stoptimes.append(vectors['timestamp'][-2])

		for csvfile in glob.iglob(udpsearchpath):
			csvfound = True
			flow = csvfile[csvfile.rfind('-')+3:-4]
			type = csvfile[csvfile.rfind('-')+1]
			rate = csvfile[csvfile.rfind('-UDP-')+5:csvfile.rfind('-')]
			if type=="r":
				typestr = "local client vs. remote server"
				dir = 0
			else:
				typestr = "local server vs. remote client"
				dir = 1
			vectors = bttraffic.IperfCsv(csvfile)
			if len(vectors['timestamp'])>2:
				resultsudp.append((flow, typestr, rate, vectors, dir))
				starttimes.append(vectors['timestamp'][0])
				stoptimes.append(vectors['timestamp'][-2])


		# then determine which timestamp range overlaps

		if len(starttimes)>0:
			starttime = max(starttimes)
			stoptime = min(stoptimes)
			
			# finally, use the overlapping range for throughputs
				
			for flow, typestr, vectors, dir in resultstcp:
				for vec0, timestamp in enumerate(vectors['timestamp']):
					if timestamp>=starttime: 
						break
				for vec1, timestamp in enumerate(vectors['timestamp']):
					if timestamp>stoptime: 
						break
				if vec1>vec0:
					ms=bttraffic.MeanStdDev(vectors['bitsps'][vec0:vec1]) # omit last row (totals)
					md=bttraffic.Median(vectors['bitsps'][vec0:vec1]) # omit last row (totals)
					output.append("Flow {0} ({1}): median {2:.3f} {5}/s, mean {3:.3f} {5}/s stdev {4:.3f} {5}/s  [el {6}-{7}]".format(flow, typestr, md[0]/unit, ms[0]/unit, ms[1]/unit, unitstr, vec0, vec1))
					totalmedian += md[0]
					totalmean += ms[0]
					totalstddev += ms[1]
					totaldir[dir] += ms[0]
					csvout.writerow([flow, md[0]/1e6, ms[0]/1e6, ms[1]/1e6,0,0])
				else:
					output.append("Flow {0} ({1}) dit not match {2}-{3}.".format(flow, typestr, vectors['timestamp'][0], vectors['timestamp'][-2]))
					
			
			for flow, typestr, vectors, dir in resultsudp:
				for vec0, timestamp in enumerate(vectors['timestamp']):
					if timestamp>=starttime: 
						break
				for vec1, timestamp in enumerate(vectors['timestamp']):
					if timestamp>=stoptime: 
						break
				if vec1>vec0:
					ms=bttraffic.MeanStdDev(vectors['bitsps'][vec0:vec1]) # omit last row (totals)
					md=bttraffic.Median(vectors['bitsps'][vec0:vec1]) # omit last row (totals)
					pl=bttraffic.Median(vectors['PL'][:-1],[10,50,90])
					output.append("Flow {0} ({1}, offered rate {2}): median {3:.3f} {9}/s, mean {4:.3f} {9}/s, stdev {5:.3f} {9}/s. PacketLoss: median-10 {6:.2f}%, median-50 {7:.2f}%, median-90 {8:.2f}%.".format(flow, typestr, rate, md[0]/unit, ms[0]/unit, ms[1]/unit, pl[0], pl[1], pl[2], unitstr))
					#~ totalmean += ms[0]
					#~ totalmedian += md[0]
				else:
					output.append("Flow {0} ({1}, offered rate {2}) dit not match.".format(flow, typestr, rate))
		else:
			output.append("not timestamp data available")
		
		
		if sum(totaldir)>0:
			aratio = totaldir[0]/(sum(totaldir))*100
			bratio = totaldir[1]/(sum(totaldir))*100
		else:
			aratio = 0
			bratio = 0
			
		csvout.writerow(['Aggregate', totalmedian/1e6, totalmean/1e6, totalstddev/1e6, aratio, bratio])
		output.insert(0,"Aggregate Throughput: mean {0:.3f} {1}/s ({2:.1f}%:{3:.1f}%)".format(totalmean/unit, unitstr, aratio, bratio))		

	return output
