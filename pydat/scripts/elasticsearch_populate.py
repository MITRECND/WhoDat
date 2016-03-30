#!/usr/bin/env python

import sys
import os
import unicodecsv
import hashlib
import signal
import time
from optparse import OptionParser
import threading
from threading import Thread, Lock
import Queue
import multiprocessing
from multiprocessing import Process, Queue as mpQueue
from pprint import pprint
from elasticsearch import Elasticsearch
import json
import HTMLParser

STATS = {'total': 0,
         'new': 0,
         'updated': 0,
         'unchanged': 0,
         'duplicates': 0
        }

VERSION_KEY = 'dataVersion'
UNIQUE_KEY = 'dataUniqueID'
FIRST_SEEN = 'dataFirstSeen'

CHANGEDCT = {}

shutdown_event = multiprocessing.Event()
finished_event = multiprocessing.Event()

def connectElastic(uri):
    es = Elasticsearch(uri,
                       sniff_on_start=True,
                       max_retries=100,
                       retry_on_timeout=True,
                       sniff_on_connection_fail=True,
                       sniff_timeout=1000)

    return es

######## READER THREAD ######
def reader_worker(work_queue, options):
    if options.directory:
        scan_directory(work_queue, options.directory, options)
    elif options.file:
        parse_csv(work_queue, options.file, options)
    else:
        print "File or Directory required"

def scan_directory(work_queue, directory, options):
    for root, subdirs, filenames in os.walk(directory):
        if len(subdirs):
            for subdir in subdirs:
                scan_directory(work_queue, subdir, options)
        for filename in filenames:
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
        print "Processing file: %s" % filename

    csvfile = open(filename, 'rb')
    dnsreader = unicodecsv.reader(csvfile, strict = True, skipinitialspace = True)
    try:
        header = dnsreader.next()
        if not check_header(header):
            raise unicodecsv.Error('CSV header not found')

        for row in dnsreader:
            if shutdown_event.is_set():
                break
            work_queue.put({'header': header, 'row': row})
    except unicodecsv.Error, e:
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

def es_bulk_thread(bulk_request_queue, options):
    es = connectElastic(options.es_uri)
    while 1:
        try:
            bulk_request = bulk_request_queue.get()
            #sys.stdout.write("Making bulk request\n")
            es.bulk(body=bulk_request)
            #sys.stdout.write("Bulk request Complete\n")
        except Exception as e:
            sys.stdout.write("Exception making bulk request: %s" % str(e))
        finally:
            bulk_request_queue.task_done()

def es_worker(insert_queue, options):
    #Ignore signals that are sent to parent process
    #The parent should properly shut this down
    os.setpgrp()

    bulk_counter = 0
    finishup = False
    bulk_request = []

    # Allow the queue to back up to however many threads there will be
    bulk_request_queue = Queue.Queue(maxsize = options.bulk_threads)

    for count in range(options.bulk_threads):
        t = Thread(target = es_bulk_thread, args = (bulk_request_queue, options))
        t.daemon = True
        t.start()

    while not finishup:
        request = insert_queue.get()
        if not isinstance(request, basestring):
            if request['type'] == 'insert':
                command = {"create": { "_id": request['_id'], 
                                       "_index": request['_index'], 
                                       "_type": request['_type']
                                     }
                          }
                data = request['insert']
                bulk_request.append(command)
                bulk_request.append(data)
                bulk_counter += 1
            elif request['type'] == 'update':
                command = {"update": { "_id": request['_id'], 
                                       "_index": request['_index'], 
                                       "_type": request['_type']
                                     }
                          }
                data = request['update']
                bulk_request.append(command)
                bulk_request.append(data)
                bulk_counter += 1
            elif request['type'] == 'delete':
                command = {"delete": {
                                        "_id": request['_id'],
                                        "_index": request['_index'],
                                        "_type": request['_type']
                                     }
                          }
                bulk_request.append(command)
                bulk_counter += 1
            else:
                print "Unrecognized"
        else:
            finishup = True 

        if ((bulk_counter >= options.bulk_size) or finishup) and bulk_counter > 0:
            bulk_request_queue.put(bulk_request)
            bulk_counter = 0
            bulk_request = []

    # Wait for threads to finish sending bulk requests
    bulk_request_queue.join()

