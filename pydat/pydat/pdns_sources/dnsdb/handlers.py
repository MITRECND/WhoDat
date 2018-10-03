'''
pdns module for DNSDB
    -obtains the 2 methods for handling passive and reverse-passive
     requests to the dnsdb API
'''
import cgi
import time
import datetime
import json
import requests
import socket
import urllib
import urlparse
import cStringIO
import unicodecsv as csv
from django.conf import settings

from dnsdb import config


def _format_results(results, fmt, dynamic_data):
    if fmt == 'json':
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
                if not isinstance(record[filt_key], basestring):  # it's a list
                    data.extend(record[filt_key])
                else:  # it's just a string
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

    # Validate ip part
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        version = 6
    except Exception as e:  # invalid ipv6
        try:
            socket.inet_pton(socket.AF_INET, ip)
        except Exception, e:
            raise TypeError("Invalid IP Address")

    output_ip = ip
    # Validate mask if present
    if mask is not None:
        try:
            mask = int(mask)
            if mask < 1:
                raise ValueError("Mask must be at least 1")
            elif version == 4 and mask > 32:
                raise ValueError("IP Mask too large for v4")
            elif version == 6 and mask > 128:
                raise ValueError("IP Mask too large for v6")
        except Exception as e:
            raise TypeError("Unable to process mask")
        output_ip += ",%d" % mask
    return output_ip


def validate_hex(input_hex):
    try:
        output_hex = "%x" % int(input_hex, 16)
    except Exception as e:
        raise TypeError("Not hex")

    if len(output_hex) % 2 == 1:  # make hex string always pairs of hex values
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


def request_rate_limit():
    url = "https://api.dnsdb.info/lookup/rate_limit"
    results = {'success': False}

    if not config.myConfig['apikey']:
        results['error'] = 'No DNSDB key.'
        return results

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

    if r.status_code != 200:
        results['error'] = "Unable to query quota."
        return results

    data = r.json()
    if 'rate' not in data:
        results['error'] = "expected field not found in response"
        return results

    rate = data['rate']

    return rate


def check_return_code(response):
    results = {'success': False}
    if response.status_code == 400:
        results['error'] = 'Url possibly misconfigured'
    elif response.status_code == 403:
        results['error'] = "API key not valid"
    elif response.status_code == 429:
        try:
            rate = request_rate_limit()
            reset = time.strftime("%Y-%m-%d %H:%M:%S",
                                  time.gmtime(rate['reset']))
            results['error'] = ('Quota reached (limit: %d) Reset: %d'
                                % (rate['limit'], reset))
        except Exception as e:
            results['error'] = "Quota reached, but unable to query limits"
    elif response.status_code == 500:
        results['error'] = "dnsdb server unable to process request"
    elif response.status_code == 503:
        results['error'] = "Request throttled, try again later"
    else:
        results['error'] = "Received unexpected response from server"

    return results


