import sys
import os
import csv
import logging
import math


#~ sys.path.append('/home/automaton/source')
#~ from testcore.database import testrun

logger = logging.getLogger(__name__)


def csvoptions():
	"""options what part of the csvfile shall be evauluated, and how.
	
	define where to look in the csv-file for data with 'blocknum', 'headerline', 'dataline' and 'datalength'.
	the default values work for the common file with headers in the first line and data beginning in the second line
		blocknum: if file consists of several table blocks seperated by empty line, the block can be selected. first block is 1
		headerline: use if the headers are not in the first line (0) of table
		dataline:  use if the data starts not in the second line(1) of table
		datalelength : use if only part of data should be used
	
	fot method csv_add_fulltable, 'headers' and 'columns' can be used used to reduce the columns which will be stored
		headers: optional list to select the column names from the csv-file
		columns: optional list to select the column numbers (starting at 0) from the csv-file
		
	for method  csv_add_extract, the following keys define which calculations should be done on the given data column (givens as number or headername) 	
		...mean: the mean of the data vector will be stored
		...meand: the mean and stddev of the data vector will be stored
		...steady, ...steadyd: like the above, bouth oly the inner part of the vector (from 10 to 90 percent of its length) will be used 
		...versus': list of (x,y) tuples which to set into relation, e.g: ('throughput','framesize') on
				framesize,throuput
				128,101.5
				1518,986.1
			results "throughput vs. framesize: 101.5 @128, 986.1 @1518."

	"""
	
	return {
		'headers': None,
		'columns':None,
		'blocknum': 1,
		'headerline': 0,
		'dataline': 1,
		'datalength': None,
		'stripwhitespace': False,
		'columnsmean': [],
		'columnsmeand': [],
		'columnssteady': [],
		'columnssteadyd': [],
		'columnsmedian': [],
		'columnsversus':[],
		'headersmean': [],
		'headersmeand': [],
		'headerssteady': [],
		'headerssteadyd': [],
		'headersmedian': [],
		'headersversus':[],
	}
	
	
	

	
