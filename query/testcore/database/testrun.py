# coding: utf-8

import sys
import os
import sqlite3
import psycopg2
import datetime
import logging
import operator
import traceback


from testcore.parseoutput import lcos


logger = logging.getLogger(__name__)

def get_empty_testrun():
	return {
		'run_timestamp': None, 
		'run_testroot': '',
		'run_testgroup' : '',
		'run_testfunc':'',
		'run_testcfg':'',
		'run_mainversion':'',
		'run_mainbuild':'',
		'run_maintag':'',
		'run_maindev': None,
	}
	
def get_empty_device():
	return {
		'dev_fwfile':  '', 
		'dev_fwdev': '', 
		'dev_fwversion': '', 
		'dev_fwbuild': '', 
		'dev_ldversion': '', 
		'dev_ldbuild': '', 
		'dev_fullname': '', 
		'dev_serial': '',
	}

def get_empty_result():
	return {
		'res_item': '',
		'res_source': '',
		'res_format': '',
		'res_value': None, 
		'res_text': '',
	}	

	
class Testrun(object):
	"""
	container for a single testrun
	
	self._run_ID can be set when instancing class. It will be used when reading from a database, but a writing to a database overwrites this value to the written one.
	
	self.run dictionary has elements
		run_timestamp DATETIME
		run_testroot
		run_testgroup
		run_testfunc
		run_testcfg
		run_mainversion
		run_mainbuild
		run_maintag
		run_maindev INTEGER
		
	self.devices is a dict of dictionaries. the first level contains the devnum to seperate different devices. The second level has elements:
		dev_devnum
		dev_fwfile
		dev_fwdev
		dev_fwversion
		dev_fwbuild
		dev_ldversion
		dev_ldbuild
		dev_fullname
		dev_serial
		
	self.testresults dictionary has elements
		res_item
		res_source
		res_format
		res_value FLOAT
		res_text
		
	addtional tables can contain arbitrary data. To fill it, pass a dictionary to add_resulttables of the follwing structure:
		name
		headers list
		data list of lists
	
	example:

	run = Testrun()
	run.add_devices({
		0: {'dev_fwfile':  '.upx', 'dev_fwdev': 'LC-9100', 'dev_fwversion': '8.70', 'dev_fwbuild': '0030', 'dev_ldversion': '', 'dev_ldbuild': '', 'dev_fullname': '', 'dev_serial': '12345'}
	})
	run.run['run_maindev'] = 0
	run.add_results([
		{'res_item': 'item', 'res_source': 'source','res_format': 'format', 'res_value': 3.14, 'res_text': u'pi'},
		{'res_item': 'item2', 'res_source': 'source','res_format': 'format', 'res_value': 2.71, 'res_text': u'e'},
	])
	run.add_resulttables({
		'headers': [
			'einer',
			'zehner',
		], 
		'data': [
			[1, 2, 3],
			[11, 22, 33],
		],
	})
	run.add_results([
		{'res_item': 'item3', 'res_source': 'source','res_format': '_FULLTABLE', 'res_value': 0, 'res_text':'tab01'},
	])
	
	"""
	
	def __init__(self, run_ID=None):
		""" init an empty testrun. The run_ID can be specified to allow reading from a database"""
		super(Testrun, self).__init__() # init next class in MRO
		self._run_ID = run_ID
		self.run = get_empty_testrun()
		self.set_run_timestamp_now()
		self.devices = {}
		self.results = {}
		self.resulttables = {}
		
	def set_run_timestamp_now(self):
		"""set current time (without microseconds)"""
		self.run['run_timestamp'] = datetime.datetime.now().replace(microsecond = 0)
		
	def set_run_ID(self, id):
		self._run_ID = id
		
	def get_run_ID(self):
		return self._run_ID
		
		
	def add_devices(self, devdicts, maindev=None):
		"""
		add devices to self.devices in a dict of dicts 
		parameters can be empty, e.g.:
		
		run.add_devices({
			0: {'dev_fwfile':  '.upx', 'dev_fwdev': 'LC-9100', 'dev_fwversion': '8.70', 'dev_fwbuild': '0030', 'dev_ldversion': '', 'dev_ldbuild': '', 'dev_fullname': '', 'dev_serial': '12345'}
		})
		
		if maindev in specified, this devices data is inserted into run_mainversion etc.
		"""
		for devnum in devdicts:
			self.devices[devnum] = get_empty_device()
			self.devices[devnum].update(devdicts[devnum])
		if maindev is not None and self.devices.has_key(maindev):
			self.run['run_mainversion'] = self.devices[maindev]['dev_fwversion']
			self.run['run_mainbuild'] = self.devices[maindev]['dev_fwbuild']
			self.run['run_maindev'] = maindev
			
	def add_result(self, resdict, force=False):
		"""
		add results given in a list of resultdicts, e.g.
		
		run.add_result({'res_item': 'item', 'res_source': 'source','res_format': 'format', 'res_value': 3.14, 'res_text': u'pi'},
			{'res_item': 'item2', 'res_source': 'source','res_format': 'format', 'res_value': 2.71, 'res_text': u'e'})
		
		internally, the data is sored in a dict with a compund key of res_item, res_source, res_format
		"""
		
		key = (resdict['res_item'], resdict['res_source'], resdict['res_format'])
		if self.results.has_key(key) and not force:
			raise NameError('tried to add duplicate key '+repr(key)+' to results '+str(self))
		self.results[key] = {'res_value': resdict['res_value'], 'res_text': resdict['res_text']}
			
	def add_results(self, resdicts, force=False):
		"""
		add results given in a list of resultdicts, e.g.
		
		run.add_results([
			{'res_item': 'item', 'res_source': 'source','res_format': 'format', 'res_value': 3.14, 'res_text': u'pi'},
			{'res_item': 'item2', 'res_source': 'source','res_format': 'format', 'res_value': 2.71, 'res_text': u'e'},
		])
		
		internally, the data is sored in a dict with a compund key of res_item, res_source, res_format
		"""
		
		for resdict in resdicts:
			self.add_result(resdict, force)
			
	def add_resulttable(self, tabledict, resdict):
		"""add an seperate table to database which is contained in a dict. 
		
		When writing to a database, name has to be unique.

		run.add_resulttable({
			'name': 'tab01',
			'headers': [
				'einer',
				'zehner',
			], 
			'data': [
				[1, 2, 3],
				[11, 22, 33],
			],
		})
		run.add_results([
			{'res_item': 'item3', 'res_source': 'source','res_format': '_FULLTABLE', 'res_value': 0, 'res_text':'tab01'},
		])
		"""
		if len(tabledict['headers']) != len(tabledict['data']):
			raise NameError('number of table headers and table colums not equal')
			
		if len(set([len(line) for line in tabledict['data']])) != 1:
			raise NameError('length of table columns unequal')
			
		tablename = '{0}-{1}'.format(resdict['res_item'], resdict['res_source'])
			
		self.resulttables[tablename] = tabledict
		resdict['res_format'] = '_FULLTABLE'
		resdict['res_text'] = tablename
		resdict['res_value'] = 0
		self.add_result(resdict)
		
	def add_resulttables(self, tablereslist):
		"""add several tables at once"""
		for tabledict, desdict in tablereslist:
			self.add_resulttable(tabledict, desdict)
			
			
	def read_db(self, dbclass, run_ID=None, forcekey=False):
		"""read testrun through specified database instance"""
		self.__init__(run_ID)
		dbclass.get_testrun(self, forcekey=forcekey)	
	
	def write_db(self, dbclass):
		"""write testrun through specified database instance"""
		dbclass.write_testrun(self)

	def write_db_with_backup(self, dbclass, dbclass_backup):
		"""write testrun through specified database instance; if not accessible, keep in backup database and try to submit next time"""
		# first, write current testrun in backup
		self.write_db(dbclass_backup)
		# then, try to move all testruns from backup to normal database
		move = Testrun()
		for run_ID in dbclass_backup.get_testrun_IDs():
			move.read_db(dbclass_backup, run_ID)
			try:
				move.write_db(dbclass)
				move.remove_db(dbclass_backup, run_ID) # specify run_ID since write_db has overwritten it
				logger.info('moved successfully testrun {0}->{1} from backup ({2}) to normal ({3})'.format(run_ID, move.get_run_ID(), dbclass_backup, dbclass))
			except:
				logger.warning('moving testrun {0} from backup ({1}) to normal ({2}) failed: {3}'.format(run_ID, dbclass_backup, dbclass, traceback.format_exc()))
				return False
		return True

		
	def remove_db(self, dbclass, run_ID=None):
		"""remove testrun with run_ID from database. If run_ID parameter is not present, take from self"""
		if run_ID is not None:
			dbclass.remove(run_ID)
		else:
			dbclass.remove(self.get_run_ID())
		

	def set_result_success(self, bool):
		"""simple standardized test verdict of True or False"""
		resdict = get_empty_result()
		resdict['res_item'] = 'testsuccess'
		resdict['res_format'] = 'bool'
		resdict['res_value'] = [0.0,1.0][bool]
		resdict['res_text'] = ['False','True'][bool]
		self.add_result(resdict, force=True)
			
	def get_result_success(self):
		"""simple standardized test verdict of True or False"""
		key = ('testsuccess','','bool')
		if self.results.has_key(key):
			return [False, True][int(self.results[key]['res_value'])]
	
	
	def __str__(self):
		"""pretty print testresult instance, e.g. 'print mytestrun' can be used"""
		
		output = []
		output.append('testrun _run_ID: '+repr(self.get_run_ID()))
		
		output.append('testrun runkey: ('+', '.join([['None', repr(self.run[key])][self.run[key]!='']  for key in ['run_testroot', 'run_testgroup', 'run_testfunc', 'run_testcfg']])+')')
		output.append('testrun:')
		for key in sorted(self.run):
			output.append('  {0:20}: {1}'.format(key, repr(self.run[key])))
		output.append('devices:')
		for dev in sorted(self.devices):
			output.append('  device '+str(dev)+':')
			for key in sorted(self.devices[dev]):
				output.append('    {0:18}: {1}'.format(key, repr(self.devices[dev][key])))
		output.append('results:')
		for reskey in sorted(self.results, key=operator.itemgetter(0,1,2)):
			output.append("  "+repr(reskey))
			if reskey[2]=='_FULLTABLE':
				tablename = self.results[reskey]['res_text']
				if self.resulttables.has_key(tablename):
					output.append('    tablename         : "{0}"'.format(tablename))
					output.append('    tableheaders      : {0}'.format(', '.join(self.resulttables[tablename]['headers'])))
					output.append('    rows              : {0}'.format(len(self.resulttables[tablename]['data'][0])))
					output.append('    columns           : {0}'.format(len(self.resulttables[tablename]['headers'])))
					for col, header in enumerate(self.resulttables[tablename]['headers']):
						output.append('      {0:16}: {1}'.format(header, self.resulttables[tablename]['data'][col]))
					
				else:
					output.append('    TABLE '+tablename+' NOT FOUND')
			else:
				if reskey[2]=='text':
					for n, line in enumerate(self.results[reskey]['res_text'].splitlines()):
						if n==0:
							output.append('    res_text          : '+line)
						else:
							output.append(24*' '+line)
				else:	
					for key,val in self.results[reskey].items():
						output.append('    {0:18}: {1}'.format(key, repr(val)))

		output.append('')
		return '\n'.join(output)

		
	def __eq__(self, other):
		"""
		allow to compare two class instances with the == operator
		"""
		
		def comp_dict(a,b):
			"""helper for comparing two dicts"""
			if set(a.keys()) != set(b.keys()):
				logger.warning('testrun compare: keys mismatch')
				return False
			else:
				for key in a.keys():
					logger.debug('testrun compare: testing key {0}'.format(key))
					if a[key] != b[key]:
						logger.warning('testrun compare: values for key {0} mismatch: {1} vs. {2}'.format(key, repr(a[key]), repr(b[key]) ))
						return False
			return True
		
		if self.get_run_ID() != other.get_run_ID(): return False
		
		if not comp_dict(self.run, other.run): return False
		
		if set(self.devices.keys()) != set(other.devices.keys()): return False
		for devnum in self.devices.keys():
			logger.debug('testrun compare: testing dev {0}'.format(devnum))
			if not comp_dict(self.devices[devnum], other.devices[devnum]): return False
			
		if not comp_dict(self.results, other.results): return False
		
		if set(self.resulttables.keys()) != set(other.resulttables.keys()): return False
		for table in self.resulttables.keys():
			logger.debug('testrun compare: testing table {0}'.format(table))
			if self.resulttables[table]['headers'] != other.resulttables[table]['headers']: 
				logger.warning('testrun compare: table {0} headers mismatch'.format(table))
				return False
			# data comparision is a little bit more complex since all data elemnets coming from database will be strings (or even unicode)
			for colA, colB in zip(self.resulttables[table]['data'], other.resulttables[table]['data']):
				#~ if colA != colB: 
					#~ logger.warning('testrun compare: columns mismatch {} vs {}'.format(repr(colA), repr(colB)))
				if map(str, colA) != map(str, colB): 
					logger.warning('testrun compare: columns mismatch {0} vs {0} after map(str)'.format(repr(colA), repr(colB)))
					return False
			
		return True



