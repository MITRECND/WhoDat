
'''
settings module for pdns source DNSDB- this module enumerates the settings 
and configurations available for DNSDB. These variables are not set here,
only enumerated and detailed. Pydat will pull default variable values from
here, if the variable is required and not set in "pydat.settings.py" 
(or rather pydat.custom_settings.py).

Requirements: 
	-This module must be named "settings.py" and placed within the
     pdns source package root
'''


'''
CONFIG_DICT - (must have this variable name) Is an enumeration
of configuration settings that are used to operate the passive-DNS 
source. Configuration variables and settings can be listed here and 
set with default values, BUT the "PDNS_SOURCES" dictionary variable
in pydat.custom_settings.py is where these variables are set.
'''
CONFIG_DICT = {
	"active": {                        
		"default_value": True,
		"required": True,
		"description": "whether the module should be processed(used) for" \
            " pdns data when pdns requests are initiated in pydat"
	},
    "type":{                             
    	"default_value": "DNSDB",
    	"required": True,
    	"description": "the internal (within django) name for the module" \
            "- used as a name tag to attach to pdns results"
    },
    "table_template":{                   
    	"default_value": "dnsdb.html",
    	"required": True,
    	"description": "the django template used to format the results from" \
            " the DNSDB API when being rendered"
    },
    "dnsdb_headers":{
        "default_value":{},
    	"required": True,
    	"description": "a dictionary of values required by the DNSDB API" \
            " (usually a key and application/format type)"
    },
    "ssl_verify":{
        "default_value": True,
        "required": True,
        "description": "verify SSL certificates in external calls"
    }
}



'''
UI_FIELDS- (must have this variable name) A list of all
the form fields for this passive-DNS source. These dictionary
entries will be processed and translated to django form fields.
The django form fields are then presented in the user interface.
The resulting inputted field values are then passed to the passive-DNS handler 
functions. UI_INPUTS sub-key values are the variable names that the 
result values will be bound to (as a key,value pair) and given to
the passive-DNS request handlers.

All UI_FIELDS must follow Django Form Field API. For example, 
'field_type' must be a string of a form field type that Django supports.
Also, all form field parameters must follow exact django API specifications
as well. For instance, for the form field parameter "choices"( for a 
field of type "ChoiceField"), the value must be a list of 2-tuples.
Note: set a field's "required" parameter to False unless you want to force
the user to enter input, even if there are default inputs.

UI inputs is broken down into 3 sub dictionaries:
-BASE - input form fields that are required for both 
        normal and reverse passive-DNS requests
-NORMAL - input form fields that required for normal
          passive-DNS requests
-REVERSE- input form fields that required for reverse
          passive-DNS requests

pyDat supplies some universal form fields already that dont require you to 
repeatedly define. pyDat will provide these fields and supply your handlers 
the values in a dictionary.

----For normal passive DNS requests they are:

"search_value" - a CharField (for a domain) - has the field label "Domain"
"result_format" - a ChoiceField where the options are {('normal','Web'),('json','JSON'),('list','List')}
                    (the value provided back to your handlers are the first string in 2-tuples)

----For reverse passive DNS requests they are:

"search_value" - a CharField (for IP , Domain, Raw ) - has the field label "Query"
"search_value_type" - a ChoiceField where the options are {('ip','IP'),('name','Domain'),('raw','Raw (Hex)')}
                    (the value provided back to your handlers are the first string in 2-tuples)
"result_format" - a ChoiceField where the options are {('normal','Web'),('json','JSON'),('list','List')}
                    (the value provided back to your handlers are the first string in 2-tuples)



'''
UI_FIELDS = {
    "BASE":{ 
        #the limit on number of records to return to the request
        "limit":{
            "field_type": "ChoiceField",
            "field_value_default": 100,
            "parameters":{
                "label": "Limit",
                "required": False,
                "choices": [(10,10),(20,20),(50,50),(100,100),(200,200),(500,500),(1000,1000)],
                "initial": 100
            }
        },
        #whether or not to exclude subdomains when handling a request
        "absolute":{
            "field_type": "BooleanField",
            "field_value_default": False,
            "parameters": {
                "label": "Absolute",
                "initial": False,
                "required": False,
                "help_text": "Excludes subdomains when checked"
            }
        },
        "filter": {
            "field_type": "ChoiceField",
            "field_value_default": "rrname",
            "parameters": {
                "label": "Filter",
                "required": False,
                "help_text": "only required if \'Format\' is set to List",
                "initial": "rrname",
                "choices": [
                    ('rrname', 'RRName'), 
                    ('rdata', 'RData')
                ]
            }
        },
        "pretty": {
            "field_type": "BooleanField",
            "field_value_default": True,
            "parameters": {
                "label": "Pretty",
                "initial": True,
                "required": False,
                "help_text": "the pretty field renders a pretty-fied version of the code if youre doing a manual REST request"
            }
        }
    },
    "NORMAL":{
        #Types that are searchable via DNSDB, update to taste
        "rrtypes":{
            "field_type": "MultipleChoiceField",
            "field_value_default": ["any"],
            "parameters":{
                "label": "RR Types",
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
                ]
            }
        }
    },
    "REVERSE":{
        #Types that are searchable via DNSDB, update to taste
        "rrtypes":{
            "field_type": "MultipleChoiceField",
            "field_value_default": ['any'],
            "parameters": {
                "label": "RR Types",
                "initial": ['any'],
                "required": False,
                "help_text": "only required if \'Type\' is set to Domain",
                "choices":[ 
                    ('any', 'Any'),
                    ('a', 'A'),
                    ('aaaa', 'AAAA'),
                    ('cname', 'CNAME'),
                    ('txt', 'TXT'),
                    ('mx', 'MX'),
                    ('ns', 'NS'),
                    ('ptr', 'PTR'),
                ]
            }
        }
    }
}