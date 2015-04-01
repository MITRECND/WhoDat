import socket
from django import forms
from django.conf import settings
from pydat.handlers import handler
import urllib

class domain_form(forms.Form):
    key = forms.ChoiceField(label="Key")
    value = forms.CharField(label="Value")
    latest = forms.BooleanField(label="Latest", initial=False, required=False)
    filt = forms.ChoiceField(label="Filter")
    fmt = forms.ChoiceField(label="Format")
    limit = forms.IntegerField(label="Limit", min_value=1,
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
    query = forms.CharField(label='Search', widget=forms.TextInput(attrs={'size': '60'}))
    filt = forms.ChoiceField(label="Filter", required=False)
    fmt = forms.ChoiceField(label="Format", required=False)
    limit = forms.IntegerField(label="Limit", min_value=1,
                               max_value=settings.LIMIT,
                               initial=settings.LIMIT,
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
            field.error_messages = {'required':'%s is required' % field.label, 
                                    'invalid_choice': '%s is invalid' % field.label}

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

#Allows you to provide a drop down of numbers but support non listed number
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

class pdns_super(forms.Form):
    fmt = forms.ChoiceField(label="Format")
    limit = ChoiceNumberField(label="Limit", maximum=settings.DNSDB_LIMIT, minimum=1)
    absolute = forms.BooleanField(label="Absolute", initial=False, required=False)
    pretty = forms.BooleanField(label='Pretty', initial=True, required=False)
    filt = forms.ChoiceField(label="Filter")
    rrtypes = forms.MultipleChoiceField(label="RR Types",
                                        widget=forms.SelectMultiple)

    def __init__(self, *args, **kwargs):
        super(pdns_super, self).__init__(*args, **kwargs)
        self.fields['fmt'].choices = [('normal', 'Web'),
                                      ('json', 'JSON'),
                                      ('list', 'List')]
        self.fields['limit'].choices = [(val, val) for val in settings.DNSDB_PAGE_LIMITS]
        self.initial['limit'] = settings.DNSDB_PAGE_LIMITS[settings.DNSDB_PAGE_LIMIT_DEFAULT]

        self.fields['filt'].choices = [('rrname', 'RRName'), 
                                       ('rdata', 'RData')]

        self.fields['rrtypes'].choices = settings.RRTYPE_KEYS
        self.initial['rrtypes'] = [settings.RRTYPE_KEYS[0][0]]

        for field in self.fields.values():
            field.error_messages = {'required':'%s is required' % field.label,
                                    'invalid_choice': '%s is invalid' % field.label}

    def clean_absolute(self):
        if 'absolute' not in self.cleaned_data or self.cleaned_data['absolute'] is None:
            return False
        else:
            return self.cleaned_data['absolute']

    def clean_pretty(self):
        if 'pretty' not in self.cleaned_data or self.cleaned_data['pretty'] is None:
            return True
        else:
            return self.cleaned_data['pretty']

    def clean_limit(self):
        limit = int(self.cleaned_data['limit'])
        if limit < 1:
            raise forms.ValidationError("Limit too small")
        elif limit > settings.DNSDB_LIMIT:
            raise forms.ValidationError("Limit too large")
        return limit



class pdns_form(pdns_super):
    domain = forms.CharField(label="Domain")

    def __init__(self, *args, **kwargs):
        super(pdns_form, self).__init__(*args, **kwargs)

    def clean_domain(self):
        domain = self.cleaned_data['domain']
        if isinstance(domain, unicode):
            domain = domain.encode("idna")
            return domain
        return domain


class pdns_r_form(pdns_super):
    key = forms.ChoiceField(label="Type")
    value = forms.CharField(label="Query")

    def __init__(self, *args, **kwargs):
        super(pdns_r_form, self).__init__(*args, **kwargs)
        self.fields['key'].choices = settings.RDATA_KEYS

    def clean_value(self):
        if 'key' not in self.cleaned_data:
            raise forms.ValidationError('Unable to parse query')
    
        key = self.cleaned_data['key']
        value = self.cleaned_data['value']
        if key == "ip": 
            (status, output) = validate_ip(value)
            if not status:
                raise forms.ValidationError(output)
            value = output
        elif key == "raw":
            output = validate_hex(value)
            if output is None:
                raise forms.ValidationError("Invalid Hex")
            value = output
        elif key == "name":
            if isinstance(value, unicode):
                value = value.encode("idna")
        return value


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
