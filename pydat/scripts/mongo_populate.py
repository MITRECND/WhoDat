#!/usr/bin/env python

import sys
import os
import csv
from optparse import OptionParser
import pymongo
from pymongo import MongoClient

NUM_ENTRIES = 0
NUM_NEW = 0
NUM_UPDATED = 0
NUM_UNCHANGED = 0
VERSION_KEY = 'dataVersion'

def scan_directory(collection, directory, options):
    for root, subdirs, filenames in os.walk(directory):
        if len(subdirs):
            for subdir in subdirs:
                scan_directory(collection, subdir, options)
        for filename in filenames:
            if options.extension != '':
                fn, ext = os.path.splitext(filename)
                if ext and ext[1:] != options.extension:
                    continue

            full_path = os.path.join(root, filename)
            parse_csv(collection, full_path, options)

def parse_csv(collection, filename, options):
    if options.verbose:
        print "Processing file: %s" % filename

    csvfile = open(filename, 'rb')
    dnsreader = csv.reader(csvfile)
    header = dnsreader.next()

    for row in dnsreader:
        process_entry(collection, header, row, options)


def process_entry(collection, header, input_entry, options):
    global VERSION_KEY
    global NUM_ENTRIES
    global NUM_NEW
    global NUM_UPDATED
    global NUM_UNCHANGED

    NUM_ENTRIES += 1
    if len(input_entry) == 0:
        return

    current_entry = None
    domainName = ''
    details = {}
    for i,item in enumerate(input_entry):
        if header[i] == 'domainName':
            if options.verbose:
                print "Processing domain: %s" % item
            domainName = item
        else:
            details[header[i]] = item

    current_entry = find_entry(collection, domainName)

    if current_entry:
        latest = current_entry['latest']

        if options.exclude != "":
            details_copy = details.copy()
            for exclude in options.exclude:
                del details_copy[exclude]

            diff = len(set(details_copy.items()) - set(latest.items())) > 0
        else:
            diff = len(set(details.items()) - set(latest.items())) > 0

            # The above diff doesn't consider keys that are only in the latest in mongo
            # So if a key is just removed, this diff will indicate there is no difference
            # even though a key had been removed.
            # I don't forsee keys just being wholesale removed, so this shouldn't be a problem

        if diff:
            if options.verbose:
                print "Updating existing entry for %s" % domainName
        
            latest_diff = dict_diff(latest, details, options)

            collection.update(  {'_id': current_entry['_id']}, 
                            { '$push': { 'history':  latest_diff}}
                         )
            NUM_UPDATED += 1
        else:
            NUM_UNCHANGED += 1
            if options.verbose:
                print "Unchanged entry for %s" % domainName

        # Regardless of if there was a diff, update 'latest' entry with new info
        # For the majority of cases this will only update the VERSION_KEY
        # Need to check and see if this is horribly inefficient or not
        details[VERSION_KEY] = options.identifier
        collection.update({'_id': current_entry['_id']}, { '$set': {'latest':  details}})
    else:
        NUM_NEW += 1
        if options.verbose:
            print "Creating new entry for %s" % domainName

        details[VERSION_KEY] = options.identifier
        entry = { 'domainName': domainName, 
                  'latest' : details, 
                  'history': [],
                  'firstVersion': options.identifier
                }
        collection.insert(entry)


def dict_diff(old, new, options): 
    output = {}
     
    diffset = set(old.items()) - set(new.items())
    diffkeys = set(new.keys()) - set(old.keys())

    if len(diffset) == 0 and len(diffkeys) == 0:
        return None

    # Keep track of keys that have been removed/added
    # This allows us to easily roll backwards
    for key in diffkeys:
        if key in options.exclude:
            continue
        output['-' + key] = new[key]

    # Key/value pairs that have changed
    for (key,value) in diffset:
        if key in options.exclude:
            continue
        output[key] = value
         
    return output

def find_entry(collection, domainName):
    entry = collection.find_one({"domainName": domainName})
    if entry:
       return entry 
    else:
        return None


def main():
    global NUM_ENTRIES
    global NUM_NEW
    global NUM_UPDATED
    global NUM_UNCHANGED

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
    optparser.add_option("-v", "--verbose", action="store_true", dest="verbose",
        default=False, help="Be verbose")
    optparser.add_option("-s", "--stats", action="store_true", dest="stats",
        default=False, help="Print out Stats after running")
    optparser.add_option("-x", "--exclude", action="store", dest="exclude",
        default="", help="Comma separated list of keys to exclude if updating entry")
    optparser.add_option("-o", "--comment", action="store", dest="comment",
        default="", help="Comment to store with metadata")

    (options, args) = optparser.parse_args()


    client = MongoClient(host=options.mongo_host, port=options.mongo_port)
    whodb = client[options.database]
    collection = whodb[options.collection]
    meta = whodb[options.collection + '_meta']

    if options.identifier is None:
        print "Identifier required"
        sys.exit(1)

    metadata = meta.find_one()
    meta_id = None
    if metadata is None: #Doesn't exist
        md = {'firstVersion': options.identifier,
              'lastVersion' : options.identifier,
              'versionStats': [],
             }
        meta_id = meta.insert(md)
    else:
        if metadata['lastVersion'] >= options.identifier:
            print "Identifier must be 'greater than' previous idnetifier"
            sys.exit(1)
        meta_id = metadata['_id']


    if options.exclude != "":
        options.exclude = options.exclude.split(',')

    # Setup indexes
    collection.ensure_index('domainName', background=True)
    collection.ensure_index('latest.contactEmail', background=True)
    collection.ensure_index('latest.registrant_name', background=True)
    collection.ensure_index('latest.registrant_telephone', background=True)

    collection.ensure_index('history.contactEmail', background=True, sparse=True)
    collection.ensure_index('history.registrant_name', background=True, sparse=True)
    collection.ensure_index('history.registrant_telephone', background=True, sparse=True)

    if options.directory:
        scan_directory(collection, options.directory, options)
    elif options.file:
        parse_csv(collection, options.file, options)
    else:
        print "File or Directory required"
        sys.exit(1) 


    # Now that it's been processed, update the metadata
    meta.update({'_id': meta_id}, {'$set' : {'lastVersion': options.identifier}})
    stats = { 'version': options.identifier,
              'total' : NUM_ENTRIES,
              'new' : NUM_NEW,
              'updated' : NUM_UPDATED,
              'unchanged' : NUM_UNCHANGED,
              'comment' : options.comment
            }
    meta.update({'_id': meta_id}, {'$push' : {'versionStats' : stats}})

    if options.stats:
        print "Stats: "
        print "Total Entries:\t\t %d" % NUM_ENTRIES
        print "New Entries:\t\t %d" % NUM_NEW
        print "Updated Entries:\t %d" % NUM_UPDATED
        print "Unchanged Entries:\t %d" % NUM_UNCHANGED

if __name__ == "__main__":
    main()
