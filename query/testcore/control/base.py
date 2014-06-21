import unittest
import time, datetime
import logging
logger = logging.getLogger(__name__)

"""
base class for control classes (telnet, ssh, serial,...)
"""

class control(object):
	
	_trace_concurrentlimit = None	
	
	def __init__(self, *args, **kwargs):
		"""
		define a control session
		"""
		self._con = None
		self.loggedin = False

		# if logfile is not None, output will NOT be updated (to prevent memory exhaustion)
		self.logfile = None
		self.output = ''
		self.debug = False
		
	def _writeout(self, data):
		if data is not None and len(data)>0:
			if self.logfile is not None:
				with open(self.logfile, 'ab') as f:
					f.write(data) #.replace('\r','').replace('\n','\r\n')) # make CR CR LF into CR LF
			else:
				self.output += data
			if self.debug:
				print data,

	def login(self):
		""" 
		login into DUT, open a control session
		return True or False wether it succeeded
		if suceeded, .close() has to be used afterwards
		"""
		return False
		
	def send(self, text):
		"""
		send text to DUT without waiting for anything
		"""
		pass
		
	def query(self, query):
		"""
		return the result of the CLI query
		if no output exists, return None
		"""
		return None
		
	def set_currenttime(self):
		"""
		set current system time on device with <time> CLI command
		return either datetime object, or None
		"""
		t = datetime.datetime.now()
		time.sleep(1.0-1.0* (t.microsecond) / 1e6)
		d = datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second) + datetime.timedelta(seconds=1) # note; safe against sleep being to short
		timestr = d.strftime('time %m/%d/%Y %H:%M:%S')
		q = self.query(timestr)
		if q is not None and q=='':
			return d
		return None
		
	def close(self):
		"""
		close active control session
		"""
		if self._con is not None:
			self._con.close()
			self._con = None
			
			
	# composite commands

	def run_(self, func, a=[], k={}, fail=False):
		"""
		wrap methods which should be run with login / close around it.
		a is for args as list, k ist the keyword args as dict
		if no login was possible, fail parametr is returned - otherwise the result of func
		"""
		if self.login():
			q = func(*a, **k)
			self.close()
			return q
		self.close()
		return fail

	def runquery(self, query):
		"""
		login / query / close in one command
		return either text, or None
		"""
		return self.run_(self.query, [query], fail=None)

	def push(self, command):
		"""
		login / send / close in one command, do not check for results
		return wether it was possible to send, if known
		"""
		return self.run_(self.send, [command])
		
	def is_alive(self):
		"""
		login / close in one command, returning wether login was possible
		"""
		return self.run_(lambda x: x, [True])
		
	def runscript(self, script):
		"""
		login / script_exec /close in one command
		"""
		return self.run_(self.script_exec, [script])
		
	def run_set_currenttime(self):
		return self.run_(self.set_currenttime, fail=None)
		
		
	def run_do_boot(self, cold=False, clear=True, boottime=90):
		"""
		perform a warm/coldboot. send the respective command, wait for DUT getting down, and wait for DUT being alive again. Maximum boottime can be specified in seconds.
		if clear is True, Save-Bootlog will be set not no before coldboot
		returns True if alive after boot, otherwise returns False
		"""
		if cold:
			if clear:
				self.runquery('set /set/config/Save-Bootlog no')
				time.sleep(0.5)
			self.push('do /o/c')
		else:
			self.push('do /o/b')
		t0 = datetime.datetime.now()
		t1 = t0 + datetime.timedelta(seconds=boottime)
		# wait for going down
		up = True
		while up and datetime.datetime.now()<t1:
			time.sleep(2)
			up = self.is_alive()
		if not up:
			# wait for coming back
			booted = self.is_alive()
			while not booted and datetime.datetime.now()<t1:
				time.sleep(2)
				booted = self.is_alive()
			return booted
		else:
			logger.warning('tried to boot, but device did not went down')
			return False
		
	def run_do_warmboot(self):
		return self.run_do_boot(cold=False)

	def run_do_coldboot(self):
		return self.run_do_boot(cold=True, clear=False)
		
	def run_do_coldbootclear(self):
		return self.run_do_boot(cold=True, clear=True)


