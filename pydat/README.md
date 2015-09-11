pyDat with ElasticSearch
==================================

When used with an ElasticSearch backend, pyDat exposes a new search interface
that allows for more customized queries to be made.

Intro to Advanced Search
------------------------------

This syntax allows a user to search for generic terms across all entries or to
search specific fields for data, crafting potentially complex queries to find
data.

Here's a simple, example search:

```
gmail.com
```

Searching for just that phrase will instruct pyDat to return pretty much any
entry that has gmail or com in it (which would be alot!). Instead, one could
search for:

```
"gmail.com"
```

By quoting the search phrase, pyDat will now search for that phrase in its
entirety so any entry that has "gmail.com" will be returned. But since
"gmail.com" shows up in a lot of records in the email fields, this would return
not only the entry for the domain gmail.com but also any entry has has an
administrative contact or registrant contact which uses a gmail email address,
probably not what we want.

Okay, with the basics out of the way, let's get a bit more advanced, say we to
find the whois entry for the domain gmail.com but don't want the clutter of
domains that use a gmail email address. We could search for:

``` domainName:"gmail.com" ```

Instead of searching the entirety of a record, pyDat will now scope your search
to only the domainName field. Again, quotes are used to instruct pyDat that
you're looking for the exact wording. You'll notice that searching for
gmail.com without quotes would actually return every .com entry (but with
gmail.com at the top) since every .com entry doesn't have 'gmail' but they
definitely have .com. What you'll  also notice, though, is that the 'score'
value displayed by pyDat for those entries will be considerably lower than the
'score' for gmail.com.

Combining Queries
----------------------

Extending the above, you can combine search terms to make more advanced search
queries. For example, if you're looking for any domain with 'foo' in it, which
also has an email address (registrant or administrative contact) that contains
'bar' in it you could do the following:

```
domainName:foo email:bar
```

By default, multiple conditions are *and*'d together. But if you want to search
for things using an *or* condition, you can use the keyword '**OR**'. As an
example, if you want to search for an entry with 'foo' in the domain and either
'bar' *or* 'bah' in the email you can do the following:

```
domainName:foo (email:bar OR email:bah)
```

Since *and* conditions are given priority, the **OR** conditions must be put in
parens and generally it's better to put **OR** conditions in parens for the
sake of clarity. The '**AND**' keyword can be further used to increase clarity,
but is unnecessary:

```
domainName:foo AND (email:bar OR email:bah)
```

Negating Queries
---------------------

If a user wants to exclude certain paramters, it is possible by prepending a
query with '**NOT**' to negate the query.

```
email:"domains@google.com" AND NOT domainName:"google.com"
```

The above example would find all domains that have an email address of
'domains@google.com' but would exclude the domain 'google.com'. Note that the
**NOT** keyword has higher precedence than **AND** or **OR** so queries will be
negated before they are combined.

Fuzzy Searching
--------------------

ElasticSearch's '*fuzzy*' searching capability allows you to find terms that
are similar to your search term. This is exposed in the query syntax using the
'**~**' character and works on specified fields (this feature will not work on
generic searches). Here's an example:

```
~domainName:foo
```

The above query will do a search on the domainName field for the value foo, but
will do a fuzzy search with fuzziness (or the Levenshtein edit distance if you
want to get technical) set to 'AUTO' so ElasticSearch will decide how fuzzy to
make the search based on the length of the query. To control the fuzziness
manually, you can add '**0**', '**1**', or '**2**' to the '**~**' character.

For example:

```
~2domainName:google
```

The above will do a fuzzy search on the domainName field using a fuzziness
value of 2 and will return any whois records that have a domain name that is 2
edits away from '*google*'.

**Note: ElasticSearch limits fuzziness to 2 at the max, internally. Entering 3
through 9 will not raise an error but will be the same as entering '2'.  the
AUTO option uses '0' for terms that are 1 character long, '1' for terms that
are between 1 and 5 characters and '2' for terms that are longer than 5
characters. These are generally good values.**

Getting Particular
---------------------

The new query syntax supports regex and wildcard searches on specific fields
using a special syntax.

**Note that fuzzy searching (as detailed above) is not supported for wildcard
and regex searches, nor would it really make any sense.**

### WildCard Searches

WildCard searches are done using quoted strings that start with a '**w**'

For example:

```
w'fo?.com'
```

Further, the wildcard syntax interprets two special characters, '**?**' and
'\*'. The '**?**' symbol represents a single character, while the '\*'
character represents any number of characters. So, the search specified above
would find foo.com but also any entry that is preceded by 'fo', following by
any single character and then followed by '.com', e.g., fop.com, fon.com, etc.

### Regex Searches

Similar to WildCard searches, the regex syntax allows for regex searches to be
applied to specified fields using quoted strings that start with a '**r**'.

For example:

```
r'foo[0-9]+\.com'
```

Further, the regex syntax should accept any special characters that
ElasticSearch will accept.

**Note: Regex searches should be a last resort,  as they can be computationally
expensive and tax a cluster unnecessarily. Consider using a wildcard search or
refining your search terms when possible.**

Date Searches
-----------------

There are three date fields that can be searched (assuming there is data
populated in the backend):

- **created**
- **updated**
- **expires**

The syntax for date searches are as follows:

```
&lt;key&gt;:YYYY-mm-dd
```

As an example to search for entries that have a created date of January 2nd
2003, you search search for:

```
created:2003-01-02
```

To search between a range of dates, you can do the following:

```
&lt;key&gt;:YYYY-mm-dd:YYYY-mm-dd
```

So to find all entries created between January 2nd 2003 and February 1st 2003,
you'd do:

