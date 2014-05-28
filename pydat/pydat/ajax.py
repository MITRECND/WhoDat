import json
import socket

from django.conf import settings
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, HttpResponse
import urllib

from pydat.handlers import do_search, ajax_search, sort_lookup


def __renderErrorJSON__(message):
    context = {'success': False,
               'error': message
              }
    return HttpResponse(json.dumps(context), content_type='application/json') 

def domains(request, key, value):
    if not request.is_ajax():
        return __renderErrorJSON__('Expected AJAX')

    if key is None or value is None:
        return __renderErrorJSON__('Missing Key and/or Value')

    if key not in [keys[0] for keys in settings.SEARCH_KEYS]:
        return __renderErrorJSON__('Invalid Key')

    key = urllib.unquote(key)
    value = urllib.unquote(value)
    
    #TODO Support Post -- need to add cooresponding form
    if request.method == "GET":
        page = int(request.GET.get('iDisplayStart', 0))
        pagesize = int(request.GET.get('iDisplayLength', 50))
        sortcols = int(request.GET.get('iSortingCols', 0))
        sEcho = request.GET.get('sEcho')
        sSearch = request.GET.get('sSearch', None)

        sort = []
        for x in range(sortcols):
            (sort_key, sort_dir) = sort_lookup(int(request.GET.get("iSortCol_%d" % x)), 
                                                request.GET.get("sSortDir_%d" % x))
            if sort_key is not None:
                sort.append((sort_key, sort_dir))

    else:
        return __renderErrorJSON__('Unsupported Method')

    if (len(sSearch) == 0):
        sSearch = None

    #XXX For some reason registrant_telephone needs to be treated as an integer
    #I'm assuming mongo consumed the value as an int since there's only numbers and
    #no symbols (such as () or -)
    if key == "registrant_telephone":
        value = int(value)

    results = ajax_search(key, value, page, pagesize, sort, sSearch)
    #Echo back the echo
    results['sEcho'] = sEcho
    
    return HttpResponse(json.dumps(results), content_type='application/json')

def domain(request, domainName = None):
    if not request.is_ajax():
        return __renderErrorJSON__('Expected AJAX')

    if request.method == "GET":
        if not domainName:
            return __renderErrorJSON__('Requires Domain Name Argument')
        domainName = urllib.unquote(domainName)

        results = do_search('domainName', domainName, filt={'_id': False}, limit = 1)

        if results['success']: #Clean up the data
            results['data'] = results['data'][0]
            del results['total']
            del results['avail']
            return HttpResponse(json.dumps(results), content_type='application/json')
        else:
            return __renderErrorJSON__(results['message'])
    else:
        return __renderErrorJSON__('Bad Method.')

def resolve(request, domainName = None):
    if domainName is None:
        return __renderErrorJSON__('Domain Name Required')

    domainName = urllib.unquote(domainName)

    try:
        (hostname, aliaslist, iplist) = socket.gethostbyname_ex(domainName)
    except Exception as e:
        return __renderErrorJSON__(str(e))

    result = {'success': True,
              'aliases': aliaslist,
              'hostname': hostname,
              'ips': []
    }
    for ip in iplist:
        ipo = { 'ip' : ip,
                'url' : reverse('pdns_r_rest', args=("ip",ip,))
              }
        result['ips'].append(ipo)

    return HttpResponse(json.dumps(result), content_type='application/json')
