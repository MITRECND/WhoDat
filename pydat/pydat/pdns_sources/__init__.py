import glob   #since in python 2.7
import os
import sys


'''
variable name constants
'''

#all normal pdns request methods must be named the following
PDNS_MOD_REQUEST_METHOD = "pdns_request_handler"
#all reverse pdns request methds must be named the following
PDNS_MOD_R_REQUEST_METHOD = "pdns_reverse_request_handler"
#path to pdns source modules
PDNS_MOD_PKG = "pydat.pdns_sources"

'''
create a list of the directory names where any pdns package
specific django templates reside so as to dynamically update
django's global list of template directories. That list is in pydat.settings.py
'''

pdns_pkg_template_dirs =set()
#recursively search pydat.pdns_modules for any templates that reside in modules
for dirpath, dirs, files in os.walk(os.path.dirname(os.path.realpath(__file__)), topdown=True):
	for dir_ in dirs:
		if "templates" in dir_:
			pdns_pkg_template_dirs.add(os.path.join(dirpath, dir_))

'''
create a list of the directory names where any passive DNS package
specific django static reside so as to dynamically update 
django's global list of static file directories. That list is in pydat.settings.py

'''
pdns_pkg_static_dirs = set()
#recursively search pydat.pdns_modules for any templates that reside in modules
for dirpath, dirs, files in os.walk(os.path.dirname(os.path.realpath(__file__)), topdown=True):
	for dir_ in dirs:
		if "static" in dir_:
			pdns_pkg_static_dirs.add(os.path.join(dirpath, dir_))