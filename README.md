WHODAT is a front end for whoisxmlapi data (or any whois data living in mongo DB inserted by that csv format) it integrated Whois data, current IP resolutions, and PDNS. In addition to providing an interactive, pivotable web-frontend for analysts to perform research, it also has an api which will allow output in JSON, CSV, or a list of suspicious domains. Finally it will pull updates daily, check them against a list of known malicious registrants and email an alert to a specified email containing the registrant, domain, and current IP. 

This is hacked together and ugly, it could use a rebuild in Flask, and an elastic search layer ontop to allow better pivoting. The hardware required to power this with 140,000,000 domains is non trivial even with only 4 indexed fields it takes 400GB of DB space for all of the primary TLDs. 

I won't be supporting this as it's not a tool the general public will find to be of value, but I know a number of large orginizations/companies have asked for assistance or access to this so I figured there was some demand for the underlying logic. Please rebuild it to be less hideous. 

Notification emails appear as such (optionally PGP encrypted):

```
     WhoDat Known Bad Registrant Alert
     ------------2013-08-03-----------

Registrant Email   Current IP   Domain Name 
blahblah@gmail.com  27.98.198.192  777eddlhdb.com
blahblah@gmail.com  127.0.0.1  txbdddbw.net 
```

Installation steps... this is not a complete guide:
```
- Install Mongo DB / PHP / Mongo PHP drivers /pymongo
- Download latest trimmed (smallest possible) whoisxmlapi quarterly DB dump
- Extract the csv files (will be about 100gig) and do something like this "for file in */*.csv; do echo $file && mongoimport --collection whois --file $file  --type csv --headerline --upsert --upsertFields domainName; done"
- Fill in your ISC DNSDB Key in index.php
- Index on domainName, registrant_name, and contactEmail
- Fill in relevant environmental and alerting data in the update.py script as well as your user/pass to download daily updates
- Enter known bad registrants you wish to track in a file and specify its location in update.py variable registrantpath
- Create a cronjob to run the update script at 0430 or so EST 30 "4 * * * /usr/bin/python /YOURUPDATEWORKINGDIR/update.py >/dev/null 2>&1"
- Place index.php in your webroot of choice

- Stop Paying DomainTools a billion dollars. 

Woot! 

-Chris 

```
Usage from the API .. again not a complete guide ;) 
```
You can query by any indexed fields, returning either a domain list, CSV, or JSON (these values are apparent from using the webfront just play with it and you can eaisly construct the query, they are all GET values)

Hidden values are "&nodl=yes" == print CSV to standard out vs download and "&limit=XXXXX" == defines the number of results to return, default is set in the php page at 2000. 
```
Screenshots: 

![Image](https://raw.github.com/MITRECND/WhoDat/master/whodat/screenshots/ss1.png)

![Image](https://raw.github.com/MITRECND/WhoDat/master/whodat/screenshots/ss2.png)

![Image](https://raw.github.com/MITRECND/WhoDat/master/whodat/screenshots/ss3.png)

![Image](https://raw.github.com/MITRECND/WhoDat/master/whodat/screenshots/ss4.png)

License stuff: 

WhoDat is copyrighted by Chris Clark 2013. Contact me at Chris@xenosys.org

WhoDat is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

WhoDat is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with WhoDat. If not, see http://www.gnu.org/licenses/.
