import sys
import os
import logging
import time
import datetime

from testcore.database import testrun
from testcore.database import tr_csv
from testcore.parseoutput import lcos
from testcore.parseoutput import batchtester
logger = logging.getLogger(__name__)


"""
Put the results of an IXIA testrun into a Testrun instance and save it to the database
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
	
	test_setup = 'IxAutomateExample' # each test setup has its own table schema inside the main PostgreSQL database. For SQLite, this maps directly to the filename.
	dbpath = r'c:\testlib\parser'	
	
	# set debuglevel to INFO (this will diyplay the levels INFO, WARNING, ERROR and CRITICAL, but not DEBUG), customize the logger output, and let it write to a file instead stdout
	logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=os.path.join(dbpath,'Py27-genres-IxA.log'))
	
	if len(sys.argv)==2:
		testpath = sys.argv[1]
			
		my_test = myTestrun() # get an instance of testrun. all attributes will be set to default
		
		my_test.run.update(batchtester.parsepath(testpath)) # update the basic information our testrun from the batchtester path

		# try to add device and firmware specific data to the Testrun instance
		try:
			devs = batchtester.parsefwlist(file=os.path.join(testpath, 'fwlist.csv'))
			devs[1]['dev_ldversion'], devs[1]['dev_ldbuild'] = lcos.parsefirmsafe(file=os.path.join(testpath, 'LC1-firmsafe.txt'))['<loader>']
			devs[1]['dev_fullname'] = lcos.parsesysinfo(file=os.path.join(testpath, 'LC1-sysinfo.txt'))['DEVICE'][0]
			my_test.add_devices(devs, 1) # maindev = 1
		except:
			pass
		
		# the testresults are extracts of several csvfiles. This command also generates textual output which can be used for BatchTesters spawn_result.txt
		resulttext = my_test.csv_add_extract(os.path.join(testpath, 'AggregateResults.csv'), testrun.get_empty_result(),  {'columnsmeand': [2,4], 'columnsmedian': [2,4], 'columnsversus': [(2,1),(4,1)]})
		with open(os.path.join(testpath,'spawn_result.txt'),'a') as f:
			f.write('\n'.join(resulttext))
		
		print my_test # the Testrun instance is directly printeable

		# open databases and write Testrun into them
		try:
			db_pg = testrun.PostgresNew(pg_host = 'lcs-qmdata', pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = test_setup)
		except:
			print sys.exc_info()
			db_pg = None
		db_lite = testrun.SqliteNew(sqlite_file = os.path.join(dbpath,test_setup+'.sqlite'))

		my_test.write_db_with_backup(db_pg, db_lite)
		
		del my_test
		db_pg.close()
		db_lite.close()
		
	

			
