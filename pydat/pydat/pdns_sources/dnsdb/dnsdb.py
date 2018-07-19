from pydat.pdns_sources import pdnsConfig, formFields

config = pdnsConfig("dnsdb", "DNSDB")
config.addConfig('apikey', True, None,
                 description="The DNSDB API Key to use")
config.addConfig('ssl_verify', False, True,
                 description="Verify SSL connection to API")


fields = formFields("dnsdb")
fields.addBaseField("limit", "ChoiceNumberField", 500,
                    parameters={"label": "Limit",
                                "required": False,
                                "choices": [(10, 10),
                                            (20, 20),
                                            (50, 50),
                                            (100, 100),
                                            (200, 200),
                                            (500, 500),
                                            (1000, 1000)],
                                "initial": 500})

fields.addBaseField("absolute", "BooleanField", False,
                    parameters={"label": "Absolute",
                                "initial": False,
                                "required": False,
                                "help_text":
                                "Excludes subdomains when checked"})

fields.addBaseField("filter", "ChoiceField", "rrname",
                    parameters={"label": "Filter",
                                "required": False,
                                "help_text":
                                "only required if \'Format\' is set to List",
                                "initial": "rrname",
                                "choices": [
                                    ('rrname', 'RRName'),
                                    ('rdata', 'RData')
                                ]})

fields.addBaseField("rrtypes", "MultipleChoiceField", ["any"],
                    parameters={"label": "RR Types",
                                "required": False,
                                "initial": ["any"],
                                "choices": [
                                    ('any', 'Any'),
                                    ('a', 'A'),
                                    ('aaaa', 'AAAA'),
                                    ('cname', 'CNAME'),
                                    ('txt', 'TXT'),
                                    ('mx', 'MX'),
                                    ('ns', 'NS'),
                                    ('ptr', 'PTR')
                                ]})

fields.addReverseField("type", "ChoiceField", "ip",
                       parameters={"label": "Type",
                                   "required": True,
                                   "help_text":
                                   "The type of data to search for",
                                   "initial": "ip",
                                   "choices": [
                                        ("ip", "IP"),
                                        ("name", "Domain"),
                                        ("raw", "Raw (Hex)")]})
