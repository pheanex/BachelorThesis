import threading
import time, datetime
import sys
import re
import serial # PySerial http://pyserial.sourceforge.net/index.html
import logging
import traceback
import unittest
logger = logging.getLogger(__name__)

import base

"""
Serial/RS232 control

requires PySerial http://pyserial.sourceforge.net/index.html
"""


class Serial(base.control):
	
	"""
	serial connection to LANCOM DUT
	
	Serial implements
		.login()
			opens serial connection and logs into to device (if required)
		.query(query)	
			get the answer for a command
		.send(text)
			sends a line of text to devices (the deafult ist to append linebreak)
		see also methods of base class (module base)

	"""
	
	def __init__(self, *args, **kwargs):
		
		super(Serial, self).__init__(*args, **kwargs) # init next class in MRO



		# DUT
		self.host = None # DUT IP
		# self.port = 23 # DUT port
		self.username = '' # DUT login credentials
		self.password = '' # DUT login credentials

		# timeouts
		self.timeout_outband = 10
		self.timeout_session = 5
		self.timeout_command = 2
		self.timeout_query = 120
		self.timeout_outband_command = 60

		self.timeout_scriptexecution = 40
		self.timeout_scriptstart = 10

		# regexes for prompts
		self.prompt_outband = re.compile(r'Outband-\d+ Bit/s OK')
		self.prompt_line = re.compile(r'[\r\n]+.*:/.*[\r\n]+> ') # linebreak, something(usually user@router).  :/. something, linebreak, >, space
		self.prompt_username = re.compile(r'[nN]ame:') # 
		self.prompt_password = re.compile(r'[pP]assword:')
		self.prompt_error = re.compile(r'[lL]ogin [eE]rror')
		
		self.serial_baudrate = 115200
		self.serial_XONXOFF = False
		self.serial_RTSCTS = True
		self.serial_DSRDTR = True
		
		self.lb = '\r' # linebreak to DUT
		
		# try to login this often
		self.logintries = 10

		for key in kwargs:
			setattr(self, key, kwargs[key]) 

		self._con = None # telnet instance
		self.loggedin = False
		
		self.inbuf = ''
		

	def _init(self):
		if self.host is not None:
			if self._con is not None:
				return True
				#~ self._con.close()
				#~ self._con = None
			try:
				self._con = serial.Serial(self.host, baudrate=self.serial_baudrate, xonxoff=self.serial_XONXOFF, rtscts=self.serial_RTSCTS, dsrdtr=self.serial_DSRDTR, timeout=0)
				self.inbuf = ''
				return True
			except:
				logger.error('{0}: opening connection failed with {1}'.format(self.host, traceback.format_exc()))
				return False
		return False


	def send(self, text='', line=True):
		"""send string, with optional linebreak"""
		if self._con is not None:
			if line:
				self._con.write(text+self.lb)
			else:
				self._con.write(text)
			return True
		else:
			logger.warning('{0}: tried to send to not existing connection'.format(self.host))
			return False
	
	def read(self):
		data = self._con.read(self._con.inWaiting())
		self._writeout(data)
		return data
		
	
	def expect(self, choices, timeout=5):
		"""wait for one of the regexes in choices to match
		if found, return choice index, choice object, and text before match
		if timeout, return either (-1, None, None) when new data arrived, or (None, None, None)
		"""
		index = False
		newdata = False
		t0 = datetime.datetime.now()
		t1 = t0+datetime.timedelta(seconds = timeout)
		# time.sleep(0.002)
		while not index and datetime.datetime.now()<t1:
			data = self.read()
			if len(data)>0:
				newdata=True
			self.inbuf+=data
			# print 'inbuf <<<', self.inbuf, '>>>'
			for pn, prompt in enumerate(choices):
				if re.search(prompt, self.inbuf) is not None:
					index = True
					text, self.inbuf = re.split(prompt, self.inbuf, maxsplit=1)
					break
			if not index:		
				time.sleep(0.001)
		logger.debug('{0}: time spent in expect {1}'.format(self.host, datetime.datetime.now()-t0))
		if index:
			return (pn, prompt, text)
		else:
			if newdata:
				return (-1, None, None)
			else:
				return (None, None, None)


	def login(self):
		"""login into LANCOM device"""
		logger.debug('{0}: trying to login if needed'.format(self.host))
		t0 = datetime.datetime.now()
		self.loggedin = False
		if self._init():
			logins = 0
			self.send('')
			while not self.loggedin and logins<self.logintries:
				index, object, text = self.expect([self.prompt_outband, self.prompt_username, self.prompt_password, self.prompt_error, self.prompt_line], 0.25)
				logger.debug('{0}: expect index {1} ({2})'.format(self.host, index, logins))
				# print 'inbuf expect ',found, '<<<', self.inbuf, '>>>'
				if index is not None:
					if index==0:
						logger.debug('{0}: got Outband'.format(self.host))
						self.send('\r',False)
					elif index==1:
						logger.debug('{0}: username queried'.format(self.host))
						self.send(self.username)
						logins +=1					
					elif index==2:
						logger.debug('{0}: password queried'.format(self.host))
						self.send(self.password)
						logins +=1					
					elif index==3:
						logger.error('{0}:got error while logging in'.format(self.host))
						logins +=1
					elif index==4:
						logger.info('{0}: got CLI prompt, logged in'.format(self.host))
						self.loggedin = True
					elif index==-1:
						logger.debug('{0}: new data, trying to stimulate output ({1})'.format(self.host, logins))
						self.send('')	
						logins +=1					
				else:
					logger.debug('{0}: no new data, trying to stimulate output ({1})'.format(self.host, logins))
					self.send('')	
					logins +=1					
		else:
			logger.error('{0}: init failed'.format(self.host))
		if self.loggedin:
			logger.info('{0}: login took {1}'.format(self.host, datetime.datetime.now()-t0))
		else:
			logger.info('{0}: no login in {1}'.format(self.host, datetime.datetime.now()-t0))
		return self.loggedin
		
	def query(self, query):
		"""return the answer to a commandline command"""
		if self.loggedin:
			#~ l.write('try to query '+query)
			self.inbuf = ''
			self.send(query)
			index, object, text = self.expect([re.compile(query)], self.timeout_query)
			index, object, text = self.expect([self.prompt_line], self.timeout_query)
			#~ self.log.write('expect returned ('+repr(index)+') object '+repr(object)+' = '+text)
			if index is not None:
				return text
		return None
		
	
	

	def script_exec(self, script, wait_for_finish=True):
		"""
		execute script 
		
		script is list of strings
		wait_for_finish: evalute script execution success (or just start it)
		"""
	
		if not self.loggedin:
			return False
			
		# send script
		script_sent = True
		exited = False
		self.send('beginscript')
		for line in script:
			self.send(line)
			if line.strip().endswith('exit'):
				exited = True
				break
			else:
				try:
					index, object, text = self.expect(['script>'],self.timeout_command)
					self._writeout(text)
				except :
					logger.error('script: exception '+traceback.format_exc())
					script_sent = False
					break
				if object is None:
					logger.error('script: timeout')
					script_sent = False
					break
		if script_sent and not exited :
			self.send('exit')
		try:
			index, object, text = self.expect([self.prompt_line], self.timeout_command)
			self._writeout(text)
		except:
			logger.error('prompt after sending script: exception '+traceback.format_exc())
			script_sent = False
		if object is None:
			logger.error('prompt after sending script: timeout')
			script_sent = False
		
		if not script_sent:
			return False
		
		# evaluate if script started
		script_start = False
		try:
			index, object, text = self.expect(['Starting script'], self.timeout_scriptstart)
			self._writeout(text)
		except:
			logger.error('script start EOF'.format(self.timeout_scriptstart))
		if index==-1:
			logger.error('script start timeout (max {0} s)'.format(self.timeout_scriptstart))
		if index==0:
			script_start = True
			
		if not wait_for_finish:
			return script_start
			
		# evaluate if script executedd
		success = False
		try:
			index, object, text = self.expect(['Finished script successfully', 'Script Error', 'Script is incomplete'], self.timeout_scriptexecution)
			self._writeout(text)
		except:
			logger.error('script execution EOF'.format(self.timeout_scriptstart))
		if index==-1:
			logger.error('script execution timeout (max {0} s)'.format(self.timeout_scriptexecution))
		elif index==0:
			success = True
		elif index==1:
			logger.warning('Script Error')
		elif index==2:
			logger.warning('Script is incomplete')
			
		return success
			

		
	def script_start(self, script):
		"""
		start a script in background (does not check for success)
		"""
		return self.script_exec(script, wait_for_finish=False)
			
		
		
