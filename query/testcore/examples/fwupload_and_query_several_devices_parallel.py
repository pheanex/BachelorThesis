import sys
sys.path.append('/home/automaton/source')
from testcore.control import ssh
from testcore.control import firmware
import multiprocessing

"""
Beispiel fuer parallelen FW-Upload und Ausfuehren von queries
"""

def worker(device):
	"""
	firmwareupload und/oder query
	"""
	
	session = ssh.SSH(**device)
	
	if 'fw_prefix' in device:
		f = firmware.Search()
		fw_file, fw_build = f.alpha_dev_version(
			alpha_root=device['alpha'], 
			dev_prefix= device['fw_prefix'], 
			fw_version=device['fw_version'])
		
		if fw_file is None:
			print 'no firmware found for {0[fw_prefix]}'.format(device)
			return None
			
		if not session.firmware_upload(fw_file):
			print 'firmware upload failed for {0}'.format(device['host'])
			return None
		else:
			print 'uploaded {0[fw_version]}.{1} to {0[host]}'.format(device, fw_build)
			
	if 'command' in device:
		
		result = session.runquery(device['command'])
		if result is None:
			print 'could not get {0[command]} from {0[host]}'.format(device)
		else:
			print 'got {0[command]} for {0[fw_prefix]} {0[host]}'.format(device)
		return result
		
	else:
		return None

if __name__=='__main__':
	
	alpha = r'\\lcs-file\LCS-EN\Alpha\LANCOM\LCOS'
	# alpha = r'/home/automaton/Alpha/LANCOM/LCOS'
	fw_version = '8.90'
	# definiere die Aufgaben fuer die Geraete.
	# Wenn fw_prefix vorhanden ist, wird die passende Firmware hochgeladen
	# Wenn command vorhanden ist, wird diese Abfrage durchgefuehrt
	devices = [
		{'fw_prefix': 'LC-1781EF', 'host': '192.168.1.101', 'command': 'sysinfo'},
		{'fw_prefix': 'LC-1781A', 'host': '192.168.1.102', 'command': 'sysinfo'},
		{'fw_prefix': 'LC-1781A-3G', 'host': '192.168.1.103', 'command': 'sysinfo'},
		{'fw_prefix': 'LC-1781-4G', 'host': '192.168.1.104', 'command': 'sysinfo'},
		{'fw_prefix': 'LC-1781A-4G', 'host': '192.168.1.105', 'command': 'sysinfo'},
		{'fw_prefix': 'LC-7100plus', 'host': '192.168.1.113', 'command': 'readmib'},
	]
	# setzen von parametern die bei allen gleich sind
	# da pool.map kann nur einen einzigen parameter uebergeben kann
	# werden alpha und fw_version mit in devices eingebaut
	for p in range(len(devices)):
		devices[p]['username']: 'root'
		devices[p]['password']: 'LANCOM'
		devices[p]['alpha'] = alpha
		devices[p]['fw_version'] = fw_version
		
	parallel = 4 # Anzahl gleichzeitiger Prozesse

	# Achtung: die beiden folgenden Anweisungen duerfen nur 
	# in einem Bereich hinter if __name__=='__main__' stehen
	pool = multiprocessing.Pool(processes = parallel)
	results = pool.map(worker, devices)

	# gib Ergebnisse aus
	for result, device in zip(results, devices):
		if result is not None:
			print '{0[command]} for {0[host]}:'.format(device)
			print result
			print
