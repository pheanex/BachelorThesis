import sys
import os
import logging
import datetime
import traceback
import testrun
# import exception
# 

logger = logging.getLogger(__name__)

def sql_in_pg(l):
	return '(' + ','.join(["'"+el+"'" for el in l]) +')'
	
	
class QueryError(Exception):
	def __init__(self, msg):
		self.value = msg
	def __str__(self):
		return self.value
		
class PGnewQuery(object):
	
	def __init__(self):
		super(PGnewQuery, self).__init__() # init next class in MRO
		
	def _query_fw_runkey_reskey(self, selectlist, fw, runkey, reskey):
		"""
		query database for elements matching the specified fwversion, runkey and reskey (all keys are tuples)
		fw can be ignored with fw=None
		
		select contains the table items which should be SELECTed
		
		"""
		
		# aggregate all items we have to select
		qd = {}
		if fw is not None:
			try:
				qd['run_mainversion'], qd['run_mainbuild'] = fw
			except:
				raise QueryError('firmware {} ist not valid, check builds definition'.format(fw))
		try:
			qd['run_testroot'], qd['run_testgroup'], qd['run_testfunc'], qd['run_testcfg'] = runkey
		except:
			raise QueryError('runkey {} ist not valid'.format(runkey))
		try:
			qd['res_item'], qd['res_source'], qd['res_format'] = reskey
		except:
			raise QueryError('reskey {} ist not valid'.format(reskey))
		
		# separate items by table
		runquery = []
		resquery = []
		for key in qd:
			if qd[key] is not None:
				if isinstance(qd[key], basestring): # in py3: isinstance(qd[key], str)
					# string 
					if key.startswith('run_'):
						runquery.append('testruns.{0}=%({0})s'.format(key))
					if key.startswith('res_'):
						resquery.append('testresults.{0}=%({0})s'.format(key))
				else:
					# list, tuple, iterator etc.
					if key.startswith('run_'):
						runquery.append('testruns.{0} IN {1}'.format(key, sql_in_pg(qd[key])))
					if key.startswith('res_'):
						resquery.append('testresults.{0} IN {1}'.format(key, sql_in_pg(qd[key])))
					
		# try to build the optimal query.
		select = ', '.join(selectlist)
		querycur = self.con.cursor()
		try:
			if select.startswith('testruns.'):
				if len(resquery)>0:
					querycur.execute('''
						SELECT {1}
						FROM {0}.testruns
						WHERE {2} AND testruns.run_ID IN (
							SELECT testresults.res_runID
							FROM {0}.testresults
							WHERE {3}
						)
						ORDER BY testruns.run_mainbuild, testruns.run_ID;
					'''.format( self.schema, select, ' AND '.join(runquery), ' AND '.join(resquery)), qd)
				else:
					querycur.execute('''
						SELECT {1}
						FROM {0}.testruns
						WHERE {2}
						ORDER BY testruns.run_mainbuild, testruns.run_ID;
					'''.format( self.schema, select, ' AND '.join(runquery), ' AND '.join(resquery)), qd)
			elif select.startswith('testresults.'):	
				if len(runquery)>0:
					querycur.execute('''
						SELECT {1}
						FROM {0}.testresults JOIN {0}.testruns ON  testresults.res_runID = testruns.run_ID
						WHERE {3} AND {2}
						ORDER BY testruns.run_mainbuild, testruns.run_ID;
					'''.format( self.schema, select, ' AND '.join(runquery), ' AND '.join(resquery)), qd)
				else:
					querycur.execute('''
						SELECT {1}
						FROM {0}.testresults JOIN {0}.testruns ON  testresults.res_runID = testruns.run_ID
						WHERE {3}
						ORDER BY testruns.run_mainbuild, testruns.run_ID;
					'''.format( self.schema, select, ' AND '.join(runquery), ' AND '.join(resquery)), qd)
			else:
				logger.error('SELECT {} failed'.format(select))
				return []
		except:
			logger.error('Database access failed: {}'.format(traceback.format_exc()))
			return []
			
		results = querycur.fetchall()
		if results is not None:
			return results
		else:
			return []		

	
	def query_ids_for_fw_runkey_reskey(self, fw, runkey, reskey):
		"""return run_ID for runs matching runkey and reskey for specified fw"""
		return [el[0] for el in self._query_fw_runkey_reskey(['testruns.run_ID'], fw, runkey, reskey)]
		
	def query_values_for_fw_runkey_reskey(self, fw, runkey, reskey):
		"""return the res_value element for for runs matching runkey and reskey for specified fw"""
		return [el[0] for el in self._query_fw_runkey_reskey(['testresults.res_value'], fw, runkey, reskey)]
		
	def query_texts_for_fw_runkey_reskey(self, fw, runkey, reskey):
		"""return the res_text element for for runs matching runkey and reskey  for specified fw"""
		return [el[0] for el in self._query_fw_runkey_reskey(['testresults.res_text'], fw, runkey, reskey)]
		
	def query_successes_for_fw_runkey(self, fw, runkey):
		"""return a success (True|False) vector matching runkey for specified fw"""
		return [[False, True][int(el[0])] for el in self._query_fw_runkey_reskey(['testresults.res_value'], fw, runkey, ('testsuccess',None,'bool'))]
		
	def query_successes_builds_ids_for_fw_runkey(self, fw, runkey):
		"""return a success-tuple (True|False, build, run_ID) vector matching runkey for specified fw"""
		return [ ([False, True][int(el[0])], el[1], el[2]) for el in self._query_fw_runkey_reskey(['testresults.res_value', 'testruns.run_mainbuild', 'testruns.run_ID'], fw, runkey, ('testsuccess',None,'bool'))]

	def query_results_for_fw_runkey_reskey(self, fw, runkey, reskey):
		"""return a result-tuple (res_item, res_source, res_format, res_value, res_text) vector matching runkey and reskey for specified fw"""
		return self._query_fw_runkey_reskey(['testresults.res_item', 'testresults.res_source',  'testresults.res_format', 'testresults.res_value', 'testresults.res_text'], fw, runkey, reskey)
		
	def query_results_builds_ids_for_fw_runkey_reskey(self, fw, runkey, reskey):
		"""return a result-tuple (res_item, res_source, res_format, res_value, res_text, run_mainbuild, run_ID) vector matching runkey and reskey for specified fw"""
		return self._query_fw_runkey_reskey(['testresults.res_item', 'testresults.res_source',  'testresults.res_format', 'testresults.res_value', 'testresults.res_text', 'testruns.run_mainbuild', 'testruns.run_ID'], fw, runkey, reskey)

	def query_resultdicts_for_fw_runkey_reskey(self, fw, runkey, reskey):
		"""return a dict (elements: res_item, res_source, res_format, res_value, res_text) vector matching runkey and reskey for specified fw"""
		return [{'res_item': res_item, 'res_source': res_source, 'res_format': res_format, 'res_value': res_value, 'res_text': res_text} 
			for res_item, res_source, res_format, res_value, res_text in self.query_results_for_fw_runkey_reskey(fw, runkey, reskey)]
			
	def query_resultdicts_builds_ids_for_fw_runkey_reskey(self, fw, runkey, reskey):
		"""return a dict (elements: res_item, res_source, res_format, res_value, res_text, run_mainbuild, run_ID) vector matching runkey and reskey for specified fw"""
		return [{'res_item': res_item, 'res_source': res_source, 'res_format': res_format, 'res_value': res_value, 'res_text': res_text, 'run_mainbuild': run_mainbuild, 'run_ID': run_ID}
			for res_item, res_source, res_format, res_value, res_text, run_mainbuild, run_ID in self.query_results_builds_ids_for_fw_runkey_reskey(fw, runkey, reskey)]
			
	def query_testruns_for_fw_runkey_reskey(self, fw, runkey, reskey):
		"""return a Testrun-instance vector matching runkey and reskey for specified fw"""
		testruns=[]
		for id in self.query_ids_for_fw_runkey_reskey(fw, runkey, reskey):
			run = testrun.Testrun()
			self.get_testrun(run, run_ID=id)
			testruns.append(run)
		return testruns
		
	def query_exists_success_for_runkey(self, runkey):
		"""return True|False wether there are any successes for runkey in the database, regardless of fw"""
		return len(self.query_successes_for_fw_runkey(None, runkey))>0
		
		
			


