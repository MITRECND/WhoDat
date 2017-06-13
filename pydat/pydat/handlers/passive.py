import cgi
import json
import requests
import sys
import time
import urllib
from django.conf import settings
from importlib import import_module
from pydat.pdns_sources import PDNS_MOD_REQUEST_METHOD, PDNS_MOD_R_REQUEST_METHOD, PDNS_MOD_PKG

'''
Global variables for passive handler
'''

'''
available to insert any critical error/status messages to be displayed within templates
'''
PDNS_STATUS={}           

'''
a container for all the defined passive DNS source handler modules
(so they dont have to be re-imported every request call)
'''
PDNS_HANDLER_MODS ={}      
    
'''
These three dictionaries all the passive DNS form fields read in from the activated pDNS source packages
   BASE - all form fields common to both normal and reverse passive DNS requests
   NORMAL - all form fields required for normal passive DNS requests
   REVERSE - all form fields required for reverse passive DNS requests
'''

PDNS_UI_FIELDS_BASE =[]     
PDNS_UI_FIELDS_NORMAL =[]
PDNS_UI_FIELDS_REVERSE =[]


'''
class- used as a data structure to hold dynamic form fields - as read
in from the passive-DNS packages settings
'''
class PassiveFormField:
    def __init__(self, **kwargs):
        '''
        django_field_name:  when building a super form (with fields from all passive-dns sources),
                            fields may have same name so will have django variable name will be seperate, unique name
                            NOTE: This unique name is of the form "source#field#", where the "source#" portion is used
                            to tag the fields by their passive DNS source group, to then be grouped together on the html form

        field_type:         type of form field, see django form fields documentation for list of acceptable fields
        field_key:          name of the field; the name that will be passed (as key) in key,value pair to templates
        field_value:        value returned from the form field (i.e. filled by user)
        field_value_default:a default field value may be specified for use when no field input is given
        passive_dns_source: passive-DNS source this variable/field belongs to
        parameters:         dictionary of form field parameters to pass to django form objects, see django form fields docs   
        '''
        self.django_field_name = None       
        self.field_type = None              
        self.field_key = None               
        self.field_value = None             
        self.field_value_default = None     
        self.passive_dns_source = None      
        self.parameters = {}


'''
This function is called by views.pdns() to retrieve pdns data and will iterate
through all passive DNS sources, calling the normal passive handlers for every active passive DNS source.
'''
def request_pdns(domain, result_format):
    results = {'success': False, 'sets': []}

    #check that pdns modules exist to run a passive dns request through
    if not settings.PDNS_SOURCES:
        results['error'] = 'No external sources configured.'
        return results

    '''
    get all common field (i.e. fields that are provided to every
    passive DNS source handler) values
    '''
    common_fields = {
                       'domain': domain,
                       'result_format': result_format
                    }

    #invoke passive dns request for each of the active pdns modules 
    for pdns_source, pdns_source_dict in settings.PDNS_SOURCES.items():
        
        #only pDNS sources that are activated will be processed for pdns request
        if not pdns_source_dict['active']:
            continue

        '''
        get all field values(that came from the http request) 
        for each specific passive-DNS source
        '''
        pdns_src_specific_fields = _get_passive_field_values(pdns_source, "normal")
        
        #call pdns module handler for pdns request, with specific pdns parameters
        pdns_mod_request_method = getattr(PDNS_HANDLER_MODS[pdns_source], PDNS_MOD_REQUEST_METHOD)
        tmp_results = pdns_mod_request_method(common_fields, pdns_src_specific_fields, pdns_source_dict)
        
        '''
        added key/value pairs required for upstream processing and template rendering
        add the results type to the response (views.py uses the type variable)
        '''
        tmp_results['type'] = pdns_source_dict['type'] 
        # add pdns specific template for a normal web response
        if result_format == "normal":
            tmp_results['table_template'] = pdns_source_dict['table_template']
             
        results['sets'].append(tmp_results)


    '''
    At least one of the passive handlers must be successful for
    the entire result to be successful.
    '''
    for set_ in results['sets']:
        if set_['success']:
            results['success'] = True
            return results

    results['error'] = "No passive data found.\n"

    #adding errors that may be passed from pdns specific sources
    for set_ in results['sets']:
        if "error" in set_:    
            results['error'] += "\n({0}: {1})".format(set_['type'], set_['error'])

    return results



