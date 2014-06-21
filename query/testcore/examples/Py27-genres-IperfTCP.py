import sys
import os
import glob
import logging
import time
import datetime

from testcore.database import testrun
from testcore.database import tr_csv
from testcore.parseoutput import lcos
from testcore.parseoutput import batchtester
from testcore.parseoutput import lcoslog
from testcore.parseoutput import parsebttraffic

logger = logging.getLogger(__name__)

"""
Put the results of an BT IPerf testrun into a Testrun instance and save it to the database
"""


class myTestrun(testrun.Testrun, tr_csv.TestrunCsv):
	"""make our own testclass
	
	our testclass combines the functionality of the base testrun.Testrun with the csv functionality by inheriting from both
	"""
	
	def __init__(self):
		"""call __init__ from the classes we inherit from
		
		note: only the name of our own testclass has to be specified, not the ones we inherit from
		"""
		super(myTestrun, self).__init__()
	


if __name__=='__main__':			

	test_setup = 'P2P2Example' # each test setup has its own table schema inside the main PostgreSQL database. For SQLite, this maps directly to the filename.
	dbpath = r'/home/batchtester/source'	
	# set debuglevel to INFO (this will diyplay the levels INFO, WARNING, ERROR and CRITICAL, but not DEBUG), customize the logger output, and let it write to a file instead stdout
	logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=os.path.join(dbpath,'Py27-genres-IperfTCP.log'))

	# sys.argv=['',r'/home/batchtester/BT/1781EF-B2B-1WAN-IPv4-TCP-TPT/1WAN-IPv4/Py27-WAN-rt-5x5.py!LC-1781EF-8.82.0100-RU1!FIRMWARE.882~BUIL0100-RU1~LC-1781EF-8.82.0100-RU1!20130909-164609']
	if len(sys.argv)>1:
		testpath = sys.argv[1].strip('"')
		unittag =  None
		if len(sys.argv)>2:
			unittag=sys.argv[2]
	
		my_test = myTestrun() # get an instance of testrun. all attributes will be set to default
		
		my_test.run.update(batchtester.parsepath(testpath)) # update the basic information our testrun from the batchtester path
		
		# try to add device and firmware specific data to the Testrun instance
		try:
			devs = batchtester.parsefwlist(file=os.path.join(testpath, 'fwlist.csv'))
		except:
			logger.warning('error when parsing fwlist {}'.format(sys.exc_info()))
			devs = {}
		lcs = []
		for lc in glob.glob(os.path.join(testpath,'LC*-*')):
			lcs.append(os.path.basename(lc).split('-',1)[0][2:])
		if len(lcs)>0:
			maindev = min(map(int,lcs))
		else:
			maindev = 1
		logger.info('parser found devices {}, maindev is {}'.format(' '.join(lcs),maindev ))	
		try:
			for lc in set(lcs):
				devs[int(lc)]['dev_ldversion'], devs[int(lc)]['dev_ldbuild'] = lcos.parsefirmsafe(file=os.path.join(testpath, 'LC'+lc+'-firmsafe.txt'))['<loader>']
				devs[int(lc)]['dev_fullname'] = lcos.parsesysinfo(file=os.path.join(testpath, 'LC'+lc+'-sysinfo.txt'))['DEVICE'][0]
				devs[int(lc)]['dev_serial'] = lcos.parsesysinfo(file=os.path.join(testpath, 'LC'+lc+'-sysinfo.txt'))['SERIAL-NUMBER'][0]
		except:
			logger.warning('error when parsing files of LC{}: {}'.format(maindev, sys.exc_info()))
		my_test.add_devices(devs, maindev) # maindev = lowest number
		
		# the testresults are extracts of several csvfiles. This command also generates textual output which can be used for BatchTesters spawn_result.txt
		resulttext = []
		resulttext.extend(parsebttraffic.parse_BTtraffic(testpath, os.path.join(testpath,'iperf_short.csv'), unittag=unittag)) # <== add extracts of csvfile
		resulttext.extend(my_test.csv_add_extract(os.path.join(testpath,'iperf_short.csv'), testrun.get_empty_result(), {'columnsversus': [(1,0), (2,0), (3,0), (4,0), (5,0)]})) # <== add extracts of csvfile
		if lcoslog.parse_loadlog_to_csv(os.path.join(testpath, 'LC'+str(maindev)+'-telnetlog-1.log'), os.path.join(testpath, 'load.csv')):
			resulttext.extend(my_test.csv_add_extract(os.path.join(testpath, 'load.csv'), testrun.get_empty_result(), {'columnssteadyd': [0,1], 'columnsmedian': [0,1]})) # <== add extracts of csvfile
				
		#~ print '\n'.join(resulttext)

		with open(os.path.join(testpath,'spawn_result.txt'),'a') as f:
			f.write('\n'.join(resulttext))
		
		print my_test # the Testrun instance is directly printeable
		
		# open databases and write Testrun into them
		try:
			db_pg = testrun.PostgresNew(pg_host = 'lcs-qmdata', pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = test_setup, pg_schema_modify=True)
		except:
			print sys.exc_info()
			db_pg = None
		db_lite = testrun.SqliteNew(sqlite_file = os.path.join(dbpath,test_setup+'.sqlite'))
		
		my_test.write_db_with_backup(db_pg, db_lite)
		
		del my_test
		db_pg.close()
		db_lite.close()