def pdns_request_handler(domain, result_format, **dynamic_data):
    scheme = "https"
    netloc = "api.dnsdb.info"
    path = "lookup/rrset/name".split('/')
    query = ["limit=%d" % (int(dynamic_data['limit']))]

    results = {'success': False}
    if not config.myConfig['apikey']:
        results['error'] = 'No DNSDB key.'
        return results

    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in dynamic_data['rrtypes']:
        if 'any-dnssec' in dynamic_data['rrtypes']:
            dynamic_data['rrtypes'] = ['any', 'any-dnssec']
        else:
            dynamic_data['rrtypes'] = ['any']

    results['data'] = {}
    wildcard = "*."

    if dynamic_data['absolute']:
        wildcard = ""

    owner_name = wildcard + urllib.quote(domain)
    path.append(owner_name)

    for rrtype in dynamic_data['rrtypes']:
        local_path = list(path) + [rrtype]
        local_path = "/".join(local_path)

        local_url = urlparse.ParseResult(scheme,
                                         netloc,
                                         local_path,
                                         "",
                                         "&".join(query),
                                         "")

        url = urlparse.urlunparse(local_url)
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

        if r.status_code not in [200, 404]:
            return check_return_code(r)

        if r.status_code == 200:
            # Each line of the response is an individual JSON blob.
            for line in r.text.split('\n'):
                # Skip empty lines.
                if not line:
                    continue
                try:
                    tmp = json.loads(line)
                except Exception as e:
                    results['error'] = \
                        "%s: %s" % (str(e), cgi.escape(line, quote=True))
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

                    for (idx, rdat) in enumerate(list(tmp['rdata'])):
                        if rdat and rdat[-1] == ".":
                            tmp['rdata'][idx] = rdat[:-1]

                try:
                    results['data'][rrtype].append(tmp)
                except KeyError:
                    results['data'][rrtype] = [tmp]

    results['success'] = True
    rate = {'limit': r.headers['X-RateLimit-Limit'],
            'remaining': r.headers['X-RateLimit-Remaining'],
            'reset': r.headers['X-RateLimit-Reset']}
    if rate['reset'] != 'n/a':
        rate['reset'] = datetime.datetime.utcfromtimestamp(
            float(rate['reset'])).strftime('%Y-%m-%d %H:%M:%S GMT')
    results['rate'] = rate

    if result_format != 'none':
        results = _format_results(results, result_format, dynamic_data)

    return results


def pdns_reverse_request_handler(search_value,
                                 result_format,
                                 **dynamic_fields):
    """method to allow for custom pdns reverse requests handler
       for DNSDB as a pdns source

    Note: the method name must be "pdns_reverse_request_handler"
    """
    scheme = "https"
    netloc = "api.dnsdb.info"
    path = "lookup/rdata".split('/')
    query = ["limit=%d" % ((int(dynamic_fields['limit'])))]

    results = {'success': False}
    if not config.myConfig['apikey']:
        results['error'] = 'No DNSDB key.'
        return results

    try:
        value = _verify_type(search_value, dynamic_fields['type'])
    except Exception as e:
        results['error'] = 'Unable to verify input'
        return results

    path.extend([dynamic_fields['type'], urllib.quote(value)])

    # If 'any' is in rrtypes and anything else too, just default to 'any'
    if 'any' in dynamic_fields['rrtypes']:
        if 'any-dnssec' in dynamic_fields['rrtypes']:
            dynamic_fields['rrtypes'] = ['any', 'any-dnssec']
        else:
            dynamic_fields['rrtypes'] = ['any']

    results['data'] = {}
    for rrtype in dynamic_fields['rrtypes']:
        local_path = list(path) + [rrtype]
        local_path = "/".join(local_path)

        local_url = urlparse.ParseResult(scheme,
                                         netloc,
                                         local_path,
                                         "",
                                         "&".join(query),
                                         "")

        url = urlparse.urlunparse(local_url)
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

        if r.status_code not in [200, 404]:
            return check_return_code(r)

        if r.status_code == 200:
            # Each line of the response is an individual JSON blob.
            for line in r.text.split('\n'):
                # Skip empty lines.
                if not line:
                    continue

                try:
                    tmp = json.loads(line)
                except Exception as e:
                    results['error'] = \
                        "%s: %s" % (str(e), cgi.escape(line, quote=True))
                    return results

                # Convert epoch timestamps to human readable.
                for key in ['time_first', 'time_last']:
                    if key in tmp:
                        tmp[key] = time.strftime("%Y-%m-%d %H:%M:%S",
                                                 time.gmtime(tmp[key]))

                rrtype = tmp['rrtype']
                # Strip the MX weight
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
    rate = {'limit': r.headers['X-RateLimit-Limit'],
            'remaining': r.headers['X-RateLimit-Remaining'],
            'reset': r.headers['X-RateLimit-Reset']}
    if rate['reset'] != 'n/a':
        rate['reset'] = datetime.datetime.utcfromtimestamp(
            float(rate['reset'])).strftime('%Y-%m-%d %H:%M:%S GMT')
    results['rate'] = rate

    if result_format != 'none':
        results = _format_results(results, result_format, dynamic_fields)

    return results
