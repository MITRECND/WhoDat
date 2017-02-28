#!/usr/bin/env python

import sys
import os
import json
import time
import argparse
import threading
from threading import Event
import Queue
import elasticsearch
from elasticsearch import helpers
from elasticsearch_populate import connectElastic, configTemplate,\
                                   optimizeIndex, unOptimizeIndex,\
                                   UPDATE_KEY,\
                                   WHOIS_META_FORMAT_STRING,\
                                   WHOIS_SEARCH_FORMAT_STRING,\
                                   WHOIS_WRITE_FORMAT_STRING,\
                                   WHOIS_ORIG_WRITE_FORMAT_STRING,\
                                   WHOIS_DELTA_WRITE_FORMAT_STRING

read_docs = 0
written_docs = 0


def progressThread(stop, total_docs):
    maxLength = len(str(total_docs))
    format_string = "\rTotal: %%.%dd\t[%%.%dd/%%.%dd]" % (maxLength, maxLength, maxLength)
    while not stop.isSet():
        sys.stdout.write(format_string % (total_docs, read_docs, written_docs))
        sys.stdout.flush()
        time.sleep(.2)

    sys.stdout.write(format_string % (total_docs, read_docs, written_docs))
    sys.stdout.write("\n")
    sys.stdout.flush()

def bulkThread(scanFinished, des, bulkQueue, bulkOpts):
    global written_docs
    def bulkIter():
        while not (scanFinished.isSet() and bulkQueue.empty()):
            try:
                req = bulkQueue.get_nowait()
            except Queue.Empty:
                time.sleep(.01)
                continue

            yield req

    try:
        for success, response in helpers.parallel_bulk(des, bulkIter(), raise_on_error=False, thread_count=bulkOpts['threads'], chunk_size=bulkOpts['size']):
            written_docs += 1
            if not success:
                sys.stdout.write("Error: %s\n" % str(response))
    except Exception as e:
        sys.stdout.write("Unexpected error making bulk request(s): %s\n" % (str(e)))

def scanIndex(source_es, source_index, dest_index, bulkRequestQueue, scanOpts):
    global read_docs

    for doc in helpers.scan(source_es, index=source_index, size=scanOpts['size']):
        _id = doc['_id']
        _type = doc['_type']
        _source = doc['_source']

        _source[UPDATE_KEY] = 0

        bulkRequest = {
            '_op_type': 'index',
            '_index': dest_index,
            '_type': _type,
            '_source': _source,
            '_id': _id
        }

        read_docs += 1
        bulkRequestQueue.put(bulkRequest)


def updateIndex(source_es, source_index, bulkRequestQueue, scanOpts):
    global read_docs

    for doc in helpers.scan(source_es, index=source_index, size=scanOpts['size']):
        _id = doc['_id']
        _type = doc['_type']

        bulkRequest = {
            '_op_type': 'index',
            '_index': source_index,
            '_type': _type,
            '_id': _id,
            'doc': {UPDATE_KEY: 0}
        }

        read_docs += 1
        bulkRequestQueue.put(bulkRequest)