class DbBase(object):
	""" public API for the several database classes """
	
	id = 'DbBase'
	
	def __init__(self, *args, **kwargs):
		""" Initialize a database connection.

		This is usually specific to the database (e.g.simple filename or ip with user credentials)  
		"""
		super(DbBase, self).__init__() # init next class in MRO
		
	def write_testrun(self, testrun):
		""" Write a single Testrun instance into the database.
		
		writing changes the run_ID attribute to the index used when writing to the database.
		note: twriting is not supported for the SliteOld class.
		"""
		pass

	def get_testrun(self, testrun, run_ID, forcekey=False):
		""" Fill the Testrun instance from the database entry specified by run_ID. 
		
		run_ID is optional. If it is not specified here, the run_ID attribute must already be set insite the Trestrun instance.
		"""
		pass

		
	def close(self):
		""" close the database connection
		"""
		pass
			
	def remove(self, run_ID):
		""" delete all data entries / testresult tables of testrun run_ID in the database
		"""
		pass
			
	def iter_testrun_IDs(self):
		""" iterate through all run_IDs existing in the database
		
		example:
		run = Testrun()
		for id in my_db.iter_testrun_IDs():
			my_db.get_tesrun(run, id)
			print run
		"""
		pass
		
	def __str__(self):
		"""get info string abaout database instance"""
		pass
		

