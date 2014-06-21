import sys
import os
import logging
import time
import datetime

import testrun
import tr_csv

logger = logging.getLogger(__name__)


class myTestrun(testrun.Testrun, tr_csv.TestrunCsv):
	"""make our own testclass
	
	our testclass combines the functionality of the base testrun.Testrun with the csv functionality by inheriting from both
	"""
	
	def __init__(self):
		"""call __init__ from the classes whe inherit from
		
		note: only the name of our own testclass has to be specified, not the ones we inherit from
		"""
		super(myTestrun, self).__init__()
		
if __name__=='__main__':
	
	# test whitespace
	filename = 'test_whitespaced.csv'
	with open(filename, 'w') as f:
		f.write(' header A , header B \n     3.14    , quick fox \n')
	
	t = myTestrun()
	options = tr_csv.csvoptions()
	options['stripwhitespace'] = True
	options['columnsmean'] = [0,1]
	columndata, currentheaders, currentcolumns = t._csv_readcsv(filename, options)
	assert(currentheaders==['header A', 'header B'])
	assert(currentcolumns==[0, 1])
	assert(columndata == {0: ['3.14'], 1: ['quick fox']})
	
	os.remove(filename)