"""
UnitTests for common methods of Serial/SSH/Telnet...
"""

class CommonTests(unittest.TestCase):

	def tearDown(self):
		try:	
			self.controlclass.close()
		except:
			pass


	# LOGIN

	def test_login_failure_due_wrong_credentials(self):
		"""
		try to login with wrong credentials, excpect fail
		"""
		self.controlclass.username = 'sdfs'
		self.controlclass.password = 'blabla'
		self.assertFalse(self.controlclass.is_alive())
		
		
	def test_login_success_with_correct_credentials(self):
		"""
		try to login with correct credentials, excpect success
		"""
		self.assertTrue(self.controlclass.is_alive())
		
	
	# runquery / push

	def test_runquery_sysinfo(self):
		"""
		get a SYSINFO with the base.runquery wrapper which handles the login
		"""
		sysinfo = self.controlclass.runquery('sysinfo')
		self.assertTrue(sysinfo is not None)		
		self.assertTrue('DEVICE' in sysinfo)		
	
	def test_runquery_set(self):
		"""
		get a SYSINFO with the base.runquery wrapper which handles the login
		"""
		result  = self.controlclass.runquery('set /set/name test')
		self.assertTrue(result is not None)		
		self.assertTrue('set ok:' in result)		
	
	
	def test_push_leds(self):
		"""
		check that base.push, which does not wait for reaction to a sent command ( in contrary to base.runquery), still is able to set config
		"""
		self.controlclass.push('set /Setup/Config/LED-Test Green')
		time.sleep(1)
		self.assertTrue('Green' in self.controlclass.runquery('ls /Setup/Config/LED-Test'))
		
		self.controlclass.push('set /Setup/Config/LED-Test Orange')
		time.sleep(1)
		self.assertTrue('Orange' in self.controlclass.runquery('ls /Setup/Config/LED-Test'))
		
		self.controlclass.push('set /Setup/Config/LED-Test Red')
		time.sleep(1)
		self.assertTrue('Red' in self.controlclass.runquery('ls /Setup/Config/LED-Test'))
		
		self.controlclass.push('set /Setup/Config/LED-Test No_Test')
		time.sleep(1)
		self.assertTrue('No_Test' in self.controlclass.runquery('ls /Setup/Config/LED-Test'))
	
	
	def test_run_warmboot(self):
		"""
		DUT will close session when booting - this should be handled without an exception happening
		"""
		self.assertTrue(self.controlclass.run_do_warmboot())
		bootlog = self.controlclass.runquery('show bootlog')
		self.assertTrue('System boot after manual boot request' in bootlog.rsplit('****',1)[1])
		
	def test_run_coldbootboot(self):
		"""
		DUT will close session when booting - this should be handled without an exception happening
		"""
		self.assertTrue(self.controlclass.run_do_coldboot())
		bootlog = self.controlclass.runquery('show bootlog')
		self.assertTrue('System boot after manual coldboot request' in bootlog.rsplit('****',1)[1])

	def test_run_coldbootbootclear(self):
		"""
		DUT will close session when booting - this should be handled without an exception happening
		"""
		self.assertTrue(self.controlclass.run_do_coldbootclear())
		bootlog = self.controlclass.runquery('show bootlog')
		self.assertTrue('System boot after manual coldboot request' in bootlog.rsplit('****',1)[1])
		self.assertTrue(bootlog.count('****')==1)

	def test_set_currenttime(self):
		"""
		verify set_currenttime can be ecexuted
		"""
		result = self.controlclass.run_set_currenttime()
		self.assertTrue(result is not None)
	
	def test_CLI_paths(self):
		"""
		check that deeper paths are aceepted
		"""
		q = None
		if self.controlclass.login():
			crontab = self.controlclass.query('cd /Setup/Config/CRON-Table ; ls')
			self.assertTrue(crontab is not None)
			self.assertTrue('Index' in crontab)
		else:
			self.assertTrue(False)
		
	def test_runquery_long(self):
		"""
		check that a query with very long output like #readmib# gets the full result
		"""
		t = datetime.datetime.now()		
		mib = self.controlclass.runquery('#readmib#')
		logger.info('readmib took {0}'.format(datetime.datetime.now() - t ))
		self.assertTrue(mib is not None)
		mibend =  [l for l in mib.splitlines()][-6:]
		self.assertTrue('END' in mibend)		
		

	# SCRIPT
	
	def test_script_exec_defective_failure(self):
		"""
		script_exec should detect a script error and return False
		"""
		self.assertTrue(self.controlclass.login())
		self.assertFalse(self.controlclass.script_exec(['set name test']))
		
		
	def test_script_start_defective_success(self):
		"""
		script_start does not try to detect script errors and return True
		"""
		self.assertTrue(self.controlclass.login())
		self.assertTrue(self.controlclass.script_start(['set name test']))
		
		
	def test_script_exec_correct_success(self):
		"""
		script_exec should detect that the script was executed successfully
		"""
		self.assertTrue(self.controlclass.login())
		self.assertTrue(self.controlclass.script_exec(['set /set/name test']))
			
			
	def test_script_run_correct_success(self):
		"""
		runscript wrapps the login and detects that the script was executed successfully
		"""
		self.assertTrue(self.controlclass.runscript(['set /set/name test']))
			
			
	def test_script_run_long_success(self):
		"""
		verify that a long script can be executed successfully
		"""
		self.controlclass.timeout_scriptexecution = 100
		self.assertTrue(self.controlclass.login())
		self.assertTrue(self.controlclass.script_exec(['flash no']+['set /set/name test']*5000+['flash yes']))

	
