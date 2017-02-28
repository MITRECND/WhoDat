#!/usr/bin/env python

import sys
import os
import unicodecsv
import hashlib
import signal
import time
import argparse
import threading
from threading import Thread, Lock
import multiprocessing
from multiprocessing import Process, Queue as mpQueue, JoinableQueue as jmpQueue
from pprint import pprint
import json
import traceback
import uuid
from io import BytesIO

from HTMLParser import HTMLParser
import Queue as queue

import elasticsearch
from elasticsearch import helpers

STATS = {'total': 0,
         'new': 0,
         'updated': 0,
         'unchanged': 0,
         'duplicates': 0
        }

VERSION_KEY = 'dataVersion'
UPDATE_KEY = 'updateVersion'
UNIQUE_KEY = 'dataUniqueID'
FIRST_SEEN = 'dataFirstSeen'

CHANGEDCT = {}

shutdown_event = multiprocessing.Event()
finished_event = multiprocessing.Event()
bulkError_event = multiprocessing.Event()

WHOIS_WRITE_FORMAT_STRING = "%s-%d"
WHOIS_ORIG_WRITE_FORMAT_STRING = "%s-orig-%d"
WHOIS_DELTA_WRITE_FORMAT_STRING = "%s-delta-%d"

WHOIS_SEARCH_FORMAT_STRING = "%s-search"
WHOIS_META_FORMAT_STRING = ".%s-meta"

WHOIS_SEARCH = None
WHOIS_META = None

def connectElastic(uri):
    es = elasticsearch.Elasticsearch(uri,
                                     sniff_on_start=True,
                                     max_retries=100,
                                     retry_on_timeout=True,
                                     sniff_on_connection_fail=True,
                                     sniff_timeout=1000,
                                     timeout=100)

    return es

######## READER THREAD ######
def reader_worker(work_queue, options):
    if options.directory:
        scan_directory(work_queue, options.directory, options)
    elif options.file:
        parse_csv(work_queue, options.file, options)
    else:
        print("File or Directory required")

def scan_directory(work_queue, directory, options):
    for root, subdirs, filenames in os.walk(directory):
        if len(subdirs):
            for subdir in sorted(subdirs):
                scan_directory(work_queue, subdir, options)
        for filename in sorted(filenames):
            if shutdown_event.is_set():
                return
            if options.extension != '':
                fn, ext = os.path.splitext(filename)
                if ext and ext[1:] != options.extension:
                    continue

            full_path = os.path.join(root, filename)
            parse_csv(work_queue, full_path, options)

def check_header(header):
    for field in header:
        if field == "domainName":
            return True

    return False


def parse_csv(work_queue, filename, options):
    if shutdown_event.is_set():
        return

    if options.verbose:
        print("Processing file: %s" % filename)

    csvfile = open(filename, 'rb')
    dnsreader = unicodecsv.reader(csvfile, strict = True, skipinitialspace = True)
    try:
        header = next(dnsreader)
        if not check_header(header):
            raise unicodecsv.Error('CSV header not found')

        for row in dnsreader:
            if shutdown_event.is_set():
                break
            work_queue.put({'header': header, 'row': row})
    except unicodecsv.Error as e:
        sys.stderr.write("CSV Parse Error in file %s - line %i\n\t%s\n" % (os.path.basename(filename), dnsreader.line_num, str(e)))


####### STATS THREAD ###########
def stats_worker(stats_queue):
    global STATS
    while True:
        stat = stats_queue.get()
        if stat == 'finished':
            break
        STATS[stat] += 1

###### ELASTICSEARCH PROCESS ######

def es_bulk_shipper_proc(insert_queue, options):
    os.setpgrp()

    global bulkError_event

    def bulkIter():
        while not (finished_event.is_set() and insert_queue.empty()):
            try:
                req = insert_queue.get_nowait()
                insert_queue.task_done()
            except queue.Empty:
                time.sleep(.1)
                continue

            yield req

    es = connectElastic(options.es_uri)
    try:
        for (ok, response) in helpers.parallel_bulk(es, bulkIter(), raise_on_error=False, thread_count=options.bulk_threads, chunk_size=options.bulk_size):
            resp = response[response.keys()[0]]
            if not ok and resp['status'] not in [404, 409]:
                    if not bulkError_event.is_set():
                        bulkError_event.set()
                    sys.stderr.write("Error making bulk request, received error reason: %s\n" % (resp['error']['reason']))
    except Exception as e:
        sys.stderr.write("Unexpected error processing bulk commands: %s\n%s\n" % (str(e), traceback.format_exc()))
        if not bulkError_event.is_set():
            bulkError_event.set()

