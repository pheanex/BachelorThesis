import os
import glob
import logging
import unittest
logger = logging.getLogger(__name__)

class Search(object):

	def __init__(self, *args, **kwargs):
		self.dev_prefix = None # prefix as it it used in the upx file
		self.alpha_root = None # path to alpha down to device's LCS or OEM dir
		self.fw_dir = None # directory 
		self.fw_version = None # 8.82 etc.
		self.fw_build = None # 124 or '0124'
		self.fw_maxbuild = 999 # larger are usually some non-release builds
		for key in kwargs:
			setattr(self, key, kwargs[key]) 		
	
	
	def alpha_dev_version(self, alpha_root=None, dev_prefix=None, fw_version=None, fw_build=None):
		"""
		finds a specified or the last (highest) build in a device's directory on Alpha. 
		Skipps empty BUIL*-directories. 
		Skipps malformed files (build has to be a 4-digit number, but additional tags like -Rel are ok)
		
		alpha_root, dev_prefix, and fw_version can either specified in the method call or in the class instance
		fw_build can be specified or be None; with None the last(highest) existing build will be searched.
		
		the firmware file and the build will be returned. If no firmware file can be found, (None, None) is returned.
		
		s = Search()
		print s.alpha_dev_version(alpha_root=r'\\lcs-file\lcs-en\Alpha\LANCOM\1711plus\LCS', dev_prefix='LC-1711plus', fw_version='8.62')
		or 
		print s.alpha_dev_version(alpha_root=r'\\lcs-file\lcs-en\Alpha\LANCOM\LCOS', dev_prefix='LC-1711plus', fw_version='8.62')
		returns
		('\\\\lcs-file\\lcs-en\\Alpha\\LANCOM\\1711plus\\LCS\\FIRMWARE.862\\BUIL0103-RU7\\LC-1711plus-8.62.0103-RU7.upx', '0103')
		"""
		
		if alpha_root is None: alpha_root=self.alpha_root
		if dev_prefix is None: dev_prefix=self.dev_prefix
		if fw_version is None: fw_version=self.fw_version
		if alpha_root is None or dev_prefix is None or fw_version is None: return (None, None)
			
		if fw_build is None: fw_build=self.fw_build
		if fw_build is None:
			buildspec = ''
		else:
			buildspec = '{0:04d}'.format(int(fw_build))
			
		
		fwfile = None
		build = None
		# iterate through BUIL directories backwards
		for fw_dir in reversed(sorted(glob.glob(os.path.join(alpha_root,'FIRMWARE.'+fw_version.replace('.',''), 'BUIL'+buildspec+'*')))):
			if os.path.isdir(fw_dir):
				file, b = self.dir_dev_version(fw_dir=fw_dir, dev_prefix=dev_prefix, fw_version=fw_version, fw_build=fw_build)
				if file is not None:
					fwfile, build = file, b
			if fwfile is not None:
				break
		return (fwfile, build)
		
		
	def dir_dev_version(self, fw_dir=None, dev_prefix=None, fw_version=None, fw_build=None):
		"""
		finds a specified or the last (highest) build in a given directory (will not traverse downards). 
		Skipps malformed files (build has to be a 4-digit number, but additional tags like -Rel are ok)
		
		fw_dir, dev_prefix, and fw_version can either specified in the method call or in the class instance
		fw_build can be specified or be None; with None the last(highest) existing build will be searched.
		
		the firmware file and the build will be returned. If no firmware file can be found, (None, None) is returned.
		
		s = Search()
		print s.alpha_dev_version(fw_dir=r'\\lcs-file\LCS-EN\Alpha\LANCOM\LCOS\FIRMWARE.862\BUIL0103', dev_prefix='LC-1711plus', fw_version='8.62')
		note: this would usually be a local directory with several build in it and not Alpha
		returns
		('\\\\lcs-file\\lcs-en\\Alpha\\LANCOM\\1711plus\\LCS\\FIRMWARE.862\\BUIL0103-RU7\\LC-1711plus-8.62.0103-RU7.upx', '0103')
		"""
		if fw_dir is None: fw_dir=self.fw_dir
		if dev_prefix is None: dev_prefix=self.dev_prefix
		if fw_version is None: fw_version=self.fw_version			
		if fw_dir is None or dev_prefix is None or fw_version is None: return (None, None)
		if fw_build is None: fw_build=self.fw_build
		if fw_build is None:
			buildspec = ''
		else:
			buildspec = '{0:04d}'.format(int(fw_build))
		
		fwfile = None
		build = None
		logger.debug('searching in fwdir: '+fw_dir)
		prefix = '{0}-{1}.'.format(dev_prefix, fw_version)
		postfix = '.upx'
		# only accept files which have certain name structure
		filespec = os.path.join(fw_dir, prefix+buildspec+'*'+postfix)
		logger.debug('search filespec: {0}'.format(filespec))
		for file in reversed(sorted(glob.glob(filespec))):
			if os.path.isfile(file) and os.path.getsize(file)>0:
				build = os.path.basename(file)[len(prefix):-1*len(postfix)][0:4] # snip -Rel -RU etc.
				try:
					num = int(build)
					if num<=self.fw_maxbuild:
						logger.debug('found file: '+file+' of build '+build)
						fwfile = file
						break
				except:
					logger.debug('skipped '+file)
		return (fwfile, build)
		

