import time

from flask_caching import Cache

from pydat.core.elastic.search.search_handler import SearchHandler


CACHE_TIMEOUT = 300  # Flask cache timeout


class FlaskElasticHandler:
    """Wrapper class around SearchHandler that adds support for flask,
    including app initialization and caching of queries
    """
    def __init__(self):
        self.es = None

    def _generate_config(self, app):
        # Collate elastic arguments
        elastic_config = app.config['ELASTICSEARCH']
        self.elastic_arguments = {
            'hosts': elastic_config['uri'],
            'username': elastic_config['user'],
            'password': elastic_config['pass'],
            'cacert': elastic_config['cacert'],
            'disable_sniffing': False,
            'indexPrefix':  elastic_config['indexPrefix'],
            'max_retries': 100,
            'retry_on_timeout': True,
        }

    def init_app(self, app):
        app.config["CACHE_TYPE"] = "SimpleCache"
        app.config["CACHE_DEFAULT_TIMEOUT"] = CACHE_TIMEOUT
        self._cache = Cache(app)
        self._generate_config(app)
        self._search_keys = app.config['SEARCHKEYS']

        try:
            self.es = SearchHandler(
                search_keys=self._search_keys,
                **self.elastic_arguments)
            self.es.connect()
        except RuntimeError:
            raise
        except Exception:
            raise

    def record_count(self):
        """Return record count of ES record index.

        Returns: (int) record count

        Raises:
            ESConnectionError - when ElasticSearch connection
                cannot be established.
            ESQueryError - when error occurs at ElasticSearch
                from sent query/request.
        """
        records = self._cache.get("record_count")
        if records is None:
            records = int(self.es.record_count)
            self._cache.set("record_count", records)

        return int(records)

    def cluster_stats(self):
        """Return stats blob on ElasticSearch cluster.

        Returns: (dict) stats blob

        Raises:
            ESConnectionError - when ElasticSearch connection
                cannot be established.
            ESQueryError - when error occurs at ElasticSearch
                from sent query/request.
        """

        stats = self._cache.get("cluster_stats")
        if stats is None:
            stats = self.es.cluster_stats
            # Cache for an hour since this is a relatively expensive query
            # whose results shouldn't change often
            stats["cache_time"] = time.time()
            self._cache.set("cluster_stats", stats, 3600)

        return stats

    def cluster_health(self):
        """Retrieve cluster health status.

        Returns: (str) status of the cluster

        Raises:
            ESConnectionError - when ElasticSearch connection
                cannot be established.
            ESQueryError - when error occurs at ElasticSearch from
                sent query/request.
        """
        health = self._cache.get("cluster_health")
        if health is None:
            health = self.es.cluster_health
            self._cache.set("cluster_health", health)

        return health

    def last_version(self):
        """Retrieve last version of index.

        Returns: (float) version number

        Raises:
            ESConnectionError - when ElasticSearch connection
                cannot be established.
            ESQueryError - when error occurs at ElasticSearch
                from sent query/request.
            RuntimeError - when error occurs processing ElasticSearch response
        """
        lastVersion = self._cache.get("last_version")
        if lastVersion is None:
            lastVersion = self.es.last_version
            self._cache.set("last_version", lastVersion)

        return lastVersion

    def last_update(self):
        """Retrieve last update version of index.

        Returns: (float) last update version

        Raises:
            ESConnectionError - when ElasticSearch connection
                cannot be established.
            ESQueryError - when error occurs at ElasticSearch from
                sent query/request.
        """
        last_update = self._cache.get("last_update")
        if last_update is None:
            last_update = self.es.last_update
            self._cache.set("last_update", last_update)

        return last_update

    def metadata(self, version=None):
        """Retrieve metadata information on index.

        Args:
            version (float): data version

        Returns: (dict) metadata blob

        Raises:
            ESConnectionError - when ElasticSearch connection
                cannot be established.
            ESQueryError - when error occurs at ElasticSearch from
                sent query/request.
        """
        if version is None:
            res = self._cache.get("all_metadata")
            if res is None:
                res = self.es.metadata()
                self._cache.set("all_metadata", res)
        else:
            version = int(version)
            res = self._cache.get(f"metadata_{version}")
            if res is None:
                res = self.es.metadata(version)
                self._cache.set(f"metadata_{version}", res)

        return res

    def getLatest(self, key, value):
        return self.es.getLatest(key, value)

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
        return self.es.search(key, value, filt, limit, low, high, versionSort)

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
        return self.es.advanced_search(search_string, skip, size, unique, sort)