'''
This function is called by views.pdns_r() to retrieve reverse pdns data and will iterate
through all passive DNS sources, calling the reverse passive handlers for every active passive DNS source.
'''
def request_pdns_reverse(search_value, search_value_type, result_format):
    results = {'success': False, 'sets': []}

    #check that pdns modules exist to run a passive dns request through
    if not settings.PDNS_SOURCES:
        results['error'] = 'No external sources configured.'
        return results

    '''
    get all common field (i.e. fields that are provided to every
    passive DNS source handler) values
    '''
    common_fields = {
                        'search_value': search_value,
                        'search_value_type': search_value_type,
                        'result_format': result_format
                    }

    #invoke passive dns request for each of the pdns modules found
    for pdns_source, pdns_source_dict in settings.PDNS_SOURCES.items():
        
        #only pDNS sources that are activated will be processed for pdns request
        if not pdns_source_dict['active']:
            continue

        #get all field values(that came from the http request) for each specific passive-DNS source
        pdns_src_specific_fields = _get_passive_field_values(pdns_source, "reverse")

        #call pdns module handler for reverse pdns request with specific parameters
        pdns_mod_request_method = getattr(PDNS_HANDLER_MODS[pdns_source], PDNS_MOD_R_REQUEST_METHOD)
        tmp_results = pdns_mod_request_method(common_fields, pdns_src_specific_fields, pdns_source_dict)

        '''
        added key/value pairs required for upstream processing and template rendering
        add the results type to the response (views.py uses the type variable)
        '''
        tmp_results['type'] = pdns_source_dict['type'] 

        #add pdns specific template for a normal web response
        if result_format == "normal":
            tmp_results['table_template'] = pdns_source_dict['table_template']
             
        results['sets'].append(tmp_results)

    for set_ in results['sets']:
        if set_['success']:
            results['success'] = True
            return results

    results['error'] = "No passive data found."
    #adding errors that may be passed from pdns specific sources
    for set_ in results['sets']:
        if "error" in set_:    
            results['error'] += "\n({0}: {1})".format(set_['type'], set_['error'])

    return results



'''
internal utility function - grabs passive form field values that were from
an http request and dictionizes them
'''
def _get_passive_field_values(pdns_source, passive_request_type):
    tmp= {}
    #get values for all base fields
    for passive_field in PDNS_UI_FIELDS_BASE:
        if passive_field.passive_dns_source == pdns_source:
            tmp[passive_field.field_key] = passive_field.field_value
            #remove value from global list as now considered received
            passive_field.field_value = None
    #get normal fields ( fields only for normal passive-DNS requests)
    if passive_request_type == "normal":
        for passive_field in PDNS_UI_FIELDS_NORMAL:
            if passive_field.passive_dns_source == pdns_source:
                tmp[passive_field.field_key] = passive_field.field_value
                #remove value from global list as now considered received
                passive_field.field_value = None
    #get normal fields ( fields only for normal passive-DNS requests)            
    elif passive_request_type == "reverse":
        for passive_field in PDNS_UI_FIELDS_REVERSE:
            if passive_field.passive_dns_source == pdns_source:
                tmp[passive_field.field_key] = passive_field.field_value
                #remove value from global list as now considered received
                passive_field.field_value = None
    return tmp



