import ipaddress
import time
import json
import requests
import urllib
import copy
import cerberus

from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.core.plugins import register_passive_plugin
from pydat.core.plugins import PassivePluginBase
from flask import Blueprint, current_app, request


BASE_SCHEMA = {
    'time_first_before': {'type': 'integer'},
    'time_first_after': {'type': 'integer'},
    'time_last_before': {'type': 'integer'},
    'time_last_after': {'type': 'integer'},
    'rrtypes': {
        'type': 'list',
        'schema': {
            'type': 'string',
            'allowed': [
                'any',
                'a',
                'aaaa',
                'cname',
                'mx',
                'ns',
                'ptr',
                'soa',
                'txt',
                # DNSSEC Types
                'any-dnssec',
                'ds',
                'rrsig',
                'nsec',
                'dnskey',
                'nsec3',
                'nsec3param',
                'dlv'
            ]
        },
        'default': ['any']
    },
    'limit': {
        'type': 'integer',
        'default': 100000,
        'ispositive': True
    }
}

FORWARD_SCHEMA = {
    'domain': {
        'type': 'string',
        'required': True
    }
}

REVERSE_SCHEMA = {
    'type': {
        'type': 'string',
        'allowed': [
            'ip',
            'name',
            'raw'
        ],
        'required': True
    },
    'value': {
        'type': 'string',
        'required': True
    }
}


