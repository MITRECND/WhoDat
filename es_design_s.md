# Design/Refactor of es.py

## Exceptions

New proposed custom exceptions:
- ESConnectionError
- ESQueryError
- ESProcessingError
- (?)Should there be a generic ESAPIError for any value/argument exceptions?

## API

Note: section titles are the old API method names

**_es_connector()_**


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

```python

```

**_advanced_search()_**

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