class TestrunCsv(object):
	
	def __init__(self):
		super(TestrunCsv, self).__init__() # init next class in MRO


	def _csv_readcsv(self, filename, options):
		"""
		helper function to read csvfile according to options into columndata dictionary
		
		if option stripwhitespace is True, headers and data will be stripped of leading/trailing whitespace before further processing 
		"""
		Fcsvfile = open(filename, 'rb')
		csvdata = csv.reader(Fcsvfile)

		# iterate through the whole csv object
		if options['blocknum']==0:
			options['blocknum=1'] # use first block
		blockn=0
		isblock=0
		blockstart=0
		lastisempty=1
		hasheader=False
		header = []
		

		# prepare data storage in a dictionary containing lists
		columndata = dict()
		currentheaders = []
		currentcolumns = []		
		
		# iterate through file and find the correct data block
		for i, row in enumerate(csvdata):

			if len(row)==0:
				lastisempty=1
				isblock=0
			if len(row)!=0 and lastisempty==1:
				# empty line separates blocks
				lastisempty=0
				blockn+=1
				blockstart=i
				#~ print 'newblock:',blockn, 'at', blockstart
				if blockn==options['blocknum']:
					isblock=1
					# print 'block found', blockstart
				else:
					isblock=0
				# continue
			
			# handle our block
			if isblock==1:
				#~ print 'block i=',i, row				
				# handle header
				if i-blockstart == options['headerline']:
					if options['headerline']!=options['dataline']:
						# print 'header: ',i, blockstart, headerline
						if options['stripwhitespace']:
							csvheaders = [el.strip() for el in row]
						else:
							csvheaders = row
						hasheader = True
						# print all possible headers
						for j, element in enumerate(csvheaders):
							logger.debug('csv header {0:4d} {1}'.format(j, csvheaders[j]))
						if options['headers'] is not None and len(options['headers']):
							for header in options['headers']:
								if header in csvheaders:
									column = csvheaders.index(header)
									columndata[column] = []
									currentheaders.append(header)
									currentcolumns.append(column)
								else:
									logger.warning('header {0}  is not in csv headers {1}'.format(header, ','.join(csvheaders)))
						elif options['columns'] is not None and len(options['columns']):
							for column in options['columns']:
								if len(csvheaders)>=column:
									columndata[column] = []
									currentheaders.append(csvheaders[column])
									currentcolumns.append(column)
								else:
									logger.warning('no {0} column in csv headers {1}'.format(column, ','.join(csvheaders)))
						else:
							for column, header in enumerate(csvheaders):
								columndata[column] = []
								currentheaders.append(header)
								currentcolumns.append(column)
						logger.debug('current headers are  {0}'.format(','.join(currentheaders)))
						
					else:
						logger.info('no explicit headerline, using defaults')
						if options['headers'] is not None:
							currentheaders = headers[:len(row)]
							currentcolumns = range(len(currentheaders))
						elif options['columns'] is not None:
							correntcolumns = columns[:len(row)]
							currentheaders = [str(h) for h in currentcolumns]
						else:
							currentcolumns = range(len(row))
							currentheaders = [str(h) for h in currentcolumns]
						logger.info('no explicit headerline, using headers {0} and columns {1}'.format(','.join(currentheaders), ','.join(map(str, currentcolumns))))							
						for column, header in enumerate(currentheaders):
							columndata[column] = []
							
						
				# handle data
				if i-blockstart >= options['dataline'] and (options['datalength'] is None or  i-blockstart <= options['datalength']+options['dataline']):
					#~ print 'data at',i
					for element in currentcolumns:
						if len(row)>element:
							if options['stripwhitespace']:
								columndata[element].append(row[element].strip())
							else:
								columndata[element].append(row[element])
				

		# close file
		Fcsvfile.close()
		return columndata, currentheaders, currentcolumns
		
		
		
	def csv_add_fulltable(self, filename, resdict, options=None):
		"""add a complete csv table to a Testrun
		
		filename: filename of csv-file
		resdict: res_item is mandatory, res_source can be specified but otherwise will be derived from the csv-file. All other are a result of the csvfile
		"""
		if options is None:
			options = csvoptions()
		columndata, currentheaders, currentcolumns = self._csv_readcsv(filename, options)
		#~ print columndata, currentheaders, currentcolumns
		if not resdict.has_key('res_source') or resdict['res_source']=='':
			resdict['res_source'] = os.path.basename(filename)
		self.add_resulttable({'headers': currentheaders, 'data': [columndata[c] for c in currentcolumns]}, resdict)
		
		
		
	def csv_add_extract(self, filename, resdict={}, options=None):
		"""extract data: mean, stddev, median etc of the column vectors. can also set two vectors in relation with 'versus'
		
		what to extract is given in the options, see def csvoptions at beginning of module
		
		from resdict only res_source will be used if it exists, all other res_ parameters are a direct result of the options and the data in the csvfile.
		
		the function returns a list of strings with a textual version of the extracted data (this can be used for batchtester spawn_result.txt) or None (if nothing was extracted)
		"""
		
		# prepare columns/headers to extract
		if options is None:
			localoptions = csvoptions()
		else:
			# localoptions = dict(**options) # copy
			localoptions = csvoptions()
			localoptions.update(options)

		if not resdict.has_key('res_source') or resdict['res_source']=='':
			res_source = os.path.basename(filename)
		else:
			res_source = resdict['res_source']
			
		# unique columns which shall be extracted
		columns2calc = list(set(localoptions['columnsmean']) | set(localoptions['columnsmeand']) | set(localoptions['columnssteady']) | set(localoptions['columnssteadyd']) | set(localoptions['columnsmedian']))
		columnstotal = list(set(columns2calc) | set([el[0] for el in localoptions['columnsversus']]) | set([el[1] for el in localoptions['columnsversus']]))
		#~ columns2calc.sort()
		#~ columnstotal.sort()
		
		# unique headers which shall be extracted
		headers2calc = list(set(localoptions['headersmean']) | set(localoptions['headersmeand']) | set(localoptions['headerssteady']) | set(localoptions['headerssteadyd']) | set(localoptions['headersmedian']))
		headerstotal = list(set(headers2calc) | set([el[0] for el in localoptions['headersversus']]) | set([el[1] for el in localoptions['headersversus']]))
		#~ headers2calc.sort()
		#~ headerstotal.sort()
		localoptions['headers'] = headerstotal
		localoptions['columns'] = columnstotal

		logger.debug('columns2calc {0}'.format(columns2calc))
		logger.debug('columnstotal {0}'.format(columnstotal))
		logger.debug('headers2calc {0}'.format(headers2calc))
		logger.debug('headerstotal {0}'.format(headerstotal))
		

		# read csvfile into columndata
		columndata, currentheaders, currentcolumns = self._csv_readcsv(filename, localoptions)		
		
		#~ print 'columndata', columndata
		logger.debug('currentheaders {0}'.format(currentheaders))
		logger.debug('currentcolumns {0}'.format(currentcolumns))
		
		
		if len(currentcolumns)==0: 
			return None
			
		output = []

		# process data
		
		# extracts of two vectors (versus)
		
		def iterversus():
			outputlinerow = []
			for i, row in enumerate(xdata):
				outputlinerow.append(ydata[i]+' @'+str(row))
				try:
					res_value = float(ydata[i])
				except:
					res_value = None
					pass
				res_text = str(ydata[i])
				resdict = {'res_item': yheader+' vs. '+xheader, 'res_format': str(row), 'res_source':res_source, 'res_value': res_value, 'res_text': res_text}
				self.add_result(resdict, force=True) # if x and y are not unique, force insert
			
			output.append(yheader + ' vs. ' + xheader + ': '+', '.join(outputlinerow) + '.')


		for yheader, xheader in localoptions['headersversus']:
			if xheader in currentheaders and yheader in currentheaders:
				xdata=columndata[currentcolumns[currentheaders.index(xheader)]]
				ydata=columndata[currentcolumns[currentheaders.index(yheader)]]
				iterversus()
				
		for ycolumn, xcolumn in localoptions['columnsversus']:
			if xcolumn in currentcolumns and ycolumn in currentcolumns:
				xheader = currentheaders[currentcolumns.index(xcolumn)]
				yheader = currentheaders[currentcolumns.index(ycolumn)]
				xdata=columndata[xcolumn]
				ydata=columndata[ycolumn]				
				iterversus()
				

		# extracts of one vector (mean, median, etc.)

		def meanStdDev (v):
			"""helper to calculate mean and standard deviation"""
			if len(v)>0:
				sumsq = sum(x*x for x in v)
				mean = sum(v)/len(v)
				stdDev = math.sqrt(sumsq/len(v) - mean*mean)
				return (mean, stdDev)
			else:
				return ("NaN","NaN")		
			
			
		def calccolumn(column, header):
			"""helper to perform calculation on a single column"""
			vec_valid = True
			try:
				vec = map(float, columndata[column])
			except ValueError:
				vec_valid = False
				logger.warning('{0} not floatable'.format(columndata[column]))
				return
			
			outputparts = []

			vec_len = len(vec)

			if vec_len==1:
				outputparts.append(str(vec[0])) # just the value
				resdict = {'res_item': header, 'res_format': 'value', 'res_source':res_source, 'res_value': vec[0], 'res_text': ''}
				self.add_result(resdict)

			if vec_len>1:
				outputparts.append(str(vec_len)+ ' el')# number of elements
				
				# do the math
				if column in localoptions['columnsmean'] or header in localoptions['headersmean']:
					mean, stddev = meanStdDev(vec)
					outputparts.append('mean={0}'.format(mean,stddev))
					self.add_result({'res_item': header, 'res_format': 'mean', 'res_source':res_source, 'res_value': mean, 'res_text': ''})

				if column in localoptions['columnsmeand'] or header in localoptions['headersmeand']:					
					mean, stddev = meanStdDev(vec)
					outputparts.append('mean={0} stddev={1:.2f}'.format(mean,stddev))
					self.add_result({'res_item': header, 'res_format': 'mean', 'res_source':res_source, 'res_value': mean, 'res_text': ''})
					self.add_result({'res_item': header, 'res_format': 'stddev', 'res_source':res_source, 'res_value': stddev, 'res_text': ''})

				if column in localoptions['columnssteady'] or header in localoptions['headerssteady']:
					mean, stddev = meanStdDev(vec[10*(vec_len-1)//100 +1 : 90*(vec_len-1)//100 +1])
					outputparts.append('steady-state-mean={0}'.format(mean,stddev))
					self.add_result({'res_item': header, 'res_format': 'meansteady', 'res_source':res_source, 'res_value': mean, 'res_text': ''})
					
				if column in localoptions['columnssteadyd'] or header in localoptions['headerssteadyd']:
					mean, stddev = meanStdDev(vec[10*(vec_len-1)//100 +1 : 90*(vec_len-1)//100 +1])
					outputparts.append('steady-state-mean={0} stddev={1:.2f}'.format(mean,stddev))
					self.add_result({'res_item': header, 'res_format': 'meansteady', 'res_source':res_source, 'res_value': mean, 'res_text': ''})					
					self.add_result({'res_item': header, 'res_format': 'stddevsteady', 'res_source':res_source, 'res_value': stddev, 'res_text': ''})					

				if column in localoptions['columnsmedian'] or header in localoptions['headersmedian']:
					mediansort=vec
					mediansort.sort()
					outputline = 'medians'
					for slice in [0,10,25,50,75,90,100]:
						pos = slice*(vec_len-1)//100 #integer division
						outputline +=  ' ' + str(slice) + '%=' + str(mediansort[pos])
						self.add_result({'res_item': header, 'res_format': 'median'+str(slice), 'res_source':res_source, 'res_value': mediansort[pos], 'res_text': ''})
					outputparts.append(outputline)
					
			output.append(header+': '+ ', '.join(outputparts) + '.')
						
			
		for header in headers2calc:
			if header in currentheaders:
				calccolumn(currentcolumns[currentheaders.index(header)], header)
				
			
		for column in columns2calc:
			if column in currentcolumns:
				calccolumn(column, currentheaders[currentcolumns.index(column)])
			

		return output
	
