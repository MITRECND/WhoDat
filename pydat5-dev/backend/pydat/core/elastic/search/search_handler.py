import datetime
import collections
import elasticsearch

from pydat.core.query_parser import parseQuery
from pydat.core.elastic import ElasticHandler
from pydat.core.elastic.exceptions import (
    ESQueryError,
    ESNotFoundError,
)


class SearchHandler(ElasticHandler):
    """Class to abstract search related usage of Elasticsearch

    This class inherits from ElasticHandler and provides functions that
    facilitate searching of Elasticsearch. Ideally all direct calls to
    elasticsearch are done through this class.
    """
    def __init__(self, search_keys, **kwargs):
        super().__init__(**kwargs)

    def record_count(self):
        """Return number of records in cluster

        Raises:
            ESQueryError: General error attempting to query record count

        Returns:
            int: Number of records in the cluster
        """
        es = self.connect()
        try:
            records = es.cat.count(index=self.indexNames.search, h="count")
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(
                "The following exception occured while trying to execute "
                f"'count' call to ElasticSearch instance: {repr(e)}")
        return int(records)

    def cluster_stats(self):
        """Generate and return statistics on the domains in the cluster

        Raises:
            ESQueryError: General error attempting to query cluster stats

        Returns:
            dict: A dict containing the output of the computation of stats
        """
        es = self.connect()
        tstr = datetime.date.today().timetuple()
        year = tstr[0] - 2
        month = tstr[1]
        year_string = "%i-%.2i-01 00:00:00" % (year, month)

        query = {"aggs": {
                    "type": {
                        "terms": {
                            "field": "tld",
                            "size": 10000
                        },
                        "aggregations": {
                            "unique": {
                                "cardinality": {
                                    "field": "domainName"
                                }
                            },
                        }
                    },
                    "created": {
                        "filter": {
                            "range": {
                                "details.standardRegCreatedDate": {
                                    "gte": year_string
                                }
                            }
                        },
                        "aggs": {
                            "dates": {
                                "date_histogram": {
                                    "field": "details.standardRegCreatedDate",
                                    "interval": "1M",
                                    "format": "yyyy-MM"
                                }
                            }
                        }
                    },
                    "updated": {
                        "filter": {
                            "range": {
                                "details.standardRegUpdatedDate": {
                                    "gte": year_string}
                            }
                        },
                        "aggs": {
                            "dates": {
                                "date_histogram": {
                                    "field": "details.standardRegUpdatedDate",
                                    "interval": "1M",
                                    "format": "yyyy-MM"
                                }
                            }
                            }
                    }
                },
                "size": 0}

        try:
            results = es.search(index=self.indexNames.search, body=query)
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(
                "The following exception occured while trying to execute "
                f"'search' call to ElasticSearch instance: {repr(e)}")

        stats = self._process_cluster_stats_results(results)

        return stats

    def cluster_health(self):
        """Return health status of cluster

        Raises:
            ESQueryError: General error attempting to query data from elastic

        Returns:
            str: A string representing status of cluster ("green", "yellow",
                "red")
        """
        es = self.connect()
        try:
            health = es.cluster.health()
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(
                "The following exception occured while trying to execute "
                f"'health' call to ElasticSearch instance: {repr(e)}")
        return health["status"]

    def last_version(self):
        """Get the version of the last metadata record in the cluster

        Raises:
            RuntimeError: Raised if no data was found in the cluster.
                Potentiall indicative of elastic not having been initailized
            ESQueryError: General error attempting to query elastic

        Returns:
            int: The last version that was imported
        """
        es = self.connect()
        try:
            result = es.get(index=self.indexNames.meta, id=0)
            if result["found"]:
                return result["_source"]["lastVersion"]
            else:
                raise RuntimeError(
                    "Could not process result from ElasticSearch")
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(
                "The following exception occured while trying to execute "
                f"'get' call to ElasticSearch instance: {repr(e)}")

    def last_update(self):
        """Get the most recent metadata record/entry from the cluster

        Raises:
            ESQueryError: General issue attempting to query cluser
            RuntimeError: If no record is found. This is potentially
                indicative of a cluster not being properly initialized

        Returns:
            dict: A dict representing the latest metadata record in the cluster
        """
        es = self.connect()
        try:
            res = es.search(
                index=self.indexNames.meta,
                body={
                    "query": {
                        "match_all": {}
                    },
                    "sort": [{"metadata": {"order": "desc"}}],
                    "size": 1
                }
            )
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(
                "The following exception occured while trying to "
                "execute 'search' call to ElasticSearch "
                f"instance: {repr(e)}")

        if res["hits"]["total"]["value"] >= 1:
            data = res["hits"]["hits"][0]["_source"]
            return data
        else:
            raise RuntimeError("Unable to query cluster metadata")

    def metadata(self, version=None):
        """Get all metadata or a specific metadata entry

        Args:
            version (int, optional): The specific version to query.
                Defaults to None.

        Raises:
            ESQueryError: General error when attempting to query elastic
            RuntimeError: Raised when no records are found in the cluster
            ESQueryError: General error when attempting to query elastic
            ESNotFoundError: Raised when a query for a specific version fails

        Returns:
            list(dict): A list of dicts representing the requested
                metdata entries
        """
        es = self.connect()

        if version is None:
            try:
                res = es.search(
                    index=self.indexNames.meta,
                    body={
                        "query": {"match_all": {}},
                        "sort": "metadata",
                        "size": 9999,
                        "track_total_hits": True,
                    }
                )
            except elasticsearch.ElasticsearchException as e:
                raise ESQueryError(
                    "The following exception occured while trying to "
                    "execute 'search' call to ElasticSearch "
                    f"instance: {repr(e)}")

            if res["hits"]["total"]["value"] > 0:
                return [r["_source"] for r in res['hits']['hits']]
            else:
                raise RuntimeError("Unable to find any metadata records")
        else:

            try:
                res = es.get(index=self.indexNames.meta, id=version)
            except elasticsearch.ElasticsearchException as e:
                raise ESQueryError(
                    "The following exception occured while trying to execute "
                    f"'get' call to ElasticSearch instance: {repr(e)}")

            if res["found"]:
                return [res["_source"]]
            else:
                raise ESNotFoundError(
                    "Unable to find metadata record by that id")

    def getLatest(self, key, value):
        """Method to obtain the latest entries of domains by a given key

        Args:
            key (str): A valid field name in the domain records
            value (str): The value of the field

        Raises:
            RuntimeError: Generic error raised if unable to process
                response from elastic

        Returns:
            dict: A dict containing the records that match the given query
        """
        if key not in self.top_level_keys:
            key = f"details.{key}"

        value = value.lower()
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {key: value}},
                        {"term": {"historical": False}},
                    ]
                }
            },
            "size": 100
        }

        try:
            domains = self._search(query)
        except ESQueryError:
            raise

        results = {
            "total": domains["hits"]["total"]["value"],
            "data": []
        }

        records = self._flatten_records(domains["hits"]["hits"])
        results["data"] = records

        return results

    def search(
            self, key, value, filt=None, limit=10000,
            low=None, high=None, versionSort=False):
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
            ESConnectionError - when ElasticSearch connection
                cannot be established.
            RuntimeError - when  error occurs when creating ES query,
                or when processing ElasticSearch results
            ESQueryError - when error occurs at ElasticSearch from
                sent query/request.
            ValueError - when 'low' and 'high' args are not integers
        """

        if key not in self.top_level_keys:
            key = f"details.{key}"

        value = value.lower()

        query = self._create_search_query(
            key, value, filt, limit, low, high, versionSort)

        try:
            domains = self._search(query)
        except ESQueryError:
            raise

        try:
            results = {"total": domains["hits"]["total"]["value"]}
            records = self._flatten_records(domains["hits"]["hits"])
            results["data"] = records
        except KeyError:
            raise RuntimeError(
                "Unable to find expected key in response from elastic"
            )
        except RuntimeError:
            raise

        return results

    def advanced_search(
            self, search_string, skip=0, size=20,
            unique=False, sort=None):  # TODO XXX versions, dates, etc
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
            RuntimeError - when unexpected error occurs when creating
                advanced query or processing results from Elasticsearch
        """
        query = self._create_advanced_query(
            search_string, skip, size, unique, sort)
        try:
            domains = self._search(query, search_type="dfs_query_then_fetch")
        except ESQueryError:
            raise

        records = self._process_advanced_search_results(
            domains, skip, size, unique)

        try:
            results = {"total": domains["hits"]["total"]["value"]}
            records = self._flatten_records(domains["hits"]["hits"])
            results["data"] = records
        except KeyError:
            raise RuntimeError(
                "Unable to find expected key in response from elastic"
            )
        except RuntimeError:
            raise

        return results

    def _search(self, query, search_type=None):
        es = self.connect()
        try:
            domains = es.search(
                index=self.indexNames.search,
                body=query,
                search_type=search_type
            )
        except elasticsearch.ElasticsearchException as e:
            raise ESQueryError(
                "The following exception occured while trying to execute "
                f"'get' call to ElasticSearch instance: {repr(e)}")

        return domains

    def _flatten_records(self, records):
        out_records = []

        try:
            for domain in records:
                pdomain = domain["_source"]
                # Take each key in details (if any) and stuff it in
                # top level dict.
                if "details" in pdomain:
                    for k, v in pdomain["details"].items():
                        pdomain[k] = v
                    del pdomain["details"]
                if "_score" in domain:
                    pdomain["_score"] = domain["_score"]

                out_records.append(pdomain)

            return out_records
        except Exception as e:
            raise RuntimeError(
                "The following error occured while processing results "
                f"from Elasticsearch: {repr(e)}")

    def _create_search_query(
            self, key, value, filt, limit, low, high, versionSort):
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

        if low is not None:
            if low == high or high is None:  # single version
                try:
                    version_filter = [{"term": {"dataVersion": low}}]
                except Exception as e:  # TODO XXX
                    raise RuntimeError(
                        "The following unexepcted error ocurred while trying "
                        f"to create search query: {repr(e)}")
            elif high is not None:
                try:
                    version_filter = [
                        {
                            "range": {
                                "dataVersion": {
                                    "gte": int(low),
                                    "lte": int(high)
                                }
                            }
                        }
                    ]
                except Exception:
                    raise ValueError("Low and High values must be integers")

        if version_filter is not None:
            final_filter.extend(version_filter)

        query = {
            "query": {
                "bool": {
                    "filter": final_filter
                }
            },
            "size": limit
        }

        if versionSort:
            query["sort"] = [{"dataVersion": {"order": "asc"}}]
        if es_source:
            query["_source"] = es_source

        return query

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
            RuntimeError - when unexpected error occurs creating the
                advanced query
            ValueError - when error occurs when parseQuey parses supplied
                query string
        """
        try:
            q = parseQuery(query)
            q['track_total_hits'] = True
        except (KeyError, ValueError) as e:
            raise ValueError(
                "The following error occured while trying to parse "
                f"query string: {repr(e)}")

        try:
            if not unique:
                if sort is not None and len(sort) > 0:
                    sortParams = list()
                    fields = set()
                    for (field, direction) in sort:
                        fields.add(field)

                        if field not in self.top_level_keys:
                            field = f"details.{field}"

                        sortParams.append({field: {"order": direction}})

                    if "_score" not in fields:
                        sortParams.append({"_score": {"order": "desc"}})

                    if "domainName" not in fields:
                        sortParams.append({"domainName": {"order": "asc"}})

                    if "dataVersion" not in fields:
                        sortParams.extend(
                            [{"dataVersion": {"order": "desc"}}])
                else:
                    sortParams = [
                        {"_score": {"order": "desc"}},
                        {"domainName": {"order": "asc"}},
                        {"dataVersion": {"order": "desc"}},
                    ]
                q["sort"] = sortParams
                q["size"] = size
                q["from"] = skip
            else:
                q["size"] = 0
                q["aggs"] = {
                    "domains": {
                        "terms": {
                            "field": "domainName",
                            "size": size,
                            "order": {"max_score": "desc"}},
                        "aggs": {
                            "max_score": {"max": {"script": "_score"}},
                            "top_domains": {
                                "top_hits": {
                                    "size": 1,
                                    "sort": [
                                        {"_score": {"order": "desc"}},
                                        {"dataVersion": {
                                            "order": "desc"
                                        }},
                                    ]}}}}}
            return q
        except Exception as e:
            raise RuntimeError(
                "The following runtime error occured while creating "
                f"advanced query: {repr(e)}")

    def _process_advanced_search_results(self, domains, skip, size, unique):
        """

        Raises:
            RuntimeError
        """
        results = {}
        try:
            if not unique:
                results["total"] = domains["hits"]["total"]["value"]

                records = self._flatten_records(domains["hits"]["hits"])
                results["data"] = records
                results["avail"] = len(results["data"])
                results["skip"] = skip
                results["page_size"] = size
                results["success"] = True
            else:
                buckets = domains["aggregations"]["domains"]["buckets"]
                results["total"] = len(buckets)
                results["data"] = []

                for bucket in buckets:
                    records = self._flatten_records(
                        bucket["top_domains"]["hits"]["hits"][0:]
                    )
                    results["data"].extend(records)

                results["avail"] = len(buckets)
                results["skip"] = 0
                results["page_size"] = size
                results["success"] = True
        except Exception as e:
            raise RuntimeError(
                "The following error occured while processing results from "
                f"Elasticsearch: {repr(e)}")
        return results

    def _process_cluster_stats_results(self, results):
        """Process cluster stats results

        Args:
            results (dict): results blob for cluster stats

        Returns: (dict) processed stats blob

        """
        stats = {
            "domainStats": {},
            "histogram": {},
        }

        try:
            for bucket in results["aggregations"]["type"]["buckets"]:
                stats["domainStats"][bucket["key"]] = \
                    (bucket["doc_count"], bucket["unique"]["value"])
            stats["domainStats"] = \
                collections.OrderedDict(sorted(stats["domainStats"].items()))

            for bucket in results[
                    "aggregations"]["created"]["dates"]["buckets"]:
                date_label = "/".join(bucket["key_as_string"].split("-"))
                if date_label not in stats["histogram"]:
                    stats["histogram"][date_label] = {}
                stats["histogram"][date_label]["created"] = bucket["doc_count"]

            for bucket in results[
                    "aggregations"]["updated"]["dates"]["buckets"]:
                date_label = "/".join(bucket["key_as_string"].split("-"))
                if date_label not in stats["histogram"]:
                    stats["histogram"][date_label] = {}
                stats["histogram"][date_label]["updated"] = bucket["doc_count"]

            stats["histogram"] = \
                collections.OrderedDict(sorted(stats["histogram"].items()))
        except Exception:
            raise RuntimeError("unable to process stats")

        return stats
