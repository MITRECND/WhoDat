import sys
import json
from elasticsearch import Elasticsearch
from django.conf import settings
from handlers.advanced_es import yacc
from datetime import date
import collections

SEARCH_INDEX = "%s-search" % (settings.ES_INDEX_PREFIX)
META_INDEX = ".%s-meta" % (settings.ES_INDEX_PREFIX)

class ElasticsearchError(Exception):
    pass

def es_connector():
    try:
        es = Elasticsearch(settings.ES_URI,
                           max_retries=100,
                           retry_on_timeout=True)
        return es
    except:
        raise

def record_count():
    try:
        es = es_connector()
    except:
        raise

    records = es.cat.count(index=SEARCH_INDEX, h="count")

    return int(records)

def cluster_stats():
    try:
        es = es_connector()
    except:
        raise


    tstr = date.today().timetuple()
    year = tstr[0] - 2
    month = tstr[1]
    year_string = "%i-%.2i-01 00:00:00" % (year, month)

    query = {"aggs": {
                "type": {
                          "terms": {"field": "tld", "size": 10000},
                            "aggregations": {"unique": {"cardinality": {"field": "domainName.hash"}}}
                        },
                "created": {
                          "filter": { "range": {"details.standardRegCreatedDate": {"gte": year_string }}}, 
                          "aggs": {
                                    "dates": {"date_histogram": {"field": "details.standardRegCreatedDate", "interval": "1M", "format": "yyyy-MM"}}
                            }
                    },
                "updated": {
                          "filter": { "range": {"details.standardRegUpdatedDate": {"gte": year_string }}}, 
                            "aggs": {
                                    "dates": {"date_histogram": {"field": "details.standardRegUpdatedDate", "interval": "1M", "format": "yyyy-MM"}},
                            }
                    }
                },
             "size": 0
            }
    #TODO XXX need to cache this but query_cache doesn't seem to be a parameter to this function
    #Might need to set query cache in the mapping instead
    results = es.search(index=SEARCH_INDEX, body = query)

    stats = {
            'domainStats': {},
            'histogram': {}
    }

    for bucket in results['aggregations']['type']['buckets']:
        stats['domainStats'][bucket['key']] = (bucket['doc_count'], bucket['unique']['value'])
   
    for bucket in results['aggregations']['created']['dates']['buckets']:
        date_label = "/".join(bucket['key_as_string'].split('-'))
        if date_label not in stats['histogram']:
            stats['histogram'][date_label] = {}
        stats['histogram'][date_label]['created'] = bucket['doc_count']

    for bucket in results['aggregations']['updated']['dates']['buckets']:
        date_label = "/".join(bucket['key_as_string'].split('-'))
        if date_label not in stats['histogram']:
            stats['histogram'][date_label] = {}
        stats['histogram'][date_label]['updated'] = bucket['doc_count']

    stats['histogram'] = collections.OrderedDict(sorted(stats['histogram'].items()))
    return stats

def cluster_health():
    try:
        es = es_connector()
    except:
        raise

    health = es.cluster.health()

    return health['status']

def lastVersion():
    try:
        es = es_connector()
        result = es.get(index=META_INDEX, id=0)
        if result['found']:
            return result['_source']['lastVersion']
        else:
            raise 
    except ElasticsearchError as e:
        return -1


def metadata(version = None):
    results = {'success': False}
    try:
        es = es_connector()
    except ElasticsearchError as e:
        results['message'] = str(e)
        return results

    if version is None:
        res = es.search(index=META_INDEX, body={"query": {"match_all": {}},"sort": "metadata"})
        if res['hits']['total'] > 0:
            newres = []
            for r in res['hits']['hits']:
               newres.append(r['_source']) 
            res = newres
        else:
            res = []
    else:
        version = int(version)
        res = es.get(index=META_INDEX, id=version)
        if res['found']:
            res = [res['_source']]
        else:
            res = []


    results['data'] = []
    for r in res:
        results['data'].append(r)
    
    results['success'] = True
    return results
    

def formatSort(colID, direction):
    sort_key = None
    sort_dir = "asc"

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
        sort_dir = "desc"

    if sort_key is None:
        return None

    return (sort_key, sort_dir)
    