```
created:2003-01-02:2003-02-01
```

Combining date searches is the same as combining other searches. For example
you can do:

```
created:2003-01-01 expires:2022-01-30:2023-01-20
```

This includes using parentheses and the '**OR**' keyword:

```
created:2003-01-01 OR created:2004-01-02
```

While date searches can be useful, they are best used in conjunction with other
queries such as:

```
domainName:w'fo???.com' created:2014-01-02:2014-01-25
```

Understanding Scoring
---------------------------

Scores returned by pyDat are the same scores returned by ElasticSearch. The
important thing to understand about ElasticSearch scores is that they are
entirely relative and should not be taken on their own. If you receive only a
single result with a score less than 1.0, that does not mean it doesn't match,
it might just mean that there was less criteria available to search against. On
the other hand, if you have thousands of results and the top result's score is
5.25 and then the second result has a score of 0.95 this should tell you that
the level of confidence that the second result matches your criteria is
considerably lower than that of the first result.

Scores that match the same will have the same score. If, for example, you are
searching for an email address:

```
email:foo@gmail.com
```

If the top results all have the same score, that means each of them matched
your query equally. Results after that might drop of drastically indicating
that only those top results might actually be relevant to your query.

Recognized Keys
--------------------

The following is a list of keys that are recognized for searching specific
fields:

- **domainName**
- **administrativeContact_email**
- **administrativeContact_name**
- **administrativeContact_organization**
- **administrativeContact_street1**
- **administrativeContact_street2**
- **administrativeContact_street3**
- **administrativeContact_street4**
- **administrativeContact_city**
- **administrativeContact_state**
- **administrativeContact_postalCode**
- **administrativeContact_country**
- **administrativeContact_fax**
- **administrativeContact_faxExt**
- **administrativeContact_telephone**
- **administrativeContact_telephoneExt**
- **registrant_email**
- **registrant_name**
- **registrant_organization**
- **registrant_street1**
- **registrant_street2**
- **registrant_street3**
- **registrant_street4**
- **registrant_city**
- **registrant_state**
- **registrant_postalCode**
- **registrant_country**
- **registrant_fax**
- **registrant_faxExt**
- **registrant_telephone**
- **registrant_telephoneExt**
- **nameServers**
- **registrarName**
- **whoisServer**
- **administrativeContact_street**
	-- shortcut for all 4 administrative street entries
- **registrant_street**
	-- shortcut for all 4 registrant street entries
- **dn**
	-- shortcut for domainName
- **email**
	-- shortcut for both emails above
- **name**
	-- shortcut for both names above
- **organization**
	-- shortcut for both organizations above
- **street**
	-- shortcut for all 8 streets above
- **city**
	-- shortcut for both cities above
- **state**
	-- shortcut for both states above
- **postalCode**
	-- shortcut for both postal codes above
- **country**
	-- shortcut for both countries above
- **telephone**
	-- shortcut for both telephone numbers above
- **telephoneExt**
	-- shortcut for both telephone extensions above
- **fax**
	-- shortcut for both faxes above
- **faxExt**
	-- shortcut for both fax extensions above
- **ns**
	-- shortcut for nameServers
- **registrar**
	-- shortcut for registrarName
- **email_local**
	-- Searches only the local part of an email (everything before the '**@**' symbol)
- **email_domain**
	-- Searches only the domain part of an email (everything after the '**@**' symbol)


Caveats/Things to Consider
---------

### Case (In)Sensitivity

pyDat advanced search is case insensitive. Although data retrieved is case
sensitive (original casing is retained) the processed data is all stored,
internally, in an insensitive manner.  Which means using capital letters in a
regex or wildcard search is pointless as they will never match. This also
applies to the commonly used character set *\[A-Z\]*. As examples, the
following queries will never match:

```
w'F?o.com'
```

```
r'foo[A-Z]+.com'
```

The above queries will never return a result as everything in the ElasticSearch
backend is down-cased when it is processed. Keep this in mind when using regex
or wildcard searches.

Unquoted strings are directly processed by ElasticSearch so there is no need to
worry about case issues for casual searches. Quoted string are also, within
pyDat, down-cased before being processed and sent to ElasticSearch, but some
other caveats are important to take into consideration with quoted strings, see
below.

### Quoted Strings

As briefly mentioned above, quoted strings are processed by pyDat before
crafting a query and sending it along to ElasticSearch. The only processing
that is done is based on whitespace. ElasticSearch will process on not just
whitespace but uncommon non alpha-numeric characters so searching for a quoted
sequence with a special character might not work as expected. For the most
part, this does not apply to searches for things that look like domain names
(e.g., "google.com" -- and this is due to the way ElasticSearch recognizes the
'**.**' character in domain names).

### Shortcut Searches

Most shortcut searches (using any of the fields above listed as shortcut for
other fields) should work as expected. The only situation where a shortcut
might work as expected is the '**street**' shortcut as it will search against
each of the fields as if they're competing. What this means is if you try to
search for a full address, this will possible not work as expected.

### Fuzzy Searches

By default, fuzzy searching in ElasticSearch is limited to 2 edits and 50
expansions (as far as I can tell from the documentation, it's a tad vague).
This should fit most cases but is probably something to consider when using
fuzzy searching.

Further specifying a fuzzy search on a quoted string will not search the same
way as a non-fuzzy search on a quoted string, nor will it return the same
results as two fuzzy searches in the same field. For example:

```
name:"john smith"
```

```
~name:john ~name:smith
```

```
~name:"john smith"
```

The above queries will all return different data, with the last one being the
most generic and probably returning the most data.
