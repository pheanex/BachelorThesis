import sys, os
import csv
import datetime
from testcore.parseoutput import lcos

def parsepath(testpath=''):
	"""Split a path made by batchtester into components"""

	pathlist=list()
	restpath=testpath
	run = {}
	while len(restpath)>0 and len(pathlist)<3:
		head, tail = os.path.split(restpath)
		if tail=='':
			if head!='':
				pathlist.append(head)
				break
		else:
			pathlist.append(tail)
			restpath=head
	
	if len(pathlist)>=3:
		rundir, run_testcfg, run_testgroup =pathlist
		run['run_testcfg']= run_testcfg
		run['run_testgroup']= run_testgroup
		runlist=rundir.split('!')
		if len(runlist)==4:
			run['run_testfunc'] = runlist[0]
			run['run_timestamp'] = datetime.datetime.strptime(runlist[3], '%Y%m%d-%H%M%S')
			run['run_testroot'] = head
			return run

	return run
	
def parseshortpath(testpath=''):
	"""Split a path made by batchtester into components"""

	pathlist=list()
	restpath=testpath
	run = {}
	while len(restpath)>0 and len(pathlist)<2:
		head, tail = os.path.split(restpath)
		print head, tail
		if tail=='':
			if head!='':
				pathlist.append(head)
				break
		else:
			pathlist.append(tail)
			restpath=head
	
	if len(pathlist)>=2:
		rundir, run_testgroup =pathlist
		run['run_testgroup']=run_testgroup
		runlist=rundir.split('!')
		if len(runlist)==4:
			run['run_testfunc'] = runlist[0]
			run['run_timestamp'] = datetime.datetime.strptime(runlist[3], '%Y%m%d-%H%M%S')
			run['run_testroot'] = head
			return run

	return run
	
	
def parsefwlist(text='', file=None):
	"""return fwname components for each device in fwlist.csv"""
	
	if file is not None:
		csvdata = csv.reader(open(file,'rb'))
	else:
		csvdata = csv.reader(text.splitlines())
	
	devices = {}
		
	for i,row in enumerate(csvdata):
		if len(row)==3:
			LCnum, fwname, fwpath = row
			try:
				LCnum = int(row[0])
			except: 
				continue
			dev_fwname, dev_fwversion, dev_fwbuild = lcos.fwsplit(fwname)
			devices[LCnum] = {'dev_fwname':dev_fwname, 'dev_fwversion':dev_fwversion, 'dev_fwbuild':dev_fwbuild}
			
	return devices


if __name__=='__main__':

	# print parsepath(r'C:\BT\IXIA-12\9100plus-WAN-IPv4-UDP-TPT\WAN-IPv4\IxA740-IPv4-GE-rt-2to1-1518-1p!LC-9100plus-8.90.0020!FIRMWARE.890~BUIL0020~LC-9100plus-8.90.0020!20130817-015737')
	print parseshortpath(r'C:\BT\CDRouter\1781EFplus-_firmware\Py27-910.py!!!20140331-190524')
	
		
	# for key,value in parsefwlist(file='fwlist.csv').items():
		# print key, value
		
	# print
		
	