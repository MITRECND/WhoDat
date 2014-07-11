#!/usr/bin/env python

import sys
import os
import csv
import hashlib
import signal
from optparse import OptionParser
import pymongo
from pymongo import MongoClient
import threading
from threading import Thread
from Queue import Queue
import multiprocessing #for num cpus
from multiprocessing import Process, Queue as mpQueue
from pprint import pprint

NUM_ENTRIES = 0
NUM_NEW = 0
NUM_UPDATED = 0
NUM_UNCHANGED = 0
VERSION_KEY = 'dataVersion'
UNIQUE_KEY = 'dataUniqueID'
FIRST_SEEN = 'dataFirstSeen'

CHANGEDCT = {}

def scan_directory(work_queue, collection, directory, options):
    for root, subdirs, filenames in os.walk(directory):
        if len(subdirs):
            for subdir in subdirs:
                scan_directory(work_queue, collection, subdir, options)
        for filename in filenames:
            if options.extension != '':
                fn, ext = os.path.splitext(filename)
                if ext and ext[1:] != options.extension:
                    continue

            full_path = os.path.join(root, filename)
            parse_csv(work_queue, collection, full_path, options)

def parse_csv(work_queue, collection, filename, options):
    if options.verbose:
        print "Processing file: %s" % filename

    csvfile = open(filename, 'rb')
    dnsreader = csv.reader(csvfile, strict = True, skipinitialspace = True)
    header = dnsreader.next()

    for row in dnsreader:
        work_queue.put({'header': header, 'row': row})

def update_required(collection, header, input_entry, options):
    if len(input_entry) == 0:
        return False

    current_entry = None
    domainName = ''
    for i,item in enumerate(input_entry):
        if header[i] == 'domainName':
            domainName = item
            break

    current_entry = find_entry(collection, domainName)

    if current_entry is None:
        return True

    if current_entry[VERSION_KEY] == options.identifier: #This record already up to date
        return False 
    else:
        return True


def mongo_worker(insert_queue, options):
    #Register signal handler for this process
    def signal_handler(signal, frame):
        try:
            if bulk_counter > 0:
                print "Flushing Processed Data to Mongo ... Please Wait"
                bulk.execute() 
        except:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    bulk_counter = 0
    client = MongoClient(host=options.mongo_host, port=options.mongo_port)
    whodb = client[options.database]
    collection = whodb[options.collection]
    finishup = False
    bulk = collection.initialize_unordered_bulk_op() 

    while not finishup:
        request = insert_queue.get()
        if not isinstance(request, basestring):
            if request['type'] == 'insert':
                bulk.insert(request['insert'])
                bulk_counter += 1
            elif request['type'] == 'update':
                bulk.find(request['find']).update(request['update'])
                bulk_counter += 1
            else:
                print "Unrecognized"
        else:
            finishup = True 

        if ((bulk_counter >= options.bulk_size) or finishup) and bulk_counter > 0:
            finished_bulk = bulk
            bulk = collection.initialize_unordered_bulk_op() 
            bulk_counter = 0

            try:
                finished_bulk.execute()
            except pymongo.bulk.BulkWriteError as bwe:
                details = bwe.details
                if options.vverbose:
                    pprint(bwe.details)
                elif options.verbose:
                    for error in details['writeErrors']:
                        print "Error inserting/updating %s\n\tmessage: %s" % (error['op']['domainName'], error['errmsg'])
                #else pass


def process_worker(work_queue, insert_queue, collection, options):
    while True:
        work = work_queue.get()
        process_entry(insert_queue, collection, work['header'], work['row'], options)
        work_queue.task_done()

def process_reworker(work_queue, insert_queue, collection, options):
    while True:
        work = work_queue.get()
        if update_required(collection, work['header'],work['row'], options):
            process_entry(insert_queue, collection, work['header'], work['row'], options)
        work_queue.task_done()
        

