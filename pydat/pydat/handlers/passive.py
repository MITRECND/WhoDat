import time
import json
import requests
import urllib
from django.conf import settings


def request_pdns(domain, absolute, rrtypes, limit, pretty = False):
    results = {'success': False}
    if not settings.DNSDB_HEADERS:
        results['error'] = 'No DNSDB key.'
        return results

    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in rrtypes and len(rrtypes) >= 2:
        rrtypes = ['any']

    results['data'] = {}
    
    wildcard = "*."
    if absolute:
        wildcard = ""
    for rrtype in rrtypes:
        url = "https://api.dnsdb.info/lookup/rrset/name/"+ wildcard + urllib.quote(domain) + "/" + rrtype + "/?limit=" + str(limit)
        try:
            r = requests.get(url,
                             proxies=settings.PROXIES,
                             headers=settings.DNSDB_HEADERS,
                             verify=settings.SSL_VERIFY)
        except Exception as e:
            results['error'] = str(e)
            return results

        # Each line of the response is an individual JSON blob.
        for line in r.text.split('\n'):
            # Skip empty lines.
            if not line:
                continue
            # Convert epoch timestamps to human readable.
            try:
              tmp = json.loads(line)
            except Exception as e:
              results['error'] = str(e)
              return results
            for key in ['time_first', 'time_last']:
                if key in tmp:
                    tmp[key] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(tmp[key]))
            rrtype = tmp['rrtype']
            # Strip the MX weight.
            if rrtype == 'MX':
                tmp['rdata'] = [rd.split()[1] for rd in tmp['rdata']]

            if pretty:
                if tmp['rrname'][-1] == ".":
                    tmp['rrname'] = tmp['rrname'][:-1] 
                for i in range(len(tmp['rdata'])):
                    if tmp['rdata'][i][-1] == ".":
                        tmp['rdata'][i] = tmp['rdata'][i][:-1]

            try:
                results['data'][rrtype].append(tmp)
            except KeyError:
                results['data'][rrtype] = [tmp]

    results['success'] = True
    return results


def request_pdns_reverse(key, value, rrtypes, limit, pretty = False):
    results = {'success': False}

    if key not in [keys[0] for keys in settings.RDATA_KEYS]:
        results['error'] = 'Invalid key'
        return results

    if not settings.DNSDB_HEADERS:
        results['error'] = 'No DNSDB key.'
        return results

    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in rrtypes and len(rrtypes) >= 2:
        rrtypes = ['any']

    results['data'] = {}
    for rrtype in rrtypes:
        url = "https://api.dnsdb.info/lookup/rdata/"+ key +"/" + urllib.quote(value) + "/" + rrtype + "/?limit=" + str(limit)
        try:
            r = requests.get(url,
                             proxies=settings.PROXIES,
                             headers=settings.DNSDB_HEADERS,
                             verify=settings.SSL_VERIFY)
        except Exception as e:
            results['error'] = str(e)
            return results

        # Each line of the response is an individual JSON blob.
        for line in r.text.split('\n'):
            # Skip empty lines.
            if not line:
                continue
            # Convert epoch timestamps to human readable.
            tmp = json.loads(line)
            for key in ['time_first', 'time_last']:
                if key in tmp:
                    tmp[key] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(tmp[key]))
            rrtype = tmp['rrtype']
            #Strip the MX weight
            if rrtype == 'MX':
                tmp['rdata'] = [tmp['rdata'].split()[1]]
            else:
                tmp['rdata'] = [tmp['rdata']]

            if pretty:
                if tmp['rrname'][-1] == ".":
                    tmp['rrname'] = tmp['rrname'][:-1] 
                for i in range(len(tmp['rdata'])):
                    if tmp['rdata'][i][-1] == ".":
                        tmp['rdata'][i] = tmp['rdata'][i][:-1]

            try:
                results['data'][rrtype].append(tmp)
            except KeyError:
                results['data'][rrtype] = [tmp]

    results['success'] = True
    return results
