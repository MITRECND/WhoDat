from types import SimpleNamespace
import elasticsearch


class ElasticHandler:
    """Base Elasticsearch handler class

        This class abstract interaction with Elasticsearch and enables
        common usage of elasticsearch without needing direct knowledge of
        things such as which metadata keys exist or how to check
        the version of the cluster. It is meant to be used as a base
        class for futher interactions with elastic
    """

    def __init__(
        self,
        hosts,
        username=None,
        password=None,
        cacert=None,
        disable_sniffing=False,
        max_retries=10,
        retry_on_timeout=True,
        timeout=30,
        # Add other options not currently handled for es config
        otherOptions=None,
        indexPrefix="pydat",
        logger=None
    ):
        if logger is None:
            import logging
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.indexNames = SimpleNamespace()
        self._indexFormatter(indexPrefix)
        self.top_level_keys = [
            'domainName',
            'tld',
            '_score'
        ]
        self.metadata_key_map = SimpleNamespace(**{
            'VERSION_KEY': 'dataVersion',
            'FIRST_SEEN': 'dataFirstSeen',
            'DATE_FIRST_SEEN': 'dateFirstSeen',
            'DATE_LAST_SEEN': 'dateLastSeen',
            'DATE_CREATED': 'dateCreated',
            'DATE_UPDATED': 'dateUpdated',
            'HISTORICAL': 'historical'
        })
        self.metadata_keys = list(vars(self.metadata_key_map).values())
        self.top_level_keys.extend(self.metadata_keys)

        self._es = None
        self._es_version = None
        self.elastic_args = {
            'hosts': hosts,
            'sniff_on_start': (not disable_sniffing),
            'sniff_on_connection_fail': (not disable_sniffing),
            'sniff_timeout': (None if disable_sniffing else 100),
            'max_retries': 100,
            'retry_on_timeout': True,
            'timeout': 100
        }

        security_args = dict()

        if username is not None and password is None:
            raise ValueError("password must be supplied with username")

        if (username is not None and password is not None):
            security_args["http_auth"] = (
                username,
                password
            )

        if cacert is not None:
            security_args["use_ssl"] = True
            security_args["ca_certs"] = cacert

        if len(security_args) > 0:
            self.elastic_args.update(security_args)

        if isinstance(otherOptions, dict):
            self.elastic_args.update(otherOptions)

    def _indexFormatter(self, prefix):
        self.indexNames.prefix = prefix
        self.indexNames.orig_write = "%s-data-write" % prefix
        self.indexNames.delta_write = "%s-data-delta-write" % prefix
        self.indexNames.orig_search = "%s-data-orig" % prefix
        self.indexNames.delta_search = "%s-data-delta" % prefix
        self.indexNames.search = "%s-data-search" % prefix
        self.indexNames.meta = "%s-meta" % prefix
        self.indexNames.template_pattern = "%s-data-*" % prefix
        self.indexNames.template_name = "%s-template" % prefix

    def connect(self):
        """Return an instance of Elasticsearch connection object

        This class will check if an existing instance exists and if not
        will create one before returning said instance

        Raises:
            RuntimeError: If elasticsearch indicates it is
                improperly configured
            RuntimeError: If a generic elasticsearch exception occurrs

        Returns:
            elasticsearch.Elasticsearch(): An instance of the
                Elasticsearch objet
        """

        if self._es is None:
            try:
                self._es = elasticsearch.Elasticsearch(**self.elastic_args)
            except elasticsearch.ImproperlyConfigured as e:
                raise RuntimeError(e)
            except elasticsearch.ElasticsearchException as e:
                raise RuntimeError(e)
            except Exception:
                self.logger.exception(
                    "Unexpected exception making elastic connection")
                raise
        return self._es

    def getVersion(self):
        """Get the version of the cluster

        Raises:
            ValueError: If the major version is less than 7

        Returns:
            int: The highest version of Elastic in the cluster
        """
        if self._es_version is None:
            es = self.connect()

            try:
                node_versions = []
                for version in es.cat.nodes(h='version').strip().split('\n'):
                    node_versions.append([int(i) for i in version.split('.')])
            except Exception:
                self.logger.exception("Unexpected exception checking versions")
                raise

            highest_version = 0
            for version in node_versions:
                if version[0] > highest_version:
                    highest_version = version[0]
                if version[0] < 7:
                    raise ValueError(
                        "Elasticsearch 7.0 is the minimum supported version")

            self._es_version = highest_version

        return self._es_version

    def checkVersion(self):
        """Check cluster version against library version

        Raises:
            RuntimeError: If installed python library version does
                not match version of cluster
        """
        library_version = elasticsearch.VERSION[0]

        if self.getVersion() != library_version:
            raise RuntimeError(
                "Python library installed does not "
                "match with greatest (major) version in cluster")
