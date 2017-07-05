
class configExistsError(Exception):
    """Error to indicate config item already defined"""

class configMissingValidationError(Exception):
    """Error to indicate a missing config during validation"""

class pdnsConfig(object):
    def __init__(self, name, displayName=None):
        self.name = name
        self.displayName = name if displayName is None else displayName
        self.configs = {}
        self.myConfig = {}

        self.addConfig("active", True, False,
                       description="whether the module should be processed(used) for" \
                                   " pdns data when pdns requests are initiated in pydat")

    def addConfig(self, name, required, default_value, description):
        if name in self.configs:
            raise configExistsError('%s already exists' % (name))
        self.configs[name] = {'default_value': default_value,
                             'required': required,
                             'description': description
        }

    def __dict__(self):
        return self.configs

    def __iter__(self):
        return self.configs

    def _try_default_var(self, name, d):
        """internal utility function for script 1 - when the initialization script finds
            a required pdns module setting with no key/value OR value defined,
            an attempt is made to use a default value for that pdns module
            variable(pulled from the pdns module settings file). If there is no
            default value defined, the pdns module is deactivated.
        """
        if name not in d.keys() or d[name] is None:
            if self.configs[name]['default_value'] is not None:
                d[name] = self.configs[name]['default_value']

    def validate(self, d):
        for (name, config) in self.configs.items():
            if config["required"]:
                self._try_default_var(name, d)
                if name not in d.keys():
                    raise configMissingValidationError("config value %s expected but not present" % (name))
            if name in d.keys():
                self.myConfig[name] = d[name]

class fieldExistsError(Exception):
    """Error to indicate form field already exists"""

class formFields(object):
    def __init__(self, name):
        self.name = name
        self.fields = {'base': {},
                       'forward': {},
                       'reverse': {}}

    def addBaseField(self, name, type, default, parameters):
        if name in self.fields['base']:
            raise fieldExistsError("Field %s already exists in base fields" % (name))

        self.fields['base'][name] = {
            "field_type": type,
            "field_value_default": default,
            "parameters": parameters
        }

    def addForwardField(self, name, type, default, parameters):
        if name in self.fields['forward']:
            raise fieldExistsError("Field %s already exists in forward fields" % (name))

        self.fields['forward'][name] = {
            "field_type": type,
            "field_value_default": default,
            "parameters": parameters
        }

    def addReverseField(self, name, type, default, parameters):
        if name in self.fields['reverse']:
            raise fieldExistsError("Field %s already exists in reverse fields" % (name))

        self.fields['reverse'][name] = {
            "field_type": type,
            "field_value_default": default,
            "parameters": parameters
        }

    @property
    def base(self):
        return self.fields['base']

    @property
    def forward(self):
        return self.fields['forward']

    @property
    def reverse(self):
        return self.fields['reverse']

class passiveHandlers(object):
    def __init__(self, forward, reverse):
        self.forwardfn = forward
        self.reversefn = reverse

    @property
    def forward(self):
        return self.forwardfn

    @property
    def reverse(self):
        return self.reversefn
