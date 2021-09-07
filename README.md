# WhoDat Project

**NOTE: During development of PyDat 5, internal operations has shifted their direction leading to the retirement of the PyDat project. Although a lot of the work has been done to finalize PyDat 5's capabilities, some capabilties remain not fully tested.**

The WhoDat project is an interface for whoisxmlapi data, or any whois data
living in ElasticSearch. It integrates whois data, current IP resolutions and
passive DNS. In addition to providing an interactive, pivotable application
for analysts to perform research, it also has an API which will allow output
in JSON format.

WhoDat was originally written by [Chris Clark](https://github.com/Xen0ph0n).
The original implementation is in PHP and available in this repository under
the [legacy_whodat](./legacy_whodat) directory. The code was re-written
from scratch by [Wesley Shields](https://github.com/wxsBSD) and
[Murad Khan](https://github.com/mraoul) in Python, and is available under the
[pydat](./pydat) directory.

The PHP version is left for those who want to run it, but it is not as full
featured or extensible as the Python implementation, and is not supported.

For more information on the PHP implementation please see the
[readme](./legacy_whodat/README.md). For more information on the
Python implementation keep reading...

## PyDat

pyDat is a Python implementation of [Chris Clark's](https://github.com/Xen0ph0n)
WhoDat code. It is designed to be more extensible and has more features than
the PHP implementation.

### PreReqs

pyDat is a python 3.6+ application that requires the following to run:

- ElasticSearch installed somewhere (version 7.x is supported)
- python packages (installed via setup script)

### Data Population

To aid in properly populating the database, a program called `pydat-populator`
is provided to auto-populate the data.
Note that the data coming from whoisxmlapi doesn't seem to be always consistent so some care should be taken when ingesting data.
More testing needs to be done to ensure all data is ingested properly.
Anyone setting up their database, should read the available flags for the script before running it to ensure they've tweaked it for their setup.
The following is the output from `pydat-populator -h`:

    usage: pydat-populator [-h] [-c CONFIG] [--debug] [--debug-level DEBUG_LEVEL]
                        [-x EXCLUDE [EXCLUDE ...]] [-n INCLUDE [INCLUDE ...]]
                        [--ignore-field-prefixes [IGNORE_FIELD_PREFIXES [IGNORE_FIELD_PREFIXES ...]]]
                        [-e EXTENSION] [-v] [-s] [--pipelines PIPELINES]
                        [--shipper-threads SHIPPER_THREADS]
                        [--fetcher-threads FETCHER_THREADS]
                        [--bulk-ship-size BULK_SHIP_SIZE]
                        [--bulk-fetch-size BULK_FETCH_SIZE]
                        [-u [ES_URI [ES_URI ...]]] [--es-user ES_USER]
                        [--es-pass ES_PASSWORD] [--cacert ES_CA_CERT]
                        [--es-disable-sniffing] [-p ES_INDEX_PREFIX]
                        [--rollover-size ES_ROLLOVER_DOCS] [--ask-pass]
                        [-r | --config-template-only | --clear-interrupted-flag]
                        [-f INGEST_FILE | -d INGEST_DIRECTORY] [-D INGEST_DAY]
                        [-o COMMENT]

    optional arguments:
    -h, --help            show this help message and exit
    -c CONFIG, --config CONFIG
                            location of configuration file for
                            environmentparameter configuration (example yaml file
                            in /backend)
    --debug               Enables debug logging
    --debug-level DEBUG_LEVEL
                            Debug logging level [0-3] (default: 1)
    -x EXCLUDE [EXCLUDE ...], --exclude EXCLUDE [EXCLUDE ...]
                            list of keys to exclude if updating entry
    -n INCLUDE [INCLUDE ...], --include INCLUDE [INCLUDE ...]
                            list of keys to include if updating entry (mutually
                            exclusive to -x)
    --ignore-field-prefixes [IGNORE_FIELD_PREFIXES [IGNORE_FIELD_PREFIXES ...]]
                            list of fields (in whois data) to ignore when
                            extracting and inserting into ElasticSearch
    -e EXTENSION, --extension EXTENSION
                            When scanning for CSV files only parse files with
                            given extension (default: csv)
    -v, --verbose         Be verbose
    -s, --stats           Print out Stats after running
    -r, --redo            Attempt to re-import a failed import or import more
                            data, uses stored metadata from previous run
    --config-template-only
                            Configure the ElasticSearch template and then exit
    --clear-interrupted-flag
                            Clear the interrupted flag, forcefully (NOT
                            RECOMMENDED)
    -f INGEST_FILE, --file INGEST_FILE
                            Input CSV file
    -d INGEST_DIRECTORY, --directory INGEST_DIRECTORY
                            Directory to recursively search for CSV files --
                            mutually exclusive to '-f' option
    -D INGEST_DAY, --ingest-day INGEST_DAY
                            Day to use for metadata, in the format 'YYYY-MM-dd',
                            e.g., '2021-01-01'. Defaults to todays date, use
                            'YYYY-MM-00' to indicate a quarterly ingest, e.g.,
                            2021-04-00
    -o COMMENT, --comment COMMENT
                            Comment to store with metadata

    Performance Options:
    --pipelines PIPELINES
                            Number of pipelines (default: 2)
    --shipper-threads SHIPPER_THREADS
                            How many threads per pipeline to spawn to send bulk ES
                            messages. The larger your cluster, the more you can
                            increase this, defaults to 1
    --fetcher-threads FETCHER_THREADS
                            How many threads to spawn to search ES. The larger
                            your cluster, the more you can increase this, defaults
                            to 2
    --bulk-ship-size BULK_SHIP_SIZE
                            Size of Bulk Elasticsearch Requests (default: 10)
    --bulk-fetch-size BULK_FETCH_SIZE
                            Number of documents to search for at a time (default:
                            50), note that this will be multiplied by the number
                            of indices you have, e.g., if you have 10
                            pydat-<number> indices it results in a request for 500
                            documents

    Elasticsearch Options:
    -u [ES_URI [ES_URI ...]], --es-uri [ES_URI [ES_URI ...]]
                            Location(s) of ElasticSearch Server (e.g.,
                            foo.server.com:9200) Can take multiple endpoints
    --es-user ES_USER     Username for ElasticSearch when Basic Auth is enabled
    --es-pass ES_PASSWORD
                            Password for ElasticSearch when Basic Auth is enabled
    --cacert ES_CA_CERT   Path to a CA Certicate bundle to enable https support
    --es-disable-sniffing
                            Disable ES sniffing, useful when ssl
                            hostnameverification is not working properly
    -p ES_INDEX_PREFIX, --index-prefix ES_INDEX_PREFIX
                            Index prefix to use in ElasticSearch (default: pydat)
    --rollover-size ES_ROLLOVER_DOCS
                            Set the number of documents after which point a new
                            index should be created, defaults to 50 million, note
                            that this is fuzzy since the index count isn't
                            continuously updated, so should be reasonably below 2
                            billion per ES shard and should take your ES
                            configuration into consideration
    --ask-pass            Prompt for ElasticSearch password

Note that when adding a new version of data to the database, you should use
either the -x flag to exclude certain fields that are not important to track
changes or the -n flag to include specific fields that are subject to scrutiny.
This will significantly decrease the amount of data that is stored between
versions. You can only use either -x or -n not both at the same time, but you
can choose whichever is best for your given environment. As an example, if you
get daily updates, you might decide that for daily updates you only care
if contactEmail changes but every quarter you might want to instead only exclude
certain fields you don't find important.

#### Config File

To save time on repetitive flag usage, `pydat-populator` takes a configuration file.
Please look at the [example config](./pydat/backend/es_populate_config.yml.example) for an example of how to create a configuration file.

### Running pyDat

pyDat does not provide any data on its own. You must provide your own whois
data in an ElasticSearch data store.

### Populating ElasticSearch with whoisxmlapi data (Ubuntu 20.04 LTS)

- Install ElasticSearch. Using [Docker](https://www.docker.elastic.co/) is the easiest mechanism
- Download latest trimmed (smallest possible) whoisxmlapi quarterly DB dump.
- Extract the csv files.
- Use the included progam when the package is installed:

>
    pydat-populator -u localhost:9200 -f ~/whois/data/1.csv -v -s -x Audit_auditUpdatedDate,updatedDate,standardRegUpdatedDate,expiresDate,standardRegExpiresDate

### Installation

PyDat 5 is a split backend/frontend application that utilizes Python Flask for providing a REST API and ReactJS for providing an interactive web UI. The easiest way to use the app is to build a docker image.

    cd pydat/
    docker build -t mitrecnd/pydat:5

The created image will compile and install the frontend components into the backend allowing deployment of the full app.

The app can then be deployed by creating a deployment configuration file and using `docker-compose`:

>
    version: '3'
    services:
        pydat:
            image: mitrecnd/pydat:5
            volumes:
                - "./config.py:/opt/pydat/config.py:ro"
            ports:
                - 127.0.0.1:8888:8888

Generate a config file by copying the `config_example.py` file as `config.py` to the same directory as the `docker-compose.yml` file.

The python backend can also be installed using pip. This is useful if you want to natively run the data population capability. Note that this not contain any frontend components as they do not come pre-compiled. Refernce the `dockerfile` if you'd like to manually compile and install the frontend.

    cd pydat/backend/
    pip install ./

Installing the package will give you accesss to the `pydat-populator` program referenced above.

## pyDat API

PyDat 5 introduces an updated REST API but maintains a `v1` set of API endpoints to approximate the output that would be returned from Pydat 4. Due to some structural changes between pyDat 4 and 5, the output will not be exactly the same.

### Pydat `v1` Endpoints

The following endpoints are exposed:

>
    api/v1/metadata/
    api/v1/metadata/<version>/

The metadata endpoint returns metadata available for the data in the database. Specifying a version will return metadata for that specific version

>
    api/v1/domain/<domainName>/
    api/v1/domain/<domainName>/latest/
    api/v1/domain/<domainName>/<version>/
    api/v1/domain/<domainName>/<version1>/<version2>/
    api/v1/domain/<domainName>/diff/<version1>/<version2>/

The domain endpoint allows you to get information about a specific domain name. By default, this will return information for any version of a domain that is found in the database. You can specify more information to obtain specific versions of domain information or to obtain the latest entry. You can also obtain a diff between two versions of a domain to see what has changed.

>
    api/v1/domains/<searchKey>/<searchValue>/
    api/v1/domains/<searchKey>/<searchValue>/latest/
    api/v1/domains/<searchKey>/<searchValue>/<version>/
    api/v1/domains/<searchKey>/<searchValue>/<version1>/<version2>/

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

#### Advanced Syntax Endpoint

    api/v1/query

This endpoint takes 4 parameters via a GET request:

    query - The query to search ES with
    size - The number of elements to return (aka page size)
    page - The page to return, combining this with size you can get the results in chunks
    unique - Attempts to return the latest entry per domainName

**Note on the unique parameter**: If you're using the unique parameter, note
that paging of results is disabled, but the size parameter will still be used
to control the number of results returned.

### PyDat `v2` Endpoints

The following endpoints are exposed:

>
    api/v2/metadata
    api/v2/metadata/<version>

These endpoints are similar to their v1 counterparts but their response format differs

>
    api/v2/resolve/<domain>

This is a new endpoint that allows you to resolve a domain name to ip addresses. Note that this capability can be disabled by the backend. Please make a call to the `/settings` endpoint to ensure this capability is enabled before calling it.

>
    api/v2/domains/diff [POST]

This endpoint allows you to obtain a diff between two versions of a domain to see what has changed. It expects a JSON request with the following form:

>
    {
        domain: "mydomain.example",
        version1: 1,
        version2: 2
    }

>
    api/v2/domain [POST]

This endpoint returns information for a given domain name and expects a JSON request with the following form:

>
    {
        value: "mydomain.example",
        version: 1, # Optional
        chunk_size: 50, # Optional
        offset: 0 # Optional
    }

>
    api/v2/query [POST]

This endpoint supports the 'advanced' query syntax capability. It expects a JSON request with the following form:

>
    {
        query: "myquery",
        chunk_size: 50, # Optional
        offset: 0, #Optional
        unique: false, # Optional
        sort_keys: [ # Optional
            "domainName",
            "registrant_name",
            "contactEmail",
            "standardRegCreatedDate",
            "registrant_telephone",
            "dataVersion",
            "_score",
        ]
    }

>
    api/v2/info

This endpoint provides health information about the Elastic cluster

>
    api/v2/settings

This endpoint is mainly used by the frontend to dynamically determine which capabilities are enabled by the backend application.

## PyDat 4 to 5 Migration

Unfortunately due to structural changes in the way data is stored in Elastic, pyDat 5 is not backwards compatible with pydat 4.
This means that data will need to be newly ingested into an ElasticSearch cluster to be used with pyDat 5.

## Legal Stuff

pyDat is copyright The MITRE Corporation 2021.

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
