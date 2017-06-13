# This file can be used to overide or extend the settings in settings.py
#
# This is an example file. You should copy this to "custom_settings.py" and
# make your changes there.
# Modifying this example file will not change the settings that pyDat uses.
#
# Using this file is better than editing settings.py directly so you
# won't need to merge future updates of settings.py.

# Set this to True if you want to see full debug output in your browser.
#DEBUG = False

# If DEBUG is set to False this must be set to the hosts that are allowed
# to access the application
#ALLOWED_HOSTS = ['*']

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


#Fill in with pdns sources within the custom_settings.py. 
#PDNS_SOURCES ={}


'''
Requirements for PDNS_SOURCES dictionary:
    -pdns_sources keys must be the same name of corresponding pdns
     package name for that pdns source. For example, the
     dnsdb source is a package called "dnsdb" and within it there
     is "dnsdb.py" module
    -pdns entries must have key/value pairs for the following keys:
       -active               (pdns module/source is active or not)
       -type                 (a tag to use as a label for pdns results sets.
                             This value will be attached to any pdns results
                             right before they are sent to a template rendering)
       -table_template       (the name of the table template for the pdns source
                             to use in rendering pdns data)

    -any additional key/value pairs may be added for specific variables used
     for that particular module

example:

PDNS_SOURCES ={
    "dnsdb":{
        "active": True,
        "type":"DNSDB",
        "table_template": "dnsdb.html",
        "dnsdb_headers":{}, 
        "ssl_verify":True        
    },
    "passivetotal":{
        "active": False,
        "type":"PassiveTotal",
        "table_template":"passivetotal.html",
        "passivetotal_key": None,
    }
}
'''

# If you need to use a proxy set it here.
#PROXIES = {
#  "http": "http://127.0.0.1",
#  "https": "https://127.0.0.1"
#}

# Verify SSL certificates in external calls
#SSL_VERIFY = True

# Limit all db queries to this many documents.
#LIMIT = 10000

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
