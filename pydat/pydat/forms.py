import sys
import socket
from django import forms
from django.conf import settings
from pydat.handlers import handler
from pydat.handlers.passive import PDNS_UI_FIELDS_BASE, PDNS_UI_FIELDS_FORWARD, PDNS_UI_FIELDS_REVERSE
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
                        widget=forms.TextInput())
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
        self.fields['fmt'].choices = [('none', 'Web'),
                                      ('json', 'JSON'),
                                      ('csv', 'CSV'),
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

class ChoiceNumberField(forms.ChoiceField):
    """Allows you to provide a drop down of numbers but support non listed number

       This class is based on forms.ChoiceField, but extended to support
       arbitrary values

       Keyword arguments:
       maximum -- maximum value
       minimum -- minimum value
    """
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

forms.ChoiceNumberField = ChoiceNumberField



class pdns_super_dynamic(forms.Form):
    # Format field is common to all passive-DNS forms and reverse passive-DNS forms
    result_format = forms.ChoiceField(label="Format")

    def __init__(self, *args, **kwargs):
        super(pdns_super_dynamic, self).__init__(*args, **kwargs)
        self.fields['result_format'].choices =[('none','Web'),
                                               ('json','JSON'),
                                               ('csv', 'CSV'),
                                               ('list','List')]

        self.add_passive_fields(PDNS_UI_FIELDS_BASE)

    def add_passive_fields(self, passive_fields):
        # For every defined base field from the passive-DNS packages
        for passive_field in passive_fields:
            try:
                self.fields[passive_field.django_field_name] = getattr(forms,
                    passive_field.field_type)()

                for parameter_key, parameter_value in passive_field.parameters.items():
                    # Unique case, have to convert the string variable to widget object
                    # (this cannot handle widgets with attribute arguments though,
                    # not sure how to handle that without excessive code and and string parsing)
                    if parameter_key == "widget":
                        parameter_value = getattr(forms, parameter_value.split(".")[1])()

                    # Django forms hold "initial" value parameters in dictionary
                    if parameter_key == "initial":
                        self.initial[passive_field.django_field_name] = parameter_value
                    else:
                        # Set parameter via normal route
                        setattr(self.fields[passive_field.django_field_name], parameter_key, parameter_value)
            except AttributeError:
                sys.exit("\nCritical Error: Error creating django form field. The type of field specified in the passive DNS configuration (settings.py) may not be a django field type OR a specified parameter of the field may be wrong\n")


class pdns_form_dynamic(pdns_super_dynamic):
    # Fields common to all forward passive-DNS requests
    search_value = forms.CharField(label="Domain",
                                   widget=forms.TextInput(attrs={'size': 60}))

    def __init__(self, *args, **kwargs):
        super(pdns_form_dynamic, self).__init__(*args, **kwargs)

        # Add fields that are specific to forward passive-DNS requests
        # for every defined base field from the passive-DNS packages
        self.add_passive_fields(PDNS_UI_FIELDS_FORWARD)


    def clean_search_value(self):
        search_value = self.cleaned_data['search_value']
        if isinstance(search_value, unicode):
            search_value = search_value.encode("idna")
            return search_value
        return search_value


class rpdns_form_dynamic(pdns_super_dynamic):
    # Field common to all reverse passive-DNS requests
    search_value = forms.CharField(label="Query",
                                   widget=forms.TextInput(attrs={'size': 60}))

    def __init__(self, *args, **kwargs):
        super(rpdns_form_dynamic, self).__init__(*args, **kwargs)

        # Add fields that are specific to reverse passive-DNS requests
        # for every defined base field from the passive-DNS packages
        self.add_passive_fields(PDNS_UI_FIELDS_REVERSE)
