import json
import pymongo
import re

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

def lastVersion():
    try:
        coll = mongo_connector(settings.COLL_WHOIS + "_meta")
    except MongoError as e:
        return -1

    metadata = coll.find_one({'metadata': 0})
    
    return metadata['lastVersion']

def metadata(version = None):
    results = {'success': False}
    try:
        coll = mongo_connector(settings.COLL_WHOIS + "_meta")
    except MongoError as e:
        results['message'] = str(e)
        return results

    if version is None:
        res = coll.find(fields = {'_id': False})
    else:
        version = int(version)
        res = coll.find({'metadata':version}, {'_id':False})

    results['data'] = []
    for r in res:
        results['data'].append(r)

    
    results['success'] = True

    return results
    

def formatSort(colID, direction):
    sort_key = None
    sort_dir = pymongo.ASCENDING

    if(colID == 1):
        sort_key = "domainName"
    elif(colID == 2):
        sort_key = "details.registrant_name"
    elif(colID == 3):
        sort_key = "details.contactEmail"
    elif(colID == 4):
        sort_key = "details.standardRegCreatedDate" 
    elif(colID == 5):
        sort_key = "details.registrant_telephone"
    elif(colID == 6):
        sort_key = "dataVersion"

    if direction == "desc":
        sort_dir = pymongo.DESCENDING

    if sort_key is None:
        return None

    return (sort_key, sort_dir)
    

def dataTableSearch(key, value, skip, pagesize, sortset, sfilter, low, high):
    results = {'success': False}
    try:
        coll = mongo_connector(settings.COLL_WHOIS)
    except MongoError as e:
        results['message'] = str(e)
        return results

    if key != settings.SEARCH_KEYS[0][0]:
        query = {'details.' + key: value}
    else:
        query = {key: value}

    if low is not None:
        if low == high or high is None: # single version
            try:
                query['dataVersion'] = int(low)
            except: #TODO XXX
                pass
        elif high is not None:
            try:
                query['dataVersion'] = {'$gte': int(low), '$lte': int(high)}
            except: #TODO XXX
                pass 
        

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
                if skey != settings.SEARCH_KEYS[0][0]:
                    exp = {'details.' + skey: {'$regex': regx}}
                else:
                    exp = {skey: {'$regex': regx}}
                query['$or'].append(exp)

    domains = coll.find(query, skip=skip, limit=pagesize, sort=sortset)

    results['aaData'] = []
    #Total Records in entire collection
    results['iTotalRecords'] = coll.count()

    for domain in domains:
        #First element is placeholder for expansion cell
        #TODO Make this configurable?
        details = domain['details']
        dom_arr = ["&nbsp;", domain['domainName'], details['registrant_name'], details['contactEmail'], 
                    details['standardRegCreatedDate'], details['registrant_telephone'], domain['dataVersion']]
        results['aaData'].append(dom_arr)

    #Number of Records after any sort of filtering/searching
    results['iTotalDisplayRecords'] = domains.count()
    results['success'] = True
    return results

def search(key, value, filt=None, limit=settings.LIMIT, low = None, high = None, versionSort = False):
    results = {'success': False}
    try:
        coll = mongo_connector(settings.COLL_WHOIS)
    except MongoError as e:
        results['message'] = str(e)
        return results

    if key != settings.SEARCH_KEYS[0][0]:
        search_document = {'details.' + key: value}
    else:
        search_document = {key: value}

    # Always filter out _id.
    filt_document = {'_id': False}

    # If filter key requested, use it.
    if filt == 'domainName':
        filt_document[filt] = 1
    elif filt != None:
        filt_document['details.' + filt] = 1

    if low != None:
        if low == high or high is None:
            search_document['dataVersion'] = int(low)
        elif high is not None:
            search_document['dataVersion'] = {'$gte': int(low), '$lte': int(high)}

    sortset = None
    if versionSort:
        sortset = [('dataVersion', pymongo.ASCENDING)] 
    domains = coll.find(search_document, filt_document, limit=limit, sort = sortset)

    results['total'] = domains.count()
    results['data'] = []
    for domain in domains:
        # Take each key in details (if any) and stuff it in top level dict.
        if 'details' in domain:
            for k, v in domain['details'].iteritems():
                domain[k] = v
            del domain['details']
        domain['Version'] = domain['dataVersion']
        del domain['dataVersion']
        results['data'].append(domain)

    results['avail'] = len(results['data'])
    results['success'] = True
    return results


