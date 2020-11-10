import os
import cerberus


DEFAULT_CONFIG = type('config', (), {
    'STATICFOLDER': '',
    'DISABLERESOLVE': False,
    'ELASTICSEARCH': {
        'uri': 'localhost:9200',
        'indexPrefix': 'pydat',
    },
    'DEBUG': False,
    'SSLVERIFY': True,
    'SEARCHKEYS': [
        ('domainName', 'Domain'),
        ('registrant_name', 'Registrant Name'),
        ('contactEmail', 'Contact Email'),
        ('registrant_telephone', 'Telephone')
    ],
    'PROXIES': {
    },
    'PDNSSOURCES': {
    },
    'PLUGINS': {
    }
})

BASE_SCHEMA = {
    'STATICFOLDER': {'type': 'string'},
    'DISABLERESOLVE': {'type': 'boolean'},
    'DEBUG': {'type': 'boolean'},
    'SSLVERIFY': {'type': 'boolean'},
    'PROXIES': {
        'type': 'dict',
        'allow_unknown': False,
        'schema': {
            'http': {
                'type': 'string',
                'nullable': True
            },
            'https': {
                'type': 'string',
                'nullable': True
            }
        }
    },
    'ELASTICSEARCH': {
        'type': 'dict',
        'schema': {
            'uri': {'type': 'string'},
            'indexPrefix': {'type': 'string'},
            'user': {
                'type': 'string',
                'nullable': True,
            },
            'pass': {
                'type': 'string',
                'nullable': True
            },
            'cacert': {
                'type': 'string',
                'nullable': True
            }
        }
    },
    'SEARCHKEYS': {
        'type': 'list',
        'schema': {
            'type': 'list',
            'items': [{'type': 'string'}, {'type': 'string'}]
        }
    },
    'PDNSSOURCES': {
        'type': 'dict',
        'allow_unknown': True
    },
    'PLUGINS': {
        'type': 'dict',
        'allow_unknown': True
    }

}


class ConfigParser:
    ENV_CONFIG_FILE = "PYDATCONFIG"

    def __init__(self, app):
        self.app = app
        self._config_ = dict()
        self.schema = BASE_SCHEMA

        if self.ENV_CONFIG_FILE in os.environ.keys():
            self.app.config.from_envvar(self.ENV_CONFIG_FILE)

        self.fromEnv()

    def fromEnv(self):
        for (key, value) in os.environ.items():
            if key.startswith('PYDAT_'):
                hierarchy = key.split('_')
                if len(hierarchy) <= 1 or hierarchy[-1] == '':
                    raise ValueError(f"Incomplete env variable {key}")
                fields = hierarchy[1:]
                tlkey = fields[0]
                if tlkey in ['SSLVERIFY', 'DEBUG', 'DISABLERESOLVE']:
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    else:
                        raise ValueError(f"Unexpected value for {tlkey}")

                    self.app.config.from_mapping(**{tlkey: value})
                elif tlkey == 'SEARCHKEYS':
                    raise AttributeError(
                        "SEARCHKEYS cannot be updated via env variable")
                else:
                    if len(fields[1:]) == 0:
                        self.app.config.from_mapping({tlkey: value})
                    else:
                        self.updateDictField(key, tlkey, fields[1:], value)

    def updateDictField(self, orig_key, tlkey, fields, value):
        if len(fields) == 1:
            if tlkey not in self.app.config.keys():
                self.app.config.from_mapping({tlkey: {fields[0]: value}})
            else:
                self.app.config[tlkey].update({fields[0]: value})
        else:
            local_key = fields[0]
            local_fields = fields[1:]
            if tlkey not in self.app.config.keys():
                self.app.config[tlkey] = dict()
            local_config = self.app.config[tlkey]
            while True:
                if len(local_fields) == 0:
                    break

                if local_key not in local_config.keys():
                    local_config[local_key] = dict()

                local_config = local_config[local_key]
                local_key = local_fields.pop(0)

            local_config[local_key] = value

    def parse(self):
        tmp_config = dict()

        for (name, value) in self.app.config.items():
            if name in self.schema.keys():
                tmp_config[name] = value

        v = cerberus.Validator(self.schema)
        valid = v.validate(tmp_config)
        if not valid:
            raise ValueError(v._errors)

        nconfig = v.normalized(tmp_config)

        for key in ['PDNSSOURCES', 'PLUGINS']:
            if key not in nconfig:
                nconfig[key] = dict()

        self.app.config.from_mapping(**nconfig)