class PostgresNew(DbBase):
	
	id = 'PostgresNew'
	
	def __init__(self, pg_host=None, pg_port=5432, pg_database='qstests', pg_user='', pg_password='', pg_schema='example', pg_schema_modify=False, pg_clearalltables=False):
		super(PostgresNew, self).__init__() # init next class in MRO
		
		if pg_host is None:
			self.con = psycopg2.connect(database=pg_database, user=pg_user, password=pg_password)
			self.databaseinfo  = 'PostgresSQL, local, database {0} using schema {1}'.format(pg_database, pg_schema)
		else:
			self.con = psycopg2.connect(host=pg_host, port=pg_port, database=pg_database, user=pg_user, password=pg_password)
			self.databaseinfo  = 'PostgresSQL, remote {0}:{1}, database {2} using schema {3}'.format(pg_host, pg_port, pg_database, pg_schema)
			
		self.cur = self.con.cursor() # note: use this ready-to-use cursor object only in atomic operations - do not nest operations.
		self.schema = pg_schema.lower()
		if pg_schema_modify:
			self._modify_schema(pg_clearalltables)


	def _modify_schema(self, pg_clearalltables):
		"""
		(re)create schema
		if schema self.pg_schema is not existing, create it
		if schema is existing and self.pg_clearalltables contains the magic word, drop all data in existing schema
		"""
		# test if schema already exists
		# self.cur_out.execute("CREATE SCHEMA IF NOT EXISTS {0};".format(self.schema)) # not in 9.1
		self.cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name='{0}';".format(self.schema))
		if self.cur.rowcount==0:
			self.cur.execute("CREATE SCHEMA {0};".format(self.schema))
			self.cur.execute("GRANT USAGE ON SCHEMA {0} TO public;".format(self.schema))
			self._create_tables()
			logger.info('created shema {0}'.format(self.schema))
		else:
			if pg_clearalltables=='IKNOWWHATIMDOING':
				self.cur.execute("DROP SCHEMA {0} CASCADE".format(self.schema))
				self.cur.execute("CREATE SCHEMA {0};".format(self.schema))
				self.cur.execute("GRANT USAGE ON SCHEMA {0} TO public;".format(self.schema))
				self._create_tables()
				logger.info('recreated shema {0}'.format(self.schema))
			else:
				logger.debug('acessing existing shema {0}'.format(self.schema))

			
		# grant access rights to public

		
	def get_available_schemas(self):
		""" return list of all available schemas in the database """
		self.cur.execute("SELECT schema_name FROM information_schema.schemata")
		schemas = self.cur.fetchall()
		return [el[0] for el in schemas]
		

	def get_highest_runID(self):
		""" look for highest run_ID """
		self.cur.execute("SELECT run_ID FROM {0.schema}.testruns ORDER BY run_ID DESC LIMIT 1;".format(self))
		last_ids = self.cur.fetchall()
		if len(last_ids)>0:
			return last_ids[0][0]
		else:
			return None

	
	def __str__(self):
		"""return info string for use by print etc."""
		return self.databaseinfo

	# pg_new
	def _create_tables(self):
		self.cur.execute("""
			CREATE TABLE IF NOT EXISTS {0.schema}.testruns (
				run_ID SERIAL PRIMARY KEY,
				run_timestamp TIMESTAMP(0),
				run_testroot TEXT,
				run_testgroup TEXT,
				run_testfunc TEXT,
				run_testcfg TEXT,
				run_mainversion TEXT,
				run_mainbuild TEXT,
				run_maintag TEXT,
				run_maindev INTEGER
			)
		""".format(self))
		self.cur.execute("""
			CREATE TABLE IF NOT EXISTS {0.schema}.testdevices (
				dev_runID INTEGER,
				dev_devnum INTEGER,
				dev_fwfile TEXT,
				dev_fwdev TEXT,
				dev_fwversion TEXT,
				dev_fwbuild TEXT,
				dev_ldversion TEXT,
				dev_ldbuild TEXT,
				dev_fullname TEXT,
				dev_serial TEXT,
				PRIMARY KEY (dev_runID, dev_devnum)
			)
		""".format(self))
		self.cur.execute("""
			CREATE TABLE IF NOT EXISTS {0.schema}.testresults (
				res_ID SERIAL PRIMARY KEY,
				res_runID INTEGER,
				res_item TEXT,
				res_source TEXT,
				res_format TEXT,
				res_value FLOAT,
				res_text TEXT
			)
		""".format(self))

	# pg_new
	def _add_datatable(self, testrun, tablenamedb, tablenamedict):
		"""add complete sql table based on data dict. headers are enclosed in [] to allow arbitrary names
		to ensure  unique name inside database, the name there is different than in the Testrun instance
		"""
		headers = testrun.resulttables[tablenamedict]['headers']
		headercreate = 'linenum SERIAL PRIMARY KEY, '+', '.join(['"'+el+'" TEXT' for el in headers])
		headernames = ', '.join(['"'+el+'"' for el in headers])
		headerquest = ', '.join(['%s' for i in headers])
		self.cur.execute('DROP TABLE IF EXISTS {0.schema}."{1}";'.format(self, tablenamedb, headercreate))
		self.cur.execute('CREATE TABLE IF NOT EXISTS {0.schema}."{1}" ({2});'.format(self, tablenamedb, headercreate))
		for datatuple in zip(*[testrun.resulttables[tablenamedict]['data'][i] for i in range(len(headers))]):
			self.cur.execute("""
				INSERT INTO {0.schema}."{1}" 
				({2}) 
				VALUES ({3}) 
				RETURNING linenum;
				""".format(self, tablenamedb, headernames, headerquest), datatuple)
			#~ for line in self.cur:
				#~ print 'table line', line[0]
		logger.info('stored {0} in table {1}'.format(headernames, tablenamedb))
		
	# pg_new
	def _add_testdevices(self, testrun):
		for dev_devnum in sorted(testrun.devices):
			self.cur.execute("""
				INSERT INTO {0.schema}.testdevices 
				(dev_runID, dev_devnum, dev_fwfile, dev_fwdev, dev_fwversion, dev_fwbuild, dev_ldversion, dev_ldbuild, dev_fullname, dev_serial) 
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
				""".format(self),(testrun._run_ID, dev_devnum, testrun.devices[dev_devnum]['dev_fwfile'], testrun.devices[dev_devnum]['dev_fwdev'], testrun.devices[dev_devnum]['dev_fwversion'], testrun.devices[dev_devnum]['dev_fwbuild'], testrun.devices[dev_devnum]['dev_ldversion'], testrun.devices[dev_devnum]['dev_ldbuild'], testrun.devices[dev_devnum]['dev_fullname'], testrun.devices[dev_devnum]['dev_serial']))

	# pg_new
	def _add_testresults(self, testrun):
		for reskey in testrun.results:
			res_item, res_source, res_format = reskey
			logger.debug('new result key {0}'.format(reskey))
			if res_format=='_FULLTABLE':
				# rename table on the fly since we have to incorporate run_ID for uniqueness
				namedict = testrun.results[reskey]['res_text']
				namedb = 'tab-{0}-{1}'.format(testrun.get_run_ID(), namedict)
				#~ testrun.results[reskey]['res_text'] = newname
				#~ testrun.resulttables[newname] = testrun.resulttables.pop(oldname)
				self._add_datatable(testrun, namedb, namedict)
				self.cur.execute("""
					INSERT INTO {0.schema}.testresults (res_runID, res_item, res_source, res_format, res_value, res_text) 
					VALUES (%s, %s, %s, %s, %s, %s);
					""".format(self), (testrun.get_run_ID(), res_item, res_source, res_format, testrun.results[reskey]['res_value'], namedb))
			else:
				self.cur.execute("""
					INSERT INTO {0.schema}.testresults (res_runID, res_item, res_source, res_format, res_value, res_text) 
					VALUES (%s, %s, %s, %s, %s, %s);
					""".format(self), (testrun.get_run_ID(), res_item, res_source, res_format, testrun.results[reskey]['res_value'], testrun.results[reskey]['res_text']))

	# pg_new
	def _add_testrun(self, testrun):
		self.cur.execute("""
			INSERT INTO {0.schema}.testruns 
			(run_timestamp, run_testroot, run_testgroup, run_testfunc, run_testcfg, run_mainversion, run_mainbuild, run_maintag, run_maindev) 
			VALUES (%(run_timestamp)s, %(run_testroot)s, %(run_testgroup)s, %(run_testfunc)s, %(run_testcfg)s, %(run_mainversion)s, %(run_mainbuild)s, %(run_maintag)s, %(run_maindev)s)
			RETURNING run_id;
			""".format(self),testrun.run)
		testrun.set_run_ID(self.cur.fetchone()[0])


	# pg_new
	def write_testrun(self, testrun):
		self._add_testrun(testrun)
		self._add_testdevices(testrun)
		self._add_testresults(testrun)
		logger.info('wrote testrun as run_ID {0} to {1}'.format(testrun.get_run_ID(), self))		
		self.con.commit()


	# pg_new
	def _get_datatable(self, testrun, tablename):
		"""get complete sql table based on data dict. headers are enclosed in [] to allow arbitrary names"""
		# get headers for tablename
		tabcur = self.con.cursor()
		tabcur.execute("""
			SELECT attrelid::regclass, attnum, attname
			FROM pg_attribute
			WHERE attrelid = '{0.schema}."{1}"'::regclass
			AND attnum > 0
			AND NOT attisdropped
			ORDER BY attnum;
			""".format(self, tablename))
		headers = [row[2] for row in tabcur]

		tabledict = {'headers': headers[1:], 'data': []}
		for header in tabledict['headers']: 
			tabledict['data'].append([])
		
		headernames = ', '.join(['"'+el+'"' for el in tabledict['headers']])
		tabcur.execute("""
			SELECT {2}
			FROM {0.schema}."{1}"
			""".format(self, tablename, headernames))
		for row in tabcur:
			for col, val in enumerate(row):
				tabledict['data'][col].append(val)
		return tabledict
		
	# pg_new
	def _get_testdevices(self, testrun):
		self.cur.execute("""
			SELECT dev_devnum, dev_fwfile, dev_fwdev, dev_fwversion, dev_fwbuild, dev_ldversion, dev_ldbuild, dev_fullname, dev_serial
			FROM {0.schema}.testdevices
			WHERE dev_runID = %s;
			""".format(self), (testrun.get_run_ID(), ))
		devicesdict = {}
		for row in self.cur:
			dev_devnum = row[0]
			devicesdict[dev_devnum] = {}
			devicesdict[dev_devnum]['dev_fwfile'], devicesdict[dev_devnum]['dev_fwdev'], devicesdict[dev_devnum]['dev_fwversion'], devicesdict[dev_devnum]['dev_fwbuild'], devicesdict[dev_devnum]['dev_ldversion'], devicesdict[dev_devnum]['dev_ldbuild'], devicesdict[dev_devnum]['dev_fullname'], devicesdict[dev_devnum]['dev_serial'] = row[1:]
		testrun.add_devices(devicesdict)

	# pg_new
	def _get_testresults(self, testrun):
		self.cur.execute("""
			SELECT res_item, res_source, res_format, res_value, res_text
			FROM {0.schema}.testresults
			WHERE res_runID = %s;
			""".format(self), (testrun.get_run_ID(), ))
		for row in self.cur:
			res_item, res_source, res_format, res_value, res_text = row
			resultdict = {'res_item': res_item, 'res_source': res_source, 'res_format': res_format, 'res_value': res_value,'res_text': res_text}
			if res_format=='_FULLTABLE':
				# use add_resulttable instead of working directly on the Testrun object to recompute tablename for Testrun instance
				testrun.add_resulttable(self._get_datatable(testrun, res_text), resultdict)
			else:
				testrun.add_result(resultdict)


	# pg_new
	def _get_testrun(self, testrun):
		self.cur.execute("""
			SELECT run_timestamp, run_testroot, run_testgroup, run_testfunc, run_testcfg, run_mainversion, run_mainbuild, run_maintag, run_maindev
			FROM {0.schema}.testruns
			WHERE run_ID = %s;
			""".format(self), (testrun.get_run_ID(), ))
		data = self.cur.fetchone()
		if data is not None:
			testrun.run['run_timestamp'], testrun.run['run_testroot'], testrun.run['run_testgroup'], testrun.run['run_testfunc'], testrun.run['run_testcfg'], testrun.run['run_mainversion'], testrun.run['run_mainbuild'], testrun.run['run_maintag'], testrun.run['run_maindev'] = data
			return True
		return False
		

	# pg_new
	def get_testrun(self, testrun, run_ID=None, forcekey=False):
		if run_ID is not None:
			testrun.set_run_ID(run_ID)
		if testrun.get_run_ID() is not None:
			if self._get_testrun(testrun):
				self._get_testdevices(testrun)
				self._get_testresults(testrun)
			self.con.commit()
		# return testrun
		
	def close(self):
		self.con.commit()
		self.con.close()

	# pg_new
	def remove(self, run_ID=None):
		if run_ID is not None:
			delcur = self.con.cursor()
			# self.con.commit()
			logger.debug('removing run_ID {0} from database'.format(run_ID))
			delcur.execute("""
				SELECT res_text FROM {0.schema}.testresults 
				WHERE res_runID = %s AND res_format = '_FULLTABLE';
				""".format(self), (run_ID, ))
			try:
				tables = delcur.fetchall()
			except:
				return False
			for table in tables:
				logger.debug('removing table {0} for run_ID {1} from database'.format(table[0], run_ID))
				delcur.execute("""
					DROP TABLE IF EXISTS {0.schema}."{1}";
					""".format(self, table[0]))
			delcur.execute("""DELETE FROM {0.schema}.testruns WHERE run_ID = %s;""".format(self), (run_ID, ))
			delcur.execute("""DELETE FROM {0.schema}.testdevices WHERE dev_runID = %s;""".format(self), (run_ID, ))
			delcur.execute("""DELETE FROM {0.schema}.testresults WHERE res_runID = %s;""".format(self), (run_ID, ))
			self.con.commit()
			logger.debug('removed run_ID {0} from {1}'.format(run_ID, self))
			return True
		return False
		
	# pg_new
	def iter_testrun_IDs(self):
		itercur = self.con.cursor()
		try:
			itercur.execute("""
				SELECT run_ID
				FROM {0.schema}.testruns
				""".format(self))
		except:
			return
		for run_ID in cur:
			yield run_ID[0]

	# pg_new
	def get_testrun_IDs(self):
		itercur = self.con.cursor()
		try:
			itercur.execute("""
				SELECT run_ID
				FROM {0.schema}.testruns
				""".format(self))
		except:
			return []
		result = itercur.fetchall()
		if result is not None:
			return [el[0] for el in result]
		else:
			return []


