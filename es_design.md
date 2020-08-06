# Design/Refactor of es.py

- Port to python3
- add docstrings for all
- R: Remove django
    - 'settings', need replacement
    - no more 'cache', need replacement
- change to f-strings
Q: What is version in this context?
- Q: testing?


## Exceptions

New proposed custom exceptions:
- ESConnectionError
- ESQueryError
- ESProcessingError
- (?)Should there be a generic ESAPIError for any value/argument exceptions?

## API

Note: section titles are the old API method names

**_es_connector()_**

Q:  
R:  
- replace use of django settings
- Possible to cache ES instance? So dont have to reconnect every call?
- make non-public
- raise ESConnectionError, and this should remove need of every method to have exception block of its own

```python
def es_connector():
    """Return python ElasticSearch client.

    Returns: (elasticsearch.ElasticSearch) python ElasticSearch client

    Raises:
        ESConnectionError - when cannot create and initialize python client
    """
    pass
```

**_record_count_**

Q:  
R:  
- replace use of django cache
- Raise ESConnectionError

```python
def record_count():
    """Return record count of ES record index.

    Returns: (int) record count
    
    Raises:
        ESConnectionError - when ElasticSearch connection cannot be established.
    """
    pass

```

**_cluster_stats()_**

Q:
- Are we okay with complex query being defined within function or pull out to top level, seperate file?
- It quietly silences an exception if the stats processing doesnt work. Do we still want that, should it raise a processing error or log it so we know the stats data form has changed?
R:
- Raise EsConnectionError
- replace usage of django cache
- extract method for ES results post-processing

```python
def cluster_stats():
    """Return stats blob on ElasticSearch cluster.

    Returns: (dict) stats blob

    Raises:
        ESConnectionError - when ElasticSearch connection cannot be established.
    """
    pass
```

**_cluster_health()_**

Q:

R:
- remove use of django cache
- raise ESConnectionError
```python
def cluster_health():
    """Retrieve cluster health status.

    Returns: (str) status of the cluster

    Raises:
        ESConnectionError - when ElasticSearch connection cannot be established.
    """
    pass

```

**_lastVersion()_**

Q:
- No try/except block for es_connector like other methods? Reason?
R:
- Fix naming convention
- remove use of django cache
- Add ESConnectionError block
- Fix ambiguous exception, raise ESProcessingError. Do we want to log exception, since we just silence it?

```python
def last_version():
    """Retrieve last version of index.

    Returns: (float) version number

    Raises:
        ESConnectionError - when ElasticSearch connection cannot be established.
        ESProcessingError - when ElasticSearch result cant be processed. Not raised, silently logged.
    """
    pass
```

**_lastUpdate()_**

Q:
- No try/except block for es_connector like other methods? Reason?
R:
- fix naming convention
- remove use of django cache
- Add ESConnectionError block
- Fix ambiguous exception, raise ESProcessingError. Do we want to log exception, since we just silence it?

```python
def last_update():
    """Retrieve last update version of index.

    Returns: (float) last update version

    Raises:
        ESConnectionError - when ElasticSearch connection cannot be established.
        ESProcessingError - when ElasticSearch result cant be processed. Not raised, silently logged.
    """
    pass
```

**_metadata()_**

Q:

R:
- replace usage of django cache
- Replace ambiguous exception with ESConnectionError

```python
def metadata(version=None):
    """Retrieve metadata information on index.

    Args:
        version (float): data version
    
    Returns: (dict) metadata blob

    Raises:
        ESConnectionError - when ElasticSearch connection cannot be established.
    """
    pass
```

**_formatSort()_**

Q:

R:
- fix naming convention
- Can we formalize the int->field mapping somehow?
- remove extraneous vars (already did in version below)

```python

def format_sort(colID, direction="asc"):
    """

    Args:
        colID (int): columnd index
        direction (str): sort direction. Options: "asc", "desc"

    Returns: (tuple) of form (<sort key> , <sort directory>)
    """
    sort_key = None

    if(colID == 1):
        sort_key = "domainName"
    elif(colID == 2):
        sort_key = "details.registrant_name"
    elif(colID == 3):
        sort_key = "details.contactEmail"
    elif(colID == 4):
        sort_key = "details.standardRegCreatedDate"
    elif(colID == 5):
        sort_key = "details.registrant_telephone"
    elif(colID == 6):
        sort_key = "dataVersion"
    elif(colID == 7):
        sort_key = "_score"

    if sort_key is None:
        return None

    return (sort_key, direction)

```

