from pydat.pdns_sources import passiveHandlers
import handlers as _handlers_
from dnsdb import config, fields

handlers = passiveHandlers(_handlers_.pdns_request_handler,
                           _handlers_.pdns_reverse_request_handler)