######## WORKER THREADS #########

def update_required(current_entry, options):
    if current_entry is None:
        return True

    if current_entry['_source'][VERSION_KEY] == options.identifier: #This record already up to date
        return False 
    else:
        return True

def process_worker(work_queue, insert_queue, stats_queue, options):
    global shutdown_event
    global finished_event
    try:
        os.setpgrp()
        es = connectElastic(options.es_uri)
        while not shutdown_event.is_set():
            try:
                work = work_queue.get_nowait()
                try:
                    entry = parse_entry(work['row'], work['header'], options)

                    if entry is None:
                        print("Malformed Entry")
                        continue

                    domainName = entry['domainName']

                    if options.firstImport:
                        current_entry_raw = None
                    else:
                        current_entry_raw = find_entry(es, domainName, options)

                    stats_queue.put('total')
                    process_entry(insert_queue, stats_queue, es, entry, current_entry_raw, options)
                finally:
                    work_queue.task_done()
            except queue.Empty as e:
                if finished_event.is_set():
                    break
                time.sleep(.0001)
            except Exception as e:
                sys.stdout.write("Unhandled Exception: %s, %s\n" % (str(e), traceback.format_exc()))
    except Exception as e:
        sys.stdout.write("Unhandled Exception: %s, %s\n" % (str(e), traceback.format_exc()))

def process_reworker(work_queue, insert_queue, stats_queue, options):
    global shutdown_event
    global finished_event
    try:
        os.setpgrp()
        es = connectElastic(options.es_uri)
        while not shutdown_event.is_set():
            try:
                work = work_queue.get_nowait()
                try:
                    entry = parse_entry(work['row'], work['header'], options)
                    if entry is None:
                        print("Malformed Entry")
                        continue

                    domainName = entry['domainName']
                    current_entry_raw = find_entry(es, domainName, options)

                    if update_required(current_entry_raw, options):
                        stats_queue.put('total')
                        process_entry(insert_queue, stats_queue, es, entry, current_entry_raw, options)
                finally:
                    work_queue.task_done()
            except queue.Empty as e:
                if finished_event.is_set():
                    break
                time.sleep(.01)
            except Exception as e:
                sys.stdout.write("Unhandled Exception: %s, %s\n" % (str(e), traceback.format_exc()))
    except Exception as e:
        sys.stdout.write("Unhandeled Exception: %s, %s\n" % (str(e), traceback.format_exc()))

def parse_entry(input_entry, header, options):
    if len(input_entry) == 0:
        return None

    htmlparser = HTMLParser()

    details = {}
    domainName = ''
    for i,item in enumerate(input_entry):
        if any(header[i].startswith(s) for s in options.ignore_field_prefixes):
            continue
        if header[i] == 'domainName':
            if options.vverbose:
                sys.stdout.write("Processing domain: %s\n" % item)
            domainName = item
            continue
        if item == "":
            details[header[i]] = None
        else:
            details[header[i]] = htmlparser.unescape(item)

    entry = {
                VERSION_KEY: options.identifier,
                FIRST_SEEN: options.identifier,
                UPDATE_KEY: options.updateVersion,
                'details': details,
                'domainName': domainName,
            }

    return entry

def process_command(request, index, _id, _type, entry = None):
    if request == 'create':
        command = {
                   "_op_type": "create",
                   "_index": index,
                   "_type": _type,
                   "_id": _id,
                   "_source": entry
                  }
        return command
    elif request == 'update':
        command = {
                   "_op_type": "update",
                   "_index": index,
                   "_id": _id,
                   "_type": _type,
                  }
        command.update(entry)
        return command
    elif request == 'delete':
        command = {
                    "_op_type": "delete",
                    "_index": index,
                    "_id": _id,
                    "_type": _type,
                  }
        return command
    elif request =='index':
        command = {
                    "_op_type": "index",
                    "_index": index,
                    "_type": _type,
                    "_source": entry
                  }
        if _id is not None:
            command["_id"] = _id
        return command

    return None #TODO raise instead?


