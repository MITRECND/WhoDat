import json
import socket

from django.conf import settings
from django.shortcuts import render, HttpResponse
from django.http import QueryDict
import urllib
import unicodecsv as csv
import cStringIO

from pydat.forms import (domain_form, advdomain_form, pdns_form_dynamic,
                         rpdns_form_dynamic)
from pydat.handlers import handler
from pydat.handlers import passive

def __renderErrorResponse__(request, view, message, data=None):
    d = {'error': message}
    if data is not None:
        d.update(data)

    context = __createRequestContext__(d)
    return render(request, view, context=context)
    

def __renderErrorPage__(request, message, data=None):
    d = {'error': message}
    if data is not None:
        d.update(data)

    context = __createRequestContext__(d)
    return render(request, 'error.html', context=context)

def __createRequestContext__(data=None):
    #Default to adding search forms to every context
    search_f = domain_form()
    pdns_f_dyn = pdns_form_dynamic()
    rpdns_f_dyn = rpdns_form_dynamic()
    advdomain_f = advdomain_form()

    ctx_var = { 'domain_form': search_f,
                'advdomain_form': advdomain_f,
                'pdns_form_dynamic': pdns_f_dyn,
                'rpdns_form_dynamic': rpdns_f_dyn,   
                'latest_version': handler.lastVersion(),
                'handler': settings.HANDLER, 
                'pdns_sources':[mod_data.config for mod_data in passive.PDNS_HANDLER_MODS.values()]
            }

    if settings.HANDLER == 'es':
        ctx_var['health'] = handler.cluster_health().capitalize()
        ctx_var['record_count'] = handler.record_count()
        ctx_var['last_import'] = handler.lastUpdate()

    if data is not None:
        ctx_var.update(data)
        if 'active' not in data:
            if 'pdns_form' in data:
                ctx_var['active'] = 1
            elif 'pdns_r_form' in data:
                ctx_var['active'] = 2
            else:
                ctx_var['active'] = 0

    return ctx_var

def index(request):
    if settings.HANDLER == 'es':
        legacy = False
    else:
        legacy = True
    context = __createRequestContext__(data={'legacy_search': legacy})
    return render(request,'domain.html', context=context)

def pdns_index(request):
    context = __createRequestContext__()
    return render(request,'pdns.html', context=context)

def rpdns_index(request):
    context = __createRequestContext__()
    return render(request, 'rpdns.html', context=context)

def stats(request):
    stats = handler.cluster_stats()
    allversions = handler.metadata()
    if allversions['success']:
        lastimport = allversions['data'][-1]
        lastten = allversions['data'][-10:]
    else:
        #XXX TODO returne error
        pass

    if lastten[0]['metadata'] == 0:
        lastten = lastten[1:]

    context = __createRequestContext__(data = {
                                                'domainStats': stats['domainStats'], 
                                                'histogram': stats['histogram'],
                                                'lastten': lastten,
                                                'lastimport': lastimport
                                            }
                                    )
    return render(request, 'stats.html', context=context)

def help(request):
    try:
        f = open(settings.SITE_ROOT + "/../README.md")
        helptxt = f.read()
        f.close()
    except:
        helptxt = "Unable to render help text."

    context = __createRequestContext__(data = {'help': helptxt})
    return render(request, 'help.html', context=context)

def about(request):
    context = __createRequestContext__()
    return render(request, 'about.html', context=context)
    

