# WhoDat Project

The WhoDat project is a front-end for whoisxmlapi data, or any whois data
living in ElasticSearch. It integrates whois data, current IP resolutions and
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

For more information on the PHP implementation please see the
[readme](../master/legacy_whodat/README.md). For more information on the
Python implementation keep reading...

## PreReqs

pyDat is a python 2.7 application that requires the following to run:

- ElasticSearch installed somewhere (versions 5.2 -> 6.x are supported, up to 6.3.1 tested)
- python packages:
  - requests
  - unicodecsv
  - markdown
  - django
  - elasticsearch (version must correspond to cluster version)
  - ply

## pyDat

pyDat is a Python implementation of [Chris Clark's](https://github.com/Xen0ph0n)
WhoDat code. It is designed to be more extensible and has more features than
the PHP implementation.

To aid in properly populating the database, a script called
[elasticsearch_populate](./pydat/scripts/elasticsearch_populate.py) is provided
to auto-populate the data. Note that the data coming from whoisxmlapi doesn't seem to be always
consistent so some care should be taken when ingesting data. More testing needs to be done to ensure
all data is ingested properly. Anyone setting up their database, should read the available flags for the
script before running it to ensure they've tweaked it for their setup. The following is the output from
elasticsearch_populate -h

    usage: elasticsearch_populate.py [-h] [-f FILE | -d DIRECTORY] [-e EXTENSION]
                                    (-i IDENTIFIER | -r | -z | --config-template-only)
                                    [-v] [--vverbose] [-s]
                                    [-x EXCLUDE | -n INCLUDE] [-o COMMENT]
                                    [-u [ES_URI [ES_URI ...]]]
                                    [--es-user ES_USER] [--es-pass ES_PASS]
                                    [--es-ask-pass] [--es-enable-ssl ES_CACERT]
                                    [--es-disable-sniffing] [-p INDEX_PREFIX]
                                    [-B BULK_SIZE] [-b BULK_FETCH_SIZE]
                                    [--rollover-size ROLLOVER_DOCS]
                                    [--pipelines PIPELINES]
                                    [--shipper-threads SHIPPER_THREADS]
                                    [--fetcher-threads FETCHER_THREADS]
                                    [--ignore-field-prefixes [IGNORE_FIELD_PREFIXES [IGNORE_FIELD_PREFIXES ...]]]
                                    [--debug]

    optional arguments:
    -h, --help            show this help message and exit
    -f FILE, --file FILE  Input CSV file
    -d DIRECTORY, --directory DIRECTORY
                            Directory to recursively search for CSV files --
                            mutually exclusive to '-f' option
    -e EXTENSION, --extension EXTENSION
                            When scanning for CSV files only parse files with
                            given extension (default: 'csv')
    -i IDENTIFIER, --identifier IDENTIFIER
                            Numerical identifier to use in update to signify
                            version (e.g., '8' or '20140120')
    -r, --redo            Attempt to re-import a failed import or import more
                            data, uses stored metadata from previous import (-o,
                            -n, and -x not required and will be ignored!!)
    -z, --update          Run the script in update mode. Intended for taking
                            daily whois data and adding new domains to the current
                            existing index in ES.
    --config-template-only
                            Configure the ElasticSearch template and then exit
    -v, --verbose         Be verbose
    --vverbose            Be very verbose (Prints status of every domain parsed,
                            very noisy)
    -s, --stats           Print out Stats after running
    -x EXCLUDE, --exclude EXCLUDE
                            Comma separated list of keys to exclude if updating
                            entry
    -n INCLUDE, --include INCLUDE
                            Comma separated list of keys to include if updating
                            entry (mutually exclusive to -x)
    -o COMMENT, --comment COMMENT
                            Comment to store with metadata
    -u [ES_URI [ES_URI ...]], --es-uri [ES_URI [ES_URI ...]]
                            Location(s) of ElasticSearch Server (e.g.,
                            foo.server.com:9200) Can take multiple endpoints
    --es-user ES_USER     Username for ElasticSearch when Basic Authis enabled
    --es-pass ES_PASS     Password for ElasticSearch when Basic Authis enabled
    --es-ask-pass         Prompt for ElasticSearch password
    --es-enable-ssl ES_CACERT
                            The path, on disk to the cacert of the ElasticSearch
                            server to enable ssl/https support
    --es-disable-sniffing
                            Disable ES sniffing, useful when ssl
                            hostnameverification is not working properly
    -p INDEX_PREFIX, --index-prefix INDEX_PREFIX
                            Index prefix to use in ElasticSearch (default: pydat)
    -B BULK_SIZE, --bulk-size BULK_SIZE
                            Size of Bulk Elasticsearch Requests
    -b BULK_FETCH_SIZE, --bulk-fetch-size BULK_FETCH_SIZE
                            Number of documents to search for at a time (default
                            50), note that this will be multiplied by the number
                            of indices you have, e.g., if you have 10
                            pydat-<number> indices it results in a request for 500
                            documents
    --rollover-size ROLLOVER_DOCS
                            Set the number of documents after which point a new
                            index should be created, defaults to 50 milllion, note
                            that this is fuzzy since the index count isn't
                            continuously updated, so should be reasonably below 2
                            billion per ES shard and should take your ES
                            configuration into consideration
    --pipelines PIPELINES
                            Number of pipelines, defaults to 2
    --shipper-threads SHIPPER_THREADS
                            How many threads per pipeline to spawn to send bulk ES
                            messages. The larger your cluster, the more you can
                            increase this, defaults to 1
    --fetcher-threads FETCHER_THREADS
                            How many threads to spawn to search ES. The larger
                            your cluster, the more you can increase this, defaults
                            to 2
    --ignore-field-prefixes [IGNORE_FIELD_PREFIXES [IGNORE_FIELD_PREFIXES ...]]
                            list of fields (in whois data) to ignore when
                            extracting and inserting into ElasticSearch
    --debug               Enables debug logging

Note that when adding a new version of data to the database, you should use
either the -x flag to exclude certain fields that are not important to track
changes or the -n flag to include specific fields that are subject to scrutiny.
This will significantly decrease the amount of data that is stored between
versions. You can only use either -x or -n not both at the same time, but you
can choose whichever is best for your given environment. As an example, if you
get daily updates, you might decide that for daily updates you only care
if contactEmail changes but every quarter you might want to instead only exclude
certain fields you don't find important.

### ScreenShot

![alt tag](https://imgur.com/QT7Mkfp.png)

### Running pyDat

pyDat does not provide any data on its own. You must provide your own whois
data in an ElasticSearch data store.

### Populating ElasticSearch with whoisxmlapi data (Ubuntu 16.04.3 LTS)

- Install ElasticSearch. Using [Docker](https://www.docker.elastic.co/) is the easiest mechanism
- Download latest trimmed (smallest possible) whoisxmlapi quarterly DB dump.
- Extract the csv files.
- Use the included script in the scripts/ directory:

>
    ./elasticsearch_populate.py -u localhost:9200 -f ~/whois/data/1.csv -i '1' -v -s -x Audit_auditUpdatedDate,updatedDate,standardRegUpdatedDate,expiresDate,standardRegExpiresDate

### Upgrading ElasticSearch 5.x -> 6.x

If you started with Elasticsearch 5.x and upgrade your cluster to 6.x, you
should run the population script with the `--config-template-only` flag to update
the backend template. This will not change the way the data is configured and
serves only to eliminate deprecation warnings that your cluster will
throw otherwise

>
    ./elasticsearch_populate -u localhost:9200 --config-template-only

## Installation

### Local Installation

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

### Docker Installation

If you don't want to install pyDat manually, you can use the docker image to
quickly deploy the system.

First, make sure to copy custom_settings_example.py to custom_settings.py
and customize it to match your environment

You can then launch pyDat by running

    docker run -d --name pydat -p 80:80 -v <path/to/custom_settings.py>:/opt/WhoDat/pydat/pydat/custom_settings.py mitrecnd/pydat

### Docker Compose

To run pydat with compose your `docker-compose.yml` file could look like:

```yaml
version: '2'
services:
    pydat:
        image: mitrecnd/pydat
        volumes:
            - "./custom_settings.py:/opt/WhoDat/pydat/pydat/custom_settings.py"
        ports:
            - 80:80
```

Note that the above config assumes that a `custom_settings.py` file exists in the
same directory as the compose file.

#### Docker Compose Test Setup

If you want to test pydat with a local docker-ized instance of ES, here is an
example compose configuration:

```yaml
version: '2'
services:
    elasticsearch:
        image: docker.elastic.co/elasticsearch/elasticsearch-oss:6.3.1
        environment:
          - cluster.name=pydat
          - bootstrap.memory_lock=true
          - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
        ulimits:
          memlock:
            soft: -1
            hard: -1
        mem_limit: 1g
        volumes:
            - pydat-data:/usr/share/elasticsearch/data
        ports:
            - 127.0.0.1:9200:9200
    pydat:
        image: mitrecnd/pydat
        volumes:
            - "./custom_settings.py:/opt/WhoDat/pydat/pydat/custom_settings.py"
        ports:
            - 0.0.0.0:8888:80

volumes:
  pydat-data:
```

Along with the contents of its cooresponding `custom_settings.py` file:

```python
DEBUG = True
ALLOWED_HOSTS = ['*']
ES_URI = 'elasticsearch:9200'
```

Note that the ElasticSearch instance is only accessible via localhost, while
pydat will be listening on all interfaces on port 8888. Also, further note that
while this is fine for small data sets, a production-level cluster is
recommended for hosting full quarterly dumps.

## pyDat API

The following endpoints are exposed:

>
    ajax/metadata/
    ajax/metadata/<version>/

The metadata endpoint returns metadata available for the data in the database. Specifying a version will return metadata for that specific version

>
    ajax/domain/<domainName>/
    ajax/domain/<domainName>/latest/
    ajax/domain/<domainName>/<version>/
    ajax/domain/<domainName>/<version1>/<version2>/
    ajax/domain/<domainName>/diff/<version1>/<version2>/

The domain endpoint allows you to get information about a specific domain name. By default, this will return information for any version of a domain that is found in the database. You can specify more information to obtain specific versions of domain information or to obtain the latest entry. You can also obtain a diff between two versions of a domain to see what has changed.

>
    ajax/domains/<searchKey>/<searchValue>/
    ajax/domains/<searchKey>/<searchValue>/latest/
    ajax/domains/<searchKey>/<searchValue>/<version>/
    ajax/domains/<searchKey>/<searchValue>/<version1>/<version2>/

The domains endpoint allows you to search for domains based on a specified key. Currently the following keys are supported:

>
    domainName
    registrant_name
    contactEmail
    registrant_telephone

Similar to the domain endpoint you can specify what versions of the data you are looking for.

Example Queries:

>
    curl http://pydat.myorg.domain/ajax/domain/google.com/latest/

    curl http://pydat.myorg.domain/ajax/domains/domainName/google.com/

### Advanced Syntax Endpoint

    ajax/query

This endpoint takes 4 parameters via a GET request:

    query - The query to search ES with
    size - The number of elements to return (aka page size)
    page - The page to return, combining this with size you can get the results in chunks
    unique - Only accepted if ES scripting is enabled (read above)

**Note on the unique parameter**: If you're using the unique parameter, note
that paging of results is disabled, but the size parameter will still be used
to control the number of results returned.

## Untested Stuff

Chris has an update.py script which I haven't used yet, so all bets are off,
but it should allow you to get regular updates on specific watched fields via
a cron job. For more information please see the [PHP implementation](../master/whodat).

## TODO

- Move Chris' update script to a common directory and test it out.

## Legal Stuff

pyDat is copyright The MITRE Corporation 2018.

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
with pyDat. If not, see <http://www.gnu.org/licenses/>.

Approved for Public Release; Distribution Unlimited 14-1633
