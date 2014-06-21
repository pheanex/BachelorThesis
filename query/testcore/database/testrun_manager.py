# coding: utf-8

from testcore.database import testrun
import logging
import Tkinter as tk
import tkMessageBox
import ttk
import sys
import traceback

"""
a simple GUI for viewing a testrun by database_schema and run_ID
deleting is also possible, handle with care
"""

def db_handle(schema=''):
	return testrun.PostgresNew(pg_host='lcs-qmdata.lcs.intern', pg_database = 'qstests', pg_user = 'dbwriter', pg_password = 'dbwriter', pg_schema = schema)

def remove(schema, ID):
	"""actual delete on the database"""
	db = db_handle(schema)
	db.remove(ID)
	db.close()		

def query_testrun():
	"""callback for query button"""
	output.delete('1.0', tk.END)
	try:
		db = db_handle(schema.get())
		run = testrun.Testrun()
		id = ID.get()
		if id=='$':
			id=db.get_highest_runID()
		else:
			id=int(id)
		run.read_db(db, run_ID=id)
		db.close()
		#~ for line in str(run).splitlines():
			#~ output.insert('end', line)
		output.insert('end', str(run))	
	except:
		output.delete('0.0', tk.END)
		output.insert(tk.END, 'query failed')
		output.insert(tk.END, '')
		#~ for line in traceback.format_exc().splitlines():
			#~ output.insert('end', line)
		output.insert('end', traceback.format_exc())

def delete_testrun():
	"""callback for delete button. Will update text widget with the data to delete, and then asks for confirmation with a modal box"""
	query_testrun()
	ans = tkMessageBox.askyesno(message='Really remove {} from {}?'.format(ID.get(), schema.get()), icon='question', title='Delete')
	if ans:
		try:
			remove(schema.get(), ID.get())
			output.delete('0.0', tk.END)
			output.insert('end', 'deleted')
		except:
			#~ output.delete(0, tk.END)
			output.insert('end', 'delete failed')
			output.insert('end', '')
			for line in traceback.format_exc().splitlines():
				output.insert('end', line)
				


if __name__=='__main__':
	logging.basicConfig(level=logging.DEBUG)

	root = tk.Tk()
	root.title('Testrun Manager')

	# define GUI elements
	content = ttk.Frame(root, padding=(10,10,10,10))
	schema_label = ttk.Label(content, text="Database Schema")
	schemavar = tk.StringVar()
	schema = ttk.Combobox(content, textvariable=schemavar)
	
	db = db_handle()
	schema['values'] = sorted(db.get_available_schemas()) # get available schemas for combobox
	db.close()

	ID_label = ttk.Label(content, text="ID")
	ID = ttk.Entry(content)
	query = ttk.Button(content, text="Query", command=query_testrun)
	delete = ttk.Button(content, text="Delete", command=delete_testrun)
	quit = ttk.Button(content, text="Quit", command=sys.exit)
	output = tk.Text(content, height=40)

	# place GUI elements
	content.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E, tk.W))
	schema_label.grid(column=0, row=0,sticky=(tk.N, tk.S, tk.E, tk.W))
	schema.grid(column=0, row=1,sticky=(tk.N, tk.S, tk.E, tk.W),pady=2, padx=2)
	ID_label.grid(column=1, row=0,sticky=(tk.N, tk.S, tk.E, tk.W))
	ID.grid(column=1, row=1,sticky=(tk.N, tk.S, tk.E, tk.W),pady=2, padx=2)
	query.grid(column=2, row=1,pady=2, padx=2)
	delete.grid(column=3, row=1,pady=2, padx=2)
	quit.grid(column=4, row=1,pady=2, padx=2)
	output.grid(column=0, row=2, columnspan=5,sticky=(tk.N, tk.S, tk.E, tk.W)) 

	# resize
	root.columnconfigure(0, weight=1)
	root.rowconfigure(0, weight=1)
	content.rowconfigure(2, weight=1)
	content.columnconfigure(0, weight=1)
	content.columnconfigure(1, weight=1)
	
	# start event loop and wait for GUI interactions
	root.mainloop()