class SqliteOld(DbBase):
	
	id = 'SqliteOld'
	
	# sqlite_old
	def __init__(self, sqlite_file, sqlite_dbver='single'):
		super(SqliteOld, self).__init__() # init next class in MRO
		self.databaseinfo = 'SQLite legacy stlye, database file {0} of type {1}'.format(sqlite_file, sqlite_dbver)

		self.con = sqlite3.connect(sqlite_file)
		self.cur = self.con.cursor()
		self.sqlite_dbver = sqlite_dbver

	def __str__(self):
		"""return info string for use by print etc."""
		return self.databaseinfo

	# sqlite_old
	def _get_datatable(self, testrun, tablename):
		"""get complete sql table based on data dict. headers are enclosed in [] to allow arbitrary names"""
		# get headers for tablename
		tabcur = self.con.cursor()
		tabcur.execute("""PRAGMA table_info({0})""".format(tablename))
		headers = [el[1] for el in tabcur.fetchall()]
		
		tabledict = {'headers': headers[1:], 'data': []}
		for header in tabledict['headers']: 
			tabledict['data'].append([])
			
		headernames = ', '.join(['"'+el+'"' for el in tabledict['headers']])
		tabcur.execute("""
			SELECT {1}
			FROM "{0}"
			""".format(tablename, headernames))
		for row in tabcur:
			for col, val in enumerate(row):
				tabledict['data'][col].append(val)
		return tabledict
		
	# sqlite_old
	def _get_testdevices(self, testrun):
		self.cur.execute("""
			SELECT testnum, testid, devnum, fwname, fwdev, fwmajor, fwminor, infodev, infosn,  ldmajor
			FROM testdevices
			WHERE testid = ?;
			""".format(self), (testrun.get_run_ID(), ))
		devicesdict = {}
		for row in self.cur:
			testnum, testid, devnum, fwname, fwdev,  fwmajor, fwminor, infodev, infosn, ldmajor = row
			lddev, ldversion, ldbuild = lcos.fwsplit(ldmajor)
			devicesdict[int(devnum)] = {
				'dev_fwfile': fwname,
				'dev_fwdev': fwdev, 
				'dev_fwversion': fwmajor, 
				'dev_fwbuild': fwminor, 
				'dev_ldversion': ldversion, 
				'dev_ldbuild': ldbuild, 
				'dev_fullname': infodev, 
				'dev_serial': infosn,
			}
		testrun.add_devices(devicesdict, min(devicesdict.keys()))
			

	# sqlite_old
	def _get_testresults(self, testrun, forcekey=False):
		self.cur.execute("""
			SELECT testitem, testformat, testvalue, source
			FROM testresults
			WHERE testid = ?;
			""".format(self), (testrun.get_run_ID(), ))
		for row in self.cur:
			res_item, res_format, value, res_source  = row
			if res_format=='fulltable': 
				res_format = '_FULLTABLE'
				res_text = value
				res_value= None
			else:
				try:
					res_value = float(value)
					res_text = ''
				except:
					res_value = None
					res_text = value
					logger.info('sqlite_old testresult not float {0}'.format(value))
			resultdict = {'res_item': res_item, 'res_source': res_source, 'res_format': res_format, 'res_value': res_value,'res_text': res_text}
			if res_format=='_FULLTABLE':
				testrun.add_resulttable(self._get_datatable(testrun, res_text), resultdict)
			else:
				testrun.add_result(resultdict, force=forcekey)


	# sqlite_old
	def _get_testrun(self, testrun):
		self.cur.execute("""
			SELECT testid, testroot, testdir, testname, testcfg, fwname, fwdev, fwmajor, fwminor, infodev, infosn, ldmajor
			FROM testruns
			WHERE testid = ?;
			""".format(self), (testrun.get_run_ID(), ))
		data = self.cur.fetchone()
		if data is not None:
			testid, testroot, testdir, testname, testcfg, fwname, fwdev, fwmajor, fwminor, infodev, infosn, ldmajor = data
			lddev, ldversion, ldbuild = lcos.fwsplit(ldmajor)
			testrun.run['run_timestamp'] = datetime.datetime.strptime(testid, '%Y%m%d-%H%M%S')
			testrun.run['run_testroot'], testrun.run['run_testgroup'], testrun.run['run_testfunc'], testrun.run['run_testcfg'] = testroot, testdir, testname, testcfg
			testrun.run['run_mainversion'], testrun.run['run_mainbuild'], testrun.run['run_maintag'], testrun.run['run_maindev'] = fwmajor, fwminor, '', 1
			if self.sqlite_dbver == 'single':
				testrun.devices[1] = {
					'dev_fwfile': fwname,
					'dev_fwdev': fwdev, 
					'dev_fwversion': fwmajor, 
					'dev_fwbuild': fwminor, 
					'dev_ldversion': ldversion, 
					'dev_ldbuild': ldbuild, 
					'dev_fullname': infodev, 
					'dev_serial': infosn,
				}
			elif self.sqlite_dbver == 'fulldev':
				self._get_testdevices(testrun)

	# sqlite_old
	def _get_testrun_memtest(self, testrun):
		# legacy memtest format
		# CREATE TABLE memtestresults (testnum INTEGER PRIMARY KEY, timestamp CHAR(15), device VARCHAR(64), fwmajor VARCHAR(8), fwminor VARCHAR(8), SN VARCHAR(32), USED FLOAT, FREE FLOAT)
		self.cur.execute("""
			SELECT testnum, timestamp, device, fwmajor, fwminor, SN, USED, FREE
			FROM memtestresults
			WHERE testnum = ?;
			""".format(self), (testrun.get_run_ID(), ))
		data = self.cur.fetchone()
		if data is not None:
			testnum, timestamp, device, fwmajor, fwminor, SN, USED, FREE = data
			testrun.run['run_timestamp'] = datetime.datetime.strptime(timestamp, '%Y%m%d-%H%M%S')
			testrun.run['run_testroot'], testrun.run['run_testgroup'], testrun.run['run_testfunc'], testrun.run['run_testcfg'] = '', '', '', ''
			testrun.run['run_mainversion'], testrun.run['run_mainbuild'], testrun.run['run_maintag'], testrun.run['run_maindev'] = fwmajor, fwminor, '',  1
			testrun.devices = {}
			testrun.add_devices({
				1: {
					'dev_fwfile': '',
					'dev_fwdev': '', 
					'dev_fwversion': fwmajor, 
					'dev_fwbuild': fwminor, 
					'dev_ldversion': '', 
					'dev_ldbuild': '', 
					'dev_fullname': device, 
					'dev_serial': SN,
				},
			})
			testrun.add_results([
				{'res_item':'used memory', 'res_source':'sysinfo', 'res_format': 'MByte', 'res_value': USED, 'res_text':''},
				{'res_item':'free memory', 'res_source':'sysinfo', 'res_format': 'MByte', 'res_value': FREE, 'res_text':''},
			])

	def get_testrun(self, testrun, run_ID=None, forcekey=False):
		if run_ID is not None:
			testrun.set_run_ID(run_ID)
		if testrun._run_ID is not None:
			if self.sqlite_dbver!='memtest':
				self._get_testrun(testrun)
				self._get_testresults(testrun,forcekey)
			else:
				self._get_testrun_memtest(testrun)
			#~ self.con.commit()
		
	def close(self):
		self.con.commit()
		self.con.close()
		
		
	def iter_testrun_IDs(self):
		itercur = self.con.cursor()
		if self.sqlite_dbver!='memtest':
			try:
				itercur.execute("""
					SELECT testid
					FROM testruns
					""".format(self))
			except:
				return
			for run_ID in itercur:
				yield run_ID[0]
		else:
			try:
				itercur.execute("""
					SELECT testnum
					FROM memtestresults
					""".format(self))
			except:
				return
			for run_ID in itercur:
				yield run_ID[0]
			
		



