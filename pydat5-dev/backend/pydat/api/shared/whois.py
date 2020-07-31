from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic


def metadata(version=None):
    try:
        if version:
            version = int(version)
            if version < 0:
                raise ValueError
    except ValueError:
        raise ClientError(f'Version {version} must be a valid integer')

    try:
        results = elastic.metadata(version)
    except elastic.NotFoundError:
        raise ClientError(f'Version {version} does not exist', 404)
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.ElasticsearchError:
        raise ServerError('Unexpected exception')

    return results


def diff(domainName, v1, v2):
    try:
        v1 = float(v1)
        v2 = float(v2)
    except ValueError:
        raise ClientError("Input paramaters are of the wrong type")

    try:
        v1_result = elastic.search('domainName', domainName, filt=None, low=v1)
        v2_result = elastic.search('domainName', domainName, filt=None, low=v2)
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.NotFoundError:
        raise ClientError(f'Cannot find domain name {domainName}', 404)
    except elastic.ElasticsearchError:
        raise ServerError('Unexpected exception')

    if not v1_result['data'] or not v2_result['data']:
        raise ClientError('Provided version has no data', 404)
    v1_result = v1_result['data'][0]
    v2_result = v2_result['data'][0]

    blacklist = {'Version', 'UpdateVersion', 'domainName', 'dataFirstSeen'}
    v1_key = set(v1_result.keys())-blacklist
    v2_key = set(v2_result.keys())-blacklist
    results = {}

    for key in v1_key-v2_key:
        results[key] = [v1_result[key], '']
    for key in v2_key-v1_key:
        results[key] = ['', v2_result[key]]
    for key in v1_key & v2_key:
        if v1_result[key] == v2_result[key]:
            results[key] = v1_result[key]
        else:
            results[key] = [v1_result[key], v2_result[key]]

    return results