def dataTableSearch(key, value, skip, pagesize, sortset, sfilter, low, high):
    results = {'success': False}
    try:
        es = es_connector()
    except ElasticsearchError as e:
        results['message'] = str(e)
        return results


    if key != settings.SEARCH_KEYS[0][0]:
        key = 'details.' + key
    #All data in ES is lowercased (during ingestion/analysis) and we're using a term filter to take
    #advantage of filter caching, we could probably use a match query instead, but these seems more
    #efficient
    value = value.lower()

    query_filter = {"term": {key: value}}
    final_filter = [query_filter]
    version_filter = None
    lowUpdate = None

    try:
        (low, lowUpdate) = low.split('.')
    except:
        pass

    if low is not None:
        if low == high or high is None: # single version
            try:
                version_filter = [{"term": {'dataVersion': int(low)}}]
            except:
                raise ValueError("Low must be interger value")

            if lowUpdate is not None:
                if int(lowUpdate) == 0:
                    updateVersionQuery = {'bool': {'should': [{"bool": {"must_not": {"exists": {"field": "updateVersion"}}}}, {"term": {"updateVersion": int(lowUpdate)}}]}}
                else:
                    updateVersionQuery = {"term": {"updateVersion": int(lowUpdate)}}
                version_filter.append(updateVersionQuery)
        elif high is not None:
            try:
                version_filter = [{"range": {"dataVersion": {"gte": int(low), "lte": int(high)}}}]
            except:
                raise ValueError("Low and High values must be integers")

    if version_filter is not None:
        final_filter.extend(version_filter)

    qquery = None

    if sfilter is not None:
        try:
            regx = ".*%s.*" % sfilter
        except:
            results['aaData'] = []
            results['iTotalRecords'] = record_count()
            results['iTotalDisplayRecords'] = 0
            results['message'] = "Invalid Search Parameter"
            return results
        else:
            shoulds = []
            for skey in [keys[0] for keys in settings.SEARCH_KEYS]:
                if skey == key: #Don't bother filtering on the key field
                    continue
                if skey != settings.SEARCH_KEYS[0][0]:
                    snkey = 'details.' + skey
                else:
                    snkey = skey
                exp = {
                        'regexp': {
                            snkey: {
                                "value": regx
                            }
                        }
                      } 

                shoulds.append(exp)

            qquery = {"should": shoulds}

    query = { 
        "query": {
            "bool": {
                "filter": final_filter
            },
        },
        "from": skip,
        "size": pagesize,
    }

    if qquery is not None:
        query['query']['bool'].update(qquery)

    if len(sortset) > 0:
        sorter = []
        for s in sortset:
            sorter.append({s[0]: {"order": s[1]}})

        query["sort"] = sorter


    if settings.DEBUG:
        try:
            sys.stdout.write("%s\n" % json.dumps(query))
            sys.stdout.flush()
        except:
            pass

    domains = es.search(index=SEARCH_INDEX, body = query)

    results['aaData'] = []
    #Total Records in all indices 
    results['iTotalRecords'] = record_count()




    if domains['hits']['total'] > 0:
        for domain in domains['hits']['hits']:
            updateVersion = domain['_source'].get('updateVersion', 0)
            entryVersion = "%d.%d" % (domain['_source']['dataVersion'], updateVersion)
            #First element is placeholder for expansion cell
            #TODO Make this configurable?
            details = domain['_source']['details']
            dom_arr = ["&nbsp;", domain['_source']['domainName'], details['registrant_name'], details['contactEmail'], 
                        details['standardRegCreatedDate'], details['registrant_telephone'], entryVersion]
            results['aaData'].append(dom_arr)

    #Number of Records after any sort of filtering/searching
    results['iTotalDisplayRecords'] = domains['hits']['total']
    results['success'] = True
    return results

