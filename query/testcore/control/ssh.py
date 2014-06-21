import threading
import datetime
import re
import time
import sys
import unittest
import logging

logger = logging.getLogger(__name__)

"""
SSH control

requires installation of pycrypto. 
 * Linux: install it from source. 
 * Windows: installer from http://www.voidspace.org.uk/python/modules.shtml#pycrypto

requires installation of paramiko. 
 * Download/Clone from https://github.com/paramiko/paramiko, and use python setup.py install

requires installation of scp.
 * Download/Clone from https://github.com/jbardin/scp.py, and use python setup.py install
"""


import paramiko # for ssh/sftp, from  http://www.lag.net/paramiko/
# old: import paramiko_scp # for scp, from https://code.launchpad.net/~jbardin-deactivatedaccount/paramiko/paramiko_scp
import scp as paramiko_scp # new: use actual version from github
import select

import base



class SSH(base.control):
	"""
	ssh to LANCOM DUT
	
	methods:
		.login()
			opens ssh tunnel to device
		.query(query)
			executes command inside DUT and returns output. Can only be used for commands which finish by themselves and do not require further interaction
		.close()
			closes ssh tunnel
	
	example:
		s = ssh()
		s.log = l
		s.host = '192.168.88.1'
		s.password = 'test'
		if s.login():
			q = s.query('sysinfo')
			if q is not None:
				l.write('query result: ')
				l.write(q)
			else:
				l.write('query was not answered')
		s.close()
	"""
		
	def __init__(self, *args, **kwargs):
		
		super(SSH, self).__init__( *args, **kwargs) # init next class in MRO		
			
		self.host = None
		self.port = 22
		self.username = '' # DUT login credentials
		self.password = '' # DUT login credentials
		
		self.timeout_scriptexecution = 40
		self.timeout_scriptstart = 10

		self.lb = '\r' # linebreak to DUT
		
		for key in kwargs:
			setattr(self, key, kwargs[key]) 		
		
		self._con = None # ssh instance
		self.loggedin = False


	def login(self):
		self.loggedin = False
		if self._con is None:
			self._con = paramiko.SSHClient()
			self._con.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # accept every host key
			try:
				self._con.connect(self.host, username=self.username, password=self.password)
				self.loggedin = True
			except paramiko.AuthenticationException:
				pass
			except:
				# self.log.write('could not connect to '+self.host)
				self.loggedin = False
		return self.loggedin

			
	def query(self,query):
		if self.loggedin:
			try:
				stdin, stdout, stderr = self._con.exec_command(query, bufsize=1024*1024*4) # specifying bufsize apparently fixes random glitches in long queries (e.g. readmib)
			except paramiko.SSHException:
				logger.error('exec '+query+' error')
			except EOFError:
				logger.warning('exec '+query+' EOF')
			else:
				return ''.join(stdout)
		return None

		
	def push(self, cmd):
		"""
		push cmd to shell, do not check for finish
		"""
		
		# open interactive shell 
		if self.login():
			channel = self._con.invoke_shell()
			channel.settimeout(5)
			bufsize = -1
			stdin = channel.makefile('wb', bufsize)
			stdout = channel.makefile('rb', bufsize)
			stderr = channel.makefile_stderr('rb', bufsize)
			exited = False
			
			# transmit script
			stdin.write(cmd+self.lb)
			stdin.flush()
			time.sleep(0.1)
			channel.settimeout(0) # do not wait for data
			time.sleep(0.1)
			stdin.close()
			stdin.channel.shutdown_write()
			self.close()
			return True
		self.close()
		return False

	

	"""
	secure copy to LANCOM DUT
	
	methods:
		.putfile(sourcefile, target)
			target is a reseved name inside the DUT, see LCOS source code
			opens/closes ssh tunnel by itself
	
	example:
		s = scp()
		s.log = l
		s.host = '192.168.88.1'
		s.password = 'test'
		s.putfile(r'c:\firmwares\LC-1711-8.62.0010.upx','firmware')
		s.putfile(r'c:\firmwares\1711.lcs','script') # uses beginscript wrapper
	"""
	
	

	def putfile(self, sourcefile, target):
		"""
		scp upload of file
		note: uploads of files which need a password is de factro not possible since paramiko does not support its parallel transport
		"""
		targets = [
			'config',
			'firmware',
			'ssl_cert',
			'ssl_privkey',
			'ssl_rootcert',
			'ssl_pkcs12',
			'ssh_rsakey',
			'ssh_dsakey',
			'ssh_authkeys',
			'ssh_known_hosts',
			'vpn_rootcer',
			'vpn_devcert',
			'vpn_devprivkey',
			'vpn_pkcs12',
			'vpn_pkcs12_2',
			'vpn_pkcs12_3',
			'vpn_pkcs12_4',
			'vpn_pkcs12_5',
			'vpn_pkcs12_6',
			'vpn_pkcs12_7',
			'vpn_pkcs12_8',
			'vpn_pkcs12_9',
			'vpn_pkcs12_2',
			'vpn_add_cas',
			'default_pkcs12',
		]
		if target in targets and self.login():
			scp = paramiko_scp.SCPClient(self._con.get_transport())
			scpsuccess = True
			try:
				scp.put(sourcefile, remote_path = target, recursive = False, preserve_times = False)
			except:
				scpsuccess = False
				logger.error('scp: put failed'+repr(sys.exc_info()))
			self.close()
			return scpsuccess
			
		if target == 'script' and self.login():
			with open(sourcefile,'r') as source:
				res = self.script_exec(source.readlines())
				self.close()
				return res

		self.close()			
		return False
	
	
	def script_exec(self, script, wait_for_finish=True):
		"""
		scp of script not supported, use beginscript inside session instead
		
		note: script is list of strings
		wait_for_finish: evalute script execution success (or just start it)
		"""
		
		# open interactive shell 
		channel = self._con.invoke_shell()
		channel.settimeout(5)
		bufsize = -1
		stdin = channel.makefile('wb', bufsize)
		stdout = channel.makefile('rb', bufsize)
		stderr = channel.makefile_stderr('rb', bufsize)
		exited = False
		
		# transmit script
		stdin.write('beginscript'+self.lb)
		for line in script:
			time.sleep(0.002)
			stdin.write(line+self.lb)
			stdin.flush()
			if line.strip().endswith('exit'):
				exited = True
				break
		if not exited:
			# force exit
			stdin.write('exit'+self.lb)
			stdin.flush()

		# eval script start
		channel.settimeout(0) # do not wait for data
		outbuf=''
		timer = self.timeout_scriptstart * 10
		start_found = False
		while not start_found and timer>0:
			# read until no available data anymore
			while True:
				try:
					outbuf += stdout.read(1)
				except:
					break
			# look for notification
			for text in ['Starting script']:
				if text in outbuf: 
					start_found = True
					break
			timer -= 1
			time.sleep(0.1)
			
			
		if not wait_for_finish:

			stdin.close()
			stdin.channel.shutdown_write()			
			stdout.close()
			channel.close()
			return start_found
		
		else:
			
			if start_found:
				# eval script execution
				timer = self.timeout_scriptexecution * 10
				msg_found = False
				while not msg_found and timer>0:
					# read until no available data anymore
					while True:
						try:
							outbuf += stdout.read(1)
						except:
							break
					# look for notification
					for text in ['Finished script successfully', 'Script Error', 'Script is incomplete']:
						if text in outbuf: 
							msg_found = True
							break
					timer -= 1
					time.sleep(0.1)
				if timer<=0:
					logger.warning('script execution timeout (max {0} s)'.format(self.timeout_scriptexecution))
				else:
					logger.debug('script execution took {0}s'.format(self.timeout_scriptexecution- timer/10))


			stdin.close()
			stdin.channel.shutdown_write()
			stdout.close()
			channel.close()
			
			# evaluate
			success = False
			if 'Finished script successfully' in outbuf:
				success = True
			elif 'Script Error' in outbuf:
				logger.warning('Script Error')
			elif 'Script is incomplete' in outbuf:
				logger.warning('Script is incomplete')
			else:
				logger.warning('Script status unknown')
			return success
			
		
		
	def script_start(self, script):
		"""
		start a script in background (does not check for success)
		"""
		return self.script_exec(script, wait_for_finish=False)
		
		
	def firmware_upload(self, fw_file):
		if fw_file is not None:
			if self.putfile(fw_file, 'firmware'):
				c = 10
				time.sleep(10)
				while c>0 and not self.is_alive():
					c-=1
					time.sleep(6)
				if c>0:
					logger.info('uploaded '+fw_file+' successfully')
					return True
				else:
					logger.error('device not ready after firmware upload')
			else:
				logger.error('SCP failed')
		return False