def advdomains(request):
    if request.method == "POST":
        search_f = advdomain_form(request.POST)
    elif request.method == "GET":
        search_f = advdomain_form(QueryDict(''))
        search_f.data['query'] = request.GET.get('query', None)
        search_f.data['fmt'] = request.GET.get('fmt','none')
        search_f.data['limit'] = request.GET.get('limit', settings.LIMIT)
        search_f.data['filt'] = request.GET.get('filt', settings.SEARCH_KEYS[0][0])
        search_f.data['unique'] = request.GET.get('unique', False)
    else:
        return __renderErrorResponse__(
                                        request,
                                        'domain.html',
                                        'Bad Method')

    if not search_f.is_valid():
        return __renderErrorResponse__(
                                        request,
                                        'domain.html',
                                        '',
                                        {'advdomain_form': search_f, 'legacy_search': False})

    fmt = search_f.cleaned_data['fmt'] or 'none'
    search_string = search_f.cleaned_data['query']
    query_unique = str(search_f.cleaned_data['unique']).lower()
    
    if fmt == 'none':
        context = __createRequestContext__(data = {'search_string': urllib.quote(search_string) or '',
                                                   'query_unique': query_unique,
                                                   'advdomain_form': search_f,
                                                   'legacy_search': False,
                                                   'fmt': fmt})

        return render(request, 'domain_results.html', context=context)
    else:
        filt_key = search_f.cleaned_data['filt']
        try:
            limit = int(search_f.cleaned_data.get('limit', settings.LIMIT))
        except:
            limit = settings.LIMIT

        filt = None
        if fmt == 'list': #Only filter if a list was requested
            filt = filt_key

        if query_unique == 'true':
            query_unique = True
        else:
            query_unique = False
        results = handler.advanced_search(
                                            search_string,
                                            0,
                                            limit,
                                            query_unique)
        if not results['success']:
            return __renderErrorResponse__(
                                            request,
                                            'domain.html',
                                            results['message'])

        if len(results['data']) == 0:
            return __renderErrorResponse__(request, 'domain.html', 'No results')

        if fmt =='json':
            data = [json.dumps(d) for d in results['data']]
        elif fmt == 'list':
            data = [d[filt_key] for d in results['data']]
        elif fmt == 'csv':
            raw_data = results['data']
            header_keys = set()
            for row in raw_data:
                header_keys = header_keys.union(set(row.keys()))
            csv_out = cStringIO.StringIO()
            writer = csv.DictWriter(csv_out, sorted(list(header_keys)))
            writer.writeheader()
            writer.writerows(raw_data)
            csv_data = csv_out.getvalue()
            csv_out.close()
            data = csv_data.split('\n')
        else:
            return __renderErrorResponse__(request,
                                           'domain.html',
                                           'Invalid Format')

        context = __createRequestContext__(data={'search_string': urllib.quote(search_string) or '',
                                                 'query_unique': str(query_unique).lower(),
                                                 'advdomain_form': search_f,
                                                 'legacy_search': False,
                                                 'fmt': fmt,
                                                 'data': data})

        return render(request, 'domain_results.html', context=context)


def domains(request, key=None, value=None):
    if request.method == "POST":
        search_f = domain_form(request.POST)

    elif request.method == "GET":
        search_f = domain_form(QueryDict(''))
        search_f.data['key'] = key
        search_f.data['value'] = value
        search_f.data['fmt'] = request.GET.get('fmt','normal')
        search_f.data['limit'] = request.GET.get('limit', settings.LIMIT)
        search_f.data['filt'] = request.GET.get('filt', settings.SEARCH_KEYS[0][0])
        search_f.data['latest'] = request.GET.get('latest', False)

    else:
        return __renderErrorPage__(request, 'Bad Method.')

    if not search_f.is_valid():
        return __renderErrorResponse__(request, 'domain.html', '', {'domain_form': search_f})

    key = urllib.unquote(search_f.cleaned_data['key'])
    value = urllib.unquote(search_f.cleaned_data['value'])

    filt_key = search_f.cleaned_data['filt']
    fmt = search_f.cleaned_data['fmt']
    limit = int(search_f.cleaned_data.get('limit', settings.LIMIT))
    latest = search_f.cleaned_data['latest']

    if latest:
        low_version = handler.lastVersion()
        high_version = low_version
    else:
        low_version = None
        high_version = None
    
    filt = None
    if fmt == 'list': #Only filter if a list was requested
        filt = filt_key

    #All web searches are AJAXy
    if fmt == "normal":
        low_version_js = low_version
        high_version_js = high_version
        if low_version == None:
            low_version_js = 'null'
        if high_version == None:
            high_version_js = 'null'
        context = __createRequestContext__(data = { 
                                                'key': urllib.quote(key),
                                                'value': urllib.quote(value),
                                                'low_version': low_version_js,
                                                'high_version': high_version_js,
                                                'domain_form': search_f,
                                                'legacy_search': True,}
                                          )
        return render(request,'domain_results.html', context=context)


    else:
        results = handler.search(key, value, filt=filt, limit=limit, low = low_version)
        if results['success'] == False:
            return __renderErrorPage__(request, results['message'])
        if fmt == 'json':
            return HttpResponse(json.dumps(results), content_type='application/json')
        elif fmt == 'list':
            data = '\n'.join([d[filt_key] for d in results['data']])
            return HttpResponse(data, content_type='text/plain')
        else:
            return __renderErrorPage__(request, 'Invalid Format.')
        

