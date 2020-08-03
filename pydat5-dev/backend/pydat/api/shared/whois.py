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
    v1_keys = set(v1_result.keys())
    v2_keys = set(v2_result.keys())
    keys = (v1_keys | v2_keys) - blacklist
    results = {}

    for key in keys:
        if key in v1_keys and key in v2_keys:
            if v1_result[key] == v2_result[key]:
                results[key] = v1_result[key]
            else:
                results[key] = [v1_result[key], v2_result[key]]
        elif key in v1_keys:
            results[key] = [v1_result[key], '']
        else:
            results[key] = ['', v2_result[key]]

    return results
