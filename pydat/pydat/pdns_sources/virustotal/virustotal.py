from pydat.pdns_sources import pdnsConfig, formFields

config = pdnsConfig("virustotal", "VirusTotal")
config.addConfig('apikey', True, None,
                 description="The VirusTotal API Key to use")
config.addConfig('ssl_verify', False, True,
                 description="Verify SSL connection to API")


fields = formFields("virustotal")

fields.addForwardField("filter", "ChoiceField", "ip_address",
                    parameters={"label": "Filter",
                                "required": False,
                                "help_text": "only required if \'Format\' is set to List",
                                "initial": "ip_address",
                                "choices": [
                                    ('ip_address', 'IP'),
                                ]})

fields.addReverseField("filter", "ChoiceField", "hostname",
                    parameters={"label": "Filter",
                                "required": False,
                                "help_text": "only required if \'Format\' is set to List",
                                "initial": "hostname",
                                "choices": [
                                    ('hostname', 'Hostname'),
                                ]})