class CommonTraceTests(unittest.TestCase):
	

	def tearDown(self):
		try:	
			self.controlclass.close()
		except:
			pass


	def test_trace_output(self):
		"""
		run a background trace thread for 20 secs and exepect a reasonable amount of data in its output
		"""
		self.controlclass.trace_command = 'rep 1 ls /st/op'
		self.controlclass.start()
		time.sleep(20)
		self.controlclass.stoptrace()
		self.controlclass.join()
		self.assertTrue(len(self.controlclass.output)>0)
		self.assertTrue(self.controlclass.output.count('Operating-Time  INFO: ') > 17)
		# print self.controlclass.output


	def test_trace_concurrent(self):
		"""
		if the controlclass supports concurrent traces on the SAME host, test two concurrent traces. 
		the trace with "who" will see at least two roots logged in (note the space behind root to exclude the root@... which might be present in the prompt)
		"""
		if self.controlclass._trace_concurrentlimit is None or self.controlclass._trace_concurrentlimit >= 2:
			tracethreads = []
			for command in ['rep 1 l /st/op ; #load# ', 'rep 1 who']:
				tr = self.getClass()
				tr.trace_command = command
				tracethreads.append(tr)
				tr.start()
				
			time.sleep(20)
			
			for thread in tracethreads:
				thread.stoptrace()
				thread.join()
				
			for tn, thread in enumerate(tracethreads):
				self.assertTrue(len(thread.output)>0)
				# print thread.output
				if tn==0:
					self.assertTrue(thread.output.count('Operating-Time  INFO: ') > 15)
				elif tn==1:
					self.assertTrue(thread.output.count(self.controlclass.username+' ') > 30)
				

	def test_trace_relogin(self):
		"""
		verify that controlclass logins again after DUT boots
		"""
		self.controlclass.trace_command = 'ls /st/op ; sleep 5000 ; do /o/b'
		self.controlclass.trace_relogin = True
		self.controlclass.start()
		time.sleep(10)
		self.controlclass.trace_command = 'ls /st/op'
		time.sleep(50)
		self.controlclass.stoptrace()
		self.controlclass.join()
		self.assertTrue(len(self.controlclass.output)>0)
		# print self.controlclass.output
		self.assertTrue(self.controlclass.output.count('Operating-Time  INFO: ') == 2)

