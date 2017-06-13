import sys
import socket
from django import forms
from django.conf import settings
from pydat.handlers import handler
from pydat.handlers.passive import PDNS_UI_FIELDS_BASE, PDNS_UI_FIELDS_NORMAL, PDNS_UI_FIELDS_REVERSE
import urllib

class domain_form(forms.Form):
    key = forms.ChoiceField(label="Key")
    value = forms.CharField(label="Value")
    filt = forms.ChoiceField(label="Filter")
    fmt = forms.ChoiceField(label="Format")
    latest = forms.BooleanField(
                            label="Latest",
                            initial=False,
                            required=False)
    limit = forms.IntegerField(
                            label="Limit",
                            min_value=1,
                            max_value=settings.LIMIT,
                            initial=settings.LIMIT)

    def __init__(self, *args, **kwargs):
        super(domain_form, self).__init__(*args, **kwargs)
        self.fields['key'].choices = settings.SEARCH_KEYS
        self.fields['fmt'].choices = [('normal', 'Web'),
                                      ('json', 'JSON'),
                                      ('list', 'List')]
        nonelist = [('none', 'None')]
        nonelist.extend(settings.SEARCH_KEYS)

        self.fields['filt'].choices = settings.SEARCH_KEYS

        for field in self.fields.values():
            field.error_messages = {'required':'%s is required' % field.label, 
                                    'invalid_choice': '%s is invalid' % field.label}

    def clean_latest(self):
        if 'latest' not in self.cleaned_data or self.cleaned_data['latest'] is None:
            return False
        else:
            return self.cleaned_data['latest']

    def clean_value(self):
        value = self.cleaned_data['value']
        if 'key' in self.cleaned_data:
            key = self.cleaned_data['key']
            if key == 'domainName': #Support Internationalization
                if isinstance(value, unicode):
                    value = value.encode("idna")
                return value
        return value


class advdomain_form(forms.Form):
    query = forms.CharField(
                        label='Search',
                        widget=forms.TextInput(attrs={'size': '60'}))
    filt = forms.ChoiceField(
                        label="Filter",
                        required=False)
    fmt = forms.ChoiceField(
                        label="Format",
                        required=False)
    limit = forms.IntegerField(
                        label="Limit",
                        min_value=1,
                        max_value=settings.LIMIT,
                        initial=settings.LIMIT,
                        required=False)
    unique = forms.BooleanField(
                        label="Unique",
                        initial=False,
                        required=False)

    def __init__(self, *args, **kwargs):
        super(advdomain_form, self).__init__(*args, **kwargs)
        self.fields['fmt'].choices = [('normal', 'Web'),
                                      ('json', 'JSON'),
                                      ('list', 'List')]
        nonelist = [('none', 'None')]
        nonelist.extend(settings.SEARCH_KEYS)

        self.fields['filt'].choices = settings.SEARCH_KEYS

        for field in self.fields.values():
            field.error_messages = {
                            'required':'%s is required' % field.label, 
                            'invalid_choice': '%s is invalid' % field.label}

    def clean_unique(self):
        if 'unique' not in self.cleaned_data or self.cleaned_data['unique'] is None:
            return False
        else:
            return self.cleaned_data['unique']

    def clean_query(self):
        if 'query' not in self.cleaned_data:
            raise forms.ValidationError("query field required")
        try:
            query = urllib.unquote(self.cleaned_data['query'])
        except:
            raise forms.ValidationError("Unable to unquote query")
        result = handler.test_query(query)
        if result is not None:
            raise forms.ValidationError("Unable to parse query: %s" % result) 
        return query