class SqliteNew(DbBase):
	
	id = 'SqliteNew'
	
	# sqlite_new
	def __init__(self, sqlite_file):
		super(SqliteNew, self).__init__() # init next class in MRO
		self.databaseinfo = 'SQLite unified style, database file {0}'.format(sqlite_file)
		
		self.con = sqlite3.connect(sqlite_file)
		self.cur = self.con.cursor()
		self._create_tables()

	def __str__(self):
		"""return info string for use by print etc."""
		return self.databaseinfo

	# sqlite_new
	def _create_tables(self):
		self.cur.execute("""
			CREATE TABLE IF NOT EXISTS testruns (
				run_ID INTEGER PRIMARY KEY,
				run_timestamp TEXT,
				run_testroot TEXT,
				run_testgroup TEXT,
				run_testfunc TEXT,
				run_testcfg TEXT,
				run_mainversion TEXT,
				run_mainbuild TEXT,
				run_maintag TEXT,
				run_maindev INTEGER
			)
		""".format(self))
		self.cur.execute("""
			CREATE TABLE IF NOT EXISTS testdevices (
				dev_runID INTEGER,
				dev_devnum INTEGER,
				dev_fwfile TEXT,
				dev_fwdev TEXT,
				dev_fwversion TEXT,
				dev_fwbuild TEXT,
				dev_ldversion TEXT,
				dev_ldbuild TEXT,
				dev_fullname TEXT,
				dev_serial TEXT,
				PRIMARY KEY (dev_runID, dev_devnum)
			)
		""".format(self))
		self.cur.execute("""
			CREATE TABLE IF NOT EXISTS testresults (
				res_ID INTEGER PRIMARY KEY,
				res_runID INTEGER,
				res_item TEXT,
				res_source TEXT,
				res_format TEXT,
				res_value FLOAT,
				res_text TEXT
			)
		""".format(self))

	# sqlite_new
	def _add_datatable(self, testrun, tablenamedb, tablenamedict):
		"""add complete sql table based on data dict. headers are enclosed in [] to allow arbitrary names"""
		headers = testrun.resulttables[tablenamedict]['headers']
		headercreate = 'linenum INTEGER PRIMARY KEY, '+', '.join(['"'+el+'" TEXT' for el in headers])
		headernames = ', '.join(['"'+el+'"' for el in headers])
		headerquest = ', '.join(['?' for i in headers])
		self.cur.execute('DROP TABLE IF EXISTS [{0}];'.format(tablenamedb))
		self.cur.execute('CREATE TABLE IF NOT EXISTS [{0}] ({1});'.format(tablenamedb, headercreate))
		for datatuple in zip(*[testrun.resulttables[tablenamedict]['data'][i] for i in range(len(testrun.resulttables[tablenamedict]['headers']))]):
			self.cur.execute("""
				INSERT INTO [{1}] 
				({2}) 
				VALUES ({3});
				""".format(self, tablenamedb, headernames, headerquest), datatuple)
			self.cur.execute("""SELECT last_insert_rowid()""")
			#~ for line in self.cur:
				#~ print 'table line', line[0]
		logger.debug('stored {0} in table'.format(headernames, tablenamedb))
		
	# sqlite_new
	def _add_testdevices(self, testrun):
		for dev_devnum in sorted(testrun.devices):
			self.cur.execute("""
				INSERT INTO testdevices 
				(dev_runID, dev_devnum, dev_fwfile, dev_fwdev, dev_fwversion, dev_fwbuild, dev_ldversion, dev_ldbuild, dev_fullname, dev_serial) 
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
				""".format(self),(testrun.get_run_ID(), dev_devnum, testrun.devices[dev_devnum]['dev_fwfile'], testrun.devices[dev_devnum]['dev_fwdev'], testrun.devices[dev_devnum]['dev_fwversion'], testrun.devices[dev_devnum]['dev_fwbuild'], testrun.devices[dev_devnum]['dev_ldversion'], testrun.devices[dev_devnum]['dev_ldbuild'], testrun.devices[dev_devnum]['dev_fullname'], testrun.devices[dev_devnum]['dev_serial']))

	# sqlite_new
	def _add_testresults(self, testrun):
		for reskey in testrun.results:
			res_item, res_source, res_format = reskey
			if res_format=='_FULLTABLE':
				# rename table on the fly since we have to incorporate run_ID for uniqueness
				namedict = testrun.results[reskey]['res_text']
				namedb = 'tab-{0}-{1}'.format(testrun.get_run_ID(), namedict)
				self._add_datatable(testrun, namedb, namedict)
				self.cur.execute("""
					INSERT INTO testresults (res_runID, res_item, res_source, res_format, res_value, res_text) 
					VALUES (?, ?, ?, ?, ?, ?);
					""".format(self), (testrun.get_run_ID(), res_item, res_source, res_format, testrun.results[reskey]['res_value'], namedb))
			else:
				self.cur.execute("""
					INSERT INTO testresults (res_runID, res_item, res_source, res_format, res_value, res_text) 
					VALUES (?, ?, ?, ?, ?, ?);
					""".format(self), (testrun.get_run_ID(), res_item, res_source, res_format, testrun.results[reskey]['res_value'], testrun.results[reskey]['res_text']))

	# sqlite_new
	def _add_testrun(self, testrun):
		self.cur.execute("""
			INSERT INTO testruns 
			(run_timestamp, run_testroot, run_testgroup, run_testfunc, run_testcfg, run_mainversion, run_mainbuild, run_maintag, run_maindev) 
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
			""".format(self), [testrun.run[name] for name in ['run_timestamp', 'run_testroot', 'run_testgroup', 'run_testfunc', 'run_testcfg', 'run_mainversion', 'run_mainbuild', 'run_maintag', 'run_maindev']])
		self.cur.execute("""SELECT last_insert_rowid()""")
		testrun.set_run_ID(self.cur.fetchone()[0])


	# sqlite_new
	def write_testrun(self, testrun):
		self._add_testrun(testrun)
		self._add_testdevices(testrun)
		self._add_testresults(testrun)
		logger.info('wrote testrun as run_ID {0} to {1}'.format(testrun.get_run_ID(), self))
		self.con.commit()


	# sqlite_new
	def _get_datatable(self, testrun, tablename):
		"""get complete sql table based on data dict. headers are enclosed in [] to allow arbitrary names"""
		# get headers for tablename
		tabcur = self.con.cursor()
		tabcur.execute("""PRAGMA table_info([{0}])""".format(tablename))
		headers = [el[1] for el in tabcur.fetchall()]
		
		tabledict = {'headers': headers[1:], 'data': []}
		for header in tabledict['headers']: 
			tabledict['data'].append([])
				
		headernames = ', '.join(['"'+el+'"' for el in tabledict['headers']])
		tabcur.execute("""
			SELECT {1}
			FROM [{0}]
			""".format(tablename, headernames))
		for row in tabcur:
			for col, val in enumerate(row):
				tabledict['data'][col].append(val)
		return tabledict
		
		
	# sqlite_new
	def _get_testdevices(self, testrun):
		self.cur.execute("""
			SELECT dev_devnum, dev_fwfile, dev_fwdev, dev_fwversion, dev_fwbuild, dev_ldversion, dev_ldbuild, dev_fullname, dev_serial
			FROM testdevices
			WHERE dev_runID = ?;
			""".format(self), (testrun.get_run_ID(), ))
		devicesdict = {}
		for row in self.cur:
			dev_devnum = row[0]
			devicesdict[dev_devnum] = {}
			devicesdict[dev_devnum]['dev_fwfile'], devicesdict[dev_devnum]['dev_fwdev'], devicesdict[dev_devnum]['dev_fwversion'], devicesdict[dev_devnum]['dev_fwbuild'], devicesdict[dev_devnum]['dev_ldversion'], devicesdict[dev_devnum]['dev_ldbuild'], devicesdict[dev_devnum]['dev_fullname'], devicesdict[dev_devnum]['dev_serial'] = row[1:]
		testrun.add_devices(devicesdict)


	# sqlite_new
	def _get_testresults(self, testrun):
		self.cur.execute("""
			SELECT res_item, res_source, res_format, res_value, res_text
			FROM testresults
			WHERE res_runID = ?;
			""".format(self), (testrun.get_run_ID(), ))
		for row in self.cur:
			res_item, res_source, res_format, res_value, res_text = row
			resultdict = {'res_item': res_item, 'res_source': res_source, 'res_format': res_format, 'res_value': res_value,'res_text': res_text}
			if res_format=='_FULLTABLE':
				testrun.add_resulttable(self._get_datatable(testrun, res_text), resultdict)
			else:
				testrun.add_result(resultdict)
				
	# sqlite_new
	def _get_testrun(self, testrun):
		self.cur.execute("""
			SELECT run_timestamp, run_testroot, run_testgroup, run_testfunc, run_testcfg, run_mainversion, run_mainbuild, run_maintag, run_maindev
			FROM testruns
			WHERE run_ID = ?;
			""".format(self), (testrun.get_run_ID(), ))
		result = self.cur.fetchone()
		if result is not None:
			run_timestamp, testrun.run['run_testroot'], testrun.run['run_testgroup'], testrun.run['run_testfunc'], testrun.run['run_testcfg'], testrun.run['run_mainversion'], testrun.run['run_mainbuild'], testrun.run['run_maintag'], testrun.run['run_maindev'] = result
			testrun.run['run_timestamp'] = datetime.datetime.strptime(run_timestamp, '%Y-%m-%d %H:%M:%S')
			return True
		else:
			logger.warning('getting testrun {0} failed since it does not exists'.format(testrun.get_run_ID()))
			return False
			


	# sqlite_new
	def get_testrun(self, testrun, run_ID=None, forcekey=False):
		if run_ID is not None:
			testrun.set_run_ID(run_ID)
		if testrun.get_run_ID() is not None:
			if self._get_testrun(testrun):
				self._get_testdevices(testrun)
				self._get_testresults(testrun)
			self.con.commit()

		
	def close(self):
		self.con.commit()
		self.con.close()
		
	def remove(self, run_ID=None):
		if run_ID is not None:
			delcur = self.con.cursor()
			logger.debug('removing run_ID {0} from database'.format(run_ID))
			delcur.execute("""
				SELECT res_text FROM testresults 
				WHERE res_runID = ? AND res_format = '_FULLTABLE';
				""", (run_ID, ))
			try:
				tables = delcur.fetchall()
			except:
				return False
			for table in tables:
				logger.debug('removing table {0} for run_ID {1} from database'.format(table[0], run_ID))
				delcur.execute("""
					DROP TABLE IF EXISTS [{}];
					""".format(table[0]))
			delcur.execute("""DELETE FROM testruns WHERE run_ID = ?;""", (run_ID, ))
			delcur.execute("""DELETE FROM testdevices WHERE dev_runID = ?;""".format(self), (run_ID, ))
			delcur.execute("""DELETE FROM testresults WHERE res_runID = ?;""".format(self), (run_ID, ))
			self.con.commit()
			logger.debug('removed run_ID {0} from {1}'.format(run_ID, self))
			return True
		return False
		
		
	def iter_testrun_IDs(self):
		itercur = self.con.cursor()
		itercur.execute("""
			SELECT run_ID
			FROM testruns
			""".format(self))
		for run_ID in itercur:
			yield run_ID[0]
			
	def get_testrun_IDs(self):
		itercur = self.con.cursor()
		try:
			itercur.execute("""
				SELECT run_ID
				FROM testruns
				""".format(self))
		except:
			return []
		result = itercur.fetchall()
		if result is not None:
			return [el[0] for el in result]
		else:
			return []