######## WORKER THREADS #########

def update_required(es, header, input_entry, options):
    if len(input_entry) == 0:
        return False

    current_entry = None
    domainName = ''
    for i,item in enumerate(input_entry):
        if header[i] == 'domainName':
            domainName = item
            break

    (entries, current_entry) = find_entry(es, domainName, options)

    if current_entry is None:
        return True

    if current_entry['_source'][VERSION_KEY] == options.identifier: #This record already up to date
        return False 
    else:
        return True

def process_worker(work_queue, insert_queue, stats_queue, options):
    global shutdown_event
    global finished_event
    os.setpgrp()
    es = connectElastic(options.es_uri)
    while not shutdown_event.is_set():
        try:
            work = work_queue.get_nowait()
            process_entry(insert_queue, stats_queue, es, work['header'], work['row'], options)
        except Queue.Empty as e:
            if finished_event.is_set():
                return
            time.sleep(.01)

def process_reworker(work_queue, insert_queue, stats_queue, options):
    global shutdown_event
    global finished_event
    os.setpgrp()
    es = connectElastic(options.es_uri)
    while not shutdown_event.is_set():
        try:
            work = work_queue.get_nowait()
            if update_required(es, work['header'],work['row'], options):
                process_entry(insert_queue, stats_queue, es, work['header'], work['row'], options)
        except Queue.Empty as e:
            if finished_event.is_set():
                return
            time.sleep(.01)

def process_entry(insert_queue, stats_queue, es, header, input_entry, options):
    global VERSION_KEY

    stats_queue.put('total')
    if len(input_entry) == 0:
        return

    htmlparser = HTMLParser.HTMLParser()

    current_entry = None
    details = {}
    domainName = ''
    for i,item in enumerate(input_entry):
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
                'details': details,
                'domainName': domainName,
            }

    (entries, current_entry_raw) = find_entry(es, domainName, options)

    global CHANGEDCT
    if current_entry_raw is not None:
        current_index = current_entry_raw['_index']
        current_id = current_entry_raw['_id']
        current_type = current_entry_raw['_type']
        current_entry = current_entry_raw['_source']

        if current_entry[VERSION_KEY] == options.identifier: # duplicate entry in source csv's?
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
            stats_queue.put('updated')
            if options.vverbose:
                sys.stdout.write("%s: Updated\n" % domainName)

            if options.enable_delta_indexes and entries > 1:
                # Delete old entry, put into a 'diff' index
                insert_queue.put({'type': 'delete',
                                  '_index': current_index,
                                  '_id': current_id,
                                  '_type': current_type
                                 })

                # Put it into a previousVersion-d index so it doesn't potentially create
                # a bunch of indexes that will need to be cleaned up later
                insert_queue.put({'type': 'insert',
                                  '_id': generate_id(domainName, options.previousVersion),
                                  '_index': '%s-%s-d' % (options.index_prefix, options.previousVersion),
                                  '_type': current_type,
                                  'insert': current_entry
                                })

            entry[FIRST_SEEN] = current_entry[FIRST_SEEN]
            entry_id = generate_id(domainName, options.identifier)
            entry[UNIQUE_KEY] = entry_id
            insert_queue.put({'type': 'insert', 
                              '_id': entry_id, 
                              '_index': "%s-%s" % (options.index_prefix, options.identifier), 
                              '_type': parse_tld(domainName), 
                              'insert':entry
                             })
        else:
            stats_queue.put('unchanged')
            if options.vverbose:
                sys.stdout.write("%s: Unchanged\n" % domainName)
            insert_queue.put({'type': 'update', 
                              '_id': current_id, 
                              '_index': current_index,
                              '_type': current_type,
                              'update': {'doc': {
                                                 VERSION_KEY: options.identifier,
                                                'details': details 
                                                }
                                        }
                             })
    else:
        stats_queue.put('new')
        if options.vverbose:
            sys.stdout.write("%s: New\n" % domainName)
        entry_id = generate_id(domainName, options.identifier)
        entry[UNIQUE_KEY] = entry_id
        insert_queue.put({'type': 'insert', 
                          '_id': entry_id, 
                          '_index': "%s-%s" % (options.index_prefix, options.identifier), 
                          '_type': parse_tld(domainName), 
                          'insert':entry
                         })