'''Allows you to provide a drop down of numbers but support non listed number'''
class ChoiceNumberField(forms.ChoiceField):
    minimum = 0
    maximum = 0

    def __init__(self, *args, **kwargs):
        if kwargs is not None:
                if 'maximum' in kwargs:
                    self.maximum = kwargs['maximum']
                    del kwargs['maximum']
                if 'minimum' in kwargs:
                    self.minimum = kwargs['minimum']
                    del kwargs['minimum']

        super(ChoiceNumberField, self).__init__(*args, **kwargs)

    def validate(self, value):
        try:
            value = int(value)
            if self.maximum > 0 and value > self.maximum:
                raise forms.ValidationError("Value too large")
            if value < self.minimum:
                raise forms.ValidationError("Value too small")
            return value
        except Exception, e:
            raise forms.ValidationError("Unable to process number")



class pdns_super_dynamic(forms.Form):
    #format field is common to all passive-DNS forms and reverse passive-DNS forms
    result_format = forms.ChoiceField(label="Result Format")

    def __init__(self, *args, **kwargs):
        super(pdns_super_dynamic, self).__init__(*args, **kwargs)
        self.fields['result_format'].choices =[('normal','Web'),('json','JSON'),('list','List')]

        #for every defined base field from the passive-DNS packages
        for passive_field in PDNS_UI_FIELDS_BASE:
            '''
            create field , and tag with additional "accordion panel" variable required
            for displaying field in correct panel when rendered
            '''
            try:
                self.fields[passive_field.django_field_name] = getattr(forms,
                 passive_field.field_type)()

                for parameter_key, parameter_value in passive_field.parameters.items():
                    '''
                    unique case, have to convert the string variable to widget object
                    (this cannot handle widgets with attribute arguments though,
                    not sure how to handle that without excessive code and and string parsing)
                    '''
                    if parameter_key == "widget":
                        parameter_value = getattr(forms, parameter_value.split(".")[1])()

                    #django forms hold "initial" value parameters in dictionary
                    if parameter_key == "initial":
                        self.initial[passive_field.django_field_name] = parameter_value
                    else:
                        #set parameter via normal route
                        setattr(self.fields[passive_field.django_field_name], parameter_key, parameter_value)
            except AttributeError:
                sys.exit("\nCritical Error: pdns_super_dynamic() - error creating django form field. The type of field specified in the passive DNS configuration (settings.py) may not be a django field type OR a specified parameter of the field may be wrong\n")
                pass

class pdns_form_dynamic(pdns_super_dynamic):
    #fields common to all normal passive-DNS requests
    search_value = forms.CharField(label="Domain")

    def __init__(self, *args, **kwargs):
        super(pdns_form_dynamic, self).__init__(*args, **kwargs)
        '''
        Add fields that are specific to normal passive-DNS requests
        for every defined base field from the passive-DNS packages
        '''
        for passive_field in PDNS_UI_FIELDS_NORMAL:
            '''
            create field, and tag with additional "accordion panel" 
            variable required for displaying field in correct panel
            when rendered
            '''
            try:
                self.fields[passive_field.django_field_name] = getattr(forms,
                    passive_field.field_type)()

                for parameter_key, parameter_value in passive_field.parameters.items():
                    '''
                    unique case, have to convert the string variable to widget object
                    (this cannot handle widgets with attribute arguments though,
                    not sure how to handle that without excessive code and and string parsing)
                    '''
                    if parameter_key == "widget":
                        parameter_value = getattr(forms, parameter_value.split(".")[1])()

                    #django forms hold "initial" value parameters in dict
                    if parameter_key == "initial":
                        self.initial[passive_field.django_field_name] = parameter_value
                    else:
                        #set parameter via normal route'''
                        setattr(self.fields[passive_field.django_field_name], parameter_key, parameter_value)

            except AttributeError:
                sys.exit("\nWARNING: pdns_super_dynamic() - error creating django form field. The type of field specified in the passive DNS configuration (settings.py) may not be a django field type OR a specified parameter of the field may be wrong\n")
                pass 

    def clean_search_value(self):
        search_value = self.cleaned_data['search_value']
        if isinstance(search_value, unicode):
            search_value = search_value.encode("idna")
            return search_value
        return search_value