class AlphaTests(unittest.TestCase):
	
	def setUp(self):
		self.search = Search()
		self.search.dev_prefix = DEV_PREFIX
		
	def test_last_alpha_862(self):
		"""103-RU7 is last FW in this version, find it"""
		self.assertTrue(self.search.alpha_dev_version(alpha_root=os.path.join(ALPHA, '1711plus', 'LCS'), fw_version='8.62')[1] == '0103')
		self.assertTrue(self.search.alpha_dev_version(alpha_root=os.path.join(ALPHA, 'LCOS'), fw_version='8.62')[1] == '0103')

	def test_build_alpha_862(self):
		"""0086-RU5 is another FW in this version, find it if build is specified"""
		self.assertTrue(self.search.alpha_dev_version(alpha_root=os.path.join(ALPHA, '1711plus', 'LCS'), fw_version='8.62', fw_build=86)[1] == '0086')
		self.assertTrue(self.search.alpha_dev_version(alpha_root=os.path.join(ALPHA, 'LCOS'), fw_version='8.62', fw_build=86)[1] == '0086')

	def test_build_alpha_880_maxbuild(self):
		"""in 880, there exists a build 8841, do not find it"""
#		self.assertTrue(self.search.alpha_dev_version(alpha_root=os.path.join(ALPHA, '1711plus', 'LCS'), fw_version='8.62', fw_build=86)[1] == '0086')
		self.assertTrue(int (self.search.alpha_dev_version(alpha_root=os.path.join(ALPHA, 'LCOS'), fw_version='8.80', dev_prefix='LC-1781EF')[1]) == 216 )
#		self.assertTrue(int (self.search.alpha_dev_version(alpha_root=os.path.join(ALPHA, 'LCOS'), fw_version='8.80', 'dev_prefix':'1781EF')[1]) <= 999 )

	def test_build_dir_862(self):
		"""dir_dev_function finds firmwares in the specified directory, this is usually local but for the testcase we use ALPHA as well."""
		self.assertTrue(self.search.dir_dev_version(fw_dir=os.path.join(ALPHA, 'LCOS','FIRMWARE.862','BUIL0103-RU7'), fw_version='8.62', fw_build=103)[1] == '0103')


if __name__=='__main__':
	
	logging.basicConfig(level=logging.CRITICAL)	
	
	DEV_PREFIX = 'LC-1711plus'
	ALPHA = r'\\lcs-file\lcs-en\Alpha\LANCOM' # windows
	#~ ALPHA = r'/home/automaton/Alpha/LANCOM' # linux

	# note: older versions of unittest do not support verbose parameter, in this case just run:
	# unittest.main()
	unittest.main(verbosity=2)
		
		
