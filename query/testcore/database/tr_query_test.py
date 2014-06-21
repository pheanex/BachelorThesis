import logging
from testcore.database import testrun
from testcore.database import tr_query

logger = logging.getLogger(__name__)

"""
unittests for tr_query
uses data written by db_testlink_unittest
"""


class myDB(testrun.PostgresNew, tr_query.PGnewQuery):
	"""make our own database class
	
	our testclass combines the functionality of the base testrun.PostgresNew with the query functionality by inheriting from both
	"""
	
	def __init__(self, *args, **kwargs):
		"""call __init__ from the classes we inherit from
		
		note: only the name of our own testclass has to be specified, not the ones we inherit from
		"""
		super(myDB, self).__init__(*args, **kwargs)

def invert(vec):
	return [not el for el in vec]
	
		
if __name__=='__main__':
	
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	
	test_setup = 'meta_testlink_unittest'
	logger.debug('open db')

	d = myDB(pg_host = 'lcs-qmdata.lcs.intern', pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = test_setup)
	
	t = testrun.Testrun()
	
	builds = ['{0:04d}'.format(b) for b in range(0,101)]

	logger.info('query_ids_for_fw_runkey_reskey unittest')
		
	logger.debug('alltrue was written first into db, so return 1,2...100')
	values = []
	for id in d.query_ids_for_fw_runkey_reskey(
		('8.84',  builds), 
		(None, 'alltrue', None, None),
		('free memory', 'show mem', 'MByte')):
		values.append(id)
	logger.debug(values)
	assert all([a==b for a,b in zip(values, range(1,102))])
	assert len(values)==len(builds)
	
	logger.info('query_values_for_fw_runkey_reskey unittest')
	
	logger.debug('alltrue values were set to floatingpoint build number, so return 0.0,2.0...100.0')
	values = []
	for value in d.query_values_for_fw_runkey_reskey(
		('8.84',  builds), 
		(None, 'alltrue', None, None),
		('free memory', 'show mem', 'MByte')):
		values.append(value)
	logger.debug(values)
	assert all([a==float(b) for a,b in zip(values, range(0,101))])
	assert len(values)==len(builds)

	logger.info('query_texts_for_fw_runkey_reskey unittest')
	
	logger.debug('alltrue texts were set to floatingpoint build number, so return 0.0,2.0...100.0')
	values = []
	for value in d.query_texts_for_fw_runkey_reskey(
		('8.84',  builds), 
		(None, 'alltrue', None, None),
		('free memory', 'show mem', 'MByte')):
		values.append(value)
	logger.debug(values)
	assert all([a==str(float(b)) for a,b in zip(values, range(0,101))])
	assert len(values)==len(builds)

	logger.info('query_successes_for_fw_runkey unittests')

	logger.debug('alltrue successes were set to True, so return True...True')
	values = []
	for value in d.query_successes_for_fw_runkey(
		('8.84', builds), 
		(None, 'alltrue', None, None)):
		values.append(value)
	logger.debug(values)
	assert all(values)
	assert len(values)==len(builds)
		
	logger.debug('allfalse successes were set to False, so return False...False')
	values = []
	for value in d.query_successes_for_fw_runkey(
		('8.84', builds), 
		(None, 'allfalse', None, None)):
		values.append(value)
	logger.debug(values)
	assert all(invert(values))
	assert len(values)==len(builds)
	
	
	logger.debug('alltrue2 successes were set to 2*True, so return True,True')
	values = []
	for value in d.query_successes_for_fw_runkey(
		('8.84', builds), 
		(None, 'alltrue2', None, None)):
		values.append(value)
	logger.debug(values)
	assert all(values)
	assert len(values)==len(builds)*2
		
	logger.debug('truefalse_samebuild successes were set to True False, so return True False True False...')
	values = []
	for value in d.query_successes_for_fw_runkey(
		('8.84', builds), 
		(None, 'truefalse_samebuild', None, None)):
		values.append(value)
	logger.debug(values)
	assert all(values[::2])
	assert all(invert(values[1::2]))
	assert len(values)==len(builds)*2
		
	logger.debug('truefalse_alternatingbuild successes were set to False True, so return False True False...')
	values = []
	for value in d.query_successes_for_fw_runkey(
		('8.84', builds), 
		(None, 'truefalse_alternatingbuild', None, None)):
		values.append(value)
	logger.debug(values)
	assert all(values[1::2])
	assert all(invert(values[::2]))
	assert len(values)==len(builds)
		
	logger.debug('hightrue highest build was written first but is only one True, builds should be sorted so return False False... True')
	values = []
	for value in d.query_successes_for_fw_runkey(
		('8.84', builds), 
		(None, 'hightrue', None, None)):
		values.append(value)
	logger.debug(values)
	assert values[-1]==True
	assert all(invert(values[:-1]))
	assert len(values)==len(builds)


	logger.debug('get memory result tuples of alltrue, MByte value should be te same as the build')
	for n, result in enumerate(d.query_results_for_fw_runkey_reskey(
		('8.84',  builds), 
		(None, 'alltrue', None, None),
		('free memory', 'show mem', 'MByte'))):	
		assert n==int(result[3])
		
	logger.debug('get memory result tuples of alltrue, MByte value should be te same as the build')
	for n, result in enumerate(d.query_results_builds_ids_for_fw_runkey_reskey(
		('8.84',  builds), 
		(None, 'alltrue', None, None),
		('free memory', 'show mem', 'MByte'))):	
		assert n==int(result[3])
		assert n==int(result[5])
		assert n==int(result[6])-1
		
	logger.debug('get memory result dicts of alltrue, MByte value should be te same as the build')
	for n, result in enumerate(d.query_resultdicts_for_fw_runkey_reskey(
		('8.84',  builds), 
		(None, 'alltrue', None, None),
		('free memory', 'show mem', 'MByte'))):	
		assert n==int(result['res_value'])
	
	logger.debug('get memory result dicts of alltrue, MByte value should be te same as the build')
	for n, result in enumerate(d.query_resultdicts_builds_ids_for_fw_runkey_reskey(
		('8.84',  builds), 
		(None, 'alltrue', None, None),
		('free memory', 'show mem', 'MByte'))):	
		assert n==int(result['res_value'])
		assert n==int(result['run_mainbuild'])
		assert n==int(result['run_ID'])-1
	
	logger.debug('get complete testruns alltrue, MByte value should be te same as the build')
	for n, run in enumerate(d.query_testruns_for_fw_runkey_reskey(
		('8.84',  builds), 
		(None, 'alltrue', None, None),
		('free memory', 'show mem', 'MByte'))):	
		assert n==int(run.run['run_mainbuild'])
		assert n==int(run.results[('free memory', 'show mem', 'MByte')]['res_value'])
		
	logger.debug('test wether any successes exists')
	assert d.query_exists_success_for_runkey((None, 'alltrue', None, None))
	assert d.query_exists_success_for_runkey((None, 'nonexisting', None, None))==False


	
	logger.info('finished successfully')