def __createAdvancedQuery__(query, skip, size, unique):
    q = yacc.parse(query)

    if not unique:
        q['sort'] = [
                        {'_score': {'order': 'desc'}}, 
                        {'domainName': {'order': 'asc'}}, 
                        {'dataVersion': {'order': 'desc'}},
                        {'updateVersion': {'order': 'desc', 'missing': 0, 'unmapped_type': 'long'}}
                    ]
        q['size'] = size
        q['from'] = skip
    else:
        q['size'] = 0
        q["aggs"] = {
                    "domains": {
                        "terms":{
                            "field": "domainName",
                            "size": size,
                            "order": {"max_score": "desc"}
                        },
                        "aggs": {
                            "max_score": {
                                "max": {"script": "_score"}
                            },
                            "top_domains":{
                                "top_hits":{
                                    "size": 1,
                                    "sort": [
                                        {'_score': {'order': 'desc'}}, 
                                        {"dataVersion": {"order": "desc"}},
                                        {"updateVersion": {"order": "desc", "missing": 0, "unmapped_type": "long"}}
                                    ]
                                }
                            }
                        }
                    }
        }

    return q



def advDataTableSearch(query, skip, pagesize, unique = False):
    results = {'success': False}
    results['aaData'] = []

    try:
        es = es_connector()
    except ElasticsearchError as e:
        results['message'] = str(e)
        return results

    try:
        q = __createAdvancedQuery__(query, skip, pagesize, unique)
    except Exception as e:
        results['message'] = str(e)
        return results

    if settings.DEBUG:
        try:
            sys.stdout.write(json.dumps(q) + "\n")
            sys.stdout.flush()
        except:
            pass
    try:
        domains = es.search(index=SEARCH_INDEX, body = q, search_type = 'dfs_query_then_fetch')
    except Exception as e:
        results['message'] = str(e)
        return results    
    
    if 'error' in domains:
        results['message'] = 'Error'
        return results

    if not unique:
        results['iTotalDisplayRecords'] = domains['hits']['total']
        results['iTotalRecords'] = record_count()

        if domains['hits']['total'] > 0:
            for domain in domains['hits']['hits']:
                pdomain = domain['_source']
                details = pdomain['details']
                updateVersion = pdomain.get('updateVersion', 0)
                entryVersion = "%d.%d" % (pdomain['dataVersion'], updateVersion)
                # Take each key in details (if any) and stuff it in top level dict.
                dom_arr = ["&nbsp;", pdomain['domainName'], 
                            details['registrant_name'], details['contactEmail'], 
                            details['standardRegCreatedDate'], details['registrant_telephone'], 
                            entryVersion, "%.2f" % round(domain['_score'], 2)]
                results['aaData'].append(dom_arr)

        results['success'] = True
    else:
        buckets = domains['aggregations']['domains']['buckets']
        results['iTotalDisplayRecords'] = len(buckets)
        results['iTotalRecords'] = len(buckets)

        for bucket in buckets:
            domain = bucket['top_domains']['hits']['hits'][0]
            pdomain = domain['_source']
            details = pdomain['details']
            updateVersion = pdomain.get('updateVersion', 0)
            entryVersion = "%d.%d" % (pdomain['dataVersion'], updateVersion)
            dom_arr = ["&nbsp;", pdomain['domainName'],
                        details['registrant_name'], details['contactEmail'],
                        details['standardRegCreatedDate'], details['registrant_telephone'],
                        entryVersion, "%.2f" % round(domain['sort'][0], 2)] # For some reason the _score goes away in the aggregations if you sort by it
            results['aaData'].append(dom_arr)

        results['success'] = True

    return results

    