class SSHTrace(threading.Thread, SSH):

	_trace_concurrentlimit = None
	#~ active = False
	#~ finished = False
	
	def __init__(self,  *args, **kwargs):
		threading.Thread.__init__(self)
		self.setDaemon(True)

		self.trace_command = None # trace / repeat command
		self.trace_relogin = True # if logout occurs, re-login automatically
		self.trace_inputtimeout = 10
		
		SSH.__init__(self,  *args, **kwargs)
		
		self.channel = None
		self.trace_active = False # used as message from foreground to background 
		self.trace_finished = False # ussed as message from background to foreground		

		#~ self.debug = True


	def starttrace(self,trace = None, timeout=None):
		""" login and start the trace command"""
		
		if self.login():
			self.channel = self._con.invoke_shell(term='vt100',width=255)
			time.sleep(1)
			if trace is not None:
				self.trace_command = trace
			if self.trace_command is not None:
				logger.info('{0}: start trace "{1}"'.format(self.host, self.trace_command))
				self.channel.send(self.trace_command+self.lb)
				bufsize = -1
				self.stdin = self.channel.makefile('wb', bufsize)
				self.stdout = self.channel.makefile('rb', bufsize)
				self.transport = self.channel.get_transport()
		else:
			logger.error('could not login')
			

	def run(self):
		"""read bytes while self.active is True"""
		
		self.trace_active = True
		
		#~ dead = self.timeout_outband_command		
		if not self.loggedin:
			self.starttrace()
			
		lastdata = datetime.datetime.now()
		while self.trace_active:
			# print self.channel.exit_status_ready(), self.channel.recv_exit_status(), self.channel.recv_ready()
			#~ print 'test channel', self.transport.active 
			if self.channel is not None and self.transport.active:
				self.channel.settimeout(0) # do not wait for data
				bytes=''
				while self.transport.active:
					try:
						#~ if self.transport.active:
						bytes += self.stdout.read(1024)
						
					except:
						break
				if len(bytes)>0:
					self._writeout(bytes)
			else:
				logger.info( 'connection lost')
				
				
				self.stdin.close()
				self.stdin.channel.shutdown_write()
				self.channel.settimeout(1) # wait for data again
				bytes = ''
				try:
					bytes= ''.join(self.stdout.read())
					self.stdout.close()
				except:
					pass
				try:
					self.channel.close()
				except EOFError:
					pass
				self._writeout(bytes)
				
			
				if self.trace_relogin:
					logger.warning('{0}: trying to login again'.format(self.host))
					self.close()
					time.sleep(5) # LCOS accepts a connection in shutdown which will die silently
					self.starttrace()
				else:	
					self.trace_active = False
		
		self.trace_finished = True
		#~ if self.tracefile is not None:
			#~ ft.close()
			#~ logger.debug('trace {0} closed'.format(self.tracefile))


	def stoptrace(self):
		
		self.trace_active = False
		#~ self.log.write('wait finish')
		fincount = 0
		while not self.trace_finished and fincount<100:
			time.sleep(0.1)
			fincount+=1
		if self.channel is not None:
			self.stdin.close()
			self.stdin.channel.shutdown_write()
			self.channel.settimeout(1) # wait for data again
			bytes = ''
			try:
				bytes= ''.join(self.stdout.read())
			except:
				pass
			try:
				self.channel.close()
			except EOFError:
				pass
			self._writeout(bytes)
		if fincount>=100: 
			logger.error('trace: finish timed out')
			return None
		self.close()
		return self.output




