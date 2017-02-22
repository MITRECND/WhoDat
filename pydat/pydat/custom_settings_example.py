# This file can be used to overide or extend the settings in settings.py
#
# This is an example file. You should copy this to "custom_settings.py" and
# make your changes there.
# Modifying this example file will not change the settings that pyDat uses.
#
# Using this file is better than editing settings.py directly so you
# won't need to merge future updates of settings.py.

# Set this to True if you want to see full debug output in your browser.
DEBUG = False

# If DEBUG is set to False this must be set to the hosts that are allowed
# to access the application
ALLOWED_HOSTS = ['*']

#Default handler is mongo
#Uncomment below line to switch handler to ElasticSearch
#HANDLER = 'es'

#To override the mongo read preference
#Uncomment the following two lines
#from pymongo import ReadPreference
#MONGO_READ_PREFERENCE = ReadPreference.PRIMARY

#Default settings for mongo
#Uncomment to change
#MONGO_HOST = 'localhost'
#MONGO_PORT = 27017
#MONGO_DATABASE = 'whois'
#COLL_WHOIS = 'whois'

#Default settings for elasticsearch
#Uncomment to change
#ES_URI = 'localhost:9200'
#ES_INDEX_PREFIX = 'whois'

# If you need to use a proxy set it here.
#PROXIES = {
#  "http": "http://127.0.0.1",
#  "https": "https://127.0.0.1"
#}

# If you have a DNSDB API key set it here.
#DNSDB_HEADERS = {
#  'X-API-Key': 'DNSDB-API-KEY-HERE',
#  'Accept': 'application/json'
#}

# If you have a passivetotal API key set it here.
#PASSIVETOTAL_KEY = ''

# Verify SSL certificates in external calls.
#SSL_VERIFY = True

#Array of values to use as limits for DNSDB lookups
#DNSDB_PAGE_LIMITS = [10, 20, 50, 100, 200, 500, 1000]
#Index of above array that should be used as default value
#DNSDB_PAGE_LIMIT_DEFAULT = 3
#Maximum Value for requests
#DNSDB_LIMIT = 1000

# Limit all db queries to this many documents.
#LIMIT = 10000

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