'''
internal utility function for script 1 - when the initialization script finds
a required pdns module setting with no key/value OR value defined, 
an attempt is made to use a default value for that pdns module 
variable(pulled from the pdns module settings file). If there is no 
default value defined, the pdns module is deactivated.
'''
def _try_default_var(pdns_source, pdns_source_dict, var, var_dict):
    #if the variable has a default value, use it
    if var_dict['default_value']:
        pdns_source_dict[var] = var_dict['default_value']
        return True
    else:
        if(pdns_source_dict['active']):
            print("Critical PDNS module error: PDNS module \"{0}\" " \
             "has required variable \"{1}\" ({2}). Variable not defined " \
             "in pydat.settings.py and there is no default value defined " \
             "in \"{0}\"s settings module. PDNS module \"{0}\" can not be " \
             "executed and has been deactivated. \n").format(pdns_source,
             var, var_dict['description'])
            pdns_source_dict['active'] = False
        return False
   
        
'''
internal utility function for script 1- a check to warn administrator if no PDNS modules
are activated and thus Passive DNS capability cannot be conducted within Pydat
'''
def _pdns_module_warn():
    for pdns_source, pdns_source_dict in settings.PDNS_SOURCES.items():
        if pdns_source_dict['active']:
            return False
    print("WARNING: No PDNS modules are active. PyDat's Passive DNS " \
        "functionality can not be conducted without any activated PDNS modules.\n")
    PDNS_STATUS['critical_error'] = "No passive DNS sources were either defined or activated"
    return True


'''
internal utility function - save repeated code
'''
def _get_passive_field_object(pdns_source,field_key, field_dict,
 source_index, field_index):
    tmp = PassiveFormField()
    tmp.passive_dns_source = pdns_source
    tmp.field_key = field_key
    tmp.field_type = field_dict['field_type']
    tmp.field_value_default = field_dict['field_value_default']
    tmp.django_field_name = "source{0}field{1}".format(
                                                        source_index,
                                                        field_index) 
    tmp.parameters = field_dict['parameters']    
    return tmp



'''
-----------------------
INITIALIZATION FUNCTIONS
-----------------------
'''

'''
-------------------------------------------------------------------------
Function/Script 1 - required to check and notify of any PDNS source
module settings that are missing. Will deactivate any PDNS package found
to be missing critical variables. 

Essentially validates "pydat.custom_settings.PDNS_SOURCES" against
"pydat.pdns_sources.*.settings.CONFIG_DICT" for each passive DNS source found.
-------------------------------------------------------------------------
'''

def check_pdns_modules():
    #iterate through all pdns sources defined in pydat.settings
    for pdns_source, pdns_source_dict in settings.PDNS_SOURCES.items():
        #if the module has the active variable and it is activated
        if 'active' in pdns_source_dict.keys() and pdns_source_dict['active']:
            try: 
                pdns_src_settings = import_module(
                                                    PDNS_MOD_PKG
                                                    + "." 
                                                    + pdns_source 
                                                    + ".settings")
            except ImportError:
                print("Error while doing initialization checks of pdns modules:" \
                 " Pydat could not import the pdns_module \"{0}\" from" \
                 "\"{1}\"\n").format(pdns_source, PDNS_MOD_PKG)
                continue
            #iterate through all pdns module variables defined in that pdns package's settings
            for var, var_dict in pdns_src_settings.CONFIG_DICT.items():
                #if the pdns module variable is required, check if defined in pydat.settings
                if var_dict["required"]: 
                    #if the required variable has no key value pair 
                    if var not in pdns_source_dict.keys():
                        print("Warning: PDNS module \"{0}\" has required configuration" \
                         " variable \"{1}\" but this variable (key/value) is not declared" \
                         " in pydat.settings.py \n").format(pdns_source,var)
                        _try_default_var(
                                            pdns_source,
                                            pdns_source_dict,
                                            var,
                                            var_dict)
                    #if the required variable has a key with no value
                    elif pdns_source_dict[var] == None:
                        print("Warning: PDNS module \"{0}\" has required " \
                              "configuration variable \"{1}\" but variable is" \
                              " not defined in pydat.settings.py\n").format(pdns_source,var)
                        _try_default_var(
                                            pdns_source,
                                            pdns_source_dict,
                                            var,
                                            var_dict)
        #if the module has no "active" variable or is not activated, then deactivate
        else:
            pdns_source_dict['active'] = False
    #final check, if no PDNS modules are found to be active, let user know         
    _pdns_module_warn()



