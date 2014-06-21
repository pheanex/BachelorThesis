import threading
import re
import time
import logging
import unittest
import datetime
import sys

import telnetlib
import socket

logger = logging.getLogger(__name__)

import base

class Telnet(base.control):
	
	"""
	telnet to LANCOM DUT
	
	methods form base
		.login()
			opens telnet to device
		.query(query)
			executes command inside DUT and returns output (waits for self.prompt_line)
		.close()
			closes telnet 
	
	example:
		t = telnet()
		t.host = '192.168.1.1'
		t.password = 'test'
		if t.login():
			# login successful
			q = t.query('sysinfo')
			if q is not None:
				l.write('query result: ')
				l.write(q)
			else:
				l.write('query was not answered')
		t.close()
	"""


	def __init__(self, *args, **kwargs):
		
		super(Telnet, self).__init__(*args, **kwargs) # init next class in MRO
		
		# DUT
		self.host = None # DUT IP
		self.port = 23 # DUT port
		self.username = '' # DUT login credentials
		self.password = '' # DUT login credentials

		# timeouts
		self.timeout_session = 5
		self.timeout_command = 2
		self.timeout_query = 30

		self.timeout_scriptexecution = 40
		self.timeout_scriptstart = 10

		# rergexes for prompts
		# the CLI prompt has do be rather strict to avaid matching stuff which can occur naturally in a queries response
		self.prompt_line = re.compile(r'[\r\n]+.*:/.*[\r\n]+> ') # linebreak, something(usually user@router).  :/. something, linebreak, >, space
		self.prompt_line_simple = '> ' # for string find in self.query. If found, the regex search for prompt_line will be performed
		self.prompt_username = re.compile(r'[nN]ame:')
		self.prompt_password = re.compile(r'[pP]assword:')
		self.prompt_error = re.compile(r'[lL]ogin [eE]rror')
		
		self.lb = '\r\n' # linebreak to DUT
		
		# try to login this often
		self.logintries = 2

		for key in kwargs:
			setattr(self, key, kwargs[key]) 

		self._con = None # telnet instance
		self.loggedin = False
		
		

	def _init(self):
		
		def optioncallback(socket, command , option):
			# do nothing
			pass
		
		if self.host is not None:
			if self._con is not None:
				self._con.close()
				self._con = None
			try:
				self._con = telnetlib.Telnet(self.host, self.port, self.timeout_session)
				# IMPORTANT: inhibit answering telnet options. Otherwise, all options are replied with WONT/DONT by telnetlib. 
				# Since the DUTs performs some option queries, the negative replies by telnetlib will result in a DUT not accespting our normal commands/username/password
				# this problem is well hidden: it occurs only when a Telnet.read_* or Telnet.expect command is used, not in scripts which only use Telnet.write
				self._con.set_option_negotiation_callback(optioncallback) # inhibit reply to option by do-nothing callback
				# self._con.set_debuglevel(1)
				return True
			except:
				logger.error('opening connection to {0}:{1} failed'.format(self.host, self.port))
				return False
		return False
		

	def send(self, text='', line=True):
		if self._con is not None:
			if line:
				self._con.write(text+self.lb)
			else:
				self._con.write(text)
			return True
		else:
			logger.warning('tried to send to not existing connection')
			return False

	
	#~ def expect(self, choices, timeout=5):
		#~ """wait for one of the regexes in choices to match
		#~ if found, return choice index, choice object, and text before match
		#~ if timeout, return either (-1, None, None) when new data arrived, or (None, None, None)
		#~ """
		#~ time_spent = 0
		#~ index = False
		#~ newdata = False
		#~ # time.sleep(0.002)
		#~ self.inbuf = ''
		#~ while not index and time_spent<timeout:
			#~ try:
				#~ data = self._con.read_some()
			#~ except EOFError:
				#~ print 'EOF'
				#~ time_spent = timeout
			#~ if data is not None:
				#~ newdata=True
				#~ self.inbuf+=data
			#~ print 'inbuf <<<', len(self.inbuf), '>>>'
			#~ for pn, prompt in enumerate(choices):
				#~ if re.search(prompt, self.inbuf) is not None:
					#~ index = True
					#~ text, self.inbuf = re.split(prompt, self.inbuf, maxsplit=1)
					#~ break
			#~ if not index:		
				#~ time.sleep(0.001)
				#~ time_spent+=0.001
					
		#~ if index:
			#~ return (pn, prompt, text)
		#~ else:
			#~ if newdata:
				#~ return (-1, None, None)
			#~ else:
				#~ return (None, None, None)


	def login(self):
		"""login into LANCOM device"""
		self.loggedin = False
		if self._init():
			logins = 0
			while not self.loggedin and logins<self.logintries:
				try:
					index, object, text = self._con.expect([self.prompt_line, self.prompt_username, self.   prompt_password, self.prompt_error], self.timeout_command)
					self._writeout(text)
				except EOFError:
					logger.debug('login: EOF reached')
					break
				#~ self.log.write('expect returned ('+repr(index)+') object '+repr(object)+' = '+text)
				if index==0:
					logger.debug('login: logged in')
					self.loggedin = True
				elif index==1:
					logger.debug('login: username queried')
					self.send(self.username)
					logins +=1
				elif index==2:
					logger.debug('login: password queried')
					self.send(self.password)
				elif index==3:
					logger.error('login: login error')
					break
				elif index==-1:
					logger.debug('login: trying to stimulate output')
					self.send()
					logins +=1
		return self.loggedin


	def query(self, query):
		"""
		return the answer to a commandline command
		
		note: telnet.expect would be the obivous choice to implement this method.
		However, expect scales badly for queries with big outputs (e.g. #readmib#) because it uses
		a regex-search on the increasing incoming buffer (which telnetlib hardcodes to increase in 
		50 byte chunks and therefore the search happens rather frequently). 
		The plain string find which is used by read_until behaves much nicer. For really large queries,
		ssh is preferable since by protocol design it does not need to look for a prompt at all.
		"""
		if self.loggedin:
			# l.write('try to query '+query)
			self.send(query)
			found_cli = False
			text = ''
			starttime = datetime.datetime.now()
			try:
				while not found_cli:
					text += self._con.read_until(self.prompt_line_simple, self.timeout_query)
					m = self.prompt_line.search(text) # complete regex search only if it makes sense, i.e. we found something which looks like a prompt at least a little bit
					if m:
						found_cli = True
					t1 = datetime.datetime.now()-starttime
					if (t1.seconds+t1.days*24*3600) > self.timeout_query:
						break
				self._writeout(text)
			except (socket.error):
				pass
			if found_cli is not None:
				if query in text:
					text = text.split(query,1)[1]
				return re.split(self.prompt_line, text, maxsplit=1)[0]
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
					index, object, text = self._con.expect(['script>'],self.timeout_query)
					self._writeout(text)
				except EOFError:
					logger.error('script: EOF reached')
					script_sent = False
					break
				if index==-1:
					logger.error('script: timeout')
					script_sent = False
					break
		if script_sent and not exited :
			self.send('exit')
		try:
			index, object, text = self._con.expect([self.prompt_line], self.timeout_command)
			self._writeout(text)
		except EOFError:
			logger.error('prompt after sending script: EOF reached')
			script_sent = False
		if index==-1:
			logger.error('prompt after sending script: timeout')
			script_sent = False
		
		if not script_sent:
			return False
		
		# evaluate if script started
		script_start = False
		try:
			index, object, text = self._con.expect(['Starting script'], self.timeout_scriptstart)
			self._writeout(text)
		except EOFError:
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
			index, object, text = self._con.expect(['Finished script successfully', 'Script Error', 'Script is incomplete'], self.timeout_scriptexecution)
			self._writeout(text)
		except EOFError:
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
			
	
		
