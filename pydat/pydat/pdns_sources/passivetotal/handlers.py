'''
 Handler module for PassiveTotal source
     -handles requests that are made to the PassiveTotal API
     through 2 core functions (normal and reverse passive DNS requests)
'''

import json
import requests
from django.conf import settings


'''Method to allow for custom pdns requests handler for DNSDB as a
   pdns source. Note: method name must be "pdns_request_handler" 
'''
def pdns_request_handler(common_field_dict,
                         specific_field_dict,
                         pdns_var_dict):
    url = 'https://www.passivetotal.org/api/v1/'

    results = {
                'success': False,
                'subsets': [] }
    params = {
                'query': common_field_dict['domain'],
                'api_key': pdns_var_dict["PASSIVETOTAL_KEY"]}

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
            # When searching for an IP the enrichment record has none
            # of these things.
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
    if not specific_field_dict['absolute']:
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

    results['key']= "domain"

    return results




'''method to allow for custom pdns reverse requests
   handler for DNSDB as a pdns source.

   Note: the method name must be "pdns_reverse_request_handler"
'''
def pdns_reverse_request_handler(common_field_dict,
                                 specific_field_dict,
                                 pdns_var_dict):

    common_field_dict['domain'] = common_field_dict['search_value']
    # Same interface in PassiveTotal if you are querying a name or IP.
    results = pdns_request_handler(
                                    common_field_dict,
                                    specific_field_dict,
                                    pdns_var_dict)

    # Store the key used when pivoting in the template.
    results['key'] = common_field_dict['search_value_type']

    return results






def __make_passivetotal_request(url, params):
    results = {'success': False}
    try:
        response = requests.get(url,
                                params=params,
                                proxies=settings.PROXIES,
                                verify=settings.SSL_VERIFY)
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