if __name__=='__main__':

	logging.basicConfig(level=logging.DEBUG)

	from perfweb.config import renderdef
	database = renderdef.database.dataitems


	if 0:
		dbfiles = {}
		for dsname, dsparams in database.datasets.items():
			dbfiles[dsparams['sqldb']] = dsparams['dbver']
			
		for dbfile, dbver in dbfiles.items():
			dbfilefull = os.path.join('/home/automaton/perfweb/',dbfile)
			if os.path.exists(dbfilefull):
				newschema = os.path.basename(dbfile).strip('.db')
				print dbfile, dbver, '<'+newschema+'>'
				t = sqlite2pg(dbfilefull, dbver, 'qstests', 'dbwriter', 'dbwriter', newschema)
				t._pg_create_tables()
				t.close()
			
			

	if 0:
		# fill a testrun
		run = Testrun()
		run.add_devices({
			0: {'dev_fwfile':  '.upx', 'dev_fwdev': 'LC-9100', 'dev_fwversion': '8.70', 'dev_fwbuild': '0030', 'dev_ldversion': '', 'dev_ldbuild': '', 'dev_fullname': '', 'dev_serial': '12345'}
		})
		run.run['run_maindev'] = 0
		run.add_results([
			{'res_item': 'item', 'res_source': 'source','res_format': 'format', 'res_value': 3.14, 'res_text': u'pi'},
			{'res_item': 'item2', 'res_source': 'source','res_format': 'format', 'res_value': 2.71, 'res_text': u'e'},
		])
		run.add_resulttable(
			{
				'headers': ['col01', 'col02'], 
				'data': [
					[1, 2, 3],
					[11, 22, 33],
				],
			},
			{
				'res_item': 'item3 und 0',
				'res_source': 'source !',
			},
		)
		
	if 0:
		print '###'
		print '### postgres'
		print '###'
		
		# init db and write testrun
		t = PostgresNew(pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = 'addtest')
		t._create_tables()
		t.write_testrun(run)
		print run
		
		# new testrun with id, fill it from db
		r2 = Testrun(run.get_run_ID())
		t2 = PostgresNew(pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = 'addtest')
		t2.get_testrun(r2)
		print r2

		print 'equal?', run==r2
		
		# remove testrun
		t.remove(run.get_run_ID())		

		t.close()

	
	if 0:
		print '###'
		print '### postgres qmdata'
		print '###'
		
		# init db and write testrun
		t = PostgresNew(pg_host='lcs-qmdata.lcs.intern', pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = 'addtest')
		t._create_tables()
		t.write_testrun(run)

		print run
		
		# new testrun with id, fill it from db
		r2 = Testrun(run.get_run_ID())
		t2 = PostgresNew(pg_host='lcs-qmdata.lcs.intern', pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = 'addtest')
		t2.get_testrun(r2)
		print r2

		print 'equal?', run==r2
		
		t.remove(run.get_run_ID())
		t.close()		
		

		
	
	if 0:	
		print '###'
		print '### sqlite_new'
		print '###'
		
		# init db and write testrun
		t = SqliteNew(sqlite_file = 'test.sqlite')
		t._create_tables()
		t.write_testrun(run)
		print run
		
		# new testrun with id, fill it from db
		r2 = Testrun(run.get_run_ID())
		t2 = SqliteNew(sqlite_file = 'test.sqlite')
		t2.get_testrun(r2)
		print 'new testrun after reading'
		print r2
		
		print 'equal?', run==r2
		
		# remove testrun
		t.remove(run.get_run_ID())		
		t.close()
		
		
	if 0:
		print '###'
		print 'sqlite_old'
		print '###'
		
		#~ db = sqlite_old(sqlite_file = '/home/automaton/perfweb/data/IxAutomate.db', sqlite_dbver='single')
		#~ id = '20130701-073052'
		
		#~ db = sqlite_old(sqlite_file = '/home/automaton/perfweb/data/P2P2.db', sqlite_dbver='fulldev')
		#~ id = '20130620-130351'
		
		db = SqliteOld(sqlite_file = '/home/automaton/perfweb/data/MZB24H.db', sqlite_dbver='fulldev')
		id = '20120322-010039'
		
		run = Testrun(id)
		
		db.get_testrun(run)
		print "sqlite_old get"
		print run
		
		#~ run2 = testrun()
		#~ run2.read_db(db, id)
		#~ print "sqlite_old reverse get"
