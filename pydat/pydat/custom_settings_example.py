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

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'whois'
MONGO_READ_PREFERENCE = ReadPreference.PRIMARY
COLL_WHOIS = 'whois'

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

# Verify SSL certificates in DNSDB calls.
# SSL_VERIFY = True

#Array of values to use as limits for DNSDB lookups
#DNSDB_PAGE_LIMITS = [10, 20, 50, 100, 200, 500, 1000]
#Index of above array that should be used as default value
#DNSDB_PAGE_LIMIT_DEFAULT = 3
#Maximum Value for requests
#DNSDB_LIMIT = 1000

# Limit all mongo queries to this many documents.
LIMIT = 50000

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
