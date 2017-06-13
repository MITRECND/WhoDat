'''
pdns module for DNSDB 
    -obtains the 2 methods for handling passive and reverse-passive 
     requests to the dnsdb API
'''
import cgi
import time
import json
import requests
import urllib
from django.conf import settings



'''Method to allow for custom pdns requests handler for DNSDB as a pdns source
   Note: method name must be "pdns_request_handler" 
'''

def pdns_request_handler(common_field_dict,
                         specific_field_dict,
                         pdns_var_dict):
    results = {'success': False }

    if not pdns_var_dict["dnsdb_headers"]:
        results['error'] = 'No DNSDB key.'
        return results

    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in specific_field_dict['rrtypes'] and len(specific_field_dict['rrtypes']) >= 2:
        specific_field_dict['rrtypes'] = ['any']

    results['data'] = {}
    wildcard = "*."
    
    if specific_field_dict['absolute']:
        wildcard = ""
    for rrtype in specific_field_dict['rrtypes']:
        url = "https://api.dnsdb.info/lookup/rrset/name/" \
                + wildcard \
                + urllib.quote(common_field_dict['domain']) + "/" \
                + rrtype \
                + "/?limit=" + str(specific_field_dict['limit'])
        try:
            r = requests.get(url,
                            proxies=settings.PROXIES,
                            headers=pdns_var_dict["dnsdb_headers"],
                            verify=pdns_var_dict["ssl_verify"]
                )
        except Exception as e:
                results['error'] = str(e)
                print ("external request didntwork")
                return results
        # Each line of the response is an individual JSON blob.
        for line in r.text.split('\n'):
            # Skip empty lines.
            if not line:
                continue
            try:
                tmp = json.loads(line)
            except Exception as e:
                results['error'] = "%s: %s" % (
                                                str(e),
                                                cgi.escape(line, quote=True))
                return results
                    # Convert epoch timestamps to human readable.
            for key in ['time_first', 'time_last']:
                if key in tmp:
                    tmp[key] = time.strftime("%Y-%m-%d %H:%M:%S",
                                             time.gmtime(tmp[key]))
            rrtype = tmp['rrtype']
            # Strip the MX weight.
            if rrtype == 'MX':
                tmp['rdata'] = [rd.split()[1] for rd in tmp['rdata']]

            if pdns_var_dict['pretty']:
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

    #additional formatting-if user desired format is list format
    filt_key = specific_field_dict['filter']
    if common_field_dict['result_format'] == "list":
        data = ''
        for rrtype in results['data'].keys():
            for record in results['data'][rrtype]:
                if not isinstance(record[filt_key], basestring): #it's a list
                    for item in record[filt_key]:
                        data += '\n%s' % item
                else: #it's just a string
                    data += '\n%s' % record[filt_key]
        data = data[1:]
        results['data'] = data

    return results



'''method to allow for custom pdns reverse requests handler
   for DNSDB as a pdns source

   Note: the method name must be "pdns_reverse_request_handler"
'''
def pdns_reverse_request_handler(common_field_dict,
                                 specific_field_dict,
                                 pdns_var_dict):
    results = {'success': False}
    if not pdns_var_dict["dnsdb_headers"]:
        results['error'] = 'No DNSDB key.'
        return results
  
    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in specific_field_dict['rrtypes'] and len(specific_field_dict['rrtypes']) >= 2:
        specific_field_dict['rrtypes'] = ['any']

    results['data'] = {}
    for rrtype in specific_field_dict['rrtypes']:
        url = "https://api.dnsdb.info/lookup/rdata/" \
                + common_field_dict['search_value_type'] +"/" \
                + urllib.quote(common_field_dict['search_value'])  + "/" \
                + rrtype \
                + "?limit=" + str(specific_field_dict['limit'])
        try:
            r = requests.get(url,
                             proxies=settings.PROXIES,
                             headers=pdns_var_dict["dnsdb_headers"],
                             verify=pdns_var_dict["ssl_verify"])
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
                results['error'] = "%s: %s" % (
                                                str(e),
                                                 cgi.escape(line, quote=True))
                return results

            # Convert epoch timestamps to human readable.
            for key in ['time_first', 'time_last']:
                if key in tmp:
                    tmp[key] = time.strftime("%Y-%m-%d %H:%M:%S",
                                             time.gmtime(tmp[key]))

            rrtype = tmp['rrtype']
            #Strip the MX weight
            if rrtype == 'MX':
                tmp['rdata'] = [tmp['rdata'].split()[1]]
            else:
                tmp['rdata'] = [tmp['rdata']]

            if pdns_var_dict['pretty']:
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

    #additional formatting-if user desired format is list format
    filt_key = specific_field_dict['filter']
    if common_field_dict['result_format'] == "list":
        data = ''
        for rrtype in results['data'].keys():
            for record in results['data'][rrtype]:
                if not isinstance(record[filt_key], basestring): #it's a list
                    for item in record[filt_key]:
                        data += '\n%s' % item
                else: #it's just a string
                    data += '\n%s' % record[filt_key]
        data = data[1:]
        results['data'] = data

    return results
            