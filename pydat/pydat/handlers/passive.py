import cgi
import json
import requests
import sys
import time
import os
import imp
import urllib
from django.conf import settings
from importlib import import_module
from pydat import pdns_sources

'''
Global variables for passive handler
'''

'''
a container for all the defined passive DNS source handler modules
(so they dont have to be re-imported every request call)
'''
PDNS_HANDLER_MODS = {}
    
'''
These three dictionaries all the passive DNS form fields read in from the activated pDNS source packages
   BASE     - all form fields common to both forward and reverse passive DNS requests
   FORWARD  - all form fields required for forward passive DNS requests
   REVERSE  - all form fields required for reverse passive DNS requests
'''

PDNS_UI_FIELDS_BASE = []
PDNS_UI_FIELDS_FORWARD = []
PDNS_UI_FIELDS_REVERSE = []


'''
class- used as a data structure to hold dynamic form fields - as read
in from the passive-DNS packages settings
'''
class PassiveFormField:
    def __init__(self, source_name, field_key, field_type,
                 field_value_default, parameters):
        '''
        django_field_name:  when building a super form (with fields from all passive-dns sources),
                            fields may have same name so will have django variable name will be seperate, unique name
                            NOTE: This unique name is of the form "source#field#", where the "source#" portion is used
                            to tag the fields by their passive DNS source group, to then be grouped together on the html form

        field_type:         type of form field, see django form fields documentation for list of acceptable fields
        field_key:          name of the field; the name that will be passed (as key) in key,value pair to templates
        field_value:        value returned from the form field (i.e. filled by user)
        field_value_default:a default field value may be specified for use when no field input is given
        source_name: passive-DNS source this variable/field belongs to
        parameters:         dictionary of form field parameters to pass to django form objects, see django form fields docs   
        '''
        self.django_field_name = "{0}_{1}".format(source_name,
                                                  field_key)
        self.field_type = field_type

        self.source_name = source_name
        self.field_key = field_key
        self.field_value_default = field_value_default
        self.parameters = parameters


'''
This function is called by views.pdns() to retrieve pdns data and will iterate
through all passive DNS sources, calling the forward passive handlers for every active passive DNS source.
'''
def request_pdns(domain, result_format, dynamic_fields):
    results = {'success': False, 'responses': []}

    #check that pdns modules exist to run a passive dns request through
    if len(PDNS_HANDLER_MODS) == 0:
        results['error'] = 'No external sources configured.'
        return results

    #invoke passive dns request for each of the active pdns modules 
    for pdns_source, module in PDNS_HANDLER_MODS.items():
        dynamic_data = dynamic_fields[pdns_source] if pdns_source in dynamic_fields else {}
        tmp_results = module.handlers.forward(domain, result_format, **dynamic_data)
        
        '''
        added key/value pairs required for upstream processing and template rendering
        add the results type to the response (views.py uses the type variable)
        '''
        tmp_results['type'] = module.config.displayName
        tmp_results['name'] = pdns_source
        results['responses'].append(tmp_results)


    '''
    At least one of the passive handlers must be successful for
    the entire result to be successful.
    '''
    for set_ in results['responses']:
        if set_['success']:
            results['success'] = True
            return results

    results['error'] = "No valid passive data found: "

    #adding errors that may be passed from pdns specific sources
    for set_ in results['responses']:
        if "error" in set_:    
            results['error'] += "\n({0}: {1})".format(set_['type'], set_['error'])

    return results



'''
This function is called by views.pdns_r() to retrieve reverse pdns data and will iterate
through all passive DNS sources, calling the reverse passive handlers for every active passive DNS source.
'''
def request_pdns_reverse(search_value, result_format, dynamic_fields):
    results = {'success': False, 'responses': []}

    #check that pdns modules exist to run a passive dns request through
    if len(PDNS_HANDLER_MODS) == 0:
        results['error'] = 'No external sources configured.'
        return results

    #invoke passive dns request for each of the pdns modules found
    for pdns_source, module in PDNS_HANDLER_MODS.items():
        dynamic_data = dynamic_fields[pdns_source] if pdns_source in dynamic_fields else {}
        #call pdns module handler for reverse pdns request with specific parameters
        tmp_results = module.handlers.reverse(search_value, result_format, **dynamic_data)

        '''
        added key/value pairs required for upstream processing and template rendering
        add the results type to the response (views.py uses the type variable)
        '''
        tmp_results['type'] = module.config.displayName
        tmp_results['name'] = pdns_source
        results['responses'].append(tmp_results)

    for set_ in results['responses']:
        if set_['success']:
            results['success'] = True
            return results

    results['error'] = "No valid passive data found: "
    #adding errors that may be passed from pdns specific sources
    for set_ in results['responses']:
        if "error" in set_:    
            results['error'] += "\n({0}: {1})".format(set_['type'], set_['error'])

    return results


'''
-----------------------
INITIALIZATION FUNCTIONS
-----------------------
'''

def _load_pdns_fields_(source_name, module):
    for field_key, field_dict in module.fields.base.items():
        tmp = PassiveFormField(source_name, field_key, field_dict['field_type'],
                               field_dict['field_value_default'], field_dict['parameters'])
        PDNS_UI_FIELDS_BASE.append(tmp)

    for field_key, field_dict in module.fields.forward.items():
        tmp = PassiveFormField(source_name, field_key, field_dict['field_type'],
                               field_dict['field_value_default'], field_dict['parameters'])
        PDNS_UI_FIELDS_FORWARD.append(tmp)

    for field_key, field_dict in module.fields.reverse.items():
        tmp = PassiveFormField(source_name, field_key, field_dict['field_type'],
                               field_dict['field_value_default'], field_dict['parameters'])
        PDNS_UI_FIELDS_REVERSE.append(tmp)


def initialize():
    #iterate through all pdns sources defined in pydat.settings
    for pdns_source, pdns_source_dict in settings.PDNS_SOURCES.items():
        #if the module has the active variable and it is activated
        if pdns_source_dict.get('active', False):
            try: 
                (file, pathname, description) = imp.find_module(pdns_source, pdns_sources.__path__)
                module = imp.load_module(pdns_source, file, pathname, description)
            except ImportError:
                print("Error while doing initialization checks of pdns modules:" \
                 " Pydat could not import the pdns_module \"{0}\"\n").format(pdns_source)
                continue

            module.config.validate(pdns_source_dict)
            PDNS_HANDLER_MODS[pdns_source] = module
            _load_pdns_fields_(pdns_source, module)

        #if the module has no "active" variable or is not activated, then deactivate
        else:
            pdns_source_dict['active'] = False
    #final check, if no PDNS modules are found to be active, let user know         
    if len(PDNS_HANDLER_MODS) == 0:
        print("WARNING: No PDNS modules are active. PyDat's Passive DNS " \
            "functionality can not be conducted without any activated PDNS modules.\n")


'''
#for testing purposes
def p_pdns_fields():
    for field in PDNS_UI_FIELDS_FORWARD:
        print("--------------")
        print("Passive-DNS source: {0}".format(field.source_name))
        print("Field key: {0}".format(field.field_key))
        print("django_name: {0}".format(field.django_field_name))
        print("field type: {0}".format(field.field_type))
        print("accordion panel: {0}".format(field.accordion_panel))
        print("params:")
        for k,v in field.parameters.items():
            print("key: {0}  value: {1}".format(k,v))
'''