def process_entry(insert_queue, stats_queue, es, entry, current_entry_raw, options):
    domainName = entry['domainName']
    details = entry['details']
    global CHANGEDCT
    api_commands = []

    if current_entry_raw is not None:
        current_index = current_entry_raw['_index']
        current_id = current_entry_raw['_id']
        current_type = current_entry_raw['_type']
        current_entry = current_entry_raw['_source']

        if not options.update and (current_entry[VERSION_KEY] == options.identifier): # duplicate entry in source csv's?
            if options.vverbose:
                sys.stdout.write('%s: Duplicate\n' % domainName)
            stats_queue.put('duplicates')
            return

        if options.exclude is not None:
            details_copy = details.copy()
            for exclude in options.exclude:
                del details_copy[exclude]

            changed = set(details_copy.items()) - set(current_entry['details'].items())
            diff = len(set(details_copy.items()) - set(current_entry['details'].items())) > 0

        elif options.include is not None:
            details_copy = {}
            for include in options.include:
                try: #TODO
                    details_copy[include] = details[include]
                except:
                    pass

            changed = set(details_copy.items()) - set(current_entry['details'].items()) 
            diff = len(set(details_copy.items()) - set(current_entry['details'].items())) > 0
            
        else:
            changed = set(details.items()) - set(current_entry['details'].items()) 
            diff = len(set(details.items()) - set(current_entry['details'].items())) > 0

            # The above diff doesn't consider keys that are only in the latest in es
            # So if a key is just removed, this diff will indicate there is no difference
            # even though a key had been removed.
            # I don't forsee keys just being wholesale removed, so this shouldn't be a problem
        for ch in changed:
            if ch[0] not in CHANGEDCT:
                CHANGEDCT[ch[0]] = 0
            CHANGEDCT[ch[0]] += 1

        if diff:
            if options.enable_delta_indexes:
                index_name = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)
            else:
                index_name = WHOIS_WRITE_FORMAT_STRING % (options.index_prefix, options.indentifier)

            if options.update and ((current_index == index_name) or (options.previousVersion == 0)): #Can't have two documents with the the same id in the same index
                stats_queue.put('new')
                if options.vverbose:
                    sys.stdout.write("%s: New/Re-Registered\n" % domainName)

                # Effectively move old entry into different document
                if options.enable_delta_indexes:
                    api_commands.append(process_command(
                                                        'create',
                                                        WHOIS_DELTA_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier),
                                                        "%s&%d" % (current_id, options.updateVersion),
                                                        current_type,
                                                        current_entry
                                        ))
                else:
                    api_commands.append(process_command(
                                                        'create',
                                                        current_index,
                                                        "%s&%d" % (current_id, options.updateVersion),
                                                        current_type,
                                                        current_entry
                                        ))

                entry_id = generate_id(domainName, options.identifier)
                entry[UNIQUE_KEY] = entry_id
                (domain_name_only, tld) = parse_domain(domainName)
                api_commands.append(process_command(
                                                     'index',
                                                     current_index,
                                                     current_id,
                                                     current_type,
                                                     entry
                                     ))
            else:
                stats_queue.put('updated')
                if options.vverbose:
                    sys.stdout.write("%s: Updated\n" % domainName)

                if options.enable_delta_indexes:
                    # Delete old entry, put into a 'diff' index
                    api_commands.append(process_command(
                                                        'delete',
                                                        current_index,
                                                        current_id,
                                                        current_type
                                        ))

                    # Put it into a previousVersion-d index so it doesn't potentially create
                    # a bunch of indexes that will need to be cleaned up later
                    api_commands.append(process_command(
                                                        'create',
                                                        WHOIS_DELTA_WRITE_FORMAT_STRING % (options.index_prefix, options.previousVersion),
                                                        current_id,
                                                        current_type,
                                                        current_entry
                                        ))

                if not options.update:
                    entry[FIRST_SEEN] = current_entry[FIRST_SEEN]
                entry_id = generate_id(domainName, options.identifier)
                entry[UNIQUE_KEY] = entry_id
                (domain_name_only, tld) = parse_domain(domainName)
                api_commands.append(process_command(
                                                     'create',
                                                     index_name,
                                                     domain_name_only,
                                                     tld,
                                                     entry
                                     ))
        else:
            if not options.update:
                stats_queue.put('unchanged')
                if options.vverbose:
                    sys.stdout.write("%s: Unchanged\n" % domainName)
                api_commands.append(process_command(
                                                     'update',
                                                     current_index,
                                                     current_id,
                                                     current_type,
                                                     {'doc': {
                                                                 VERSION_KEY: options.identifier,
                                                                'details': details
                                                             }
                                                     }
                                     ))
    else:
        stats_queue.put('new')
        if options.vverbose:
            sys.stdout.write("%s: New\n" % domainName)
        entry_id = generate_id(domainName, options.identifier)
        entry[UNIQUE_KEY] = entry_id
        (domain_name_only, tld) = parse_domain(domainName)

        if options.enable_delta_indexes:
            index_name = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)
        else:
            index_name = WHOIS_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)

        if options.update:
            api_commands.append(process_command(
                                                'index',
                                                index_name,
                                                domain_name_only,
                                                tld,
                                                entry
                                ))
        else:
            api_commands.append(process_command(
                                                'create',
                                                index_name,
                                                domain_name_only,
                                                tld,
                                                entry
                                ))
    for command in api_commands:
        insert_queue.put(command)