def search(key, value, filt=None, limit=settings.LIMIT, low = None, high = None, versionSort = False):
    results = {'success': False}
    try:
        es = es_connector()
        index = '%s-*' % settings.ES_INDEX_PREFIX
    except ElasticsearchError as e:
        results['message'] = str(e)
        return results

    if key != settings.SEARCH_KEYS[0][0]:
        key = 'details.' + key
    value = value.lower()


    es_source = None
    # If filter key requested, use it.
    if filt == 'domainName':
        es_source = ['domainName']
    elif filt != None:
        es_source = ['details.' + filt]

    query_filter = {"term": {key: value}}
    final_filter = [query_filter]
    version_filter = None
    lowUpdate = None

    try:
        (low, lowUpdate) = low.split('.')
    except Exception as e:
        pass

    if low is not None:
        if low == high or high is None: # single version
            try:
                version_filter = [{"term": {'dataVersion': int(low)}}]
                if lowUpdate is not None:
                    if int(lowUpdate) == 0:
                        updateVersionQuery = {'bool': {'should': [{"bool": {"must_not": {"exists": {"field": "updateVersion"}}}}, {"term": {"updateVersion": int(lowUpdate)}}]}}
                    else:
                        updateVersionQuery = {"term": {"updateVersion": int(lowUpdate)}}
                    version_filter.append(updateVersionQuery)
            except: #TODO XXX
                raise
        elif high is not None:
            try:
                version_filter = [{"range": {"dataVersion": {"gte": int(low), "lte": int(high)}}}]
            except:
                raise ValueError("Low and High values must be integers")

    if version_filter is not None:
        final_filter.extend(version_filter)

    query = { 
        "query": {
            "bool": {
                "filter": final_filter
            },
        },
        "size": limit,
    }

    if versionSort:
        query["sort"] = [{"dataVersion": {"order": "asc"}}, {"updateVersion": {"order": "asc", "missing": 0, "unmapped_type": "long"}}]
    if es_source:
        query["_source"] = es_source

    #XXX DEBUG CODE
    try:
        sys.stdout.write("%s\n" % json.dumps(query))
        sys.stdout.flush()
    except:
        pass
    domains = es.search(index=SEARCH_INDEX, body = query)

    results['total'] = domains['hits']['total']
    results['data'] = []

    for domain in domains['hits']['hits']:
        pdomain = domain['_source']
        # Take each key in details (if any) and stuff it in top level dict.
        if 'details' in pdomain:
            for k, v in pdomain['details'].iteritems():
                pdomain[k] = v
            del pdomain['details']
        if 'dataVersion' in pdomain:
            pdomain['Version'] = pdomain['dataVersion']
            del pdomain['dataVersion']

        if 'updateVersion' in pdomain:
            pdomain['UpdateVersion'] = pdomain['updateVersion']
            del pdomain['updateVersion']
        else:
            pdomain['UpdateVersion'] = 0

        results['data'].append(pdomain)

    results['avail'] = len(results['data'])
    results['success'] = True
    return results


def test_query(search_string):
    try:
        query = yacc.parse(search_string)
    except Exception as e:
        return str(e)

    return None

def advanced_search(search_string, skip = 0, size = 20, unique = False): #TODO XXX versions, dates, etc
    results = {'success': False}
    try:
        es = es_connector()
    except ElasticsearchError as e:
        results['message'] = str(e)
        return results

    try:
        query = __createAdvancedQuery__(search_string, skip, size, unique) 
    except Exception as e:
        results['message'] = str(e)
        return results

    try:
        domains = es.search(index=SEARCH_INDEX, body = query, search_type='dfs_query_then_fetch')
    except Exception as e:
        results['message'] = str(e)
        return results

    if not unique:
        results['total'] = domains['hits']['total']
        results['data'] = []

        for domain in domains['hits']['hits']:
            pdomain = domain['_source']
            # Take each key in details (if any) and stuff it in top level dict.
            if 'details' in pdomain:
                for k, v in pdomain['details'].iteritems():
                    pdomain[k] = v
                del pdomain['details']
            if 'dataVersion' in pdomain:
                pdomain['Version'] = pdomain['dataVersion']
                del pdomain['dataVersion']
            if 'updateVersion' in pdomain:
                pdomain['UpdateVersion'] = pdomain['updateVersion']
                del pdomain['updateVersion']
            results['data'].append(pdomain)

        results['avail'] = len(results['data'])
        results['skip'] = skip
        results['page_size'] = size
        results['success'] = True
    else:
        buckets = domains['aggregations']['domains']['buckets']
        results['total'] = len(buckets)
        results['data'] = []

        for bucket in buckets:
            domain = bucket['top_domains']['hits']['hits'][0]
            pdomain = domain['_source']
            # Take each key in details (if any) and stuff it in top level dict.
            if 'details' in pdomain:
                for k, v in pdomain['details'].iteritems():
                    pdomain[k] = v
                del pdomain['details']
            if 'dataVersion' in pdomain:
                pdomain['Version'] = pdomain['dataVersion']
                del pdomain['dataVersion']
            if 'updateVersion' in pdomain:
                pdomain['UpdateVersion'] = pdomain['updateVersion']
                del pdomain['updateVersion']
            results['data'].append(pdomain)

        results['avail'] = len(buckets)
        results['skip'] = 0 
        results['page_size'] = size
        results['success'] = True

    return results



