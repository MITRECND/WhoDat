'''
pdns module for DNSDB 
    -obtains the 2 methods for handling passive and reverse-passive 
     requests to the dnsdb API
'''
import cgi
import time
import json
import requests
import socket
import urllib
import cStringIO
import unicodecsv as csv
from django.conf import settings

from dnsdb import config

def _format_results(results, fmt, dynamic_data):
    if fmt =='json':
        data = []
        for rrtype in results['data']:
            for d in results['data'][rrtype]:
                data.append(json.dumps(d))
        results['data'] = data
    elif fmt == 'list':
        filt_key = dynamic_data['filter']
        data = []
        for rrtype in results['data'].keys():
            for record in results['data'][rrtype]:
                if not isinstance(record[filt_key], basestring): #it's a list
                    data.extend(record[filt_key])
                else: #it's just a string
                    data.append(record[filt_key])
        data = list(set(data[1:]))
        results['data'] = data
    elif fmt == 'csv':
        DEFAULT_KEYS = ['rrtype',
                        'rrname',
                        'rdata',
                        'bailiwick',
                        'count',
                        'time_first',
                        'time_last',
                        'zone_time_first',
                        'zone_time_last']
        compiled_data = []
        header_keys = set()
        for rrtype in results['data']:
            for d in results['data'][rrtype]:
                compiled_data.append(d)
                header_keys = header_keys.union(set(d.keys()))

        header_keys = sorted(list(header_keys))
        if sorted(DEFAULT_KEYS) == header_keys:
            header_keys = DEFAULT_KEYS
        csv_out = cStringIO.StringIO()
        writer = csv.DictWriter(csv_out, header_keys)
        writer.writeheader()
        writer.writerows(compiled_data)
        csv_data = csv_out.getvalue()
        csv_out.close()
        data = csv_data.split('\n')
        results['data'] = data
    else:
        raise RuntimeError("Unrecognized format %s" % (fmt))

    return results

def validate_ip(input_ip):
    ip = ""
    mask = None
    version = 4
    if input_ip.count("/") > 0:
        if input_ip.count("/") > 1:
            raise TypeError("Invalid IP Syntax")
        (ip, mask) = input_ip.split("/")
    else:
        ip = input_ip

    #Validate ip part
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        version = 6
    except: #invalid ipv6
        try:
            socket.inet_pton(socket.AF_INET, ip)
        except Exception, e:
            raise TypeError("Invalid IP Address")

    output_ip = ip
    #Validate mask if present
    if mask is not None:
        try:
            mask = int(mask)
            if mask < 1:
                raise ValueError("Mask must be at least 1")
            elif version == 4 and mask > 32:
                raise ValueError("IP Mask too large for v4")
            elif version == 6 and mask > 128:
                raise ValueError("IP Mask too large for v6")
        except:
            raise TypeError("Unable to process mask")
        output_ip += ",%d" % mask
    return output_ip

def validate_hex(input_hex):
    try:
        output_hex = "%x" % int(input_hex, 16)
    except:
        raise TypeError("Not hex")

    if len(output_hex) % 2 == 1: #make hex string always pairs of hex values
        output_hex = "0" + output_hex

    return output_hex

def _verify_type(value, type):
    if type == 'ip':
        try:
            value = validate_ip(value)
        except Exception as e:
            raise TypeError("Unable to verify search value as ip")
    elif type == 'name':
        if isinstance(value, unicode):
            value = value.encode("idna")
    elif type == 'raw':
        try:
            value = validate_hex(value)
        except Exception as e:
            raise TypeError("Unable to verify type as hex")
    else:
        raise RuntimeError("Unexpected type")

    return value


def pdns_request_handler(domain, result_format, **dynamic_data):
    results = {'success': False }

    if not config.myConfig['apikey']:
        results['error'] = 'No DNSDB key.'
        return results

    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in dynamic_data['rrtypes']:
        dynamic_data['rrtypes'] = ['any']

    results['data'] = {}
    wildcard = "*."
    
    if dynamic_data['absolute']:
        wildcard = ""

    for rrtype in dynamic_data['rrtypes']:
        url = "https://api.dnsdb.info/lookup/rrset/name/" \
                + wildcard \
                + urllib.quote(domain) + "/" \
                + rrtype \
                + "/?limit=" + str(dynamic_data['limit'])
        try:
            headers = {'Accept': 'application/json',
                       'X-API-Key': config.myConfig['apikey']}
            r = requests.get(url,
                            proxies=settings.PROXIES,
                            headers=headers,
                            verify=config.myConfig["ssl_verify"])
        except Exception as e:
                results['error'] = str(e)
                return results

        if r.status_code != 404:
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

                if result_format in ['none', 'list']:
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

    if result_format != 'none':
        results = _format_results(results, result_format, dynamic_data)

    return results



'''method to allow for custom pdns reverse requests handler
   for DNSDB as a pdns source

   Note: the method name must be "pdns_reverse_request_handler"
'''
def pdns_reverse_request_handler(search_value, result_format, **dynamic_fields):
    results = {'success': False}

    if not config.myConfig['apikey']:
        results['error'] = 'No DNSDB key.'
        return results

    try:
       value = _verify_type(search_value, dynamic_fields['type'])
    except Exception as e:
        results['error'] = 'Unable to verify input'
        return results
  
    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in dynamic_fields['rrtypes']:
        dynamic_fields['rrtypes'] = ['any']

    results['data'] = {}
    for rrtype in dynamic_fields['rrtypes']:
        url = "https://api.dnsdb.info/lookup/rdata/" \
                + dynamic_fields['type'] +"/" \
                + urllib.quote(value)  + "/" \
                + rrtype \
                + "?limit=" + str(dynamic_fields['limit'])
        try:
            headers = {'Accept': 'application/json',
                       'X-API-Key': config.myConfig['apikey']}
            r = requests.get(url,
                             proxies=settings.PROXIES,
                             headers=headers,
                             verify=config.myConfig["ssl_verify"])
        except Exception as e:
            results['error'] = str(e)
            return results

        if r.status_code != 404:
            # Each line of the response is an individual JSON blob.
            for line in r.text.split('\n'):
                # Skip empty lines.
                if not line:
                    continue

                try:
                    tmp = json.loads(line)
                except Exception as e:
                    results['error'] = "%s: %s" % (str(e),
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

                if result_format in ['none', 'list']:
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
    if result_format != 'none':
        results = _format_results(results, result_format, dynamic_fields)

    return results

