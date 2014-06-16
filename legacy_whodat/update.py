#!/usr/bin/python
#Daily Update Script for Whodat
#Downloads, unzips, cuts, and upserts daily CSV's and alerts on known bad registrars (or any other data you want to check for inside the new registrations)
#By Chris@xenosec.org

import sys, urllib, urllib2, os, socket
from datetime import datetime, timedelta
from pymongo import MongoClient


tlds = ["com","org","net","mobi","us","coop","pro","info","biz"]
updatepath = "/path/to/useforupdateprocessing/"
registrantpath = "/path/to/badregistrants.txt"
login = 'whosxmlapiusername'
password = 'whoisxmlapipassword'
notifyemail = 'example@dot.com'
sendingemail = 'alerts@whodatisawesome.fake'
pgp = False

def updatesearch(date):
	client = MongoClient()
	whoisColl = client['test']['whois']
	emails = [line.strip() for line in open(registrantpath, 'r')]
	outfile = open( updatepath + "newdomains.txt", 'w')
	outfile.write("     WhoDat Known Bad Registrant Alert\n")
	outfile.write("     ------------"+date+"-----------\n\n")
	outfile.write("Registrant Email   Current IP   Domain Name \n")
	count = 0 
	for email in emails:
		for domain in whoisColl.find({u"contactEmail":email, u"standardRegCreatedDate":{'$regex': date+".*"}}):
			try:
				data = socket.gethostbyname(domain[u'domainName'])
				ip = str(data)
			except Exception:
				ip = "No DNS Record"
			outfile.write(domain[u'contactEmail'] + "  "+ ip + "  " + domain[u'domainName'] +  "\n")
			count += 1 
	outfile.close()
	if count > 0:
		if pgp == False:
			os.system('mail  -s "WhoDat Registration Alert ( '+ date+' )" '+ notifyemail +' -- -f '+ sendingemail+ ' < ' + updatepath + 'newdomains.txt')
		else:
			os.system('gpg --trust-model always -ea -r '+ notifyemail +' -o - ' + updatepath + 'newdomains.txt  | mail  -s "WhoDat Registration Alert ( '+ date+' )" '+ notifyemail +' -- -f '+ sendingemail)	
	os.remove('' + updatepath + 'newdomains.txt')

def downloads(date):
	for tld in tlds:
		try:
			passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
			passman.add_password(None, "http://bestwhois.org", username, password)
			authhandler = urllib2.HTTPBasicAuthHandler(passman)
			opener = urllib2.build_opener(authhandler)
			url = "http://bestwhois.org/domain_name_data/domain_names_whois/" + date + tld +".csv.gz"
			print url
			result = opener.open(urllib2.Request(url))
			downloadfile = result.read()
			if len(downloadfile) > 0:
		 		fo = open(updatepath + date + tld + ".csv.gz", "w")
				fo.write(downloadfile)
				fo.close()
		except Exception:
			continue
	if not  os.path.isfile(updatepath + date + "com" + ".csv.gz"):
		os.system('echo "Error downloading updates for WhoDat!" |  mail  -s "[!] WhoDat Update Error " '+ notifyemail +'  -- -f ' + sendingemail )


def unzip(date):
	for tld in tlds:
		os.system('gunzip' + updatepath +date+tld+'.csv.gz')

def cropfile(date):
	for tld in tlds:
		os.system('cut -d "," -f 1-43 '+ updatepath +date + tld + '.csv  > ' + updatepath + date + tld +'.done.csv')

def insertfile(date):
	for tld in tlds:
		os.system('mongoimport --collection whois --file ' + updatepath+ date + tld +'.done.csv  --type csv --headerline --upsert --upsertFields domainName')

def deletefiles(date):
	for file in os.listdir(updatepath):
		if file.startswith(date):
			os.remove(updatepath+ file)
def main():
	yesterday = datetime.now()-timedelta(days=1)
	date = yesterday.strftime("%Y_%m_%d_")
	dbyesterday = datetime.now()-timedelta(days=2)
	searchdate = dbyesterday.strftime("%Y-%m-%d")
	#use if the automagic missed a day
	#date = "2013_07_08_"
	#searchdate = "2013-07-07"
	downloads(date)
	unzip(date)
	cropfile(date)
	insertfile(date)
	deletefiles(date)
	updatesearch(searchdate)
if __name__ == '__main__':
	main()