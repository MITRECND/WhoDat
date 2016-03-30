WhoDat Project
==============


The WhoDat project is a front-end for whoisxmlapi data, or any whois data
living in a MongoDB. It integrates whois data, current IP resolutions and
passive DNS. In addition to providing an interactive, pivotable application
for analysts to perform research, it also has an API which will allow output
in JSON or list format.

WhoDat was originally written by [Chris Clark](https://github.com/Xen0ph0n).
The original implementation is in PHP and available in this repository under
the [legacy_whodat](../master/legacy_whodat) directory. The code was re-written
from scratch by [Wesley Shields](https://github.com/wxsBSD) and
[Murad Khan](https://github.com/mraoul) in Python, and is available under the
[pydat](../master/pydat) directory.

The PHP version is left for those who want to run it, but it is not as full
featured or extensible as the Python implementation, and is not supported.

For more information on the PHP implementation please see the [readme](../master/legacy_whodat/README.md). For more information on the Python implementation
keep reading...


ElasticSearch
==============

<b>The ElasticSearch backend code is still under testing, please consider the following before using ES as a backend:</b>

- Some things might be broken
    - I.e., some error handling might be non-existent
- There might be random debug output printed out
- The search language might not be complete
- The data template used with ElasticSearch might change
    - Which means you might have ot re-ingest all of your data at some point!


<b>PreReqs to run with ElasticSearch</b>:

- ElasticSearch installed somewhere
- python elasticsearch library (pip install elasticsearch)
- python lex yacc library (pip install ply)
- below specified prereqs too 

<b>ElasticSearch Scripting</b>
ElasticSearch comes with dynamic Groovy scripting disabled due to potential sandbox breakout issues with the Groovy container. Unfortunately, the only way to do certain things in ElasticSearch is via this scripting language. Because the default installation of ES does not have a work-around, there is a setting called ES_SCRIPTING_ENABLED in the pyDat settings file which is set to False by default. When set to True, the pyDat advanced search capability will expose an extra feature called 'Unique Domains' which given search results that will return multiple results for a given domain (e.g., due to multiple versions of a domain matching) will return only the latest entry instead of all entries. Before setting this option to True, you must install a script server-side on every ES node -- to do this, please copy the file called \_score.groovy from the es_scripts directory to your scripts directory located in the elasticsearch configuration directory. On package-based installs of ES on RedHat/CentOS or Ubuntu this should be /etc/elasticsearch/scripts. If the scripts directory does not exist, please create it. Note you have to restart the Node for it to pick up the script.

<b> ElasticSearch Plugins</b>

The murmur3 mapping type was removed from the ElasticSearch core and into a plugin. The stats page uses this field to obtain information about the domains loaded in elasticsearch and further the template provided will not load if the murmur3 mapper is not loaded. Ensure the plugin is installed on *every* node in your cluster before proceeding. Alternatively, you can remove 'hash' field from domainName in the template and disable the stats page (just html comment or remove the link from the header).


To install the plugin, use the plugin utility on every node:

<pre>
plugin install mapper-murmur3
</pre>


This will require a restart of the node to pick up the plugin.


pyDat
=====

pyDat is a Python implementation of [Chris Clark's](https://github.com/Xen0ph0n)
WhoDat code. It is designed to be more extensible and has more features than
the PHP implementation.

Version 2.0 of pyDat introduced support for historical whois searches. This capability
necessitated modifying the way data is stored in the database. To aid in properly populating
the database, a script called [elasticsearch_populate](./pydat/scripts/elasticsearch_populate.py) is provided
to auto-populate the data. Note that the data coming from whoisxmlapi doesn't seem to be always
consistent so some care should be taken when ingesting data. More testing needs to be done to ensure
all data is ingested properly. Anyone setting up their database, should read the available flags for the
script before running it to ensure they've tweaked it for their setup. The following is the output from
elasticsearch_populate -h

<pre>
Usage: elasticsearch_populate.py [options]

Options:
  -h, --help            show this help message and exit
  -f FILE, --file=FILE  Input CSV file
  -d DIRECTORY, --directory=DIRECTORY
                        Directory to recursively search for CSV files -
                        prioritized over 'file'
  -e EXTENSION, --extension=EXTENSION
                        When scanning for CSV files only parse files with
                        given extension (default: 'csv')
  -i IDENTIFIER, --identifier=IDENTIFIER
                        Numerical identifier to use in update to signify
                        version (e.g., '8' or '20140120')
  -t THREADS, --threads=THREADS
                        Number of workers, defaults to 2. Note that each
                        worker will increase the load on your ES cluster
  -B BULK_SIZE, --bulk-size=BULK_SIZE
                        Size of Bulk Insert Requests
  -v, --verbose         Be verbose
  --vverbose            Be very verbose (Prints status of every domain parsed,
                        very noisy)
  -s, --stats           Print out Stats after running
  -x EXCLUDE, --exclude=EXCLUDE
                        Comma separated list of keys to exclude if updating
                        entry
  -n INCLUDE, --include=INCLUDE
                        Comma separated list of keys to include if updating
                        entry (mutually exclusive to -x)
  -o COMMENT, --comment=COMMENT
                        Comment to store with metadata
  -r, --redo            Attempt to re-import a failed import or import more
                        data, uses stored metatdata from previous import (-o
                        and -x not required and will be ignored!!)
  -u ES_URI, --es-uri=ES_URI
                        Location of ElasticSearch Server (e.g.,
                        foo.server.com:9200)
  -p INDEX_PREFIX, --index-prefix=INDEX_PREFIX
                        Index prefix to use in ElasticSearch (default: whois)
  --bulk-threads=BULK_THREADS
                        How many threads to use for making bulk requests to ES
</pre>


Note that when adding a new version of data to the database, you should use either the -x flag to exclude certain
fields that are not important to track changes or the -n flag to include specific fields that are subject to scrutiny.
This will significantly decrease the amount of data that is stored between versions. You can only use either -x or -n not both
at the same time, but you can choose whichever is best for your given environment. As an example, if you get daily updates, you
might decide that for daily updates you only care if contactEmail changes but every quarter you might want to instead only exclude
certain fields you don't find important.

Version 3.0 of pyDat introduces ElasticSearch as the backend going forward for storing and searching data. Although the mongo backend
should still work, it should be considered deprecated and it is recommended installations move to ES as a backend as it provides 
numerous benefits with regards to searching, including a full-featured query language allowing for more powerful searches.

ScreenShot
===========

![alt tag](https://imgur.com/QT7Mkfp.png)

Running pyDat
=============

pyDat does not provide any data on its own. You must provide your own whois data in an ElasticSearch data store . Beyond the data in ElasticSearch you will need
[Django](https://djangoproject.com), [unicodecsv](https://pypi.python.org/pypi/unicodecsv), 
[requests](https://pypi.python.org/pypi/requests) (at least 2.2.1) and [markdown](https://pypi.python.org/pypi/Markdown). 


Populating ElasticSearch with whoisxmlapi data (Ubuntu 14.04.3 LTS)
===========================================================

- Install ElasticSearch. Using [Docker](https://hub.docker.com/_/elasticsearch/) is the easiest mechanism
- Download latest trimmed (smallest possible) whoisxmlapi quarterly DB dump.
- Extract the csv files.

- Use the included script in the scripts/ directory:

```
./elasticsearch_populate.py -u localhost:9200 -f ~/whois/data/1.csv -i '1' -v -s -x Audit_auditUpdatedDate,updatedDate,standardRegUpdatedDate,expiresDate,standardRegExpiresDate
```

Local Installation
--------------------

- Copy pydat to /var/www/ (or prefered location)
- Copy pydat/custom_settings_example.py to pydat/custom_settings.py.
- Edit pydat/custom_settings.py to suit your needs.
  - Include your Passive DNS keys if you have any!
- Configure Apache to use the provided wsgi interface to pydat.
```bash
sudo apt-get install libapache2-mod-wsgi
sudo vi /etc/apache2/sites-available/whois

<VirtualHost *:80>
        ServerName whois
        ServerAlias whois
        # Install Location
        WSGIScriptAlias / /var/www/pydat/wsgi.py
        Alias /static/ /var/www/pydat/pydat/static/
        <Location "/static/">
            Options -Indexes
        </Location>
</VirtualHost>
```

Docker Installation
-------------------

If you don't want to install pyDat manually, you can use the docker image to quickly deploy the system.

First, make sure to copy custom_settings_example.py to custom_settings.py and customize it to match your environment

You can then launch pyDat by running

```
docker run -d --name pydat -p 80:80 -v <path/to/custom_settings.py>:/opt/WhoDat/pydat/pydat/custom_settings.py mitrecnd/pydat
``` 


pyDat API
===========================================================

Starting with pyDat 2.0 there's a scriptable API that allows you to make search requests and obtain JSON data. The following endpoints are exposed:

```
ajax/metadata/
ajax/metadata/<version>/
```

The metadata endpoint returns metadata available for the data in the database. Specifying a version will return metadata for that specific version

```
ajax/domain/<domainName>/
ajax/domain/<domainName>/latest/
ajax/domain/<domainName>/<version>/
ajax/domain/<domainName>/<version1>/<version2>/
ajax/domain/<domainName>/diff/<version1>/<version2>/
```

The domain endpoint allows you to get information about a specific domain name. By default, this will return information for any version of a domain that is found in the database. You can specify more information to obtain specific versions of domain information or to obtain the latest entry. You can also obtain a diff between two versions of a domain to see what has changed.

**Warning**: The output from the /diff endpoint has changed slightly in 3.0 to conform to the output of other endpoints. Data for the diff now resides in the 'data' object nested under the root

```
ajax/domains/<searchKey>/<searchValue>/
ajax/domains/<searchKey>/<searchValue>/latest/
ajax/domains/<searchKey>/<searchValue>/<version>/
ajax/domains/<searchKey>/<searchValue>/<version1>/<version2>/
```

The domains endpoint allows you to search for domains based on a specified key. Currently the following keys are supported:

```
domainName
registrant_name
contactEmail
registrant_telephone
```

Similar to the domain endpoint you can specify what versions of the data you are looking for.


Example Queries:

```
curl http://pydat.myorg.domain/ajax/domain/google.com/latest/

curl http://pydat.myorg.domain/ajax/domains/domainName/google.com/
```

Advanced Syntax Endpoint
-------------------------

If using ElasticSearch as the backend, a new endpoint is available that supports search via the advanced query syntax:

```
ajax/query
```

This endpoint takes 4 parameters via a GET request:

```
query - The query to search ES with
size - The number of elements to return (aka page size)
page - The page to return, combining this with size you can get the results in chunks
unique - Only accepted if ES scripting is enabled (read above)
```

###Note on the unique parameter
If you're using the unique parameter, note that paging of results is disabled, but the size paramter will still be used to control the number of results returned.


Untested Stuff
=============

Chris has an update.py script which I haven't used yet, so all bets are off,
but it should allow you to get regular updates on specific watched fields via
a cron job. For more information please see the [PHP implementation](../master/whodat).

TODO
====

- Move Chris' update script to a common directory and test it out.

Legal Stuff
===========

pyDat is copyright The MITRE Corporation 2016.

The PHP implementation is copyright Chris Clark, 2013. Contact him at
Chris@xenosys.org.

The PHP and Python versions are licensed under the same license.

pyDat is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

pyDat is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along
with pyDat. If not, see http://www.gnu.org/licenses/.

Approved for Public Release; Distribution Unlimited 14-1633