**_dataTableSearch_**

Q:
- What does this do?
- What are the args?
- Does the signature/API need to be enhanced?
R:
- fix naming convention
- fix exception logic around formatting regx string.
- can we make `settings.SEARCH_KEYS` an enum so access is descriptive like `settings.SEARCH_KEYS.DOMAIN_NAME` and not `[0][0]`
- Duplicate value errors for 'low' and 'high' args, just make one
- extract submethod for forming filter query portion
- exrract submethod for processing ES results

```python
def data_table_search(key, value, skip, pagesize, sortset, sfilter, low, high):
    """

    Args:
        key (str): key field
        value (): key value
        skip (int): 
        pagesize (int): number of ElasticSearch result hits to retrieve
        sortset (list): tuples of the form (sort_key, sort_direction)
        sfilter (str): regex search filter
        low (float): lower bound version value
        high (float): upper bound version value
    
    Returns: (dict) results blob

    Raises:
        ValueError - if 'low' and 'high' args are not integers
    """
    pass
```

**_createAdvancedQuery_**

Q:
- assuming dont need to tweak at all?
R:
- fix naming convention
- is it a dunder/special method w/ before/after double underscores?
- 
```python
def _create_advanced_query(query, skip, size, unique, sort=None):
    """Advanced query creator.

    Args:
        query (str): search query
        skip (int): 
        size (int): number of result hits to retrieve
        unique (bool): restrict results to unique set of records
        sort (list): tuples of the form (sort_key, sort_direction)

    Returns: (dict) ElasticSearch query object
    """
    pass
```

**_advDataTableSearch()_**

Q:
- assuming dont need to tweak at all?
- An error from the ES query fails gracefully and erro message is passed to caller. Do we want to maintain this of actual raise a custom Exception.
R:
- fix naming convention
- replace use of django settings
- raise ESQueryError
- extract submethod for processing of ER results

```python
def adv_data_table_search(query, skip, pagesize, unique=False, sort=None):
    """

    Args:
        query (str): query string
        skip (int):
        pagesize (int): number of ElastcSearch result hits to retrieve
        unique (bool):  restrict results to unique set of records
        sort (list): tuples of the form (sort_key, sort_direction)

    Returns: (dict) results blob

    Raises:
        
    """
    pass

```

**_search()_**

Q:
- @Murad/Hanna - any  API changes we know this needs inherently with v2?
- Whats the SEARCH_INDEX, I thought with ES you just hit specific index you want? or is SEARCH_INDEX just the main domainName index?

R:
- change to f-strings
- can we make `settings.SEARCH_KEYS` an enum so access is descriptive like `settings.SEARCH_KEYS.DOMAIN_NAME` and not `[0][0]`
- L565 - remove try/except and replace logic
- L570 - extract to own method (version filter logic)
- extract method for post-processing and transforming ES result

```python
def search(key, value, filt=None, limit=settings.LIMIT, low=None, high=None, version_sort=False):
    """Search whois index for records with supplied key/values.

    Args:
        key (str): key field
        value (): key value
        filt (str): record field to restrict results hits data to
        limit (int): query results limit size
        low (float): lower bound version value
        high (float): upper bound version value
        version_sort (bool): sort results by version

    Returns: (dict) results blob

    Raises:
        ESProcessingError - when  error occurs formatting version filter of ES query 
        ValueError - when 'low' and 'high' args are not integers

    """
    pass
```

**_test_query()_**

Q:
    - Still need?
R:

```python

```

**_advanced_search()_**

Q:
- Why do we catch and handle an ES search call exception here but not in other query calls?
- Why is skip=0 default here, on other methods its None
R:
- extract sub-method for processing of ES results

```python
def advanced_search(query, skip=0, size, unique):
    """Search whois index with advanced search, via supplied regex.

    Args:
        query (str): search query
        skip (int): 
        size: number of result hits to retrieve
        unique (bool): restrict results to unique set of records

    Returns: (dict) ElasticSearch query object

    """
    pass

```


