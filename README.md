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


pyDat
=====

pyDat is a Python implementation of [Chris Clark's](https://github.com/Xen0ph0n)
WhoDat code. It is designed to be more extensible and has more features than
the PHP implementation.

Version 2.0 of pyDat includes support for historical whois searches. This capability
necessitated modifying the way data is stored in the database. To aid in properly populating
the database, a script called [mongo_populate](./pydat/scripts/mongo_populate.py) is provided
to auto-populate the data. Note that the data coming from whoisxmlapi doesn't seem to be always
consistent so some care should be taken when ingesting data. More testing needs to be done to ensure
all data is ingested properly

ScreenShots
===========

![alt tag](http://imgur.com/DmzZIgH.png)
![alt tag](http://i.imgur.com/6vPVU6a.png)

Running pyDat
=============

pyDat does not provide any data on its own. You must provide your own whois
data in a MongoDB. Beyond the data in a MongoDB you will need
[Django](https://djangoproject.com), [pymongo](https://pypi.python.org/pypi/pymongo/), [unicodecsv](https://pypi.python.org/pypi/unicodecsv)
and [requests](https://pypi.python.org/pypi/requests) (at least 2.2.1).

Populating Mongo with whoisxmlapi data (Ubuntu 12.04.4 LTS)
===========================================================

- Install [MongoDB](http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/)
- Download latest trimmed (smallest possible) whoisxmlapi quarterly DB dump.
- Extract the csv files.

- Use the included script in the scripts/ directory:

```
./mongo_populate.py -f ~/whois/data/1.csv -i '1' -v -s -x Audit_auditUpdatedDate,updatedDate,standardRegUpdatedDate,expiresDate,standardRegExpiresDate
```

- Copy pydat to /var/www/ (or prefered location)
- Copy pydat/custom_settings_example.py to pydat/custom_settings.py.
- Edit pydat/custom_settings.py to suit your needs.
  - Include your DNSDB key if you have one!
- Configure Apache to use the provided wsgi interface to pydat.
```
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

pyDat API
===========================================================

pyDat 2.0 has a scriptable API that allows you to make search requests and obtain JSON data. The following endpoints are exposed:

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

pyDat is copyright The MITRE Corporation 2014.

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