class CustomValidator(cerberus.Validator):
    def _validate_ispositive(self, ispositive, field, value):
        """ Test that value is greater than 0.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if ispositive and value < 0:
            self._error(field, "Must be greater than 0")


@register_passive_plugin
class DnsdbPlugin(PassivePluginBase):
    def __init__(self):
        dnsdb_bp = Blueprint("passive_dnsdb", __name__)
        # Forward and Reverse are auto-registered by parent
        dnsdb_bp.route('/rate_limits', methods=["GET"])(self.rate_limits)
        super().__init__("dnsdb", dnsdb_bp)

        self.logger = current_app.logger

        # Setup Schemas
        self.forward_schema = copy.deepcopy(BASE_SCHEMA)
        self.forward_schema.update(FORWARD_SCHEMA)
        self.reverse_schema = copy.deepcopy(BASE_SCHEMA)
        self.reverse_schema.update(REVERSE_SCHEMA)

        # TODO Should validators also be setup?

        self.scheme = "https"
        self.netloc = "api.dnsdb.info"
        self.default_params = {
            'swclient': 'pydat',
            'version': '5'
        }

    def _validate(self, data, validator):
        valid = validator.validate(data)

        if not valid:
            invalid_fields = [
                error.document_path[0] for error in validator._errors]

            # print(validator._errors)
            raise ClientError(
                f"Unable to validate field(s) {','.join(invalid_fields)}")

        normalized = validator.normalized(data)

        # If 'any' is in rrtypes and anything else too, just default to 'any'
        if 'any' in normalized['rrtypes']:
            if 'any-dnssec' in normalized['rrtypes']:
                normalized['rrtypes'] = ['any', 'any-dnssec']
            else:
                normalized['rrtypes'] = ['any']
        elif 'any-dnssec' in normalized['rrtypes']:
            normalized['rrtypes'] = ['any-dnssec']

        return normalized

    def forward(self):
        if not request.is_json:
            raise ClientError("Expected json data")

        json_data = request.get_json()

        validator = CustomValidator(self.forward_schema)
        config = self._validate(json_data, validator)
        results = self.dnsdb_forward(**config)

        return results

    def reverse(self):
        if not request.is_json:
            raise ClientError("Expected json data")

        json_data = request.get_json()

        validator = CustomValidator(self.reverse_schema)
        config = self._validate(json_data, validator)

        results = self.dnsdb_reverse(**config)
        return results

    def rate_limits(self):
        try:
            rate = self.request_rate_limit()
        except RuntimeError:
            raise ServerError("unable to query rate limit information")
        except Exception:
            raise ServerError(
                "unexpected error getting rate limit information")

        return rate

    def setConfig(self, **kwargs):
        if 'APIKEY' not in kwargs:
            raise ValueError("Expected an API KEY")

        self.proxies = current_app.config.get('PROXIES', None)
        self.sslverify = current_app.config.get('SSLVERIFY', True)
        self.headers = {
            'Accept': 'application/json',
            'X-API-Key': kwargs['APIKEY']
        }

    def validate_hex(self, input_hex):
        try:
            output_hex = "%x" % int(input_hex, 16)
        except Exception:
            raise TypeError("Not hex")

        # make hex string always pairs of hex values
        if len(output_hex) % 2 == 1:
            output_hex = "0" + output_hex

        return output_hex

    def _validate_domain(self, domain):
        prefix = ''
        suffix = ''

        if domain[0] == '.':
            prefix = '.'
            domain = domain[1:]

        if domain[-1] == '.':
            suffix = '.'
            domain = domain[:-1]

        try:
            domain = domain.encode("idna")
        except Exception:
            raise TypeError("unable to verify domain provided")

        try:
            outdomain = domain.decode("utf-8")
        except Exception:
            raise TypeError("unable to sanitize domain")

        return f"{prefix}{outdomain}{suffix}"

    def _verify_type(self, value, type):
        if type == 'ip':
            try:
                ipaddress.ip_address(value)
            except ValueError:
                raise TypeError("Unable to verify search value as ip")
        elif type == 'name':
            value = str(self._validate_domain(value))
        elif type == 'raw':
            try:
                value = self.validate_hex(value)
            except Exception:
                raise TypeError("Unable to verify type as hex")
        else:
            raise RuntimeError("Unexpected type")

        return value

    def request_rate_limit(self):
        url = "https://api.dnsdb.info/lookup/rate_limit"

        try:
            r = requests.get(
                url,
                proxies=self.proxies,
                headers=self.headers,
                verify=self.sslverify)
        except Exception:
            raise RuntimeError(
                "Unexpected exception when querying for rate limits")

        if r.status_code != 200:
            raise RuntimeError(
                "Received non-200 response when checking rate limit")

        data = r.json()
        if 'rate' not in data:
            raise RuntimeError("Unable to parse response from dnsdb")

        rate = data['rate']
        return rate

    def check_return_code(self, response):
        self.logger.info(
            f"Received non-200 response from dnsdb:\n{response.text}"
        )

        if response.status_code == 400:
            raise ClientError('Request possibly misconfigured')
        elif response.status_code == 403:
            raise ServerError("API key not valid", status_code=503)
        elif response.status_code == 429:
            try:
                rate = self.request_rate_limit()
                reset = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.gmtime(rate['reset']))
                raise ServerError(
                    f"Quota reached (limit: {rate['limit']}) Reset: {reset}",
                    status_code=503
                )
            except Exception:
                self.logger.exception()
                raise ServerError("Quota reached, but unable to query limits")
        elif response.status_code == 500:
            raise ServerError("dnsdb server unable to process request")
        elif response.status_code == 503:
            raise ServerError(
                "Request throttled, try again later",
                status_code=503
            )
        else:
            raise ServerError("Received unexpected response from server")

    def handle_request(self, path, params, rrtypes):
        param_string = "&".join([
            f"{key}={value}" for (key, value) in params.items()
        ])

        response = {
            'rate': {},
            'data': {}
        }

        for rrtype in rrtypes:
            local_path = list(path) + [rrtype]
            local_path = "/".join(local_path)

            local_url = urllib.parse.ParseResult(
                self.scheme, self.netloc, local_path,
                "", param_string, "")

            url = urllib.parse.urlunparse(local_url)

            self.logger.debug(f"Request Url: {url}")

            try:
                r = requests.get(
                    url,
                    proxies=self.proxies,
                    headers=self.headers,
                    verify=self.sslverify)
            except Exception as e:
                raise RuntimeError(e)

            if r.status_code not in [200, 404]:
                self.check_return_code(r)
                return

            try:
                rate = {
                        'limit': r.headers['X-RateLimit-Limit'],
                        'remaining': r.headers['X-RateLimit-Remaining'],
                        'reset': r.headers['X-RateLimit-Reset']
                }

                response['rate'] = rate
            except Exception:
                self.logger.exception(
                    "unable to find rate information in response")

            self.logger.debug(r.text)

            if r.status_code == 404:
                continue

            # Each line of the response is an individual JSON blob.
            for line in r.text.split('\n'):
                # Skip empty lines.
                if not line:
                    continue
                try:
                    tmp = json.loads(line)
                except Exception:
                    self.logger.exception("Unable to parse data from dnsdb")
                    raise ServerError(
                        "Unable to parse data from upstream service")

                rrtype = tmp['rrtype']

                # Turn rdata into a list for consistency
                if isinstance(tmp['rdata'], str):
                    tmp['rdata'] = [tmp['rdata']]

                if rrtype == 'MX':
                    # Strip the MX weight.
                    tmp['rdata'] = [rd.split()[1] for rd in tmp['rdata']]
                elif rrtype == 'NS':
                    # Normalize time field
                    if 'zone_time_first' in tmp and 'time_first' not in tmp:
                        tmp['time_first'] = tmp['zone_time_first']
                        del tmp['zone_time_first']

                    if 'zone_time_last' in tmp and 'time_last' not in tmp:
                        tmp['time_last'] = tmp['zone_time_last']
                        del tmp['zone_time_last']

                try:
                    response['data'][rrtype].append(tmp)
                except KeyError:
                    response['data'][rrtype] = [tmp]

        return response

    def dnsdb_forward(self, **options):
        path = "lookup/rrset/name".split('/')
        params = copy.deepcopy(self.default_params)

        rrtypes = options['rrtypes']
        domain = options['domain']

        for key in ['rrtypes', 'domain']:
            del options[key]

        params.update(options)

        owner_name = urllib.parse.quote(domain)
        path.append(owner_name)

        return self.handle_request(path, params, rrtypes)

    def dnsdb_reverse(self, **options):
        path = "lookup/rdata".split('/')
        params = copy.deepcopy(self.default_params)

        field_type = options['type']
        value = options['value']
        rrtypes = options['rrtypes']

        for key in ['type', 'value', 'rrtypes']:
            del options[key]

        params.update(options)

        if field_type == 'ip':
            for rrtype in rrtypes:
                if rrtype not in ['a', 'aaaa', 'any']:
                    raise ClientError(
                        f"rrtype {rrtype} invalid when type is ip")

        try:
            value = self._verify_type(value, field_type)
            value = urllib.parse.quote(value)
        except Exception:
            self.logger.exception("unable to verify input type")
            raise ClientError("Unable to verify input type")

        path.extend([
            field_type,
            value
        ])

        return self.handle_request(path, params, rrtypes)
