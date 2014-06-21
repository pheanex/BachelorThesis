import sys
sys.path.append(r'C:\Source')
from testcore.control import ssh
from testcore.control import firmware

devices = [
	{'fw_prefix': 'LC-1681V', 'host': '192.168.1.2', 'username': 'root', 'password': 'LANCOM', 'command': '#readmib#'},
	{'fw_prefix': 'LC-9100', 'host': '192.168.1.3', 'username': 'root', 'password': 'LANCOM', 'command': 'readmib'},
]
alpha = r'\\lcs-file\LCS-EN\Alpha\LANCOM\LCOS'
fw_version = '8.84'

for device in devices:
	
	session = ssh.SSH(**device)
	
	f = firmware.Search()
	fw_file, fw_build = f.alpha_dev_version(
		alpha_root=alpha, 
		dev_prefix= device['fw_prefix'], 
		fw_version=fw_version)
	
	if fw_file is None:
		print 'no firmware found for {0[fw_prefix]}'.format(device)
		continue
		
	if not session.firmware_upload(fw_file):
		print 'firmware upload failed for {0}'.format(device['host'])
		continue
	else:
		print 'uploaded {0}.{1}'.format(fw_version, fw_build)
		
	result = session.runquery(device['command'])
	if result is None:
		print 'could not get {0[command]} from {0[host]}'.format(device)
	else:
		print '{0[command]} for {0[fw_prefix]} {0[host]}'.format(device)
		print result
	