class SerialTrace(threading.Thread, Serial):


	"""
	SerialTrace implements a thread running in the background to execute a trace/repeat command. 
	If a logout/boot happens, it will be automatically logged in again.
	
	See examples at end of file
	"""
	
	_trace_concurrentlimit = 1 # how many traces per host can run concurrent
	
	def __init__(self,  *args, **kwargs):
		threading.Thread.__init__(self)
		self.setDaemon(True)
		
		self.trace_command = None # trace / repeat command
		self.trace_relogin = True # if logout / new "Outband" occurs, re-login automatically

		Serial.__init__(self,  *args, **kwargs) # this also sets args, kwargs as attributes
		
		self.trace_active = False # used as message from foreground to background 
		self.trace_finished = False # ussed as message from background to foreground
		
		
	
	def starttrace(self,trace = None, timeout=None):
		""" login and start the trace command"""
		
		if self.login():
			time.sleep(1)
			if trace is not None:
				self.trace_command = trace
			if self.trace_command is not None:
				logger.debug('{0}: start trace "{1}"'.format(self.host, self.trace_command))
				self.send(self.trace_command)


	def run(self):
		"""background thread to read bytes / relogin while self.active is True"""
		self.trace_active = True
		outband = False
		dead = self.timeout_outband_command
		if not self.loggedin:
			self.starttrace()
			
		while self.trace_active:
			#~ print 'dead-counter {0}'.format(dead)
			index, object, text = self.expect([self.prompt_outband, self.prompt_line], 1)
				# print 'inbuf expect ',found, '<<<', self.inbuf, '>>>'
			if index is not None:
				if index==0:
					logger.debug('{0}: got Outband'.format(self.host))
					outband = True
					self.send('')
					dead = self.timeout_outband_command
				elif index==1:
					# logger.info('{0}: got CLI prompt, logged in'.format(self.host))
					self.loggedin = True
					outband = False
					dead = self.timeout_outband_command
				elif index==-1:
					# normal data, continue
					outband = False
			else:
				if self.trace_relogin:
					dead -= 1
					if dead<=0:
						logger.warning('{0}: no data, trying to login again'.format(self.host))
						self.starttrace()
						dead = self.timeout_outband_command
			if outband and self.trace_relogin:
				self.starttrace()
				
		self.read()
				
		self.trace_finished = True


	def stoptrace(self):
		"""end background thread"""
		
		self.trace_active = False
		#~ self.log.write('wait finish')
		fincount = 0
		while not self.trace_finished and fincount<100:
			time.sleep(0.1)
			fincount+=1
		try:
			self.read()
		except:
			logger.error('{0}: read serial trace defunct'.format(self.host))
		if fincount>=100: 
			logger.error('{0}: finishing trace timed out'.format(self.host))
			return None
		self.close()
		return self.output
		
		
