import time
import json
import pymongo
import requests
import re
import urllib

from django.conf import settings

class MongoError(Exception):
    pass

# Setup standard connector to the MongoDB instance for use in any functions
def mongo_connector(collection, preference=settings.MONGO_READ_PREFERENCE):
    try:
        connection = pymongo.Connection("%s" % settings.MONGO_HOST,
                                        settings.MONGO_PORT,
                                        read_preference=preference)
        db = connection[settings.MONGO_DATABASE]
        return db[collection]
    except pymongo.errors.ConnectionFailure as e:
        raise MongoError("Error connecting to Mongo database: %s" % e)
    except KeyError as e:
        raise MongoError("Unknown database or collection: %s" % e)
    except:
        raise

def sort_lookup(colID, direction):
    sort_key = None
    sort_dir = pymongo.ASCENDING

    if(colID == 1):
        sort_key = "domainName"
    elif(colID == 2):
        sort_key = "registrant_name"
    elif(colID == 3):
        sort_key = "contactEmail"
    elif(colID == 4):
        sort_key = "standardRegCreatedDate" 
    elif(colID == 5):
        sort_key = "registrant_telephone"
        

    if direction == "desc":
        sort_dir = pymongo.DESCENDING

    return (sort_key, sort_dir)
    

def ajax_search(key, value, skip, pagesize, sortset, sfilter):
    results = {'success': False}
    try:
        coll = mongo_connector(settings.COLL_WHOIS)
    except MongoError as e:
        results['message'] = str(e)
        return results

    query = {key: value}

    if sfilter is not None:
        try:
            regx = re.compile("%s" % sfilter, re.IGNORECASE)
        except:
            results['aaData'] = []
            results['iTotalRecords'] = coll.count()
            results['iTotalDisplayRecords'] = 0
            results['message'] = "Invalid Search Parameter"
            return results
        else:
            query['$or'] = []
            for skey in [keys[0] for keys in settings.SEARCH_KEYS]:
                if skey == key: #Don't bother filtering on the key field
                    continue
                exp = {skey: {'$regex': regx}}
                query['$or'].append(exp)
                
    domains = coll.find(query, skip=skip, limit=pagesize, sort=sortset)

    results['aaData'] = []
    #Total Records in entire collection
    results['iTotalRecords'] = coll.count()

    for domain in domains:
        #First element is placeholder for expansion cell
        #TODO Make this configurable?
        dom_arr = ["&nbsp;", domain['domainName'], domain['registrant_name'], domain['contactEmail'], 
                    domain['standardRegCreatedDate'], domain['registrant_telephone']]
        results['aaData'].append(dom_arr)

    #Number of Records after any sort of filtering/searching
    results['iTotalDisplayRecords'] = domains.count()
    results['success'] = True
    return results

def do_search(key, value, filt={}, limit=settings.LIMIT):
    results = {'success': False}
    try:
        coll = mongo_connector(settings.COLL_WHOIS)
    except MongoError as e:
        results['message'] = str(e)
        return results

    domains = coll.find({key: value}, filt, limit=limit)

    results['total'] = domains.count()
    results['data'] = [domain for domain in domains]
    results['avail'] = len(results['data'])
    results['success'] = True
    return results

def do_pdns(domain, absolute, rrtypes, limit, pretty = False):
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
            tmp = json.loads(line)
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

def do_pdns_r(key, value, rrtypes, limit, pretty = False):
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
