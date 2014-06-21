import sys
import logging
import time
import datetime

sys.path.append('/home/automaton/source')
from testcore.database import testrun
from testcore.database import tr_csv

logger = logging.getLogger(__name__)


class myTestrun(testrun.Testrun, tr_csv.TestrunCsv):
	"""make our own testclass
	
	our testclass combines the functionality of the base testrun.Testrun with the csv functionality by inheriting from both
	"""
	
	def __init__(self):
		"""call __init__ from the classes whe inherit from
		
		note: only the name of our own testclass has to be specified, not the ones we inherit from
		"""
		super(myTestrun, self).__init__()
	

def test_sleep(seconds):
	"""my awesome test which does sleep <seconds> seconds"""
	logger.info('Starting sleep test')
	
	start = datetime.datetime.now()
	try:
		# do something
		time.sleep(seconds)
		success = True
	except:
		success = False
	duration = datetime.datetime.now() - start
		
	logger.info('Finished sleep test')
	return success, duration.total_seconds()


if __name__=='__main__':

	# all modules generate output via python's logging class. 
	# we, as their user, can define which type of logging messages, and how we want so see them.
	# as default, the debuglevel, the name of the module which generated the message, and the message itself are displayed
	
	# set debuglevel to INFO (this will diyplay the levels INFO, WARNING, ERROR and CRITICAL, but not DEBUG)
	logging.basicConfig(level=logging.INFO)
	# chjange to format and include timestamps
	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	# log to a file instead of the console
	logging.basicConfig(filename='mytestrun.log')
	
	test_setup = 'example'
	
	try:
		db_pg = testrun.PostgresNew(pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = test_setup)
	except:
		db_pg = None
	db_lite = testrun.SqliteNew(sqlite_file = test_setup+'.sqlite')

	
	
	for testnum in [1, 2, 3, 4, 5, 6]:
		logger.info('test number {}'.format(testnum))
		
		if testnum==1:
			
			# perform a timing test, fill the Testrun instance, and store it
			
			my_test = myTestrun() # get an instance of testrun. all attributes will be set to default
			# update the basic information our testrun
			my_test.run.update({
				'run_testgroup' : 'test_examples',
				'run_testcfg':'lc1781.lcs',
				'run_mainversion':'8.92',
				'run_mainbuild':'0042',
				'run_maintag':'RC0',
			})
			my_test.run.update({
				'run_testfunc':'test_sleep',
			})
			
			success, duration = test_sleep(1.5)  # <== test function will return success=True and a time measurement
			my_test.set_result_success(success)
			
			result = {
				'res_item': 'PC-python2.7-sleep-1500',
				'res_source': '',
				'res_format': 'seconds',
				'res_value': duration, 
				'res_text': '',
			}
			my_test.add_result(result)
			
			print my_test
			my_test.write_db_with_backup(db_pg, db_lite)
			del my_test
			

		elif testnum==2:
			
			# perform atiming test that fails, fill the Testrun insance and store it
			
			
			my_test = myTestrun() # get an instance of testrun. all attributes will be set to default
			# update the basic information our testrun
			my_test.run.update({
				'run_testgroup' : 'test_examples',
				'run_testcfg':'lc1781.lcs',
				'run_mainversion':'8.92',
				'run_mainbuild':'0042',
				'run_maintag':'RC0',
			})
			my_test.run.update({
				'run_testfunc':'test_sleep',
			})
			
			success, duration = test_sleep(None)  # <== test function will return success = False
			my_test.set_result_success(success)
			
			result = {
				'res_item': 'PC-python2.7-sleep-None',
				'res_source': '',
				'res_format': 'seconds',
				'res_value': duration, 
				'res_text': '',
			}
			my_test.add_result(result)
			
			print my_test
			my_test.write_db_with_backup(db_pg, db_lite)
			del my_test

		
		elif testnum==3:
			
			# loop the timing test, store the vector in a seperate table of the Testrun instance, and store it
			
			my_test = myTestrun() # get an instance of testrun. all attributes will be set to default
			# update the basic information our testrun
			my_test.run.update({
				'run_testgroup' : 'test_examples',
				'run_testcfg':'lc1781.lcs',
				'run_mainversion':'8.92',
				'run_mainbuild':'0042',
				'run_maintag':'RC0',
			})
			my_test.run.update({
				'run_testfunc':'test_sleep',
			})
			
			successes = []
			durations = []
			for i in range(20):
				success, duration = test_sleep(0.025)
				successes.append(success)
				durations.append(duration)
			my_test.set_result_success(all(successes)) # True if all are True
			
			result = {
				'res_item': 'PC-python2.7-sleep-25-iter',
				'res_source': 'iter100',
				'res_format': '',
				'res_value': None, 
				'res_text': '',
			}
			my_test.add_resulttable({'headers': ['element','duration in seconds'], 'data': [range(len(durations)), durations]}, result)  # <== add a table consisting of list of vectors, and header names
			
			print my_test
			my_test.write_db_with_backup(db_pg, db_lite)
			del my_test
			
			
		if testnum in [4,5]:
			# straighforward csv file
			with open('ipsec-udp-throughput.csv','w') as f:
				f.write('\n'.join(el.strip() for el in 
					"""framesize,tunnel,throughput,fps,loss
					128,100,6.4,50013,0.0
					1024,100,51.2,50064,0.0
					1518,100,76.8,50111,0.0
					""".splitlines()))
				

		if testnum==4:
			
			# put complete csv table into the Testrun instance, and store it
			
			my_test = myTestrun() # get an instance of testrun. all attributes will be set to default
			# update the basic information our testrun
			my_test.run.update({
				'run_testgroup' : 'test_examples',
				'run_testcfg':'lc1781.lcs',
				'run_mainversion':'8.92',
				'run_mainbuild':'0042',
				'run_maintag':'RC0',
			})
			my_test.run.update({
				'run_testfunc':'ipsec-udp-full',
			})
			
			result = {
				'res_item': 'throughput_per_framesize',
				'res_source': '',
				'res_format': '',
				'res_value': None, 
				'res_text': '',
			}
			my_test.csv_add_fulltable('ipsec-udp-throughput.csv', result) # <== add a complete csvfile
			
			print my_test
			my_test.write_db_with_backup(db_pg, db_lite)
			del my_test
		
				
		if testnum==5:
			
			# put extracts of a csv table into the Testrun instance
			
			my_test = myTestrun() # get an instance of testrun. all attributes will be set to default
			# update the basic information our testrun
			my_test.run.update({
				'run_testgroup' : 'test_examples',
				'run_testcfg':'lc1781.lcs',
				'run_mainversion':'8.92',
				'run_mainbuild':'0042',
				'run_maintag':'RC0',
			})
			my_test.run.update({
				'run_testfunc':'ipsec-udp-full',
			})
			
			result = testrun.get_empty_result()
			options = tr_csv.csvoptions()
			options.update({
				'headersmeand': ['tunnel','fps'],
				'headersversus' : [('framesize','throughput')],
			})
			my_test.csv_add_extract('ipsec-udp-throughput.csv', result, options) # <== add extracts of csvfile
			
			print my_test
			my_test.write_db_with_backup(db_pg, db_lite)
			del my_test

			
		if testnum in [6]:
			# csvfile with several blocks, and header not directly followed by data
			with open('ipsec-udp-throughput-large.csv','w') as f:
				f.write('\n'.join(el.strip() for el in 
					"""testsuite,version
					IxLoad,6.30
					
					framesize,tunnel,throughput,fps,loss
					number,numer,number,number,percentage
					128,100,6.4,50013,0.0
					1024,100,51.2,50064,0.0
					1518,100,76.8,50111,0.0
					""".splitlines()))
				
		if testnum==6:
			
			# put extracts of a csv table into the Testrun instance, with the csv table consisting of extra stiff we want to ignore  
			
			my_test = myTestrun() # get an instance of testrun. all attributes will be set to default
			# update the basic information our testrun
			my_test.run.update({
				'run_testgroup' : 'test_examples',
				'run_testcfg':'lc1781.lcs',
				'run_mainversion':'8.92',
				'run_mainbuild':'0042',
				'run_maintag':'RC0',
			})
			my_test.run.update({
				'run_testfunc':'ipsec-udp-full',
			})
			
			result = testrun.get_empty_result()
			options = tr_csv.csvoptions()
			options.update({
				'headersmeand': ['tunnel','fps'],
				'headersversus' : [('framesize','throughput')],
				'blocknum' : 1,
				'datastart': 2,
			})
			my_test.csv_add_extract('ipsec-udp-throughput.csv', result, options) # <== add extracts of csvfile
			
			print my_test
			my_test.write_db_with_backup(db_pg, db_lite)
			del my_test
			
			
		
		print '-'*100
			
			