def checkVersion(es):
    try:
        es_versions = []
        for version in es.cat.nodes(h='version').strip().split('\n'):
            es_versions.append([int(i) for i in version.split('.')])
    except Exception as e:
        sys.stderr.write("Unable to retrieve destination ElasticSearch version ... %s\n" % (str(e)))
        sys.exit(1)

    for version in es_versions:
        if version[0] < 5 or (version[0] >= 5 and version[1] < 2):
            return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Script to migrate previous format 'delta' indexes to new format")

    parser.add_argument("-u", "--es-uri", nargs="*", dest="source_uri",
        default=['localhost:9200'], help="Location(s) of ElasticSearch server (e.g., foo.server.com:9200) can take multiple endpoints")
    parser.add_argument("-p", "--index-prefix", action="store", dest="index_prefix",
        default='whois', help="Index prefix to use in ElasticSearch (default: whois)")

    parser.add_argument("-g", "--upgrade", action="store_true", default=False, dest="upgrade",
                        help="If upgrading an existing cluster, this will update aliases/names used to match new format and migrate metadata")

    parser.add_argument("-d", "--dest-es-uri", nargs="*", dest="dest_uri",
        default=['localhost:9200'], help="Location(s) of destination ElasticSearch server (e.g., foo.server.com:9200) can take multiple endpoints")
    parser.add_argument("-n", "--dest-index-prefix", action="store", dest="dest_index_prefix",
        default='whois', help="Index prefix to use in destination ElasticSearch (default: whois)")

    parser.add_argument("--bulk-threads", type=int, dest="bulk_threads", default=4, help="Number of bulk threads to use with destination ES cluster")
    parser.add_argument("--bulk-size", type=int, dest="bulk_size", default=1000, help="Number of records to batch when making bulk requests")
    parser.add_argument("--scan-size", type=int, dest="scan_size", default=1000, help="Number of records to fetch when making scan requests")

    options = parser.parse_args()

    bulk_options = {'threads': options.bulk_threads,
                    'size': options.bulk_size}

    scan_options = {'size': options.scan_size}

    data_template = None
    template_path = os.path.dirname(os.path.realpath(__file__))

    try:
        with open("%s/es_templates/data.template" % template_path, 'r') as dtemplate:
            data_template = json.loads(dtemplate.read())
    except Exception as e:
        sys.stderr.write("Unable to read data template\n")
        sys.exit(1)

    major = elasticsearch.VERSION[0]
    if major != 5:
        sys.stderr.write("Python ElasticSearch library version must coorespond to version of ElasticSearch being used -- Library major version: %d\n" % (major))
        sys.exit(1)

    try:
        source_es = connectElastic(options.source_uri)
    except elasticsearch.exceptions.TransportError as e:
        sys.stderr.write("Unable to connect to source ElasticSearch ... %s\n" % (str(e)))
        sys.exit(1)

    global WHOIS_META, WHOIS_SEARCH
    WHOIS_META      = WHOIS_META_FORMAT_STRING % (options.dest_index_prefix)
    WHOIS_SEARCH    = WHOIS_SEARCH_FORMAT_STRING % (options.dest_index_prefix)

    if options.upgrade: # Update existing cluster to new convention
        options.dest_uri = options.source_uri

    try:
        dest_es = connectElastic(options.dest_uri)
    except elasticsearch.exceptions.TransportError as e:
        sys.stderr.write("Unable to connect to destination ElasticSearch ... %s\n" % (str(e)))
        sys.exit(1)

    if not checkVersion(dest_es):
        sys.stderr.write("Destination ElasticSearch version must be 5.2 or greater\n")
        sys.exit(1)

    try:
        doc = source_es.get(index="@%s_meta" % (options.index_prefix), id=0)
        if 'deltaIndexes' not in doc['_source'] or not doc['_source']['deltaIndexes']:
            options.deltaIndexes=False
        else:
            options.deltaIndexes=True
    except:
        sys.stderr.write("Unable to fetch required data from metadata index")
        sys.exit(1)

    # Initialize template in destination cluster
    configTemplate(dest_es, data_template, options.dest_index_prefix)

    if options.upgrade:
        global read_docs
        scanFinished = Event()
        stop = Event()
        bulkRequestQueue = Queue.Queue(maxsize=10000)

        try:
            meta_count = source_es.count(index="@%s_meta" % (options.index_prefix))['count']
        except:
            sys.stderr.write("Unable to get number of entries\n")
            sys.exit(1)

        try:
            doc_count = source_es.count(index="%s-*" % (options.index_prefix))['count']
        except:
            sys.stderr.write("Unable to get number of metadata entries\n")
            sys.exit(1)

        total_docs = meta_count + doc_count

        progress_thread = threading.Thread(target=progressThread, args=(stop, total_docs))
        progress_thread.start()

        bulk_thread = threading.Thread(target=bulkThread, args=(scanFinished, dest_es, bulkRequestQueue, bulk_options))
        bulk_thread.daemon=True
        bulk_thread.start()

        alias_actions = []
        res = source_es.search(index="@%s_meta" % (options.index_prefix), body={"query": {"match_all": {}}, "sort": "metadata", "size": "10000"})
        try:
            if res['hits']['total'] > 0:
                lastVersion = res['hits']['hits'][0]['_source']['lastVersion']
                for i, doc in enumerate(res['hits']['hits']):
                    _id = doc['_id']
                    _type = doc['_type']
                    _source = doc['_source']
                    version = _source['metadata']

                    if version != 0:
                        if options.deltaIndexes:
                            source_index = "%s-%d-o" % (options.index_prefix, version)
                            actions = [{"add": {"index": source_index, "alias": WHOIS_ORIG_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)}},
                                       {"add": {"index": source_index, "alias":  WHOIS_SEARCH}}]

                            if version != lastVersion:
                                source_delta_index = "%s-%d-d" % (options.index_prefix, version)
                                actions.extend([{"add": {"index": source_delta_index, "alias": WHOIS_DELTA_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)}},
                                               {"add": {"index": source_delta_index, "alias": WHOIS_SEARCH}}])
                        else:
                            source_index = "%s-%d" % (options.index_prefix, version)
                            actions = [{"add": {"index": source_index, "alias": WHOIS_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)}},
                                       {"add": {"index": source_index, "alias":  WHOIS_SEARCH}}]

                        alias_actions.extend(actions)

                        

                    bulkRequest = {
                        '_op_type': 'update',
                        '_index': WHOIS_META,
                        '_type': _type,
                        '_id': _id,
                        'doc': {UPDATE_KEY: 0}
                    }

                    bulkRequestQueue.put(bulkRequest)

                alias_actions.append({"add": {"index": "@%s_meta" % (options.index_prefix), "alias": WHOIS_META}})
                dest_es.indices.update_aliases(body={"actions": alias_actions})
        except KeyboardInterrupt as e:
            pass

    else:
        # Create Metadata Index
        dest_es.indices.create(index=WHOIS_META, body = {"settings" : {
                                                                "index" : {
                                                                    "number_of_shards" : 1,
                                                                    "analysis" : {
                                                                        "analyzer" : {
                                                                            "default" : {
                                                                                "type" : "keyword"
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        })

        global read_docs
        scanFinished = Event()
        stop = Event()
        bulkRequestQueue = Queue.Queue(maxsize=10000)

        try:
            meta_count = source_es.count(index="@%s_meta" % (options.index_prefix))['count']
        except:
            sys.stderr.write("Unable to get number of entries\n")
            sys.exit(1)

        try:
            doc_count = source_es.count(index="%s-*" % (options.index_prefix))['count']
        except:
            sys.stderr.write("Unable to get number of metadata entries\n")
            sys.exit(1)

        total_docs = meta_count + doc_count

        progress_thread = threading.Thread(target=progressThread, args=(stop, total_docs))
        progress_thread.start()

        bulk_thread = threading.Thread(target=bulkThread, args=(scanFinished, dest_es, bulkRequestQueue, bulk_options))
        bulk_thread.daemon=True
        bulk_thread.start()

        lastVersion = 0
        res = source_es.search(index="@%s_meta" % (options.index_prefix), body={"query": {"match_all": {}}, "sort": "metadata", "size": "10000"})
        try:
            if res['hits']['total'] > 0:
                lastVersion = res['hits']['hits'][0]['_source']['lastVersion']
                for i, doc in enumerate(res['hits']['hits']):
                    read_docs += 1
                    _id = doc['_id']
                    _type = doc['_type']
                    _source = doc['_source']
                    version = _source['metadata']

                    if version != 0:
                        _source[UPDATE_KEY] = 0

                        if options.deltaIndexes:
                            source_index = "%s-%d-o" % (options.index_prefix, version)
                            dest_index = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)

                            if version != lastVersion:
                                source_delta_index = "%s-%d-d" % (options.index_prefix, version)
                                dest_delta_index = WHOIS_DELTA_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)
                                dest_es.indices.create(index=WHOIS_DELTA_WRITE_FORMAT_STRING % (options.dest_index_prefix, version))
                                optimizeIndex(dest_es, dest_delta_index, 0)
                                scanIndex(source_es, source_delta_index, dest_delta_index, bulkRequestQueue, scan_options)

                        else:
                            source_index = "%s-%d" % (options.index_prefix, version)
                            dest_index = WHOIS_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)

                        body = {}
                        if i == 1: # double shards for first set
                            body['settings'] = {"index": {
                                                    "number_of_shards": int(data_template["settings"]["number_of_shards"]) * 2
                                                }}
                        dest_es.indices.create(index=dest_index, body=body)
                        optimizeIndex(dest_es, dest_index, 0)
                        scanIndex(source_es, source_index, dest_index, bulkRequestQueue, scan_options)


                    bulkRequest = {
                        '_op_type': 'index',
                        '_index': WHOIS_META,
                        '_type': _type,
                        '_source': _source,
                        '_id': _id
                    }

                    bulkRequestQueue.put(bulkRequest)
            else:
                sys.stderr.write("Unable to find any metadata entries\n")
                sys.exit(1)
        except KeyboardInterrupt as e:
            scanFinished.set()
            stop.set()

        scanFinished.set()
        bulk_thread.join()
        stop.set()
        progress_thread.join()


        for i, doc in enumerate(res['hits']['hits']):
            version = doc['_source']['metadata']
            if version != 0:
                if options.deltaIndexes:
                    source_index = "%s-%d-o" % (options.index_prefix, version)
                    dest_index = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)

                    if version != lastVersion:
                        dest_delta_index = WHOIS_DELTA_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)
                        unOptimizeIndex(dest_es, dest_delta_index, data_template)
                else:
                    source_index = "%s-%d" % (options.index_prefix, version)
                    dest_index = WHOIS_WRITE_FORMAT_STRING % (options.dest_index_prefix, version)

                unOptimizeIndex(dest_es, dest_index, data_template)

    
if __name__ == "__main__":
    main()