def process_entry(insert_queue, collection, header, input_entry, options):
    global VERSION_KEY
    global NUM_ENTRIES
    global NUM_NEW
    global NUM_UPDATED
    global NUM_UNCHANGED

    NUM_ENTRIES += 1
    if len(input_entry) == 0:
        return

    current_entry = None
    details = {}
    domainName = ''
    for i,item in enumerate(input_entry):
        if header[i] == 'domainName':
            if options.vverbose:
                print "Processing domain: %s" % item
            domainName = item
            continue
        details[header[i]] = item

    entry = {
                VERSION_KEY: options.identifier,
                FIRST_SEEN: options.identifier,
                'details': details,
                'domainName': domainName,
            }

    current_entry = find_entry(collection, domainName)

    global CHANGEDCT
    if current_entry:
        if current_entry[VERSION_KEY] == options.identifier: # duplicate entry in source csv's?
            return

        if len(options.exclude):
            details_copy = details.copy()
            for exclude in options.exclude:
                del details_copy[exclude]


            changed = set(details_copy.items()) - set(current_entry['details'].items()) 
            diff = len(set(details_copy.items()) - set(current_entry['details'].items())) > 0
            
        else:
            changed = set(details.items()) - set(current_entry['details'].items()) 
            diff = len(set(details.items()) - set(current_entry['details'].items())) > 0

            # The above diff doesn't consider keys that are only in the latest in mongo
            # So if a key is just removed, this diff will indicate there is no difference
            # even though a key had been removed.
            # I don't forsee keys just being wholesale removed, so this shouldn't be a problem
        for ch in changed:
            if ch[0] not in CHANGEDCT:
                CHANGEDCT[ch[0]] = 0
            CHANGEDCT[ch[0]] += 1

        if diff:
            if options.vverbose:
                print "Creating entry for updated domain %s" % domainName
        
            entry[FIRST_SEEN] = current_entry[FIRST_SEEN]
            entry[UNIQUE_KEY] = generate_id(domainName, options.identifier)
            insert_queue.put({'type': 'insert', 'insert':entry})
            NUM_UPDATED += 1
        else:
            NUM_UNCHANGED += 1
            if options.vverbose:
                print "Unchanged entry for %s" % domainName
            insert_queue.put({'type': 'update', 'find': {UNIQUE_KEY: current_entry[UNIQUE_KEY]}, 'update': {'$set': {'details': details, VERSION_KEY: options.identifier}}})
    else:
        NUM_NEW += 1
        if options.vverbose:
            print "Creating new entry for %s" % domainName
        entry[UNIQUE_KEY] = generate_id(domainName, options.identifier)
        insert_queue.put({'type': 'insert', 'insert':entry})

def generate_id(domainName, identifier):
    dhash = hashlib.md5(domainName).hexdigest() + str(identifier)
    return dhash
    

def find_entry(collection, domainName):
    try:
        entry = collection.find({"domainName": domainName}, sort=[(VERSION_KEY, pymongo.DESCENDING)])[0]
    except IndexError:
        return None

    return entry


