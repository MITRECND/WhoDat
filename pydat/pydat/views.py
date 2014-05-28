import json
import socket

from django.conf import settings
from django.template import RequestContext
from django.shortcuts import render_to_response, HttpResponse
from django.http import QueryDict
import urllib

from pydat.forms import domain_form, pdns_form, pdns_r_form, validate_ip, validate_hex
from pydat.handlers import do_search, do_pdns, do_pdns_r


def __renderErrorPage__(request, message, data = None):
    d = {'error' : message}
    if data is not None:
        d.update(data)

    context = __createRequestContext__(request, d)
    return render_to_response('error.html', context)

def __createRequestContext__(request, data = None):
    #Default to adding search forms to every context
    search_f = domain_form()
    pdns_f = pdns_form()
    pdns_r_f = pdns_r_form()
   
    ctx_var = { 'domain_form' : search_f,
                'pdns_form': pdns_f,
                'pdns_r_form': pdns_r_f,
              } 

    if data is not None:
        ctx_var.update(data)
        if 'active' not in data:
            if 'pdns_form' in data:
                ctx_var['active'] = 1
            elif 'pdns_r_form' in data:
                ctx_var['active'] = 2
            else:
                ctx_var['active'] = 0

    return RequestContext(request, ctx_var)

def index(request):
    context = __createRequestContext__(request)
    return render_to_response('index.html', context)

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

    else:
        return __renderErrorPage__(request, 'Bad Method.')

    if not search_f.is_valid():
        return __renderErrorPage__(request, '', {'domain_form' : search_f})

    key = urllib.unquote(search_f.cleaned_data['key'])
    value = urllib.unquote(search_f.cleaned_data['value'])

    filt_key = search_f.cleaned_data['filt']
    fmt = search_f.cleaned_data['fmt']
    limit = int(search_f.cleaned_data.get('limit', settings.LIMIT))

    if fmt == 'list': #Only filter if a list was requested
        filt = {filt_key: 1, '_id': False}
    else:
        filt = {'_id': False}


    #All web searches are AJAXy
    if fmt == "normal":
        context = __createRequestContext__(request, data = { 'key': urllib.quote(key),
                                                             'value': urllib.quote(value),
                                                             'domain_form': search_f,
               })
        return render_to_response('domain.html', context)

    else:
        if key == "registrant_telephone":
            value = int(value)

        results = do_search(key, value, filt=filt, limit=limit)
        if results['success'] == False:
            return __renderErrorPage__(request, results['message'])
        if fmt == 'json':
            return HttpResponse(json.dumps(results), content_type='application/json')
        elif fmt == 'list':
            data = '\n'.join([d[filt_key] for d in results['data']])
            return HttpResponse(data, content_type='text/plain')
        else:
            return __renderErrorPage__(request, 'Invalid Format.')
        