def generate_id(domainName, identifier):
    dhash = hashlib.md5(domainName.encode('utf-8')).hexdigest() + str(identifier)
    return dhash

def parse_tld(domainName):
    parts = domainName.rsplit('.', 1)
    return parts[-1]

def parse_domain(domainName):
    parts = domainName.rsplit('.', 1)
    return (parts[0], parts[1])
    

def find_entry(es, domainName, options):
    try:
        (domain_name_only, tld) = parse_domain(domainName)
        docs = []
        for index_name in options.INDEX_LIST:
            getdoc = {'_index': index_name, '_type': tld, '_id': domain_name_only}
            docs.append(getdoc)

        result = es.mget(body = {"docs": docs})

        for res in result['docs']:
            if res['found']:
                return res

        return None
    except Exception as e:
        print("Unable to find %s, %s" % (domainName, str(e)))
        return None


def unOptimizeIndex(es, index, template):
    try:
        es.indices.put_settings(index=index,
                            body = {"settings": {
                                        "index": {
                                            "number_of_replicas": template['settings']['number_of_replicas'],
                                            "refresh_interval": template['settings']["refresh_interval"]
                                        }
                                    }
                            })
    except Exception as e:
        pass

def optimizeIndex(es, index, refresh_interval="300s"):
    try:
        es.indices.put_settings(index=index,
                            body = {"settings": {
                                        "index": {
                                            "number_of_replicas": 0,
                                            "refresh_interval": refresh_interval
                                        }
                                    }
                            })
    except Exception as e:
        pass


def configTemplate(es, data_template, index_prefix):
    if data_template is not None:
        data_template["template"] = "%s-*" % index_prefix
        es.indices.put_template(name='%s-template' % index_prefix, body = data_template)



###### MAIN ######

