DEBUG = True
SSL_VERIFY = True
ELASTICSEARCH = {
    'uri': 'localhost:9200',
    'index_prefix': 'pydat',
    'user': None,
    'pass': None,
    'cacert': None,
}

PDNS_SOURCES = {

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