def main():
    global NUM_ENTRIES
    global NUM_NEW
    global NUM_UPDATED
    global NUM_UNCHANGED
    global VERSION_KEY
    global CHANGEDCT

    def signal_handler(signal, frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    optparser = OptionParser(usage='usage: %prog [options]')
    optparser.add_option("-f", "--file", action="store", dest="file",
        default=None, help="Input CSV file")
    optparser.add_option("-d", "--directory", action="store", dest="directory",
        default=None, help="Directory to recursively search for CSV files - prioritized over 'file'")
    optparser.add_option("-e", "--extension", action="store", dest="extension",
        default='csv', help="When scanning for CSV files only parse files with given extension (default: 'csv')")
    optparser.add_option("-i", "--identifier", action="store", dest="identifier", type="int",
        default=None, help="Numerical identifier to use in update to signify version (e.g., '8' or '20140120')")
    optparser.add_option("-m", "--mongo-host", action="store", dest="mongo_host",
        default='localhost', help="Location of mongo db/cluster")
    optparser.add_option("-p", "--mongo-port", action="store", dest="mongo_port", type="int",
        default=27017, help="Location of mongo db/cluster")
    optparser.add_option("-b", "--database", action="store", dest="database",
        default='whois', help="Name of database to use (default: 'whois')")
    optparser.add_option("-c", "--collection", action="store", dest="collection",
        default='whois', help="Name of collection to use (default: 'whois')")
    optparser.add_option("-t", "--threads", action="store", dest="threads", type="int",
        default=multiprocessing.cpu_count(), help="Number of worker threads")
    optparser.add_option("-B", "--bulk-size", action="store", dest="bulk_size", type="int",
        default=1000, help="Size of Bulk Insert Requests")
    optparser.add_option("-v", "--verbose", action="store_true", dest="verbose",
        default=False, help="Be verbose")
    optparser.add_option("--vverbose", action="store_true", dest="vverbose",
        default=False, help="Be very verbose (Prints status of every domain parsed)")
    optparser.add_option("-s", "--stats", action="store_true", dest="stats",
        default=False, help="Print out Stats after running")
    optparser.add_option("-x", "--exclude", action="store", dest="exclude",
        default="", help="Comma separated list of keys to exclude if updating entry")
    optparser.add_option("-o", "--comment", action="store", dest="comment",
        default="", help="Comment to store with metadata")
    optparser.add_option("-r", "--redo", action="store_true", dest="redo",
        default=False, help="Attempt to re-import a failed import")

    (options, args) = optparser.parse_args()

    if options.vverbose:
        options.verbose = True


    work_queue = Queue(maxsize=options.bulk_size)
    insert_queue = mpQueue(maxsize=options.bulk_size)

    client = MongoClient(host=options.mongo_host, port=options.mongo_port)
    whodb = client[options.database]
    collection = whodb[options.collection]
    meta = whodb[options.collection + '_meta']

    if options.identifier is None and options.redo is False:
        print "Identifier required"
        sys.exit(1)

    metadata = meta.find_one({'metadata':0})
    meta_id = None
    if metadata is None: #Doesn't exist
        if options.redo is False:
            md = {
                  'metadata': 0,
                  'firstVersion': options.identifier,
                  'lastVersion' : options.identifier,
                 }
            meta_id = meta.insert(md)
            metadata = meta.find_one({'_id': meta_id})

            # Setup indexes
            collection.ensure_index(UNIQUE_KEY, background=True, unique=True)
            collection.ensure_index(VERSION_KEY, background=True)
            collection.ensure_index('domainName', background=True)
            collection.ensure_index([('domainName', pymongo.ASCENDING), (VERSION_KEY, pymongo.ASCENDING)], background=True)
            collection.ensure_index('details.contactEmail', background=True)
            collection.ensure_index('details.registrant_name', background=True)
            collection.ensure_index('details.registrant_telephone', background=True)
        else:
            print "Cannot redo when no initial import exists"
            sys.exit(1)
    else:
        if options.redo is False: #Identifier is auto-pulled from db, no need to check
            if options.identifier < 1:
                print "Identifier must be greater than 0"
                sys.exit(1)
            if metadata['lastVersion'] >= options.identifier:
                print "Identifier must be 'greater than' previous identifier"
                sys.exit(1)
        meta_id = metadata['_id']

    mongo_worker_thread = Process(target=mongo_worker, args=(insert_queue, options))
    mongo_worker_thread.start()

    if options.redo is False:
        if options.exclude != "":
            options.exclude = options.exclude.split(',')
        else:
            options.exclude = []

        #Start worker threads
        if options.verbose:
            print "Starting %i worker threads" % options.threads

        for i in range(options.threads):
            t = Thread(target=process_worker, 
                        args=(work_queue, 
                              insert_queue, 
                              collection, 
                              options), 
                        name='Worker %i' % i)
            t.daemon = True
            t.start()

        #Upate the lastVersion in the metadata
        meta.update({'_id': meta_id}, {'$set' : {'lastVersion': options.identifier}})
        #Create the entry for this import
        meta.insert({ 
                        'metadata': options.identifier,
                        'comment' : options.comment,
                        'excluded_keys': options.exclude,
                })
    else: #redo is True
        #Get the record for the attempted import
        options.identifier = int(metadata['lastVersion'])
        redo_record = meta.find_one({'metadata': options.identifier})
        options.exclude = redo_record['excluded_keys']
        options.comment = redo_record['comment']

        #Start the reworker threads
        if options.verbose:
            print "Starting %i reworker threads" % options.threads

        for i in range(options.threads):
            t = Thread(target=process_reworker, 
                        args=(work_queue, 
                              insert_queue, 
                              collection, 
                              options), 
                        name='Worker %i' % i)
            t.daemon = True
            t.start()
        #No need to update lastVersion or create metadata entry
        
    #Start Processing the entries
    if options.directory:
        scan_directory(work_queue, collection, options.directory, options)
    elif options.file:
        parse_csv(work_queue, collection, options.file, options)
    else:
        print "File or Directory required"
        sys.exit(1) 


    work_queue.join()
    insert_queue.put("finished")
    mongo_worker_thread.join()
    
    #Update the stats for this import
    #TODO this will be inaccurate in a re-do event, need to track better
    meta.update({'metadata': options.identifier}, {'$set' : {
                                                'total' : NUM_ENTRIES,
                                                'new' : NUM_NEW,
                                                'updated' : NUM_UPDATED,
                                                'unchanged' : NUM_UNCHANGED,
                                                'changed_stats': CHANGEDCT
                                            }
                                    });


    if options.stats:
        print "Stats: "
        print "Total Entries:\t\t %d" % NUM_ENTRIES
        print "New Entries:\t\t %d" % NUM_NEW
        print "Updated Entries:\t %d" % NUM_UPDATED
        print "Unchanged Entries:\t %d" % NUM_UNCHANGED

if __name__ == "__main__":
    main()
