import sys
import os
import csv
import logging
logger = logging.getLogger(__name__)

def fix_ixvpn_csv(csvin, csvout):
	"""
	recalculate Encyption Mbps - IXIA numbers are based on encrypted and not cleartext bytes
	"""
	
	# read data
	
	de_Mbps = dict()
	en_Mbps_raw = dict()

	# read input csv
	if os.path.exists(csvin):
		with open(csvin, 'rb') as Fin:
			csvdata = csv.reader(Fin)
			for i, row in enumerate(csvdata):
				if i > 0:
					if row[0] == 'Decryption':
						de_Mbps[row[1]] = float(row[2])
					if row[0] == 'Encryption':
						en_Mbps_raw[row[1]] = float(row[2])
		
		# process data
		en_overhead = 58 # bytes encryption overhead
		tunit = 1000000
		
		en_Mbps = dict()
		en_fps = dict()
		de_fps = dict()
		for size, speed in en_Mbps_raw.iteritems():
			try:
				bytes = int(size)
				en_Mbps[size] = speed * bytes / (bytes + en_overhead)
				en_fps[size] = speed * tunit / bytes / 8
			except:
				en_Mbps[size] = en_Mbps_raw[size]
				en_fps[size] = 0

		for size, speed in de_Mbps.iteritems():
			try:
				bytes = int(size)
				de_fps[size] = speed * tunit / bytes / 8
			except:
				de_fps[size] = 0
		
		# write output csv
		with open(csvout, 'wb') as Fout:
			w = csv.writer(Fout, delimiter=',')
			w.writerow(['Frame Size','Encryption Mbps','Encryption fps','Decryption Mbps','Decryption fps'])
			for size in en_Mbps:
				w.writerow([size.strip(), en_Mbps[size], en_fps[size], de_Mbps[size], de_fps[size]])
			logger.info('writen fixed ixvpn csv {}'.format(csvout))
	if len(en_Mbps.keys())>0:
		return True
	else:
		return False

if __name__=='__main__':
	fix_ixvpn_csv(r'C:\BT\IXIA-12\1711plus-WAN-IPSECv4-UDP-TPT\WAN-IPSECv4-0001T\IxVPN-IPSECv4-FE-rt-0001T-1418-1p!LC-1711plus-8.84.0031!FIRMWARE.884~BUIL0031~LC-1711plus-8.84.0031!20130828-083452\Throughput.csv',r'C:\BT\IXIA-12\1711plus-WAN-IPSECv4-UDP-TPT\WAN-IPSECv4-0001T\IxVPN-IPSECv4-FE-rt-0001T-1418-1p!LC-1711plus-8.84.0031!FIRMWARE.884~BUIL0031~LC-1711plus-8.84.0031!20130828-083452\Throughput2.csv')