# UnitTest module wrapper	

class SSHTests(base.CommonTests):
	
	def setUp(self):
		self.controlclass = SSH(host=DUThost, username=DUTuser, password=DUTpw, debug=DEBUG)
	

class SSHTraceTests(base.CommonTraceTests):

	def setUp(self):
		self.controlclass = self.getClass()
	
	# some testcases need more than one class instance, provide method to get one
	@staticmethod
	def getClass():
		return SSHTrace(host=DUThost, username=DUTuser, password=DUTpw, debug=DEBUG)


class SCPTests(unittest.TestCase):

	def setUp(self):
		self.controlclass = SSH(host=DUThost, username=DUTuser, password=DUTpw, debug=DEBUG)

	def test_SCT_firmwareupload(self):
		"""
		upload a FW with SCP 
		"""
		self.assertTrue(self.controlclass.firmware_upload(DUTfw_file))


if __name__=='__main__':
	
	#
	# To run unitests, change parameters below to match your DUT/setup
	#
	
	DEBUG=False # print output of device
	
	# config target which shall be used for unittests
	DUThost = '192.168.1.2'
	DUTuser = 'root'
	DUTpw = 'LANCOM'
	
	# the SCP firmware upload uses the following parameters to find a firmware in Alpha
	DUTfw_prefix = 'LC-1681V' 
	DUTfw_version = '8.84'
	ALPHA = r'\\lcs-file\lcs-en\Alpha\LANCOM\LCOS' # windows
	
	# example hirschmann:
	# DUTfw_prefix = 'BAT_OWL' 
	# DUTfw_version = '8.90'
	# ALPHA = r'\\lcs-file\LCS-EN\Alpha\LANCOM\BAT_OWL\hirschmann'
	
	# example linux
	# ALPHA = r'/home/automaton/Alpha/LANCOM/LCOS'
	
	import firmware
	f = firmware.Search()
	f.dev_prefix = DUTfw_prefix
	DUTfw_file, DUTfw_build = f.alpha_dev_version(alpha_root=ALPHA, fw_version=DUTfw_version)
	
	# configure logging
	logging.basicConfig(level=logging.CRITICAL)
	for handler in logging.root.handlers:
		handler.addFilter(logging.Filter('__main__')) # silence other modules (e.g. paramiko) output

	if sys.version_info[:2]>(2,6):
		unittest.main(verbosity=2)
	else:
		unittest.main()
	
	
