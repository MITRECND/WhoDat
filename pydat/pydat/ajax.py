import json
import socket

from django.conf import settings
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, HttpResponse
import urllib

from pydat.handlers import handler

def __renderErrorJSON__(message):
    context = {'success': False,
               'error': message
              }
    return HttpResponse(json.dumps(context), content_type='application/json') 


def metadata(request, version = None):
    results = handler.metadata(version)

    if results['success'] == False:
        return __renderErrorJSON__(results['message'])

    return HttpResponse(json.dumps(results), content_type='application/json')


def dataTable(request, key, value, low = None, high = None):
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
        sSearch = request.GET.get('sSearch', '')

        sort = []
        for x in range(sortcols):
            sortTuple = handler.formatSort(int(request.GET.get("iSortCol_%d" % x)), 
                                                request.GET.get("sSortDir_%d" % x))
            if sortTuple is not None:
                sort.append(sortTuple)

    else:
        return __renderErrorJSON__('Unsupported Method')

    if (len(sSearch) == 0):
        sSearch = None

    results = handler.dataTableSearch(key, value, page, pagesize, sort, sSearch, low, high)
    #Echo back the echo
    results['sEcho'] = sEcho
    
    return HttpResponse(json.dumps(results), content_type='application/json')

def domains_latest(request, key, value):
    return domains(request, key, value, low = handler.lastVersion())

def domains(request, key, value, low = None, high = None):
    if key is None or value is None:
        return __renderErrorJSON__('Missing Key and/or Value')

    if key not in [keys[0] for keys in settings.SEARCH_KEYS]:
        return __renderErrorJSON__('Invalid Key')


    key = urllib.unquote(key)
    value = urllib.unquote(value)
    
    #TODO Support Post -- need to add cooresponding form
    if request.method == "GET":
        limit = int(request.GET.get('limit', settings.LIMIT))
    else:
        return __renderErrorJSON__('Unsupported Method')

    versionSort = False
    if key == 'domainName':
        versionSort = True

    results = handler.search(key, value, filt = None, low = low, high = high, versionSort = versionSort)
    if results['success'] == False:
        return __renderErrorJSON__(results['message'])

    return HttpResponse(json.dumps(results), content_type='application/json')

def domain_latest(request, domainName):
    return domain(request, domainName, low = handler.lastVersion());

def domain(request, domainName = None, low = None, high = None):
    if request.method == "GET":
        if not domainName:
            return __renderErrorJSON__('Requires Domain Name Argument')
        domainName = urllib.unquote(domainName)

        results = handler.search('domainName', domainName, filt=None, low = low, high = high, versionSort = True)

        return HttpResponse(json.dumps(results), content_type='application/json')
        if results['success']: #Clean up the data
            results['data'] = results['data'][0]
            del results['total']
            del results['avail']
            return HttpResponse(json.dumps(results), content_type='application/json')
        else:
            return __renderErrorJSON__(results['message'])
    else:
        return __renderErrorJSON__('Bad Method.')

def domain_diff(request, domainName = None, v1 = None, v2 = None):
    if request.method == "GET":
        if not domainName or not v1 or not v2:
            return __renderErrorJSON__('Required Parameters Missing')
        domainName = urllib.unquote(domainName)

        v1_res = handler.search('domainName', domainName, filt=None, low = int(v1))
        v2_res = handler.search('domainName', domainName, filt=None, low = int(v2))

        try:
            v1_res = v1_res['data'][0]
            v2_res = v2_res['data'][0]
        except:
            return __renderErrorJSON__("Did not find results")

        keylist = set(v1_res.keys()).union(set(v2_res.keys()))

        keylist.remove('Version')
        keylist.remove('domainName')

        output = {}
        for key in keylist: 
            if key in v1_res and key in v2_res:
                if v1_res[key] == v2_res[key]:
                    output[key] = v1_res[key] 
                else:
                    output[key] = [v1_res[key], v2_res[key]]
            else:
                try:
                    output[key] = [v1_res[key], '']
                except:
                    output[key] = ['', v2_res[key]]
        
        output['success'] = True 
        return HttpResponse(json.dumps(output), content_type='application/json')
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
