import cgi
import time
import json
import requests
import urllib
from django.conf import settings


def __request_pdns_dnsdb(domain, absolute, rrtypes, limit, pretty):
    results = {'success': False, 'type': 'DNSDB'}

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
            try:
                tmp = json.loads(line)
            except Exception as e:
                results['error'] = "%s: %s" % (str(e), cgi.escape(line, quote=True))
                return results
            # Convert epoch timestamps to human readable.
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

def __make_passivetotal_request(url, params):
    results = {'success': False}
    try:
        response = requests.get(url,
                                params=params,
                                proxies=settings.PROXIES)
    except Exception as e:
        results['error'] = "PassiveTotal: network connection error (%s)" % e
        return results

    if response.status_code != 200:
        results['error'] = "Response status code: %s" % response.status_code
        return results

    loaded = response.json()

    if not loaded['success']:
        results['error'] = "PassiveTotal: query error (%s)" % loaded['error']
        return results

    results['success'] = True
    results['results'] = loaded['results']
    return results

def __request_pdns_passivetotal(domain, absolute, rrtypes, limit, pretty):
    results = { 'success': False, 'type': 'PassiveTotal', 'subsets': [] }
    params = {'query': domain, 'api_key': settings.PASSIVETOTAL_KEY}
    url = 'https://www.passivetotal.org/api/v1/'

    data = __make_passivetotal_request(url + 'passive/', params)
    if data['success'] and len(data['results']) > 0:
        data = data['results']

        subset = { 'title': 'Unique Resolutions' }
        subset['data'] = data['unique_resolutions']
        results['subsets'].append(subset)

        enrichment = data['enrichment_map']

        # The records table columns change depending upon if the query is
        # for a domain or an IP. The common headers are listed here and
        # if others are encountered later they are appended.
        subset = { 'title': 'Records',
                   'headers': ['Resolution', 'First Seen', 'Last Seen'],
                   'data': [] }
        for record in data['records']:
            tmp = {}
            tmp['last_seen'] = record['lastSeen']
            tmp['first_seen'] = record['firstSeen']
            tmp['resolve'] = record['resolve']

            enrichment_record = enrichment[record['resolve']]
            # When searching for an IP the enrichment record has none of these
            # things.
            if 'network' in enrichment_record:
                if 'Network' not in subset['headers']:
                    subset['headers'].append('Network')
                tmp['network'] = enrichment_record['network']
            if 'as_name' in enrichment_record:
                if 'AS Name' not in subset['headers']:
                    subset['headers'].append('AS Name')
                tmp['as_name'] = enrichment_record['as_name']
            if 'asn' in enrichment_record:
                if 'AS Number' not in subset['headers']:
                    subset['headers'].append('AS Number')
                tmp['asn'] = enrichment_record['asn']

            subset['data'].append(tmp)

        results['subsets'].append(subset)
        results['success'] = True

    # Do the subdomain request if not absolute
    if not absolute:
        # Alter query parameter to be *.domain
        params['query'] = '*.' + params['query']
        data = __make_passivetotal_request(url + 'subdomains/', params)
        if data['success'] and len(data['results']) > 0:
            data = data['results']

            subset = { 'title': 'Subdomains', 'data': [] }
            for (subdomain, sub_data) in data['subdomains'].iteritems():
                enrichment = sub_data['enrichment']
                for entry in sub_data['records']:
                    tmp = {}
                    tmp['subdomain'] = subdomain + '.' + domain
                    tmp['last_seen'] = entry['lastSeen']
                    tmp['first_seen'] = entry['firstSeen']
                    tmp['resolve'] = entry['resolve']

                    enrichment_record = enrichment[entry['resolve']]
                    tmp['network'] = enrichment_record['network']
                    tmp['as_name'] = enrichment_record['as_name']
                    tmp['asn'] = enrichment_record['asn']

                    subset['data'].append(tmp)

            results['subsets'].append(subset)
            results['success'] = True

    return results

def request_pdns(domain, absolute, rrtypes, limit, pretty = False):
    results = {'success': False, 'sets': []}
    if not settings.DNSDB_HEADERS and not settings.PASSIVETOTAL_KEY:
        results['error'] = 'No external sources configured.'
        return results

    if settings.DNSDB_HEADERS:
        dnsdb_results = __request_pdns_dnsdb(domain,
                                             absolute,
                                             rrtypes,
                                             limit,
                                             pretty)
        results['sets'].append(dnsdb_results)

    if settings.PASSIVETOTAL_KEY:
        passivetotal_results = __request_pdns_passivetotal(domain,
                                                           absolute,
                                                           rrtypes,
                                                           limit,
                                                           pretty)
        # Note we searched for a domain.
        passivetotal_results['key'] = 'domain'
        results['sets'].append(passivetotal_results)

    # At least one of the passive handlers must be successful for
    # the entire thing to be successful.
    for set_ in results['sets']:
        if set_['success']:
            results['success'] = True
            return results

    results['error'] = "No passive data found."
    return results

def __request_pdns_reverse_dnsdb(key, value, rrtypes, limit, pretty):
    results = {'success': False, 'type': 'DNSDB'}
    results['data'] = {}
    for rrtype in rrtypes:
        url = "https://api.dnsdb.info/lookup/rdata/"+ key +"/" + urllib.quote(value) + "/" + rrtype + "?limit=" + str(limit)
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

            try:
                tmp = json.loads(line)
            except Exception as e:
                results['error'] = "%s: %s" % (str(e), cgi.escape(line, quote=True))
                return results

            # Convert epoch timestamps to human readable.
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

def __request_pdns_reverse_passivetotal(key, value, rrtypes, limit, pretty):
    # Same interface in PassiveTotal if you are querying a name or IP.
    results = __request_pdns_passivetotal(value, True, rrtypes, limit, pretty)

    # Store the key used when pivoting in the template.
    results['key'] = key

    return results

def request_pdns_reverse(key, value, rrtypes, limit, pretty = False):
    results = {'success': False, 'sets': []}

    if key not in [keys[0] for keys in settings.RDATA_KEYS]:
        results['error'] = 'Invalid key'
        return results

    if not settings.DNSDB_HEADERS:
        results['error'] = 'No DNSDB key.'
        return results

    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in rrtypes and len(rrtypes) >= 2:
        rrtypes = ['any']

    if settings.DNSDB_HEADERS:
        dnsdb_results = __request_pdns_reverse_dnsdb(key,
                                                     value,
                                                     rrtypes,
                                                     limit,
                                                     pretty)
        results['sets'].append(dnsdb_results)

    if settings.PASSIVETOTAL_KEY:
        passivetotal_results = __request_pdns_reverse_passivetotal(key,
                                                                   value,
                                                                   rrtypes,
                                                                   limit,
                                                                   pretty)
        results['sets'].append(passivetotal_results)

    for set_ in results['sets']:
        if set_['success']:
            results['success'] = True
            return results

    results['error'] = "No passive data found."
    return results
