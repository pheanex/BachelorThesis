import os
import shutil
import logging
import re
import time
logger = logging.getLogger(__name__)

class TelnetTFTPwrap(object):


	def __init__(self, *args, **kwargs):
		super(TFTPwrap, self).__init__(*args,**kwargs) # init next class in MRO
		self.TFTPserver = None
		self.TFTPdir = None
		self.TFTPprefix = ''
		
	def loadfirmware(self, file, timeout_boot = 150):
		"""
		load firmware file into device and wait for the end of booting
		
		file must be a valid file in a place from where it can by delivered by the TFTP-server
		"""	
		success = False
		blocks = 0
		if self.loggedin:
			self.send('loadfirmware -s {0} -f {1}'.format(self.TFTPserver, file))
			while not success:
				try:
					index, object, text = self._con.expect([self.prompt_line, '#', 'going down', re.compile('[E|e]rror')], self.timeout_command)
				except EOFError:
					logger.error('loadfirmware: telnet session reached EOF')
					break
				if index==0:
					logger.debug('loadfirmware: got prompt')
				elif index==1:
					blocks +=1
				elif index==2:
					logger.info('loadfirmware: transferred circa {} KB. device is now booting'.format(blocks*8))
					success = True
				elif index==3:
					logger.error('loadfirmware: got error message from device')
					break
				elif index==-1:
					logger.error('loadfirmware: waiting for device timed out')
					break
					
		if success:
			time.sleep(20)
			loop=0
			success = False
			while not success and loop<timeout_boot:
				success = self.is_alive()
				if not success:
					time.sleep(10)
					loop+=10
		return success
		
	def run_loadfirmware(self, file):
		"""
		load fimrmware file into device. Login/firmwware/close in one method.
		file will be copied into TFTP servers directory beforehand, with self.TFTPprefix before the filename (for cases where directory is used ba several agents)
		"""
		
		if self.TFTPserver is not None and self.TFTPdir is not None and self.login():
			tftpfile = os.path.join(self.TFTPdir, self.TFTPprefix+os.path.basename(file))
			shutil.copyfile(file, tftpfile)
			logger.debug('copied {0} to {1}'.format(file, tftpfile))
			q = self.loadfirmware(os.path.basename(tftpfile))
			self.close()
			return q
		self.close()
		return False
		
		
		
	def readconfig(self, file):
		pass
		
	def writeconfig(self, file):
		pass
		
	def readscript(self, dest, parameters=''):
		pass
		
	def loadscript(self, dest, parameters=''):
		pass
		
		
	
	