def pdns(request, search_value=None):
    if request.method == 'POST':
        pdns_f_dyn = pdns_form_dynamic(request.POST)
    elif request.method == 'GET':
        pdns_f_dyn = pdns_form_dynamic(QueryDict(''))
        pdns_f_dyn.data['search_value'] = search_value
        pdns_f_dyn.data['result_format'] = request.GET.get('result_format', 'none')

        # Filling form with all empty fields for a forward passive-DNS request
        for passive_field in passive.PDNS_UI_FIELDS_BASE + passive.PDNS_UI_FIELDS_FORWARD:
            pdns_f_dyn.data[passive_field.django_field_name] = request.GET.get(
                passive_field.django_field_name,
                passive_field.field_value_default)

    else:
        return __renderErrorResponse__(request,
                                       'pdns.html',
                                       'Bad Method')

    if not pdns_f_dyn.is_valid():
        return __renderErrorResponse__(request,
                                   'pdns.html',
                                   'Unable to verify form data',
                                    data = {"passive_form": pdns_f_dyn})
    
    # Get clean values for all common passive form fields
    search_value = pdns_f_dyn.cleaned_data['search_value']
    result_format = pdns_f_dyn.cleaned_data['result_format']


    dynamic_fields = {}
    # Obtain cleaned data for every passive-DNS field
    for passive_field in passive.PDNS_UI_FIELDS_BASE + passive.PDNS_UI_FIELDS_FORWARD:
        if passive_field.source_name not in dynamic_fields:
            dynamic_fields[passive_field.source_name] = {}

        cleaned_value = pdns_f_dyn.cleaned_data[passive_field.django_field_name]
        # If user did not enter a required field, grab a defined default value
        if not cleaned_value:
            cleaned_value = passive_field.field_value_default

        dynamic_fields[passive_field.source_name][passive_field.field_key] = cleaned_value

    results = passive.request_pdns(search_value, result_format, dynamic_fields)

    if not results['success']:
        return __renderErrorResponse__(request,
                                       'pdns.html',
                                       results['error'],
                                       data = {'passive_form': pdns_f_dyn ,})

    context = __createRequestContext__(data={'results': results['responses'],
                                             'inverse': False,
                                             'pdns_form_dynamic': pdns_f_dyn,
                                             'fmt': result_format})

    return render(request, 'pdns_results.html', context=context)


def pdns_r(request, search_value = None, search_value_type = None):
    if request.method == 'POST':
        rpdns_f_dyn = rpdns_form_dynamic(request.POST)
    elif request.method == 'GET': # Craft a form to make it easier to validate
        rpdns_f_dyn = rpdns_form_dynamic(QueryDict(''))
        rpdns_f_dyn.data['search_value']= search_value
        rpdns_f_dyn.data['result_format'] = request.GET.get('result_format','none')

        # Filling form with all empty fields for a reverse passive-DNS request
        for passive_field in passive.PDNS_UI_FIELDS_BASE + passive.PDNS_UI_FIELDS_REVERSE:
            rpdns_f_dyn.data[passive_field.django_field_name] = request.GET.get(
                passive_field.django_field_name,
                passive_field.field_value_default)
    else:
        return __renderErrorResponse__(request,
                                      'rpdns.html',
                                      'Unsupported Method')

    if not rpdns_f_dyn.is_valid():
        return __renderErrorResponse__(request,
                                       'rpdns.html',
                                       'Unable to verify form data',
                                        data={'passive_form': rpdns_f_dyn})

    # Get clean values for all common reverse passive form fields
    search_value = rpdns_f_dyn.cleaned_data['search_value']
    result_format = rpdns_f_dyn.cleaned_data['result_format']
  
    dynamic_fields = {}
    # Obtain cleaned data for every reverse passive-DNS field
    for passive_field in passive.PDNS_UI_FIELDS_BASE + passive.PDNS_UI_FIELDS_REVERSE:
        if passive_field.source_name not in dynamic_fields:
            dynamic_fields[passive_field.source_name] = {}

        cleaned_value = rpdns_f_dyn.cleaned_data[passive_field.django_field_name]
        # If user did not enter a required field, grab field defined default value
        if not cleaned_value:
           cleaned_value = passive_field.field_value_default

        dynamic_fields[passive_field.source_name][passive_field.field_key] = cleaned_value

    results = passive.request_pdns_reverse(search_value, result_format, dynamic_fields)

    if not results['success']:
        return __renderErrorResponse__(request,
                                       'rpdns.html',
                                       results['error'],
                                       data = {'rpdns_form_dynamic': rpdns_f_dyn})

    context = __createRequestContext__(data={'results': results['responses'],
                                             'inverse': True,
                                             'rpdns_form_dynamic': rpdns_f_dyn,
                                             'fmt': result_format})

    return render(request,'rpdns_results.html', context=context)
