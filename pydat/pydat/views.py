import json
import socket

from django.conf import settings
from django.template import RequestContext
from django.shortcuts import render_to_response, HttpResponse
from django.http import QueryDict
import urllib

from pydat.forms import domain_form, advdomain_form, pdns_form, pdns_r_form, validate_ip, validate_hex
from pydat.handlers import handler
from pydat.handlers import passive

def __renderErrorResponse__(request, view, message, data = None):
    d = {'error': message}
    if data is not None:
        d.update(data)

    context = __createRequestContext__(request, d)
    return render_to_response(view, context)
    

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
    advdomain_f = advdomain_form()

    ctx_var = { 'domain_form' : search_f,
                'advdomain_form': advdomain_f,
                'pdns_form': pdns_f,
                'pdns_r_form': pdns_r_f,
                'latest_version': handler.lastVersion(),
                'handler': settings.HANDLER
              } 

    if settings.HANDLER == 'es':
        ctx_var['health'] = handler.cluster_health().capitalize()
        ctx_var['record_count'] = handler.record_count()
        ctx_var['last_import'] = handler.lastVersion()

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
    if settings.HANDLER == 'es':
        legacy = False
    else:
        legacy = True
    context = __createRequestContext__(request, data = { 'legacy_search': legacy})
    return render_to_response('domain.html', context)

def pdns_index(request):
    context = __createRequestContext__(request)
    return render_to_response('pdns.html', context)

def rpdns_index(request):
    context = __createRequestContext__(request)
    return render_to_response('rpdns.html', context)

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

    context = __createRequestContext__(request, data = {'domainStats': stats['domainStats'], 
                                                        'histogram': stats['histogram'],
                                                        'lastten': lastten,
                                                        'lastimport': lastimport})
    return render_to_response('stats.html', context)

def help(request):
    try:
        f = open(settings.SITE_ROOT + "/../README.md")
        helptxt = f.read()
        f.close()
    except:
        helptxt = "Unable to render help text."

    context = __createRequestContext__(request, data = {'help': helptxt})
    return render_to_response('help.html', context)

def about(request):
    context = __createRequestContext__(request)
    return render_to_response('about.html', context)
    

def advdomains(request):
    if request.method == "POST":
        search_f = advdomain_form(request.POST)
    elif request.method == "GET":
        search_f = advdomain_form(QueryDict(''))
        search_f.data['query'] = request.GET.get('query', None)
        search_f.data['fmt'] = request.GET.get('fmt','normal')
        search_f.data['limit'] = request.GET.get('limit', settings.LIMIT)
        search_f.data['filt'] = request.GET.get('filt', settings.SEARCH_KEYS[0][0])
        search_f.data['unique'] = request.GET.get('unique', False)
    else:
        #return __renderErrorPage__(request, 'Bad Method')
        return __renderErrorResponse__(request, 'domain.html', 'Bad Method')

    if not search_f.is_valid():
        return __renderErrorResponse__(request, 'domain.html', '', {'advdomain_form': search_f, 'legacy_search': False})
        #return __renderErrorPage__(request, '', {'advdomain_form': search_f})
        #context = __createRequestContext__(request, data = { 'advdomain_form': search_f } )
        #return render_to_response('domain.html', context)

    fmt = search_f.cleaned_data['fmt'] or 'normal'
    search_string = search_f.cleaned_data['query']
    query_unique = str(search_f.cleaned_data['unique']).lower()

    
    if fmt == 'normal':
        context = __createRequestContext__(request, data = { 'search_string': urllib.quote(search_string) or '',
                                                             'query_unique': query_unique,
                                                             'advdomain_form': search_f,
                                                             'legacy_search': False,
               })

        return render_to_response('domain_results.html', context)
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
        results = handler.advanced_search(search_string, 0, limit, query_unique)
        if not results['success']:
            #return __renderErrorPage__(request, results['message'])
            return __renderErrorResponse__(request, 'domain.html', results['message'])
        if fmt=='json':
            return HttpResponse(json.dumps(results), content_type='application/json')
        elif fmt == 'list':
            data = '\n'.join([d[filt_key] for d in results['data']])
            return HttpResponse(data, content_type='text/plain')
        else:
            #return __renderErrorPage__(request, 'Invalid Format.')
            return __renderErrorResponse__(request, 'domain.html',  'Invalid Format')

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
        return __renderErrorResponse__(request, 'domain.html', '', {'domain_form' : search_f})

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
        context = __createRequestContext__(request, data = { 'key': urllib.quote(key),
                                                             'value': urllib.quote(value),
                                                             'low_version': low_version_js,
                                                             'high_version': high_version_js,
                                                             'domain_form': search_f,
                                                             'legacy_search': True,
               })
        return render_to_response('domain_results.html', context)

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

    results = passive.request_pdns(domain, absolute, rrtypes, limit, pretty)
    if fmt == 'normal':
        if results['success']:
            context = __createRequestContext__(request, {'results': results,
                                                         'inverse': False,
                                                         'pdns_form': pdns_f,
                                                        })
            return render_to_response('pdns_results.html', context)
        else:
            return __renderErrorPage__(request, results['error'], {'pdns_form': pdns_f})
    elif fmt == 'json':
        return HttpResponse(json.dumps(results), content_type='application/json')
    elif fmt == 'list':
        data = ''
        for set_ in results['sets']:
            # Only handle DNSDB in list format.
            if set_['type'] != 'DNSDB':
                continue
            for rrtype in set_['data'].keys():
                for record in set_['data'][rrtype]:
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

    results = passive.request_pdns_reverse(key, value, rrtypes, limit, pretty)
    if fmt == 'normal':
        if results['success']:
            context = __createRequestContext__(request, {'results': results, 'inverse': True, 'pdns_r_form': pdns_r_f})
            return render_to_response('pdns_results.html', context)
        else:
            return __renderErrorPage__(request, results['error'], {'pdns_r_form':pdns_r_f})
    elif fmt == 'json':
        return HttpResponse(json.dumps(results), content_type='application/json')
    elif fmt == 'list':
        data = ''
        for set_ in results['sets']:
            # Only handle DNSDB in list format.
            if set_['type'] != 'DNSDB':
                continue
            for rrtype in set_['data'].keys():
                for record in set_['data'][rrtype]:
                    if not isinstance(record[filt_key], basestring): #it's a list
                        for item in record[filt_key]:
                            data += '\n%s' % item
                    else: #it's just a string
                        data += '\n%s' % record[filt_key]
        data = data[1:]
        return HttpResponse(data, content_type='text/plain')
    else:
        return __renderErrorPage__(request, 'Invalid Format.')
