import collections
from datetime import date
import json
import sys
import time

import elasticsearch
from elasticsearch import Elasticsearch
from flask_caching import Cache
from flask import current_app
from pydat.core.advanced_es import yacc

#TODO: RE usage of settings with  Flask now, the settings.py module can be loaded as well into the app
#object, and thus accessed here via "current_app.config". But make sure settings.py module is loaded into
# Flask app. Currently dont know where in code/bootup that is being done since using blueprints etc..


CACHE_TIMEOUT = 300  # Flask cache timeout
DOC_TYPE = "doc"


class ESConnectionError(Exception):
    """Custom error exception that denotes a failure to establish
    a python ElasticSearch client handle, thus implying a connectivity
    problem to the ElasticSearch instance.
    """
    pass


class ESQueryError(Exception):
    """Custom error exception that denotes a failure when making a query call
    to ElasticSearch instance
    """
    pass


class ElasticsearchHandler:
    """ """
    def __init__(self):
        pass

    def init_app(self, app):
        app.config["CACHE_TYPE"] = "simple"
        app.config["CACHE_DEFAULT_TIMEOUT"] = CACHE_TIMEOUT
        self._cache = Cache(app)
        self._search_index = f"{app.config['ELASTICSEARCH']['indexPrefix']}-search"
        self._meta_index = f".{app.config['ELASTICSEARCH']['indexPrefix']}-meta"

    def record_count(self):
        """Return record count of ES record index.

        Returns: (int) record count
        
        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
        """
        records = self._cache.get("record_count")
        if records is None:
            es = self._es_connector()
            try:
                records = es.cat.count(index=self._search_index, h="count")
                self._cache.set("record_count", records)
            except elasticsearch.ElasticsearchException as e:
                raise ESQueryError(f"The following exception occured while trying to execute 'count' call to ElasticSearch instance: {repr(e)}")
        return int(records)

    def cluster_stats(self):
        """Return stats blob on ElasticSearch cluster.

        Returns: (dict) stats blob

        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
        """
        es = self._es_connector()
        tstr = date.today().timetuple()
        year = tstr[0] - 2
        month = tstr[1]
        year_string = "%i-%.2i-01 00:00:00" % (year, month)

        query = {"aggs": {
                    "type": {"terms": {"field": "tld", "size": 10000},
                            "aggregations":
                            {"unique":
                            {"cardinality": {"field": "domainName"}}}},
                    "created": {"filter": {"range":
                                {"details.standardRegCreatedDate":
                                {"gte": year_string}}},
                                "aggs": {"dates":
                                        {"date_histogram":
                                        {"field":
                                            "details.standardRegCreatedDate",
                                            "interval": "1M",
                                            "format": "yyyy-MM"}}}},
                    "updated": {"filter":
                                {"range":
                                {"details.standardRegUpdatedDate":
                                {"gte": year_string}}},
                                "aggs": {"dates":
                                        {"date_histogram":
                                        {"field":
                                            "details.standardRegUpdatedDate",
                                            "interval": "1M",
                                            "format": "yyyy-MM"}}}}},
                "size": 0}

        results = self._cache.get("cluster_stats")
        if results is None:
            try:
                results = es.search(index=self._search_index, body=query)
            except elasticsearch.ElasticsearchException as e:
                raise ESQueryError(f"The following exception occured while trying to execute 'search' call to ElasticSearch instance: {repr(e)}")
            # Cache for an hour since this is a relatively expensive query
            # whose results shouldn't change often
            results["cache_time"] = time.time()
            self._cache.set("cluster_stats", results, 3600)

        stats = self._process_cluster_stats_results(results)

        return stats

    def cluster_health(self):
        """Retrieve cluster health status.

        Returns: (str) status of the cluster

        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
        """
        health = self._cache.get("cluster_health")
        if health is None:
            es = self._es_connector()
            try:
                health = es.cluster.health()
            except elasticsearch.ElasticsearchException as e:
                raise ESQueryError(f"The following exception occured while trying to execute 'health' call to ElasticSearch instance: {repr(e)}")
            self._cache.set("cluster_health", health)
        return health["status"]

    def last_version(self):
        """Retrieve last version of index.

        Returns: (float) version number

        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
            RuntimeError - when error occurs processing ElasticSearch response
        """
        lastVersion = self._cache.get("lastVersion")
        if lastVersion is None:
            es = self._es_connector()
            try:
                result = es.get(index=self._meta_index, doc_type=DOC_TYPE, id=0)
                if result["found"]:
                    self._cache.set("lastVersion",
                            result["_source"]["lastVersion"])
                    return result["_source"]["lastVersion"]
                else:
                    raise RuntimeError("Could not process result from ElasticSearch")
            except elasticsearch.ElasticsearchException as e:
                raise ESQueryError(f"The following exception occured while trying to execute 'get' call to ElasticSearch instance: {repr(e)}")
        else:
            return lastVersion

    def last_update(self):
        """Retrieve last update version of index.

        Returns: (float) last update version

        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
        """
        try:
            update = self._cache.get("lastUpdate")
            if update is None:
                es = self._es_connector()
                try:
                    res = es.search(index=self._meta_index,
                                    body={"query": {"match_all": {}},
                                        "sort": [{"metadata": {"order": "desc"}}],
                                        "size": 1})
                except elasticsearch.ElasticsearchException as e:
                    raise ESQueryError(f"The following exception occured while trying to execute 'search' call to ElasticSearch instance: {repr(e)}")

                if res["hits"]["total"] >= 1:
                    data = res["hits"]["hits"][0]["_source"]
                    update = "%d.%d" % (data["metadata"],
                                        data.get("updateVersion", 0))
                else:
                    update = "0.0"
                self._cache.set("update", update)
        except KeyError as e:
            #TODO: Log? or raise RuntimeError? What was trying to be caught here originally?
            update = "0.0"

        return update

    def metadata(self, version=None):
        """Retrieve metadata information on index.

        Args:
            version (float): data version
        
        Returns: (dict) metadata blob

        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
        """
        results = {"success": False}
        es = self._es_connector()

        if version is None:
            res = self._cache.get("all_metadata")
            if res is None:
                try:
                    res = es.search(index=self._meta_index,
                                    body={"query": {"match_all": {}},
                                        "sort": "metadata",
                                        "size": 999})
                    self._cache.set("all_metadata", res)
                except elasticsearch.ElasticsearchException as e:
                    raise ESQueryError(f"The following exception occured while trying to execute 'search' call to ElasticSearch instance: {repr(e)}")

            if res["hits"]["total"] > 0:
                newres = []
                for r in res["hits"]["hits"]:
                    newres.append(r["_source"])
                res = newres
            else:
                res = []
        else:
            version = int(version)
            try:
                res = es.get(index=self._meta_index, doc_type=DOC_TYPE, id=version)
            except elasticsearch.ElasticsearchException as e:
                raise ESQueryError(f"The following exception occured while trying to execute 'get' call to ElasticSearch instance: {repr(e)}")
            if res["found"]:
                res = [res["_source"]]
            else:
                res = []

        results["data"] = []
        for r in res:
            results["data"].append(r)

        results["success"] = True
        return results

    def format_sort(self, colID, direction="asc"):
        """

        Args:
            colID (int): columnd index
            direction (str): sort direction. Options: "asc", "desc"

        Returns: (tuple) of form (<sort key> , <sort directory>)
        """
        sort_key = None

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
        elif(colID == 7):
            sort_key = "_score"

        if sort_key is None:
            return None

        return (sort_key, direction)

    def data_table_search(self, key, value, skip, pagesize, sortset, sfilter, low, high):
        """

        Args:
            key (str): key field
            value (): key value
            skip (int): starting results offset
            pagesize (int): number of ElasticSearch result hits to retrieve
            sortset (list): tuples of the form (sort_key, sort_direction)
            sfilter (str): regex search filter
            low (float): lower bound version value
            high (float): upper bound version value
        
        Returns: (dict) results blob

        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            ValueError - if 'low' and 'high' args are not integers.
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
            RuntimeError - when unexpected error processing ElasticSearch results
        """
        results = {"success": False}
        es = self._es_connector()

        if key != current_app.config["SEARCHKEYS"][0][0]:
            key = f"details.{key}"

        # All data in ES is lowercased (during ingestion/analysis) and we're using
        # a term filter to take advantage of filter caching, we could probably
        # use a match query instead, but these seems more efficient
        value = value.lower()

        query = self._create_data_table_search_query(key, value, skip, pagesize, sortset, sfilter, low, high)

        if current_app.config["DEBUG"]:
            try:
                sys.stdout.write(f"{json.dumps(query)}\n")
                sys.stdout.flush()
            except Exception as e:
                pass

        try:
            domains = es.search(index=self._search_index,
                                body=query)
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(f"The following exception occured while trying to execute 'get' call to ElasticSearch instance: {repr(e)}")

        results.update(self._process_data_table_search_results(domains))
        return results

    def adv_data_table_search(self, query, skip, pagesize, unique=False, sort=None):
        """

        Args:
            query (str): query string
            skip (int): starting results offset
            pagesize (int): number of ElastcSearch result hits to retrieve
            unique (bool):  restrict results to unique set of records
            sort (list): tuples of the form (sort_key, sort_direction)

        Returns: (dict) results blob

        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            RuntimeError - when enexpected exception in creating the query or processing ES results
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
        """
        es = self._es_connector()
        q = self._create_advanced_query(query, skip, pagesize, unique, sort)

        if current_app.config["DEBUG"]:
            try:
                sys.stdout.write(f"{json.dumps(q)}\n")
                sys.stdout.flush()
            except Exception as e:
                pass
        try:
            domains = es.search(index=self._search_index, body=q,
                                search_type="dfs_query_then_fetch")
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(f"The following exception occured while trying to execute 'search' call to ElasticSearch instance: {repr(e)}")

        results = self._process_adv_data_table_search(domains, unique)

        return results

    def search(self, key, value, filt=None, limit=10000, low=None, high=None, versionSort=False):
        """Search whois index for records with supplied key/values.

        Args:
            key (str): key field
            value (str): key value
            filt (str): record field to restrict results hits data to
            limit (int): query results limit size
            low (float): lower bound version value
            high (float): upper bound version value
            version_sort (bool): sort results by version

        Returns: (dict) results blob

        Raises:
            ESConnectionError - when ElasticSearch connection cannot be established.
            RuntimeError - when  error occurs when creating ES query, or when processing ElasticSearch results
            ESQueryError - when error occurs at ElasticSearch from sent query/request.
            ValueError - when 'low' and 'high' args are not integers
        """
        results = {"success": False}
        es = self._es_connector()
        index = f"{current_app.config['ELASTICSEARCH']['indexPrefix']}-*"

        if key != current_app.config["SEARCHKEYS"][0][0]:
            key = f"details.{key}"
        value = value.lower()

        # preserve None args, otherwise will break in _create_search_query()
        if low is not None:
            low = str(low)
        if high is not None:
            high = str(high)

        query = self._create_search_query(key, value, filt, limit, low, high, versionSort)

        # XXX DEBUG CODE
        try:
            sys.stdout.write(f"{json.dumps(query)}\n")
            sys.stdout.flush()
        except Exception as e:
            pass
        try:
            domains = es.search(index=self._search_index, body=query)
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(f"The following exception occured while trying to execute 'get' call to ElasticSearch instance: {repr(e)}")

        results.update(self._process_search_query_results(domains))
        return results

    def test_query(self, search_string):
        try:
            query = yacc.parse(search_string)
        except Exception as e:
            return str(e)

        return None

    def advanced_search(self, search_string, skip=0, size=20, unique=False, sort=None):  # TODO XXX versions, dates, etc
        """Search whois index with advanced search, via supplied regex.

        Args:
            query (str): search query
            skip (int): starting results offset
            size: number of result hits to retrieve
            unique (bool): restrict results to unique set of records
            sort (list): tuples of the form (sort_key, sort_direction)

        Returns: (dict) results blob

        Raises:
            ESConnectionError - when cannot create and initialize python client
            RuntimeError - when unexpected error occurs when creating advanced query or processing results from Elasticsearch
        """
        results = {"success": False}
        es = self._es_connector()
        query = self._create_advanced_query(search_string, skip, size, unique, sort)
        try:
            domains = es.search(index=self._search_index, body=query,
                                search_type="dfs_query_then_fetch")
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(f"The following exception occured while trying to execute 'get' call to ElasticSearch instance: {repr(e)}")

        results.update(self._process_advanced_search_results(domains, skip, size, unique))

        return results


    # -- Internal --


    def _es_connector(self):
        """Return python ElasticSearch client.

        Returns: (elasticsearch.ElasticSearch) python ElasticSearch client

        Raises:
            ESConnectionError - when cannot create and initialize python client
        """
        security_args = dict()

        # Check if client is cached      TODO: Right now cant do. The client is not pickle-able (which is what Flask cache does)
        #es_client = self._cache.get("es_client")
        #if es_client is not None and es_client.ping():
        #    return self._cache.get("es_client")
        if current_app.config["ELASTICSEARCH"].get("user", None) is not None and current_app.config["ELASTICSEARCH"].get("pass" , None) is not None:
            security_args["http_auth"] = (current_app.config["ELASTICSEARCH"]["user"],
                                        current_app.config["ELASTICSEARCH"]["pass"])
        if current_app.config["ELASTICSEARCH"].get("cacert", None)is not None:
            security_args["use_ssl"] = True
            security_args["ca_certs"] = current_app.config["ELASTICSEARCH"]["cacert"]

        try:
            es = Elasticsearch(current_app.config["ELASTICSEARCH"]["uri"],
                            max_retries=100,
                            retry_on_timeout=True,
                            **security_args)
            # TODO: originally tried to do 'es.ping()' as a connection test as well
            # but when tested with no ES instance running, this would indefinitely hang

            #self._cache.set("es_client", es, 600)  TODO: Right now cant do. The client is not pickle-able (which is what Flask cache does)
            return es
        except elasticsearch.ImproperlyConfigured as e:
            raise ESConnectionError(f"The following ElasticSearch client config error occured: {repr(e)}")
        except elasticsearch.ElasticsearchException:
            raise EsConnectionError(f"The following ElasticSearch client config error occured: {repr(e)}")

    def _create_search_query(self, key, value, filt, limit, low, high, versionSort):
        """
        
        Raises:
            ValueError
        """
        es_source = None
        # If filter key requested, use it.
        if filt == "domainName":
            es_source = ["domainName"]
        elif filt is not None:
            es_source = [f"details.{filt}"]

        query_filter = {"term": {key: value}}
        final_filter = [query_filter]
        version_filter = None
        lowUpdate = None

        try:
            (low, lowUpdate) = low.split('.')
        except Exception as e:
            pass

        if low is not None:
            if low == high or high is None:  # single version
                try:
                    version_filter = [{"term": {"dataVersion": int(low)}}]
                    if lowUpdate is not None:
                        if int(lowUpdate) == 0:
                            updateVersionQuery = \
                                {"bool":
                                {"should":
                                [{"bool":
                                    {"must_not":
                                    {"exists":
                                    {"field": "updateVersion"}}}},
                                {"term": {"updateVersion": int(lowUpdate)}}]}}
                        else:
                            updateVersionQuery = \
                                {"term": {"updateVersion": int(lowUpdate)}}
                        version_filter.append(updateVersionQuery)
                except Exception as e:  # TODO XXX
                    raise RuntimeError(f"The following unexepcted error ocurred while trying to create search query: {repr(e)}")
            elif high is not None:
                try:
                    version_filter = [{"range":
                                    {"dataVersion":
                                        {"gte": int(low), "lte": int(high)}}}]
                except Exception as e:
                    raise ValueError("Low and High values must be integers")

        if version_filter is not None:
            final_filter.extend(version_filter)

        query = {"query": {
                "bool": {
                "filter": final_filter}},
                "size": limit}

        if versionSort:
            query["sort"] = [{"dataVersion": {"order": "asc"}},
                            {"updateVersion": {"order": "asc",
                                                "missing": 0,
                                                "unmapped_type": "long"}}]
        if es_source:
            query["_source"] = es_source

        return query

    def _process_search_query_results(self, domains):
        """
        Raises:
            RuntimeError
        """
        results = {}
        results["total"] = domains["hits"]["total"]
        results["data"] = []
        try:
            for domain in domains["hits"]["hits"]:
                pdomain = domain["_source"]
                # Take each key in details (if any) and stuff it in top level dict.
                if "details" in pdomain:
                    for k, v in pdomain["details"].items():
                        pdomain[k] = v
                    del pdomain["details"]
                if "dataVersion" in pdomain:
                    pdomain["Version"] = pdomain["dataVersion"]
                    del pdomain["dataVersion"]

                if "updateVersion" in pdomain:
                    pdomain["UpdateVersion"] = pdomain["updateVersion"]
                    del pdomain["updateVersion"]
                else:
                    pdomain["UpdateVersion"] = 0

                results["data"].append(pdomain)

            results["avail"] = len(results["data"])
            results["success"] = True
        except Exception as e:
            raise RuntimeError(f"The following error occured while processing results from Elasticsearch: {repr(e)}")
        return results

    def _process_advanced_search_results(self, domains, skip, size, unique):
        """
        
        Raises:
            RuntimeError
        """
        results = {}
        try:
            if not unique:
                results["total"] = domains["hits"]["total"]
                results["data"] = []

                for domain in domains["hits"]["hits"]:
                    pdomain = domain["_source"]
                    # Take each key in details (if any) and stuff it in top level dict.
                    if "details" in pdomain:
                        for k, v in pdomain["details"].items():
                            pdomain[k] = v
                        del pdomain["details"]
                    if "dataVersion" in pdomain:
                        pdomain["Version"] = pdomain["dataVersion"]
                        del pdomain["dataVersion"]
                    if "updateVersion" in pdomain:
                        pdomain["UpdateVersion"] = pdomain["updateVersion"]
                        del pdomain["updateVersion"]
                    results["data"].append(pdomain)

                results["avail"] = len(results["data"])
                results["skip"] = skip
                results["page_size"] = size
                results["success"] = True
            else:
                buckets = domains["aggregations"]["domains"]["buckets"]
                results["total"] = len(buckets)
                results["data"] = []

                for bucket in buckets:
                    domain = bucket["top_domains"]["hits"]["hits"][0]
                    pdomain = domain["_source"]
                    # Take each key in details (if any) and stuff it in top level dict.
                    if "details" in pdomain:
                        for k, v in pdomain["details"].items():
                            pdomain[k] = v
                        del pdomain["details"]
                    if "dataVersion" in pdomain:
                        pdomain["Version"] = pdomain["dataVersion"]
                        del pdomain["dataVersion"]
                    if "updateVersion" in pdomain:
                        pdomain["UpdateVersion"] = pdomain["updateVersion"]
                        del pdomain["updateVersion"]
                    results["data"].append(pdomain)

                results["avail"] = len(buckets)
                results["skip"] = 0
                results["page_size"] = size
                results["success"] = True
        except Exception as e:
            raise RuntimeError(f"The following error occured while processing results from Elasticsearch: {repr(e)}")
        return results

    def _process_cluster_stats_results(self, results):
        """Process cluster stats results

        Args:
            results (dict): results blob for cluster stats

        Returns: (dict) processed stats blob

        """
        stats = {"domainStats": {},
                    "histogram": {},
                    "creation": results["cache_time"]}

        try:
            for bucket in results["aggregations"]["type"]["buckets"]:
                stats["domainStats"][bucket["key"]] = \
                    (bucket["doc_count"], bucket["unique"]["value"])
            stats["domainStats"] = \
                collections.OrderedDict(sorted(stats["domainStats"].items()))

            for bucket in results["aggregations"]["created"]["dates"]["buckets"]:
                date_label = "/".join(bucket["key_as_string"].split("-"))
                if date_label not in stats["histogram"]:
                    stats["histogram"][date_label] = {}
                stats["histogram"][date_label]["created"] = bucket["doc_count"]

            for bucket in results["aggregations"]["updated"]["dates"]["buckets"]:
                date_label = "/".join(bucket["key_as_string"].split("-"))
                if date_label not in stats["histogram"]:
                    stats["histogram"][date_label] = {}
                stats["histogram"][date_label]["updated"] = bucket["doc_count"]

            stats["histogram"] = \
                collections.OrderedDict(sorted(stats["histogram"].items()))
        except Exception as e:
            CACHE.delete("cluster_stats")
            #TODO: Log? or raise runtime error?

        return stats

    def _create_data_table_search_query(self, key, value, skip, pagesize, sortset, sfilter, low, high):
        """ """
        query_filter = {"term": {key: value}}
        final_filter = [query_filter]
        version_filter = None
        lowUpdate = None

        try:
            (low, lowUpdate) = low.split('.')
        except Exception as e:
            pass

        if low is not None:
            if low == high or high is None:  # single version
                try:
                    version_filter = [{"term": {"dataVersion": int(low)}}]
                except Exception as e:
                    raise ValueError("Low must be interger value")

                if lowUpdate is not None:
                    if int(lowUpdate) == 0:
                        updateVersionQuery = \
                            {"bool":
                            {"should":
                            [{"bool":
                                {"must_not":
                                {"exists":
                                {"field": "updateVersion"}}}},
                                {"term": {"updateVersion": int(lowUpdate)}}]}}
                    else:
                        updateVersionQuery = \
                            {"term": {"updateVersion": int(lowUpdate)}}
                    version_filter.append(updateVersionQuery)
            elif high is not None:
                try:
                    version_filter = [{"range":
                                    {"dataVersion":
                                        {"gte": int(low), "lte": int(high)}}}]
                except Exception as e:
                    raise ValueError("Low and High values must be integers")

        if version_filter is not None:
            final_filter.extend(version_filter)

        qquery = None

        if sfilter is not None:
            try:
                regx = ".*%s.*" % sfilter
            except Exception as e:
                results["aaData"] = []
                results["iTotalRecords"] = self.record_count()
                results["iTotalDisplayRecords"] = 0
                results["message"] = "Invalid Search Parameter"
                return results
            else:
                shoulds = []
                for skey in [keys[0] for keys in current_app.config["SEARCHKEYS"]]:
                    if skey == key:  # Don"t bother filtering on the key field
                        continue
                    if skey != current_app.config["SEARCHKEYS"][0][0]:
                        snkey = "details.{skey}"
                    else:
                        snkey = skey
                    exp = {"regexp":
                        {snkey:
                            {"value": regx}}}

                    shoulds.append(exp)

                qquery = {"should": shoulds}

        query = {"query": {"bool": {"filter": final_filter}},
                "from": skip,
                "size": pagesize}

        if qquery is not None:
            query["query"]["bool"].update(qquery)

        if len(sortset) > 0:
            sorter = []
            for s in sortset:
                sorter.append({s[0]: {"order": s[1]}})

            query["sort"] = sorter

        return query 

    def _process_data_table_search_results(self, domains):
        results = {}
        results["aaData"] = []
        # Total Records in all indices
        results["iTotalRecords"] = self.record_count()
        try:
            if domains["hits"]["total"] > 0:
                for domain in domains["hits"]["hits"]:
                    updateVersion = domain["_source"].get("updateVersion", 0)
                    entryVersion = "%d.%d" % (domain["_source"]["dataVersion"],
                                            updateVersion)
                    # First element is placeholder for expansion cell
                    # TODO Make this configurable?
                    details = domain["_source"]["details"]
                    dom_arr = ["&nbsp;",
                            domain["_source"]["domainName"],
                            details["registrant_name"],
                            details["contactEmail"],
                            details["standardRegCreatedDate"],
                            details["registrant_telephone"],
                            entryVersion]
                    results["aaData"].append(dom_arr)

            # Number of Records after any sort of filtering/searching
            results["iTotalDisplayRecords"] = domains["hits"]["total"]
            results["success"] = True
        except Exception as e:
            raise RuntimeError(f"Unexpected error processing domain results from ElasticSearch: {repr(r)}")
        return results

    def _process_adv_data_table_search(self, domains, unique):
        """
        Raises:
            RuntimError
        """
        results = {"success": False}
        results["aaData"] = []
        try:
            if "error" in domains:
                results["message"] = "Error"
                return results

            if not unique:
                results["iTotalDisplayRecords"] = domains["hits"]["total"]
                results["iTotalRecords"] = self.record_count()

                if domains["hits"]["total"] > 0:
                    for domain in domains["hits"]["hits"]:
                        pdomain = domain["_source"]
                        details = pdomain["details"]
                        updateVersion = pdomain.get("updateVersion", 0)
                        entryVersion = "%d.%d" % (pdomain["dataVersion"],
                                                updateVersion)
                        # Take each key in details (if any) and stuff
                        # it in top level dict.
                        dom_arr = ["&nbsp;",
                                pdomain["domainName"],
                                details["registrant_name"],
                                details["contactEmail"],
                                details["standardRegCreatedDate"],
                                details["registrant_telephone"],
                                entryVersion,
                                "%.2f" % round(domain["_score"], 2)]
                        results["aaData"].append(dom_arr)

                results["success"] = True
            else:
                buckets = domains["aggregations"]["domains"]["buckets"]
                results["iTotalDisplayRecords"] = len(buckets)
                results["iTotalRecords"] = len(buckets)

                for bucket in buckets:
                    domain = bucket["top_domains"]["hits"]["hits"][0]
                    pdomain = domain["_source"]
                    details = pdomain["details"]
                    updateVersion = pdomain.get("updateVersion", 0)
                    entryVersion = "%d.%d" % (pdomain["dataVersion"], updateVersion)
                    # For some reason the _score goes away in the
                    # aggregations if you sort by it
                    dom_arr = ["&nbsp;",
                            pdomain["domainName"],
                            details["registrant_name"],
                            details["contactEmail"],
                            details["standardRegCreatedDate"],
                            details["registrant_telephone"],
                            entryVersion,
                            "%.2f" % round(domain["sort"][0], 2)]

                    results["aaData"].append(dom_arr)

                results["success"] = True
        except Exception as e:
            raise RuntimeError(f"Unexpected error processing domain results from ElasticSearch: {repr(e)}")
        return results

    def _create_advanced_query(self, query, skip, size, unique, sort=None):
        """Advanced query creator.

        Args:
            query (str): search query
            skip (int): starting results offset
            size (int): number of result hits to retrieve
            unique (bool): restrict results to unique set of records
            sort (list): tuples of the form (sort_key, sort_direction)

        Returns: (dict) ElasticSearch query object

        Raises:
            RuntimeError - when unexpected error occurs creating the advanced query
            ValueError - when error occurs when yacc parses supplied query string
        """
        try:
            try:
                q = yacc.parse(query)
            except (KeyError, ValueError) as e:
                raise ValueError(f"The following error occured while yacc tried to parse query string: {repr(e)}")
            if not unique:
                if sort is not None and len(sort) > 0:
                    sortParams = list()
                    fields = set()
                    for (field, direction) in sort:
                        fields.add(field)
                        sortParams.append({field: {"order": direction}})
                        if field == "dataVersion":
                            sortParams.append({"updateVersion":
                                            {"order": "desc",
                                                "missing": 0,
                                                "unmapped_type": "long"}})

                    if "_score" not in fields:
                        sortParams.append({"_score": {"order": "desc"}})

                    if "domainName" not in fields:
                        sortParams.append({"domainName": {"order": "asc"}})

                    if "dataVersion" not in fields:
                        sortParams.extend(
                            [{"dataVersion": {"order": "desc"}},
                            {"updateVersion": {"order": "desc",
                                                "missing": 0,
                                                "unmapped_type": "long"}}])
                else:
                    sortParams = [
                        {"_score": {"order": "desc"}},
                        {"domainName": {"order": "asc"}},
                        {"dataVersion": {"order": "desc"}},
                        {"updateVersion": {"order": "desc",
                                        "missing": 0,
                                        "unmapped_type": "long"}}]
                q["sort"] = sortParams
                q["size"] = size
                q["from"] = skip
            else:
                q["size"] = 0
                q["aggs"] = {"domains": {
                            "terms": {"field": "domainName",
                                    "size": size,
                                    "order": {"max_score": "desc"}},
                            "aggs": {"max_score": {"max": {"script": "_score"}},
                                    "top_domains": {
                                    "top_hits": {
                                        "size": 1,
                                        "sort":
                                        [{"_score": {"order": "desc"}},
                                        {"dataVersion": {"order": "desc"}},
                                        {"updateVersion":
                                        {"order": "desc",
                                        "missing": 0,
                                        "unmapped_type": "long"}}]}}}}}
            return q
        except Exception as e:
            raise RuntimeError(f"The following runtime error occured while creating advanced query: {repr(e)}")