'''        
--------------------------------------------------------------------------
Function/Script 2 - (must come after Function/Script 1) Proactively import 
all the passive- DNS source handler modules to have access to when actual 
passive-DNS requests are made
--------------------------------------------------------------------------
'''

def load_pdns_modules():
    #iterate through all passive-DNS sources that are defined in pydat.settings
    for pdns_source, pdns_source_dict in settings.PDNS_SOURCES.items():
        #if pdns-source active, then grab its handlers module
        if not pdns_source_dict['active']:
            continue
        try:
            PDNS_HANDLER_MODS[pdns_source] = import_module(
                                                        PDNS_MOD_PKG
                                                        + "." 
                                                        + pdns_source 
                                                        + ".handlers")
        except ImportError:
            print("Error: Pydat could not import the pdns source {0} "\
                "handler module from {1}. Due to this, pdns source {0}" \
                " will be deactivated").format(pdns_source, PDNS_MOD_PKG)
            pdns_source_dict["active"] = False
            continue


'''
------------------------------------------------------------------------
Function/Script-3 - read in and internalize all the user interface form fields (that
each passive-DNS source has defined to be presented to the user)

Essentially read in "pydat.pdns_sources.*.settings.UI_FIELDS" for all
defined and active passive DNS sources
------------------------------------------------------------------------
'''

def load_pdns_fields():
    for source_index, (pdns_source, pdns_source_dict) in enumerate(sorted(settings.PDNS_SOURCES.items())):
        #if the module has the active variable and is activated
        if pdns_source_dict['active']:
            try: 
                pdns_src_settings = import_module(
                                                PDNS_MOD_PKG
                                                + "."
                                                + pdns_source
                                                + ".settings")
            except ImportError:
                print("Error while doing processing of passive-DNS user-interface" \
                 "fields for passive-DNS source: \"{0}\".Pydat could not import" \
                 "the settings module from \"{1}.pdns_source\"\n").format(
                 pdns_source, settings.PDNS_MOD_PKG)
                continue
            field_index = 0
            for field_key, field_dict in pdns_src_settings.UI_FIELDS["BASE"].items():
                tmp = _get_passive_field_object(
                                                pdns_source,
                                                field_key,
                                                field_dict,
                                                source_index,
                                                field_index
                                                )
                PDNS_UI_FIELDS_BASE.append(tmp)
                field_index+=1

            for field_key, field_dict in pdns_src_settings.UI_FIELDS["NORMAL"].items():
                tmp = _get_passive_field_object(
                                                pdns_source,
                                                field_key,
                                                field_dict,
                                                source_index,
                                                field_index
                                                )
                PDNS_UI_FIELDS_NORMAL.append(tmp)
                field_index+=1

            for field_key, field_dict in pdns_src_settings.UI_FIELDS["REVERSE"].items():
                tmp = _get_passive_field_object(
                                                pdns_source,
                                                field_key,
                                                field_dict,
                                                source_index,
                                                field_index
                                                )
                PDNS_UI_FIELDS_REVERSE.append(tmp)
                field_index+=1

'''
#for testing purposes
def p_pdns_fields():
    for field in PDNS_UI_FIELDS_NORMAL:
        print("--------------")
        print("Passive-DNS source: {0}".format(field.passive_dns_source))
        print("Field key: {0}".format(field.field_key))
        print("django_name: {0}".format(field.django_field_name))
        print("field type: {0}".format(field.field_type))
        print("accordion panel: {0}".format(field.accordion_panel))
        print("params:")
        for k,v in field.parameters.items():
            print("key: {0}  value: {1}".format(k,v))
'''


#Initialize passive DNS modules
check_pdns_modules()
load_pdns_modules()
load_pdns_fields()