def main():
    global STATS
    global VERSION_KEY
    global CHANGEDCT
    global shutdown_event
    global finished_event
    global bulkError_event

    parser = argparse.ArgumentParser()

    dataSource = parser.add_mutually_exclusive_group(required=True)
    dataSource.add_argument("-f", "--file", action="store", dest="file",
        default=None, help="Input CSV file")
    dataSource.add_argument("-d", "--directory", action="store", dest="directory",
        default=None, help="Directory to recursively search for CSV files -- mutually exclusive to '-f' option")
    dataSource.add_argument("--config-template-only", action="store_true", default=False, dest="config_template_only",
                        help="Configure the ElasticSearch template and then exit")

    parser.add_argument("-e", "--extension", action="store", dest="extension",
        default='csv', help="When scanning for CSV files only parse files with given extension (default: 'csv')")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-i", "--identifier", action="store", dest="identifier", type=int,
        default=None, help="Numerical identifier to use in update to signify version (e.g., '8' or '20140120')")
    mode.add_argument("-r", "--redo", action="store_true", dest="redo",
        default=False, help="Attempt to re-import a failed import or import more data, uses stored metadata from previous import (-o, -n, and -x not required and will be ignored!!)")
    mode.add_argument("-z", "--update", action= "store_true", dest="update",
        default=False, help = "Run the script in update mode. Intended for taking daily whois data and adding new domains to the current existing index in ES.")

    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
        default=False, help="Be verbose")
    parser.add_argument("--vverbose", action="store_true", dest="vverbose",
        default=False, help="Be very verbose (Prints status of every domain parsed, very noisy)")
    parser.add_argument("-s", "--stats", action="store_true", dest="stats",
        default=False, help="Print out Stats after running")

    updateMethod = parser.add_mutually_exclusive_group()
    updateMethod.add_argument("-x", "--exclude", action="store", dest="exclude",
        default="", help="Comma separated list of keys to exclude if updating entry")
    updateMethod.add_argument("-n", "--include", action="store", dest="include",
        default="", help="Comma separated list of keys to include if updating entry (mutually exclusive to -x)")

    parser.add_argument("-o", "--comment", action="store", dest="comment",
        default="", help="Comment to store with metadata")
    parser.add_argument("-u", "--es-uri", nargs="*", dest="es_uri",
        default=['localhost:9200'], help="Location(s) of ElasticSearch Server (e.g., foo.server.com:9200) Can take multiple endpoints")
    parser.add_argument("-p", "--index-prefix", action="store", dest="index_prefix",
        default='whois', help="Index prefix to use in ElasticSearch (default: whois)")
    parser.add_argument("-B", "--bulk-size", action="store", dest="bulk_size", type=int,
        default=1000, help="Size of Bulk Elasticsearch Requests")
    parser.add_argument("--optimize-import", action="store_true", dest="optimize_import",
        default=False, help="If enabled, will change ES index settings to speed up bulk imports, but if the cluster has a failure, data might be lost permanently!")

    parser.add_argument("-t", "--threads", action="store", dest="threads", type=int,
        default=2, help="Number of workers, defaults to 2. Note that each worker will increase the load on your ES cluster since it will try to lookup whatever record it is working on in ES")
    parser.add_argument("--bulk-threads", action="store", dest="bulk_threads", type=int,
        default=1, help="How many threads to spawn to send bulk ES messages. The larger your cluster, the more you can increase this")
    parser.add_argument("--enable-delta-indexes", action="store_true", dest="enable_delta_indexes",
        default=False, help="If enabled, will put changed entries in a separate index. These indexes can be safely deleted if space is an issue, also provides some other improvements")
    parser.add_argument("--es5", action="store_true", dest="es5", default=False,
                        help="If enabled, will use template made for ElasticSearch 5 -- only needs to be set on the first run of the system")
    parser.add_argument("--ignore-field-prefixes", nargs='*',dest="ignore_field_prefixes", type=str,
        default=['zoneContact','billingContact','technicalContact'], help="list of fields (in whois data) to ignore when extracting and inserting into ElasticSearch")

    options = parser.parse_args()

    if options.vverbose:
        options.verbose = True

    options.firstImport = False

    #as these are crafted as optional args, but are really a required mutually exclusive group, must check that one is specified
    if not (options.identifier or options.redo or options.update):
        print("Please select a script mode: Insert , Redo, or Update")
        parser.parse_args(["-h"])


    threads = []

    work_queue = jmpQueue(maxsize=10000)
    insert_queue = jmpQueue(maxsize=10000)
    stats_queue = mpQueue()

    global WHOIS_META, WHOIS_SEARCH
    # Process Index/Alias Format Strings
    WHOIS_META          = WHOIS_META_FORMAT_STRING % (options.index_prefix)
    WHOIS_SEARCH        = WHOIS_SEARCH_FORMAT_STRING % (options.index_prefix)

    data_template = None
    template_path = os.path.dirname(os.path.realpath(__file__))
    major = elasticsearch.VERSION[0]
    if major != 5:
        print("Python ElasticSearch library version must coorespond to version of ElasticSearch being used -- Library major version: %d" % (major))
        sys.exit(1)

    with open("%s/es_templates/data.template" % template_path, 'r') as dtemplate:
        data_template = json.loads(dtemplate.read())

    try:
        es = connectElastic(options.es_uri)
    except elasticsearch.exceptions.TransportError as e:
        print("Unable to connect to ElasticSearch ... %s" % (str(e)))
        sys.exit(1)

    try:
        es_versions = []
        for version in es.cat.nodes(h='version').strip().split('\n'):
            es_versions.append([int(i) for i in version.split('.')])
    except Exception as e:
        sys.stderr.write("Unable to retrieve destination ElasticSearch version ... %s\n" % (str(e)))
        sys.exit(1)

    for version in es_versions:
        if version[0] < 5 or (version[0] >= 5 and version[1] < 2):
            sys.stderr.write("Destination ElasticSearch version must be 5.2 or greater\n")
            sys.exit(1)


    if options.config_template_only:
        configTemplate(es, data_template, options.index_prefix)
        sys.exit(0)

    es = connectElastic(options.es_uri)
    metadata = None
    version_identifier = 0
    previousVersion = 0

    #Create the metadata index if it doesn't exist
    if not es.indices.exists(WHOIS_META):
        if options.identifier <= 0:
            print("Identifier must be greater than 0")
            sys.exit(1)

        if options.redo or options.update:
            print("Script cannot conduct a redo or update when no initial data exists")
            sys.exit(1)

        version_identifier = options.identifier

        configTemplate(es, data_template, options.index_prefix)

        #Create the metadata index with only 1 shard, even with thousands of imports
        #This index shouldn't warrant multiple shards
        #Also use the keyword analyzer since string analsysis is not important
        es.indices.create(index=WHOIS_META, body = {"settings" : {
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
        # Create the 0th metadata entry
        metadata = { "metadata": 0,
                     "firstVersion": options.identifier,
                     "lastVersion": options.identifier,
                     "deltaIndexes": options.enable_delta_indexes,
                    }
        es.create(index=WHOIS_META, doc_type='meta', id = 0, body = metadata)

        #Specially create the first index to have 2x the shards than normal
        #since future indices should be diffs of the first index (ideally)
        if options.enable_delta_indexes:
            index_name = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)
        else:
            index_name = WHOIS_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)

        es.indices.create(index=index_name,
                            body = {"settings": { 
                                        "index": { 
                                            "number_of_shards": int(data_template["settings"]["number_of_shards"]) * 2
                                        }
                                    }
                            })
        options.firstImport = True
    else:
        try:
            result = es.get(index=WHOIS_META, id=0)
            if result['found']:
                metadata = result['_source']
            else:
                raise Exception("Not Found")
        except:
            print("Error fetching metadata from index")
            sys.exit(1)

        options.enable_delta_indexes = metadata['deltaIndexes']

        if options.identifier is not None:
            if options.identifier < 1:
                print("Identifier must be greater than 0")
                sys.exit(1)
            if metadata['lastVersion'] >= options.identifier:
                print("Identifier must be 'greater than' previous identifier")
                sys.exit(1)

            version_identifier = options.identifier
            previousVersion = metadata['lastVersion']

            # Pre-emptively create index
            if options.enable_delta_indexes:
                index_name = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)

                # Pre-emptively create delta index
                if previousVersion > 0:
                    es.indices.create(index=WHOIS_DELTA_WRITE_FORMAT_STRING % (options.index_prefix, previousVersion))
            else:
                index_name = WHOIS_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)

            es.indices.create(index=index_name)


        else: # redo or update
            result = es.search(index=WHOIS_META,
                               body = { "query": {
                                            "match_all": {}
                                        },
                                        "sort":[
                                            {"metadata": {"order": "asc"}}
                                        ]
                                      })

            if result['hits']['total'] == 0:
                print("Unable to fetch entries from metadata index")
                sys.exit(1)

            previousVersion = int(result['hits']['hits'][-2]['_id'])
            version_identifier = previousVersion

    options.previousVersion = previousVersion

    index_list = es.search(index=WHOIS_META,
                           body = { "query": {
                                        "match_all": {}
                                    },
                                    "_source": "metadata",
                                    "sort":[
                                        {"metadata": {"order": "desc"}}
                                    ]
                                  })

    index_list = [entry['_source']['metadata'] for entry in index_list['hits']['hits'][:-1]]
    options.INDEX_LIST = []

    for index_version in index_list:
        if options.enable_delta_indexes:
            index = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.index_prefix, index_version)
        else:
            index = WHOIS_WRITE_FORMAT_STRING % (options.index_prefix, index_version)

        options.INDEX_LIST.append(index)

    # Change Index settings to better suit bulk indexing
    if options.optimize_import:
        if options.enable_delta_indexes:
            index = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.index_prefix, version_identifier)

            if options.previousVersion != 0:
                optimizeIndex(es, WHOIS_DELTA_WRITE_FORMAT_STRING % (options.index_prefix, options.previousVersion))
        else:
            index = WHOIS_WRITE_FORMAT_STRING % (options.index_prefix, version_identifier)

        optimizeIndex(es, index)

    options.updateVersion = 0

    if options.exclude != "":
        options.exclude = options.exclude.split(',')
    else:
        options.exclude = None

    if options.include != "":
        options.include = options.include.split(',')
    else:
        options.include = None

    # Redo or Update Mode
    if options.redo or options.update:
        # Get the record for the attempted import
        version_identifier = int(metadata['lastVersion'])
        options.identifier = version_identifier
        try:
            previous_record = es.get(index=WHOIS_META, id=version_identifier)['_source']
        except:
           print("Unable to retrieve information for last import")
           sys.exit(1)

        if 'excluded_keys' in previous_record:
            options.exclude = previous_record['excluded_keys']
        elif options.redo:
            options.exclude = None

        if 'included_keys' in previous_record:
            options.include = previous_record['included_keys']
        elif options.redo:
            options.include = None

        options.comment = previous_record['comment']
        STATS['total'] = int(previous_record['total'])
        STATS['new'] = int(previous_record['new'])
        STATS['updated'] = int(previous_record['updated'])
        STATS['unchanged'] = int(previous_record['unchanged'])
        STATS['duplicates'] = int(previous_record['duplicates'])
        if 'updateVersion' in previous_record:
            options.updateVersion = int(previous_record['updateVersion'])

        if options.update:
            options.updateVersion += 1

        CHANGEDCT = previous_record['changed_stats']

        if options.verbose:
            if options.redo:
                print("Re-importing for: \n\tIdentifier: %s\n\tComment: %s" % (version_identifier, options.comment))
            else:
                print("Updating for: \n\tIdentifier: %s\n\tComment: %s" % (version_identifier, options.comment))

        for ch in CHANGEDCT.keys():
            CHANGEDCT[ch] = int(CHANGEDCT[ch])

        #Start the reworker threads
        if options.verbose:
            print("Starting %i %s threads" % (options.threads, "reworker" if options.redo else "update"))

        if options.redo:
            target = process_reworker
        else:
            target = process_worker

        for i in range(options.threads):
            t = Process(target=target,
                        args=(work_queue,
                              insert_queue,
                              stats_queue,
                              options),
                        name='Worker %i' % i)
            t.daemon = True
            t.start()
            threads.append(t)
        #No need to update lastVersion or create metadata entry

    #Insert(normal) Mode
    else:
        #Start worker threads
        if options.verbose:
            print("Starting %i worker threads" % options.threads)

        for i in range(options.threads):
            t = Process(target=process_worker,
                        args=(work_queue, 
                              insert_queue, 
                              stats_queue,
                              options), 
                        name='Worker %i' % i)
            t.daemon = True
            t.start()
            threads.append(t)

        #Update the lastVersion in the metadata
        es.update(index=WHOIS_META, id=0, doc_type='meta', body = {'doc': {'lastVersion': options.identifier}} )

        #Create the entry for this import
        meta_struct = {  
                        'metadata': options.identifier,
                        'updateVersion': 0,
                        'comment' : options.comment,
                        'total' : 0,
                        'new' : 0,
                        'updated' : 0,
                        'unchanged' : 0,
                        'duplicates': 0,
                        'changed_stats': {} 
                       }

        if options.exclude != None:
            meta_struct['excluded_keys'] = options.exclude
        elif options.include != None:
            meta_struct['included_keys'] = options.include
            
        es.create(index=WHOIS_META, id=options.identifier, doc_type='meta',  body = meta_struct)


    es_bulk_shipper = Thread(target=es_bulk_shipper_proc, args=(insert_queue, options))
    es_bulk_shipper.start()

    stats_worker_thread = Thread(target=stats_worker, args=(stats_queue,), name = 'Stats')
    stats_worker_thread.daemon = True
    stats_worker_thread.start()

    #Start up Reader Thread
    reader_thread = Thread(target=reader_worker, args=(work_queue, options), name='Reader')
    reader_thread.daemon = True
    reader_thread.start()

    try:
        while True:
            reader_thread.join(.1)
            if not reader_thread.is_alive():
                break
            # If bulkError occurs stop reading from the files
            if bulkError_event.is_set():
                sys.stdout.write("Bulk API error -- forcing program shutdown \n")
                raise KeyboardInterrupt("Error response from ES worker, stopping processing")

        if options.verbose:
            sys.stdout.write("All files ingested ... please wait for processing to complete ... \n")
            sys.stdout.flush()

        while not work_queue.empty():
            # If bulkError occurs stop processing
            if bulkError_event.is_set():
                sys.stdout.write("Bulk API error -- forcing program shutdown \n")
                raise KeyboardInterrupt("Error response from ES worker, stopping processing")

        work_queue.join()

        try:
            # Since this is the shutdown section, ignore Keyboard Interrupts
            # especially since the interrupt code (below) does effectively the same thing
            insert_queue.join()
            finished_event.set()
            es_bulk_shipper.join()
            for t in threads:
                t.join()

            # Change settings back
            if options.optimize_import:
                if options.enable_delta_indexes:
                    index = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.index_prefix, version_identifier)

                    if options.previousVersion != 0:
                        unOptimizeIndex(es, WHOIS_DELTA_WRITE_FORMAT_STRING % (options.index_prefix, options.previousVersion), data_template)
                else:
                    index = WHOIS_WRITE_FORMAT_STRING % (options.index_prefix, version_identifier)

                unOptimizeIndex(es, index, data_template)

            stats_queue.put('finished')
            stats_worker_thread.join()

            #Update the stats
            try:
                es.update(index=WHOIS_META, id=version_identifier,
                                                 doc_type='meta',
                                                 body = { 'doc': {
                                                          'updateVersion': options.updateVersion,
                                                          'total' : STATS['total'],
                                                          'new' : STATS['new'],
                                                          'updated' : STATS['updated'],
                                                          'unchanged' : STATS['unchanged'],
                                                          'duplicates': STATS['duplicates'],
                                                          'changed_stats': CHANGEDCT
                                                        }}
                                                );
            except Exception as e:
                sys.stdout.write("Error attempting to update stats: %s\n" % str(e))
        except KeyboardInterrupt:
            pass

        if options.verbose:
            sys.stdout.write("Done ...\n\n")
            sys.stdout.flush()


        if options.stats:
            print("Stats: ")
            print("Total Entries:\t\t %d" % STATS['total'])
            print("New Entries:\t\t %d" % STATS['new'])
            print("Updated Entries:\t %d" % STATS['updated'])
            print("Duplicate Entries\t %d" % STATS['duplicates'])
            print("Unchanged Entries:\t %d" % STATS['unchanged'])

    except KeyboardInterrupt as e:
        sys.stdout.write("\rCleaning Up ... Please Wait ...\nWarning!! Forcefully killing this might leave Elasticsearch in an inconsistent state!\n")
        shutdown_event.set()

        # Flush the queue if the reader is alive so it can see the shutdown_event
        # in case it's blocked on a put
        sys.stdout.write("\tShutting down input reader threads ...\n")
        while reader_thread.is_alive():
            try:
                work_queue.get_nowait()
                work_queue.task_done()
            except queue.Empty:
                break

        reader_thread.join()

        # Don't join on the work queue, we don't care if the work has been finished
        # The worker threads will exit on their own after getting the shutdown_event

        # Joining on the insert queue is important to ensure ES isn't left in an inconsistent state if delta indexes are being used
        # since it 'moves' documents from one index to another which involves an insert and a delete
        insert_queue.join()

        # All of the workers should have seen the shutdown event and exited after finishing whatever they were last working on
        sys.stdout.write("\tStopping workers ... \n")
        for t in threads:
            t.join()

        # Send the finished message to the stats queue to shut it down
        stats_queue.put('finished')
        stats_worker_thread.join()

        sys.stdout.write("\tWaiting for ElasticSearch bulk uploads to finish ... \n")
        finished_event.set()
        es_bulk_shipper.join()

        #Attempt to update the stats
        #XXX
        try:
            sys.stdout.write("\tFinalizing metadata\n")
            es.update(index=WHOIS_META, id=options.identifier,
                                             body = { 'doc': {
                                                        'total' : STATS['total'],
                                                        'new' : STATS['new'],
                                                        'updated' : STATS['updated'],
                                                        'unchanged' : STATS['unchanged'],
                                                        'duplicates': STATS['duplicates'],
                                                        'changed_stats': CHANGEDCT
                                                    }
                                            })
        except:
            pass

        sys.stdout.write("\tFinalizing settings\n")
        # Make sure to de-optimize the indexes for import
        if options.optimize_import:
            if options.enable_delta_indexes:
                index = WHOIS_ORIG_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)

                if options.previousVersion != 0:
                    unOptimizeIndex(es, WHOIS_DELTA_WRITE_FORMAT_STRING % (options.index_prefix, options.previousVersion), data_template)
            else:
                index = WHOIS_WRITE_FORMAT_STRING % (options.index_prefix, options.identifier)

            unOptimizeIndex(es, index, data_template)

        try:
            work_queue.close()
            insert_queue.close()
            stats_queue.close()
        except:
            pass

        sys.stdout.write("... Done\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
