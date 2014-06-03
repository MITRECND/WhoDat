pyDat
=====

pyDat is a Python implementation of [Chris Clark's](https://github.com/Xen0ph0n)
WhoDat code. It is designed to be more extensible and has more features than
the PHP implementation.

ScreenShots
=============
![alt tag](http://imgur.com/DmzZIgH.png)
![alt tag](http://i.imgur.com/6vPVU6a.png)

Running pyDat
=============

pyDat does not provide any data on its own. You must provide your own whois
data in a MongoDB. Beyond the data in a MongoDB you will need
[Django](https://djangoproject.com), [pymongo](https://pypi.python.org/pypi/pymongo/),
and [requests](https://pypi.python.org/pypi/requests) (at least 2.2.1).

Populating Mongo with whoisxmlapi data (Ubuntu 12.04.4 LTS)
======================================

- Install [MongoDB](http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/)
- Download latest trimmed (smallest possible) whoisxmlapi quarterly DB dump.
- Extract the csv files.
- Import them (adjust for your needs):
```
for file in */*.csv; do echo $file && mongoimport --db whois --collection whois --file $file --type csv --headerline --upsert --upsertFields domainName; done
```
- Create indexes on domainName, registrant_name, contactEmail and registrant_telephone.
```
db.whois.ensureIndex( {domainName: 1})
db.whois.ensureIndex( {contactEmail: 1})
db.whois.ensureIndex( {registrant_name: 1})
db.whois.ensureIndex( {registrant_telephone: 1})

```
- Copy pydat to /var/www/ (or prefered location)
- Copy pydat/custom_settings_example.py to pydat/custom_settings.py.
- Edit pydat/custom_settings.py to suit your needs.
  - Change DEBUG - True
  - Include your DNSDB key if you have one!
- Configure Apache to use the provided wsgi interface to pydat.
```
sudo apt-get install libapache2-mod-wsgi
sudo nano /etc/apache2/sites-available/whois

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
Untested Stuff
=============

Chris has an update.py script which I haven't used yet, so all bets are off,
but it should allow you to get regular updates on specific watched fields via
a cron job. For more information please see the [PHP implementation](../master/whodat).

TODO
====

- Move Chris' update script to a common directory and test it out.
- Find a way to implement historical searches.

Legal Stuff
===========

pyDat is copyrighted by The MITRE Corporation 2014.

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
