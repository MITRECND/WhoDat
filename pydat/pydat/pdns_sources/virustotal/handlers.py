import cgi
import time
import json
import requests
import socket
import urllib
import cStringIO
import unicodecsv as csv
from django.conf import settings

from virustotal import config

from pydat.pdns_sources.dnsdb.handlers import validate_ip

def _format_results(results, fmt, dynamic_fields):
    if fmt =='json':
        data = [json.dumps(d) for d in results['data']]
        results['data'] = data
    elif fmt == 'list':
        filt_key = dynamic_fields['filter']
        data = [d[filt_key] for d in results['data']]
        results['data'] = data
    elif fmt == 'csv':
        compiled_data = []
        header_keys = set()
        for d in results['data']:
            compiled_data.append(d)
            header_keys = header_keys.union(set(d.keys()))

        csv_out = cStringIO.StringIO()
        writer = csv.DictWriter(csv_out, sorted(list(header_keys)))
        writer.writeheader()
        writer.writerows(compiled_data)
        csv_data = csv_out.getvalue()
        csv_out.close()
        data = csv_data.split('\n')
        results['data'] = data
    else:
        raise RuntimeError("Unrecognized format %s" % (fmt))

    return results

def pdns_request_handler(domain, result_format, **dynamic_fields):
    results = {'success': False }

    if not config.myConfig['apikey']:
        results['error'] = 'No VT key.'
        return results

    results['data'] = {}
    
    url = 'https://www.virustotal.com/vtapi/v2/domain/report'

    try:
        params = {'domain': domain, 'apikey': config.myConfig['apikey']}

        headers = {'Accept-Encoding': 'gzip, deflate',
                   "User-Agent": "gzip, test application"}

        r = requests.get(url,
                        proxies=settings.PROXIES,
                        headers=headers,
                        params=params,
                        verify=config.myConfig["ssl_verify"])
    except Exception as e:
            results['error'] = str(e)
            return results

    response_json = r.json()

    if response_json['response_code'] == 1:
        if result_format != 'none':
            results['data'] = response_json['resolutions']
            results = _format_results(results, result_format, dynamic_fields)
        else:
            results['data'] = response_json
    else:
        results['error'] = "Not found"
        return results

    results['success'] = True


    return results



def pdns_reverse_request_handler(search_value, result_format, **dynamic_fields):
    results = {'success': False}

    if not config.myConfig['apikey']:
        results['error'] = 'No VT key.'
        return results

    try:
        search_value = validate_ip(search_value)
    except Exception as e:
        results['error'] = str(e)
        return results

    results['data'] = {}
    url = 'https://www.virustotal.com/vtapi/v2/ip-address/report'
    try:
        params = {'ip': search_value, 'apikey': config.myConfig['apikey']}
        headers = {'Accept-Encoding': 'gzip, deflate',
                   "User-Agent": "gzip, test application"}

        r = requests.get(url,
                         proxies=settings.PROXIES,
                         headers=headers,
                         params=params,
                         verify=config.myConfig["ssl_verify"])
    except Exception as e:
        results['error'] = str(e)
        return results

    response_json = r.json()

    if response_json['response_code'] == 1:
        results['data'] = response_json['resolutions']
    else:
        results['error'] = "Not found"
        return results

    results['success'] = True

    if result_format != 'none':
        results = _format_results(results, result_format, dynamic_fields)

    return results

