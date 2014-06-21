import os

def fwsplit(fwname):
	"""
	try to extract fwdev, fwversion, fwbuild from string by identifying two digits encased by dots and working from there
	used for loader name in legacy sqlite data, newer databases only contain already splitted elements
	"""
	fwdev, fwversion, fwbuild = '','',''
	try:
		points = fwname.split('.')
	except:
		return fwdev, fwversion, fwbuild		
	# search .dd. element (second half of version)
	valid = False
	for pos,el in enumerate(points):
		if len(el)==2 and pos>0:
			try:
				num=int(el)
				valid = True
				break
			except:
				pass
				
	if valid:
		# fwversion, and fwdev ix existing
		start = points[pos-1].split('-')
		if len(start)>=2:
			# at least one - before .dd. part
			fwversion = start[-1]
			fwdev = '-'.join(start[:-1])
		else:
			fwversion = start[0]
		fwversion += '.'+points[pos]
		
		# fwbuild
		try:
			fwbuild = points[pos+1][0:4]
			fwbuild = '{0:04d}'.format(int(fwbuild))
		except:
			fwbuild = ''
	return fwdev, fwversion, fwbuild	


def parsefirmsafe(text='', file=None):
	"""
	parse firmsafe, either from text or from file
	
	returns a dict. status (active, inactive, <loader> is the key, the value is tuple of (version, build)
	"""

	if file is not None and os.path.exists(file):
		with open(file,'r') as f:
			text = f.read()

	firmsafe = {}
	for line in text.splitlines():
		linelist=line.split()
		if len(linelist)==6:
			pos,type,version,date, size, index = linelist
			try:
				pos = int(pos)
			except:
				continue
			firmsafe[type] = fwsplit(version)[1:]
			
	return firmsafe
	


def parsesysinfo(text='', file=None):
	"""
	parse sysinfo, either text or from file
	
	returns a dict. the first path of each line is the key. All second parts of each line a build into lists, since the keys can occur multiple lines
	"""
	
	if file is not None and os.path.exists(file):
			with open(file,'r') as f:
				text = f.read()
		
	
	sysinfo = {}
	for line in text.splitlines():
		linelist=line.split(None,1)
		if len(linelist)>1:
			key=linelist[0].strip(':')
			value=linelist[1].strip()
			if not sysinfo.has_key(key):
				sysinfo[key] = list()
			sysinfo[key].append(value)
	return sysinfo	
	
def parse_table(text=''):
	"""
	dissect the output of a table into a list of the headers and a list of the rows. 
	rows are splitted based on the header positions to preserve elements with spaces in them.
	
	returns two empty lists if problems occur
	"""
	table_rows = []
	table_header = []
	text_lines = [line for line in text.splitlines() if len(line.strip())] # strip empty lines so line index works
	if len(text_lines) and text_lines[1]=='-'*len(text_lines[1]):
		instring = False
		position = 0
		positions = list()
		table_header = text_lines[0].split()
		for c in text_lines[0]:
			if not c.isspace():
				if not instring:
					positions.append(position)
					instring = True
			else:
				if instring:
					instring = False
			position += 1
		for line in text_lines[2:]:
			line_list = list()
			last = 0
			for position in positions[1:]:
				line_list.append(line[last:position].strip())
				last = position
			line_list.append(line[last:].strip())
			table_rows.append(line_list)
		return (table_header, table_rows)
	else:
		return ([], [])
	
def parse_table_dict(text=''):
	"""
	dissect the output of a table into a list of one dict per table row. the dict keys get extracted from the table header.
	rows are splitted based on the header positions to preserve elements with spaces in them.
	
	returns empty list if problems occur
	"""
	
	table_header, table_rows = parse_table(text)
	table_dicts = []
	for row in table_rows:
		table_dicts.append(dict([(key, value) for key,value in zip(table_header, row)]))
	return table_dicts
	
def parse_table_vectors(text=''):
	"""
	dissect the output into a dict of one vector per header.
	returns {} if problems occur
	"""
	table_header, table_rows = parse_table(text)
	table_dict = {}
	for key in table_header:
		table_dict[key] = [row[table_header.index(key)] for row in table_rows]
	return table_dict
		
	
	
		

if __name__=='__main__':
		
	for key,value in parsesysinfo(file='LC1-sysinfo.txt').items():
		print key, value
		
	print
	
	for key,value in parsefirmsafe(file='LC1-firmsafe.txt').items():
		print key, value
		
	print
	
	
	table_data = '''

Network-name      Start-Address-Pool  End-Address-Pool    Netmask             Broadcast-Address   Gateway-Address     DNS-Default      DNS-Backup       NBNS-Default     NBNS-Backup      Operating  Broadcast-Bit  Master-Server    2nd-Master-Server   3rd-Master-Server   4th-Master-Server   Cache   Adaption   Cluster
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
INTR ANET         172.16.100.128      172.16.100.132      255.255.255.0       0.0.0.0             0.0.0.0             0.0.0.0          0.0.0.0          0.0.0.0          0.0.0.0          Yes        No             0.0.0.0          0.0.0.0             0.0.0.0             0.0.0.0             No      No         No
DMZ               0.0.0.0             0.0.0.0             0.0.0.0             0.0.0.0             0.0.0.0             0.0.0.0          0.0.0.0          0.0.0.0          0.0.0.0          No         No             0.0.0.0          0.0.0.0             0.0.0.0             0.0.0.0             No      No         No

	
	'''	
	table_data_err = '''

Network-name      Start-Address-Pool  End-Address-Pool    Netmask             Broadcast-Address   Gateway-Address     DNS-Default      DNS-Backup       NBNS-Default     NBNS-Backup      Operating  Broadcast-Bit  Master-Server    2nd-Master-Server   3rd-Master-Server   4th-Master-Server   Cache   Adaption   Cluster
INTR ANET         172.16.100.128      172.16.100.132      255.255.255.0       0.0.0.0             0.0.0.0             0.0.0.0          0.0.0.0          0.0.0.0          0.0.0.0          Yes        No             0.0.0.0          0.0.0.0             0.0.0.0             0.0.0.0             No      No         No
DMZ               0.0.0.0             0.0.0.0             0.0.0.0             0.0.0.0             0.0.0.0             0.0.0.0          0.0.0.0          0.0.0.0          0.0.0.0          No         No             0.0.0.0          0.0.0.0             0.0.0.0             0.0.0.0             No      No         No

	
	'''	

	assert(parse_table(table_data_err)==([],[]))
	header, rows = parse_table(table_data)
	print header 
	for row in rows:
		print row
		
	assert(parse_table_dict(table_data_err)==[])
	tds = parse_table_dict(table_data)
	for td in tds:
		for key in sorted(td):
			print key, repr(td[key])
		print
	assert(tds[0]['Network-name']=='INTR ANET')
	
	assert(parse_table_vectors(table_data_err)=={})
	tdv = parse_table_vectors(table_data)
	for key in sorted(tdv):
		print key, tdv[key]
	assert(tdv['Network-name']==['INTR ANET', 'DMZ'])
	
	
	
		
	