#~ #		print run2
		
		#~ print 'equal?', run==run2

	if 0: 
		print '###'
		print 'sqlite_old memtest'
		print '###'

		db = SqliteOld(sqlite_file = '/home/automaton/perfweb/data/memtest.db', sqlite_dbver='memtest')
		id = '2783'
		
		run = testrun(id)
		
		db.get_testrun(run)
		print "sqlite_old get"
		print run
		
	#~ if 1:
		#~ db = sqlite_old(sqlite_file = '/home/automaton/perfweb/data/P2P2.db', sqlite_dbver='fulldev')
		
		#~ run = testrun()
		
		#~ count = 0
		#~ starttime = datetime.datetime.now()
		#~ for id in db.iter_testrun_IDs():
			#~ print id
			#~ run.read_db(db, id)
			#~ count += 1
			#~ if count ==1000:
				#~ break
		#~ endtime = datetime.datetime.now()
		#~ print starttime
		#~ print endtime
		#~ print endtime - starttime
		#~ print (endtime - starttime) / count
		
	


	if 0:
		print lcos.fwsplit('3.39.0001')
		print lcos.fwsplit('LC-XXX-3.39.0001')
		print lcos.fwsplit('LC-XXX-3.39.0001-blabla')
		print lcos.fwsplit('LC-XXX-3.39-blabla')


	if 0: 
		tun = Testrun()
		
		run.set_result_success(True)
		if run.get_result_success():
			print 'Hooray'
		else:
			print 'WTF?!'
			
		run.set_result_success(False)
		if run.get_result_success():
			print 'Hooray'
		else:
			print 'WTF?!'
			
	if 1:
		t = PostgresNew(pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = 'unknown')
		schemas = t.get_available_schemas()
		for schema in schemas:
			t.schema = schema
			print schema, t.get_highest_runID()
		
			
		