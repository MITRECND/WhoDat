DEBUG = True
SSLVERIFY = True
ELASTICSEARCH = {
    'uri': 'localhost:9200',
    'indexPrefix': 'pydat',
    'user': None,
    'pass': None,
    'cacert': None,
}

PDNSSOURCES = {
    "dnsdb": {
        "APIKEY": '1234'
    }
}

PROXIES = {
    'http': 'http://127.0.0.1',
    'https': 'https://127.0.0.1',
}

SEARCHKEYS = [
    ('domainName', 'Domain'),
    ('registrant_name', 'Registrant Name'),
    ('contactEmail', 'Contact Email'),
    ('registrant_telephone', 'Telephone')
]