# UnitTest module wrapper	

class SerialTests(base.CommonTests):
	
	def setUp(self):
		self.controlclass = Serial(host=DUThost, username=DUTuser, password=DUTpw, serial_XONXOFF= DUTxonxoff, serial_RTSCTS=DUTrtscts, serial_DSRDTR=DUTdsrdtr, debug=DEBUG, timeout_query=240)
		

	def tearDown(self):
		if self.controlclass._con is not None:
			self.controlclass.send('quit') # each test shall start at the login
		try:	
			self.controlclass.close()
		except:
			pass


class SerialTraceTests(base.CommonTraceTests):

	def setUp(self):
		self.controlclass = SerialTrace(host=DUThost, username=DUTuser, password=DUTpw, serial_XONXOFF= DUTxonxoff, serial_RTSCTS=DUTrtscts, serial_DSRDTR=DUTdsrdtr, debug=DEBUG)		
		

if __name__=='__main__':
	
	#
	# To run unitests, change parameters below to match your DUT/setup
	#
	
	DEBUG=False # print output of device
	#~ DEBUG=True # print output of device
	
	# config target which shall be used for unittests
	DUThost = 'COM7' # windows
	# DUThost = '/dev/ttyUSB0' # linux
	DUTuser = 'root'
	DUTpw = 'LANCOM'
	DUTxonxoff = False
	DUTrtscts = True
	DUTdsrdtr = True
	# note: when using USB converter on linux, both hardware flowcontrols might have to be set to False, e.g.
	# DUTxonxoff = True
	# DUTrtscts = False
	# DUTdsrdtr = False

	logging.basicConfig(level=logging.CRITICAL)
	
	if sys.version_info[:2]>(2,6):
		unittest.main(verbosity=2)
	else:
		unittest.main()