def generate_id(domainName, identifier):
    dhash = hashlib.md5(domainName).hexdigest() + str(identifier)
    return dhash

def parse_tld(domainName):
    parts = domainName.split('.')
    return parts[-1]
    

def find_entry(es, domainName, options):
    try:
        result = es.search(index="%s-*" % options.index_prefix,
                          body = { "query":{
                                        "term": { 'domainName': domainName}
                                    },
                                    "sort": [
                                        {
                                         VERSION_KEY: {"order": "desc",
                                                       "unmapped_type": "long"
                                                      }
                                        }
                                    ]
                                 })

        if result['hits']['total'] == 0:
            return (0, None)

        """
        tups = []
        for r in result['hits']['hits']:
            tups.append((r['_source']['domainName'], r['_source']['dataVersion']))

        print tups
        """
        
        return (result['hits']['total'], result['hits']['hits'][0])
    except Exception as e:
        print "Unable to find %s, %s" % (domainName, str(e))
        return (0, None)




###### MAIN ######

def main():
    global STATS
    global VERSION_KEY
    global CHANGEDCT
    global shutdown_event
    global finished_event

    def signal_handler(signum, frame):
        signal.signal(signal.SIGINT, SIGINT_ORIG)
        sys.stdout.write("\rCleaning Up ... Please Wait ...\n")
        shutdown_event.set()

        #Let the current workload finish
        sys.stdout.write("\tStopping Workers\n")
        for t in threads:
            t.join(1)

        stats_queue.put('finished')
        insert_queue.put("finished")

        stats_worker_thread.join(5)

        #Give the Elasticsearch process 5 seconds to exit
        es_worker_thread.join(5)

        #If it's still alive, terminate it
        if es_worker_thread.is_alive():
            try:
                es_worker_thread.terminate()
            except:
                pass

        #Attempt to update the stats
        #XXX
        try:
            es.update(index=meta_index_name, id=options.identifier, 
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

        if reader_thread.is_alive():
            try:
                #Flush the queue so reader can see the shutdown_event
                while not work_queue.empty():
                    work_queue.get_nowait()
            except:
                pass

        reader_thread.join()

        try:
            work_queue.close()
            insert_queue.close()
            stats_queue.close()
        except:
            pass

        sys.stdout.write("... Done\n")
        sys.exit(0)


    optparser = OptionParser(usage='usage: %prog [options]')
    optparser.add_option("-f", "--file", action="store", dest="file",
        default=None, help="Input CSV file")
    optparser.add_option("-d", "--directory", action="store", dest="directory",
        default=None, help="Directory to recursively search for CSV files - prioritized over 'file'")
    optparser.add_option("-e", "--extension", action="store", dest="extension",
        default='csv', help="When scanning for CSV files only parse files with given extension (default: 'csv')")
    optparser.add_option("-i", "--identifier", action="store", dest="identifier", type="int",
        default=None, help="Numerical identifier to use in update to signify version (e.g., '8' or '20140120')")
    optparser.add_option("-t", "--threads", action="store", dest="threads", type="int",
        default=2, help="Number of workers, defaults to 2. Note that each worker will increase the load on your ES cluster")
    optparser.add_option("-B", "--bulk-size", action="store", dest="bulk_size", type="int",
        default=5000, help="Size of Bulk Insert Requests")
    optparser.add_option("-v", "--verbose", action="store_true", dest="verbose",
        default=False, help="Be verbose")
    optparser.add_option("--vverbose", action="store_true", dest="vverbose",
        default=False, help="Be very verbose (Prints status of every domain parsed, very noisy)")
    optparser.add_option("-s", "--stats", action="store_true", dest="stats",
        default=False, help="Print out Stats after running")
    optparser.add_option("-x", "--exclude", action="store", dest="exclude",
        default="", help="Comma separated list of keys to exclude if updating entry")
    optparser.add_option("-n", "--include", action="store", dest="include",
        default="", help="Comma separated list of keys to include if updating entry (mutually exclusive to -x)")
    optparser.add_option("-o", "--comment", action="store", dest="comment",
        default="", help="Comment to store with metadata")
    optparser.add_option("-r", "--redo", action="store_true", dest="redo",
        default=False, help="Attempt to re-import a failed import or import more data, uses stored metatdata from previous import (-o and -x not required and will be ignored!!)")

    #ES Specific Options
    optparser.add_option("-u", "--es-uri", action="store", dest="es_uri",
        default='localhost:9200', help="Location of ElasticSearch Server (e.g., foo.server.com:9200)")
    optparser.add_option("-p", "--index-prefix", action="store", dest="index_prefix",
        default='whois', help="Index prefix to use in ElasticSearch (default: whois)")
    optparser.add_option("--bulk-threads", action="store", dest="bulk_threads", type="int",
        default=1, help="How many threads to use for making bulk requests to ES")
    optparser.add_option("-T", "--enable-delta-indexes", action="store_true", dest="enable_delta_indexes",
        default=False, help="If enabled, will put changed entries that are not the original or latest in a separate index. These indexes can be safely deleted if space is an issue")

    if (len(sys.argv) < 2):
        optparser.parse_args(['-h'])

    (options, args) = optparser.parse_args()

    if options.vverbose:
        options.verbose = True


    threads = []
    work_queue = mpQueue(maxsize=options.bulk_size)
    insert_queue = mpQueue(maxsize=options.bulk_size)
    stats_queue = mpQueue()

    meta_index_name = '@' + options.index_prefix + "_meta"

    data_template = None
    template_path = os.path.dirname(os.path.realpath(__file__))
    with open("%s/es_templates/data.template" % template_path, 'r') as dtemplate:
        data_template = json.loads(dtemplate.read())

    if options.identifier is None and options.redo is False:
        print "Identifier required\n"
        optparser.parse_args(['-h'])
    elif options.identifier is not None and options.redo is True:
        print "Redo requested and Identifier Specified. Please choose one or the other\n"
        optparser.parse_args(['-h'])
    elif options.exclude != "" and options.include != "":
        print "Options include and exclude are mutually exclusive, choose only one\n"
        optparser.parse_args(['-h'])

    es = connectElastic(options.es_uri)
    metadata = None
    previousVersion = 0

    #Create the metadata index if it doesn't exist
    if not es.indices.exists(meta_index_name):
        if options.redo:
            print "Cannot redo when no initial data exists"
            sys.exit(1)

        if data_template is not None:
            data_template["template"] = "%s-*" % options.index_prefix
            es.indices.put_template(name='%s-template' % options.index_prefix, body = data_template)

        #Create the metadata index with only 1 shard, even with thousands of imports
        #This index shouldn't warrant multiple shards
        #Also use the keyword analyzer since string analsysis is not important
        es.indices.create(index=meta_index_name, body = {"settings" : {
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
        #Create the 0th metadata entry
        metadata = { "metadata": 0,
                     "firstVersion": options.identifier,
                     "lastVersion": options.identifier
                    }
        es.create(index=meta_index_name, doc_type='meta', id = 0, body = metadata)

        #Specially create the first index to have 2x the shards than normal
        #since future indices should be diffs of the first index (ideally)
        es.indices.create(index='%s-%s' % (options.index_prefix, options.identifier), 
                            body = {"settings": { 
                                        "index": { 
                                            "number_of_shards": int(data_template["settings"]["number_of_shards"]) * 2
                                        }
                                    }
                            })

    else:
        try:
            result = es.get(index=meta_index_name, id=0)
            if result['found']:
                metadata = result['_source']
            else:
                raise Exception("Not Found")
        except:
            print "Error fetching metadata from index"
            sys.exit(1)

        if options.redo is False: #Identifier is auto-pulled from db, no need to check
            if options.identifier < 1:
                print "Identifier must be greater than 0"
                sys.exit(1)
            if metadata['lastVersion'] >= options.identifier:
                print "Identifier must be 'greater than' previous identifier"
                sys.exit(1)

            previousVersion = metadata['lastVersion']
        else:
            result = es.search(index=meta_index_name,
                               body = { "query": {
                                            "match_all": {}
                                        },
                                        "sort":[
                                            {"_id": {"order": "asc"}}
                                        ]
                                      })

            if result['hits']['total'] == 0:
                print "Unable to fetch entries from metadata index"
                sys.exit(1)

            previousVersion = results['hits']['hits'][-2]['_id']

    options.previousVersion = previousVersion

    if options.redo is False:
        if options.exclude != "":
            options.exclude = options.exclude.split(',')
        else:
            options.exclude = None

        if options.include != "":
            options.include = options.include.split(',')
        else:
            options.include = None

        #Start worker threads
        if options.verbose:
            print "Starting %i worker threads" % options.threads

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

        #Upate the lastVersion in the metadata
        es.update(index=meta_index_name, id=0, doc_type='meta', body = {'doc': {'lastVersion': options.identifier}} )

        #Create the entry for this import
        meta_struct = {  
                        'metadata': options.identifier,
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
            
        es.create(index=meta_index_name, id=options.identifier, doc_type='meta',  body = meta_struct)

    else: #redo is True
        #Get the record for the attempted import
        options.identifier = int(metadata['lastVersion'])
        try:
            redo_record = es.get(index=meta_index_name, id=options.identifier)['_source']
        except:
           print "Unable to retrieve information for last import"
           sys.exit(1) 

        if 'excluded_keys' in redo_record:
            options.exclude = redo_record['excluded_keys']
        else:
            options.exclude = None

        if 'included_keys' in redo_record:
            options.include = redo_record['included_keys']
        else:
            options.include = None

        options.comment = redo_record['comment']
        STATS['total'] = int(redo_record['total'])
        STATS['new'] = int(redo_record['new'])
        STATS['updated'] = int(redo_record['updated'])
        STATS['unchanged'] = int(redo_record['unchanged'])
        STATS['duplicates'] = int(redo_record['duplicates'])
        CHANGEDCT = redo_record['changed_stats']

        if options.verbose:
            print "Re-importing for: \n\tIdentifier: %s\n\tComment: %s" % (options.identifier, options.comment)

        for ch in CHANGEDCT.keys():
            CHANGEDCT[ch] = int(CHANGEDCT[ch])

        #Start the reworker threads
        if options.verbose:
            print "Starting %i reworker threads" % options.threads

        for i in range(options.threads):
            t = Process(target=process_reworker,
                        args=(work_queue, 
                              insert_queue, 
                              stats_queue,
                              options), 
                        name='Worker %i' % i)
            t.daemon = True
            t.start()
            threads.append(t)
        #No need to update lastVersion or create metadata entry

    #Start up the Elasticsearch Bulk Processor
    es_worker_thread = Process(target=es_worker, args=(insert_queue, options))
    es_worker_thread.daemon = True
    es_worker_thread.start()

    stats_worker_thread = Thread(target=stats_worker, args=(stats_queue,), name = 'Stats')
    stats_worker_thread.daemon = True
    stats_worker_thread.start()

    #Set up signal handler before we go into the real work
    SIGINT_ORIG = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal_handler)

    #Start up Reader Thread
    reader_thread = Thread(target=reader_worker, args=(work_queue, options), name='Reader')
    reader_thread.daemon = True
    reader_thread.start()

    while True:
        reader_thread.join(.1)
        if not reader_thread.is_alive():
            break

    time.sleep(.1)

    while not work_queue.empty():
        time.sleep(.01)

    finished_event.set()

    for t in threads:
        t.join()

    insert_queue.put("finished")
    es_worker_thread.join()

    stats_queue.put('finished')
    stats_worker_thread.join()
    
    #Update the stats
    es.update(index=meta_index_name, id=options.identifier, 
                                     doc_type='meta',
                                     body = { 'doc': {
                                              'total' : STATS['total'],
                                              'new' : STATS['new'],
                                              'updated' : STATS['updated'],
                                              'unchanged' : STATS['unchanged'],
                                              'duplicates': STATS['duplicates'],
                                              'changed_stats': CHANGEDCT
                                            }}
                                    );


    if options.stats:
        print "Stats: "
        print "Total Entries:\t\t %d" % STATS['total'] 
        print "New Entries:\t\t %d" % STATS['new'] 
        print "Updated Entries:\t %d" % STATS['updated'] 
        print "Duplicate Entries\t %d" % STATS['duplicates'] 
        print "Unchanged Entries:\t %d" % STATS['unchanged'] 

if __name__ == "__main__":
    main()