class rpdns_form_dynamic(pdns_super_dynamic):
    #field common to all reverse passive-DNS requests
    search_value = forms.CharField(label="Query")
    search_value_type = forms.ChoiceField(label ="Type", help_text="type of the query value")

    def __init__(self, *args, **kwargs):
        super(rpdns_form_dynamic, self).__init__(*args, **kwargs)
        self.fields['search_value_type'].choices = [('ip','IP'), 
                                                    ('name','Domain'),
                                                    ('raw','Raw (Hex)')]
        self.initial['search_value_type'] = ['ip']

        '''
        Add fields that are specific to normal passive-DNS requests
        for every defined base field from the passive-DNS packages
        '''
        for passive_field in PDNS_UI_FIELDS_REVERSE:
            '''
            create field, and tag with additional "accordion panel" 
            variable required for displaying field in correct panel
            when rendered
            '''
            try:
                self.fields[passive_field.django_field_name] = getattr(forms,
                    passive_field.field_type)()
                
                for parameter_key, parameter_value in passive_field.parameters.items():
                    '''
                    unique case, have to convert the string variable to widget object
                    (this cannot handle widgets with attribute arguments though,
                    not sure how to handle that without excessive code and and string parsing)
                    '''
                    if parameter_key == "widget":
                        parameter_value = getattr(forms, parameter_value.split(".")[1])()
                        
                    #django forms hold "initial" value parameters in dict
                    if parameter_key == "initial":
                        self.initial[passive_field.django_field_name] = parameter_value
                    else:
                        #set parameter via normal route
                        setattr(self.fields[passive_field.django_field_name], parameter_key, parameter_value)

            except AttributeError:
                sys.exit("\nWARNING: pdns_super_dynamic() - error creating django form field. The type of field specified in the passive DNS configuration (settings.py) may not be a django field type OR a specified parameter of the field may be wrong\n")
                pass 


    def clean(self):
        search_value_type = self.cleaned_data["search_value_type"]
        search_value = self.cleaned_data["search_value"]

        if not search_value_type:
            raise forms.ValidationError('Unable to parse query')
    
        if search_value_type == "ip": 
            (status, output) = validate_ip(search_value)
            if not status:
                raise forms.ValidationError(output)
            search_value = output
        elif search_value_type == "raw":
            output = validate_hex(search_value)
            if output is None:
                raise forms.ValidationError("Invalid Hex")
            search_value = output
        elif search_value_type == "name":
            if isinstance(search_value, unicode):
                search_value = search_value.encode("idna")
        
        self.cleaned_data['seach_value'] = search_value
        
        return self.cleaned_data


def validate_ip(input_ip):
    ip = ""
    mask = None
    version = 4
    if input_ip.count("/") > 0:
        if input_ip.count("/") > 1:
            return (False, "Invalid IP Syntax")
        (ip, mask) = input_ip.split("/")
    else:
        ip = input_ip
    
    #Validate ip part
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        version = 6
    except: #invalid ipv6
        try:
            socket.inet_pton(socket.AF_INET, ip)
        except Exception, e:
            return (False, "Invalid IP Address")

    output_ip = ip
    #Validate mask if present
    if mask is not None:
        try:
            mask = int(mask) 
            if mask < 1:
                return (False, "Mask must be at least 1")
            elif version == 4 and mask > 32:
                return (False, "IP Mask too large for v4")
            elif version == 6 and mask > 128:
                return (False, "IP Mask too large for v6")
        except:
            return (False, "Unable to process mask")
        output_ip += ",%d" % mask
    return (True, output_ip)

def validate_hex(input_hex):
    try:
        output_hex = "%x" % int(input_hex, 16)
    except:
        return None
    if len(output_hex) % 2 == 1: #make hex string always pairs of hex values
        output_hex = "0" + output_hex

    return output_hex
