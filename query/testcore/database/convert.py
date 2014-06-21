import sys, os
import logging
import datetime

from perfweb.config import renderdef
from perfweb.config import dataitems

from testcore.database import testrun


def convert_one(db_in, db_out, keepfilter=None, runfunc=None):
	run = testrun.Testrun()
		
	readcount = 0
	readerr = 0
	writecount = 0
	readtime = None
	writetime = None
	
	for id in db_in.iter_testrun_IDs():

		keep = True
		
		starttime = datetime.datetime.now()
		try:
			run.read_db(db_in, id, forcekey=True)
		except:
			keep = False
			readerr +=1
		#~ print run
		endtime = datetime.datetime.now()
		if readtime is not None:
			readtime += endtime - starttime
		else:
			readtime = endtime - starttime
		readcount += 1
		if keepfilter is not None:
			keep = keepfilter(run)
		
		if keep:
			if runfunc is not None:
				run = runfunc(run)
			starttime = datetime.datetime.now()
			run.write_db(db_out)
			endtime = datetime.datetime.now()
			if writetime is not None:
				writetime += endtime - starttime
			else:
				writetime = endtime - starttime
				
			writecount += 1
			
		if readcount%10 == 0:
			logging.info('{} testruns read, {} testruns written, {} read failed,'.format(readcount, writecount, readerr))
			
	if readcount>0:
		logging.info('{} testruns read, readtime total {} / per run {}'.format(readcount, readtime, readtime / readcount))
	if writecount>0:
		logging.info('{} testruns written, writetime total {} / per run {}'.format(writecount, writetime, writetime / writecount))


def db_ver():
	di = dataitems.sqlite('')
	dbs = {}
	for key, value in di.datasets.items():
		dbs[value['sqldb']] = value['dbver']
	return dbs
		
	
	
	



if __name__=="__main__":
	
	# logging.basicConfig(filename='convert.log', level=logging.INFO)
	logging.basicConfig(level=logging.INFO)
	database = renderdef.database.dataitems
	
	def trunc_old_FWs(testrun):
		try:
			v = int(testrun.run['run_mainversion'].replace('.',''))
			b = int(testrun.run['run_mainbuild'])
		except:
			logging.debug('keep: not parseable {} {}'.format(testrun.run['run_mainversion'], testrun.run['run_mainbuild']))
			return False
		if v<862 and not v==7.82:
			for vsave, bsave in [(850, 91), (850, 142), (850, 191), (850, 214), (860, 189)]:
				if v==vsave and b==bsave: 
					return True
			logging.debug('keep: fw too old {} {}'.format(testrun.run['run_mainversion'], testrun.run['run_mainbuild']))
			return False
		return True
	
			
	for dbname,ver in db_ver().items(): # [('memtest.db','memtest') ]
	#~ for dbname,ver in [('memtest.db','memtest') ]:
		dbtag = os.path.splitext(dbname)[0]
		logging.info('#')
		logging.info('#')
		logging.info('# converting database {} ({})'.format(dbname, ver))
		logging.info('#')
		logging.info('#')
		if 1 :
			db_in = testrun.SqliteOld(sqlite_file = os.path.join('/home/automaton/data/sqliteold',dbname), sqlite_dbver=ver)
			db_out = testrun.PostgresNew(
				pg_database = 'qstests', 
				pg_user = 'dbwriter', 
				pg_password = 'dbwriter', 
				pg_schema = dbtag, 
				pg_schema_modify = True,
				pg_clearalltables='IKNOWWHATIMDOING',
			)
			convert_one(db_in, db_out, trunc_old_FWs)
			db_in.close()
			db_out.close()
			
			