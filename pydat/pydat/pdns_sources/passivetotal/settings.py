'''
settings module for pdns source DNSDB- this module enumerates the
settings and configurations available for DNSDB. These variables
are not set here, only enumerated and detailed. Pydat will pull
default variable values from here, if the variable is required
and not set in "pydat.settings.py" (or rather pydat.custom_settings.py).

Requirements: 
	-This module must be named "settings.py" and placed within the
     pdns source package's root
'''

CONFIG_DICT = {
	"active": {                        
		"default_value": True,
		"required":True,
		"description": "whether the module should be processed(used) for" \
        " pdns data when pdns requests are initiated in pydat"
	},
    "type":{                             
    	"default_value":" passiveTotal",
    	"required": True,
    	"description": "the internal (within django) name for the " \
        "module- used as a name tag to attach to pdns results"
    },
    "table_template":{                   
    	"default_value": "passivetotal.html",
    	"required": True,
    	"description": "the django template used to format the results" \
        " from the DNSDB API when being rendered"
    },
    "passivetotal_key":{
    	"default_value": None,
    	"required": True,
    	"description": "key required to access the Passive Total API"
	}  
}



'''
UI_FIELDS- (must have this variable name) A list of all
the form fields for this passive-DNS source. These dictionary
entries will be processed and translated to django form fields.
The django form fields are then presented in the user interface.
The result field values are then passed to the passive-DNS handler 
functions. UI_INPUTS sub-key values are the variable names that the 
result values will be bound to (as a key,value pair) and given to
the passive-DNS request handlers.

UI inputs is broken down into 3 sub dictionaries:
-BASE - input form fields that are required for both 
        normal and reverse passive-DNS requests
-NORMAL - input form fields that required for normal
          passive-DNS requests
-REVERSE- input form fields that required for reverse
          passive-DNS requests


Note: pyDat supplies a universal search CharField(django) (for a URL, IP, Domain),
so do not include it. That variable's name is "search_value" and is passed to 
both passive-DNS and reverse passive-DNS handlers and a the passive-DNS template
(if one is provided).
'''

UI_FIELDS = {
    "BASE":{
        #whether or not to exclude subdomains when handling a request 
        "absolute":{
            "field_type": "BooleanField",
            "field_value_default": False,
            "parameters":{
                "label": "Absolute",
                "initial": False,
                "required": False
            }
        }
    },
    "NORMAL":{

    },
    "REVERSE":{
    
    }
}