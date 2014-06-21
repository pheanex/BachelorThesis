import csv
import getopt
import sys
import os
import glob
import logging

logger = logging.getLogger(__name__)

class parselog:
	
	def __init__(self):
		#default
		self.logfile = ''
		self.csvfile = None
		self.doload = False
		self.doloadstrip = False
		self.dogeneric = False
		self.generickeys = [
			['Operating-Time  INFO:',(None,None),['Operating-Time']],
			['Tunnel  INFO:',(None,None),['VPN-Tunnel','PPTP-Tunnel']],
			['CPU load   1s:',(None,None),['CPU load 1s']],
			['  1s:',(None,None),['CPU load 1s']],
		] # user definable: serachstrings and the keys the found values should be assigned to. multiple occurences in the list 
		self.genericpos = {}
		self.genericdict = {}
		self.genericblock = {}
		self.genericdelim = 'Sec.-REPEAT]'


	def _parseload(self, line):
		'''
		parse two types of blocks for the 1s value
		
				CPU Load   Schedules/Sec   Epochs/Sec
		  1s:    0.40%             512       0.0000
		  5s:    0.44%             512       0.0000
		 60s:    0.50%             517       0.0110
		300s:    0.74%             541       0.0068

		CPU load   1s:   0.66%
		CPU load   5s:   0.98%
		CPU load  60s:   1.46%
		CPU load 300s:   1.41%
		'''
		#~ print line

		if line.startswith('CPU load   1s:') and self.recordload:
			# read old block
			value = line[line.find(':')+1 : line.find('%')]
			#~ print value
			try:
				self.loadblock.append((float(value), None))
			except (ValueError):
				pass
				
		elif line.startswith('CPU-Load-1s-Percent') and self.recordload:
			# read old block
			value = line[line.find(':')+1 : line.find('%')]
			#~ print value
			try:
				self.loadblock.append((float(value), None))
			except (ValueError):
				pass
				
		elif line.startswith('  1s:') and self.recordload:
			# read new block
			value = line[line.find(':')+1 : line.find('%')]
			shed = line[line.find('%')+1:].split()[0]
			#~ print value,shed
			try:
				self.loadblock.append((float(value), float(shed)))
			except (ValueError):
				pass
				
		elif line.startswith('Outband-115200 Bit/s OK'):
			self.load.append(self.loadblock)
			self.loadblock=[]
			self.recordload = True
			#~ print "cleared load and started recording again"
			
		elif line.startswith('Starting script'):
			self.recordload = False
		elif line.startswith('A new firmware is being uploaded'):
			self.recordload = False
			#~ print "stopped recording"
			#~ for el in self.load: print el
			
		return
		
		
	def _initgeneric(self):
		'''
		self.generickeys = [
			['Operating-Time  INFO:',['Operating-Time']],
			['Tunnel  INFO:',['VPN-Tunnel','PPTP-Tunnel']],
			['CPU load   1s:',['CPU load 1s']],
			['  1s:',['CPU load 1s']],
		]
		'''
		for tag, positions, keys in self.generickeys:
			for key in keys:
				self.genericdict[key] = list()
		self._initgenericblock()

	def _initgenericblock(self):
		self.genericpos = {}
		self.genericpostemp = {}
		for tag, positions, keys in self.generickeys:
			for key in keys:
				self.genericblock[key] = None
			self.genericpos[tag] = 0
			self.genericpostemp[tag] = 0
			
		
	def _parsegeneric(self, line):
		'''
		generic parser which matches user definable searchstrings at assigns to values found to keys in the resulting dictionaries.
		multiple occurences per block are possible.
		each bluck results in one row in the csv
		self.generickeys: searchstring/keys definition
		self.generickdelim: block delimiter
		
		Example Block:
		Operating-Time  INFO:    1D 9:09:07

		Tunnel  INFO:    99

		Tunnel  INFO:    594

		CPU load   1s:  95.46%
		CPU load   5s:  88.87%
		CPU load  60s:  27.69%
		CPU load 300s:  26.41%

		[1 Sec.-REPEAT];[Test]root@AI-local2:/
		'''
		#~ print line
		
		if self.genericdelim in line:
			
			#~ print 'found delim', self.genericblock
			for key, value in self.genericblock.iteritems():
				
				self.genericdict[key].append(value)
			self._initgenericblock()
		
		else:

			for tag, positions, keys in self.generickeys:
				gp = self.genericpos[tag]
				# print tag, gp
				if gp<len(keys):
					key = keys[self.genericpos[tag]]
					#~ print gp, self.genericpos, key
					if line.startswith(tag):
						posstart, posend = positions
						if posstart==None:
							posstart=len(tag)
						if posend==None:
							posend=len(line)
						value = line[posstart:posend].strip()
						# print 'found', tag, '->', key,'=', value
						self.genericblock[key] = value
						self.genericpostemp[tag] += 1
			for tag, positions, keys in self.generickeys:
				if self.genericpostemp[tag]>=1:
					self.genericpos[tag] += 1
				#~ else:
					#~ print gp, self.genericpos, 'tag', tag,'out of range'
		return
		
		
	def _stripload(self, loadinput):
		strippedload = []
		state = 0
		zerocount = 5
		count = 5
		target = 10
		minlength = 10
		length = 0
		debug = False
		if debug: logger.debug('start load eval')
		for load,shed in loadinput:
			if debug: print load, state,
			if (load>target) and state==0:
				if debug: logger.debug('before zerocounting')
			elif (load<target) and state==0:
				if debug: logger.debug('start zerocounting')
				state = 1
				count = zerocount
			elif (load<target) and state==1  and (count>0):
				if debug: logger.debug('zerocounting, count at {}'.format(count))
				count += -1
			elif (load>target) and state==1  and (count>0):
				if debug: logger.debug('aborted zerocounting')
				state = 0
			elif (load<target) and state==1  and (count==0):
				if debug: logger.debug('finished zerocounting, wait for target')
				state = 2
			elif (load<target) and state==2:
				if debug: logger.debug('wait for target')
			elif (load>target) and (state==2 or state==3):
				if debug: logger.debug('target reached, copying')
				strippedload.append((load,shed))
				state = 3
				length +=1
			elif (load<target) and state==3:
				if length<minlength:
					if debug: logger.debug('discared, too few values')
					state = 2
					length = 0
					strippedload = []
				else:
					if debug: logger.debug('not copying')
					state = 4
			elif state==4:
				if debug: logger.debug('ignore')
			else:
				if debug: logger.debug('?')
		return strippedload
				

	def parse(self):
		self.load = []
		self.loadblock = []
		self.recordload = True

		logfiles = glob.glob(self.logfile)
		if len(logfiles)>0:
			
			if self.dogeneric:
				self._initgeneric()
			
			logger.debug('open {}'.format(logfiles[0]))
			with open(logfiles[0],'r') as Fin:

				for line in Fin:
					# iterate through lines of the logfile and let the different parsers run on a line
					if self.doload:
						self._parseload(line)
					if self.dogeneric:
						self._parsegeneric(line)

			if self.doload:
				self.load.append(self.loadblock)

			newload = []
			if self.doloadstrip:
				for loadblock in self.load:
					stripped = self._stripload(loadblock)
					if stripped != []:
						newload = stripped
			else:
				for loadblock in self.load:
					newload.extend(loadblock)
			self.load = newload
				
			if self.csvfile is not None:
				with open(self.csvfile, 'wb') as f:
					w = csv.writer(f, delimiter=',')
					if self.doload:
						w.writerow(['Load','Shedules/s'])
						w.writerows(self.load)
					if self.dogeneric:
						allkeys = []
						for tag, positions, keys in self.generickeys:
							allkeys.extend(keys)
						uniquekeys = []
						for key in allkeys:
							if key not in uniquekeys:
								uniquekeys.append(key)
						w.writerow(uniquekeys)
						for i, egal in enumerate(self.genericdict[uniquekeys[0]]):
							w.writerow([self.genericdict[key][i] for key in uniquekeys])
							
					logger.info('wrote {}'.format(self.csvfile))
			else:	
				if self.doload:
					for el in p.load: 
						logger.info(el)
				if self.dogeneric:
					logger.info(el)
							
		else:
			logger.warning('{} not found'.format(self.logfile))
			return False
		return True


def parse_loadlog_to_csv(logfile, csvfile):
	"""parse a standard logfile with rep #load# ouput into a csv
	the logfile can originate from a serial capture, only the the load after ther last boot will be examined
	"""
	p = parselog()
	p.logfile = logfile
	p.csvfile = csvfile
	p.doload = True
	p.doloadstrip = True
	p.dogeneric = False
	return p.parse()


if __name__=="__main__":
	logging.basicConfig(level=logging.DEBUG)
	p = parselog()
	p.logfile = r'C:\BT\IXIA-12\1781EW-WAN-IPSECv4-HTTP-TPT\WAN-IPSECv4-0001T\IxL630-IPSECv4-GE-rt-001U-010S-GET!LC-1781EW-8.84.0036!FIRMWARE.884~BUIL0036~LC-1781EW-8.84.0036!20130909-144704\LC1-COMlog.log'
	p.doload = True
	p.doloadstrip = True
	p.dogeneric = True
	p.parse()