class TelnetTrace(threading.Thread, Telnet):

	_trace_concurrentlimit = None

	"""
	TelnetTrace implements a thread running in the background to execute a trace/repaet command. 
	
	See examples at end of file
	"""
	def __init__(self,  *args, **kwargs):
		threading.Thread.__init__(self)
		self.setDaemon(True)
		
		self.trace_command = None # trace / repeat command
		self.trace_relogin = True # if logout / new "Outband" occurs, re-login automatically

		Telnet.__init__(self,  *args, **kwargs) # this also sets args, kwargs as attributes
		
		self.trace_active = False # used as message from foreground to background 
		self.trace_finished = False # ussed as message from background to foreground
		
		
	
	def starttrace(self,trace = None, timeout=None):
		""" login and start the trace command"""
		
		if self.login():
			time.sleep(1)
			if trace is not None:
				self.trace_command = trace
			if self.trace_command is not None:
				logger.info('{0}: start trace "{1}"'.format(self.host, self.trace_command))
				self.send(self.trace_command)


	def run(self):
		"""background thread to read bytes / relogin while self.active is True"""
		self.trace_active = True

		if not self.loggedin:
			self.starttrace()
			
		while self.trace_active:
			try:
				index, object, text = self._con.expect([self.prompt_line], 1)
				self._writeout(text)
				if index is not None:
					if index==0:
						#~ logger.debug('{}: got CLI prompt, logged in'.format(self.host))
						self.loggedin = True
					if index==-1:
						#~ logger.debug('{}: timeout '.format(self.host))
						self.loggedin = True
				else:
					pass
			except:
				if self.trace_relogin:
					logger.warning('{0}: EOF, trying to login again'.format(self.host))
					self.starttrace()
				
				
		#~ self.read()
				
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
			#~ self.read()
			pass
		except:
			logger.error('{0}: read serial trace defunct'.format(self.host))
		if fincount>=100: 
			logger.error('{0}: finishing trace timed out'.format(self.host))
			return None
		self.close()
		return self.output


# UnitTest module wrapper	

class TelnetTests(base.CommonTests):
	
	def setUp(self):
		self.controlclass = Telnet(host=DUThost, username=DUTuser, password=DUTpw, debug=DEBUG)
	

class TelnetTraceTests(base.CommonTraceTests):

	def setUp(self):
		self.controlclass = self.getClass()# TelnetTrace(host=DUThost, username=DUTuser, password=DUTpw)

	# some testcases need more than one class instance, provide method to get one
	@staticmethod
	def getClass():
		return TelnetTrace(host=DUThost, username=DUTuser, password=DUTpw, debug=DEBUG)


if __name__=='__main__':
	
	#
	# To run unitests, change parameters below to match your DUT/setup
	#
	
	DEBUG=False # print output of device
	
	# config target which shall be used for unittests
	DUThost = '192.168.1.2'
	DUTuser = 'root'
	DUTpw = 'LANCOM'
	
	logging.basicConfig(level=logging.CRITICAL)
	
	if sys.version_info[:2]>(2,6):
		unittest.main(verbosity=2)
	else:
		unittest.main()
	
