import telnet
import tftpwrap
import firmware
import logging
logger = logging.getLogger(__name__)

class myTelnet(telnet.Telnet, tftpwrap.TelnetTFTPwrap):
	
	def __init__(self, *args, **kwargs):
		
		super(myTelnet, self).__init__(*args, **kwargs) # init next class in MRO
		
		
if __name__=='__main__':

	logging.basicConfig(level=logging.DEBUG)	
	
	s = firmware.Search()
	s.dev_prefix = 'LC-9100'
	fw, build = s.alpha_dev_version(alpha_root=r'\\lcs-file\lcs-en\Alpha\LANCOM\9100\LCS', fw_version='8.84')

	t = myTelnet(host='192.168.80.214')
	t.TFTPserver = '192.168.80.2'
	t.TFTPdir = r'C:\TFTP'
	t.TFTPprefix = 'unittest-'
	assert(fw is not None)
	assert(t.run_loadfirmware(fw))
