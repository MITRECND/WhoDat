import time
import elasticsearch
from elasticsearch import helpers

from pydat.core.elastic import ElasticHandler

METADATA_INDEX_BODY = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "keyword"
                    }
                }
            }
        }
    },
    # Override some default mapping types
    "mappings": {
        "properties": {
            "dateProcessed": {
                "type": "keyword"
            },
            "dateIngest": {
                "type": "keyword"
            }
        }
    }
}


class BulkFetchError(Exception):
    pass


class BulkShipError(Exception):
    pass


class RolloverRequired(Exception):
    def __init__(self, write_alias, search_alias, **kwargs):
        self.write_alias = write_alias
        self.search_alias = search_alias
        super().__init__(**kwargs)


class IngestHandler(ElasticHandler):
    ROLLOVER_TIME = 30  # 30 seconds

    def __init__(
        self,
        rollover_size=50000000,
        **kwargs
    ):
        self.rollover_size = rollover_size
        super().__init__(**kwargs)

    @property
    def templateExists(self):
        es = self.connect()
        try:
            es.indices.get_template(
                name=self.indexNames.template_name
            )
        except elasticsearch.exceptions.NotFoundError:
            return False

        return True

    @property
    def metaExists(self):
        es = self.connect()

        if es.indices.exists(self.indexNames.meta):
            return True
        else:
            return False

    @property
    def metaRecord(self):
        es = self.connect()

        try:
            result = es.get(index=self.indexNames.meta, id=0)
            if result['found']:
                metadata = result['_source']
                return metadata
            else:
                return None
        except Exception as e:
            raise RuntimeError(e)

    def getMetadata(self, version):
        es = self.connect()

        try:
            record = es.get(
                index=self.indexNames.meta,
                id=version)['_source']
        except Exception as e:
            raise RuntimeError(e)

        return record

    def updateMetadata(self, version, body):
        es = self.connect()

        try:
            es.update(
                index=self.indexNames.meta, id=version,
                body=body
            )
        except Exception:
            raise

    def createMetadata(self, version, body):
        es = self.connect()

        try:
            es.create(index=self.indexNames.meta, id=version, body=body)
        except Exception:
            raise

    def clearInterrupted(self):
        if not self.metaExists or self.metaRecord is None:
            raise RuntimeError("Cannot find metadata records for cluster")

        self.updateMetadata(0, {'doc': {'importing': 0}})

    def configTemplate(self, template):
        es = self.connect()
        template["index_patterns"] = [self.indexNames.template_pattern]

        # Shared template info
        template["aliases"][self.indexNames.search] = {}

        # Actually configure template
        es.indices.put_template(
            name=self.indexNames.template_name,
            body=template
        )

    def refreshIndices(self, name=None):
        es = self.connect()
        if name is None:
            name = self.indexNames.search
        es.indices.refresh(index=name)

    def refreshIndex(self, name):
        es = self.connect()
        es.indices.refresh(index=name)

    def resolveAlias(self):
        es = self.connect()
        index_list = es.indices.get_alias(name=self.indexNames.orig_search)
        return sorted(index_list.keys(), reverse=True)

    @property
    def rolloverRequiredOrig(self):
        es = self.connect()
        try:
            doc_count = int(
                es.cat.count(
                    index=self.indexNames.orig_write, h="count"
                )
            )

            if doc_count > self.rollover_size:
                return True
        except elasticsearch.exceptions.NotFoundError:
            self.logger.warning("Unable to find required index\n")
        except Exception:
            self.logger.exception("Unexpected exception\n")

        return False

    @property
    def rolloverRequiredDelta(self):
        es = self.connect()
        try:
            doc_count = int(
                es.cat.count(
                    index=self.indexNames.delta_write, h="count"
                )
            )

            if doc_count > self.rollover_size:
                return True
        except elasticsearch.exceptions.NotFoundError:
            self.logger.warning("Unable to find required index\n")
        except Exception:
            self.logger.exception("Unexpected exception\n")

        return False

    @property
    def rolloverRequired(self):
        self.logger.debug("Checking if rollover required")
        if self.rolloverRequiredOrig:
            return 1
        elif self.rolloverRequiredDelta:
            return 2
        else:
            return 0

    def rolloverIndices(self, write_alias, search_alias):
        es = self.connect()
        try:
            orig_name = list(es.indices.get_alias(name=write_alias).keys())[0]
        except Exception:
            self.logger.exception("Unable to get/resolve index alias")

        try:
            es.indices.rollover(
                alias=write_alias,
                body={
                    "aliases": {search_alias: {}}
                }
            )
        except Exception:
            self.logger.exception("Unable to issue rollover command: %s")

        try:
            es.indices.refresh(index=orig_name)
        except Exception:
            self.logger.exception("Unable to refresh rolled over index")

    def rolloverTimer(self, timer):
        now = time.time()
        if now - timer >= self.ROLLOVER_TIME:
            timer = now
            if self.rolloverRequiredOrig:
                raise RolloverRequired(
                    write_alias=self.indexNames.orig_write,
                    search_alias=self.indexNames.orig_search
                )
            elif self.rolloverRequiredDelta:
                raise RolloverRequired(
                    write_alias=self.indexNames.delta_write,
                    search_alias=self.indexNames.delta_search
                )

        return timer

    def fetchDocuments(self, documents):
        es = self.connect()

        fetched = None
        try:
            response = es.mget(body={"docs": documents})
            fetched = response['docs']
        except elasticsearch.exceptions.TransportError as e:
            if (e.status_code == 429 and "circuit_break" in e.error):
                raise BulkFetchError((
                    "fetch size too large! Reduce and try again"
                )) from None
            else:
                raise RuntimeError("Unexpected elastic transport error")
        except Exception:
            raise

        return fetched

    def shipDocuments(self, documents_iter, bulk_size):
        es = self.connect()

        try:
            for (ok, response) in helpers.streaming_bulk(
                es, documents_iter,
                raise_on_error=False,
                chunk_size=bulk_size
            ):
                resp = response[list(response)[0]]
                if not ok and resp['status'] not in [404, 409]:
                    self.logger.debug("Response: %s" % (str(resp)))
                    raise BulkShipError(
                        "Error making bulk request, received "
                        f"error reason: {resp['error']['reason']}"
                    )
        except elasticsearch.exceptions.TransportError as e:
            if (e.status_code == 429 and "circuit_break" in e.error):
                raise BulkShipError((
                    "Bulk Ship too large! Reduce and try again"
                )) from None
            else:
                raise RuntimeError(
                    "Unhandled elasticsearch transport exception")
        except Exception:
            raise

    def initialize(self, template):
        es = self.connect()
        self.configTemplate(template=template)

        es.indices.create(
            index=self.indexNames.meta,
            body=METADATA_INDEX_BODY
        )

        # Create the 0th metadata entry
        metadata = {
            "metadata": 0,
            "firstVersion": 0,
            "lastVersion": 0,
            "importing": 0,
        }

        es.create(
            index=self.indexNames.meta,
            id=0,
            body=metadata
        )

        # Create the first whois rollover index
        index_name = "%s-data-000001" % self.indexNames.prefix
        es.indices.create(
            index=index_name,
            body={
                "aliases": {
                    self.indexNames.orig_write: {},
                    self.indexNames.orig_search: {}
                }
            }
        )

        # Create the first whois delta rollover index
        delta_name = "%s-data-delta-000001" % self.indexNames.prefix
        es.indices.create(
            index=delta_name,
            body={
                "aliases": {
                    self.indexNames.delta_write: {},
                    self.indexNames.delta_search: {}
                }
            }
        )