def pdns(request, domain = None):
    if request.method == 'POST':
        pdns_f = pdns_form(request.POST)
    elif request.method == 'GET':
        pdns_f = pdns_form(QueryDict(''))
        pdns_f.data['domain'] = domain
        pdns_f.data['limit'] = request.GET.get('limit', settings.DNSDB_PAGE_LIMITS[settings.DNSDB_PAGE_LIMIT_DEFAULT])
        pdns_f.data['rrtypes'] = request.GET.getlist('rrtypes', [settings.RRTYPE_KEYS[0][0]])
        pdns_f.data['fmt'] = request.GET.get('fmt', 'normal')
        pdns_f.data['absolute'] = request.GET.get('absolute', False)
        pdns_f.data['pretty'] = request.GET.get('pretty', True)
        pdns_f.data['filt'] = request.GET.get('filt', 'rrname')

    else:
        return __renderErrorPage__(request, 'Bad Method')
    

    if not pdns_f.is_valid():
        return __renderErrorPage__(request, '', {'pdns_form': pdns_f})

    domain = pdns_f.cleaned_data['domain']
    fmt = pdns_f.cleaned_data['fmt']
    absolute = pdns_f.cleaned_data['absolute']
    limit = pdns_f.cleaned_data['limit']
    rrtypes = pdns_f.cleaned_data['rrtypes']
    pretty = pdns_f.cleaned_data['pretty']
    filt_key = pdns_f.cleaned_data['filt']

    if limit is None:
        limit = settings.DNSDB_PAGE_LIMITS[settings.DNSDB_PAGE_LIMIT_DEFAULT]

    if absolute is None:
        absolute = False

    results = do_pdns(domain, absolute, rrtypes, limit, pretty)
    if fmt == 'normal':
        if results['success']:
            context = __createRequestContext__(request, {'results': results,
                                                         'inverse': False,
                                                         'pdns_form': pdns_f,
                                                        })
            return render_to_response('pdns.html', context)
        else:
            return __renderErrorPage__(request, results['error'], {'pdns_form': pdns_f})
    elif fmt == 'json':
        return HttpResponse(json.dumps(results), content_type='application/json')
    elif fmt == 'list':
        data = ''
        for rrtype in results['data'].keys():
            for record in results['data'][rrtype]:
                if not isinstance(record[filt_key], basestring): #it's a list
                    for item in record[filt_key]:
                        data += '\n%s' % item
                else: #it's just a string
                    data += '\n%s' % record[filt_key]
        data = data[1:]
        return HttpResponse(data, content_type='text/plain')
    else:
        return __renderErrorPage__(request, 'Invalid Format.')

def pdns_r(request, key = None, value = None):
    if request.method == 'POST':
        pdns_r_f = pdns_r_form(request.POST)
    elif request.method == 'GET': #Craft a form to make it easier to validate
        pdns_r_f = pdns_r_form(QueryDict(''))
        pdns_r_f.data['key'] = key
        pdns_r_f.data['value']= value
        pdns_r_f.data['rrtypes'] = request.GET.getlist('rrtypes', [settings.RRTYPE_KEYS[0][0]])
        pdns_r_f.data['fmt'] = request.GET.get('fmt','normal')
        pdns_r_f.data['limit'] = request.GET.get('limit', settings.DNSDB_PAGE_LIMITS[settings.DNSDB_PAGE_LIMIT_DEFAULT])
        pdns_r_f.data['pretty'] = request.GET.get('pretty', True)
        pdns_r_f.data['filt'] = request.GET.get('filt', 'rrname')
    else:
        return __renderErrorPage__(request, 'Unsupported Method.')

    if not pdns_r_f.is_valid():
        return __renderErrorPage__(request, '', {'pdns_r_form' : pdns_r_f})

    key = pdns_r_f.cleaned_data['key']
    value = pdns_r_f.cleaned_data['value']
    fmt = pdns_r_f.cleaned_data['fmt']
    limit = pdns_r_f.cleaned_data['limit']
    pretty = pdns_r_f.cleaned_data['pretty']
    filt_key = pdns_r_f.cleaned_data['filt']
    rrtypes = pdns_r_f.cleaned_data['rrtypes']


    if limit is None:
        limit = settings.DNSDB_PAGE_LIMITS[settings.DNSDB_PAGE_LIMIT_DEFAULT]

    results = do_pdns_r(key, value, rrtypes, limit, pretty)
    if fmt == 'normal':
        if results['success']:
            context = __createRequestContext__(request, {'results': results, 'inverse': True, 'pdns_r_form': pdns_r_f})
            return render_to_response('pdns.html', context)
        else:
            return __renderErrorPage__(request, results['error'], {'pdns_r_form':pdns_r_f})
    elif fmt == 'json':
        return HttpResponse(json.dumps(results), content_type='application/json')
    elif fmt == 'list':
        data = ''
        for rrtype in results['data'].keys():
            for record in results['data'][rrtype]:
                if not isinstance(record[filt_key], basestring): #it's a list
                    for item in record[filt_key]:
                        data += '\n%s' % item
                else: #it's just a string
                    data += '\n%s' % record[filt_key]
        data = data[1:]
        return HttpResponse(data, content_type='text/plain')
    else:
        return __renderErrorPage__(request, 'Invalid Format.')
