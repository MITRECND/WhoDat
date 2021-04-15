from pydat.core.elastic.search.search_handler import SearchHandler


class FlaskElasticHandler(SearchHandler):
    """Wrapper class around SearchHandler that adds support for flask

    This class wraps the SearchHandler class to enable usage by flask,
    specifically deffering initialization of elastic capabilities with
    an init_app function that can be called by code using the application
    factories pattern
    """
    def __init__(self):
        pass

    def _generate_config(self, app):
        # Collate elastic arguments
        elastic_config = app.config['ELASTICSEARCH']
        self.elastic_arguments = {
            'hosts': elastic_config['uri'],
            'username': elastic_config.get('user', None),
            'password': elastic_config.get('pass', None),
            'cacert': elastic_config.get('cacert', None),
            'disable_sniffing': False,
            'indexPrefix':  elastic_config['indexPrefix'],
            'max_retries': 100,
            'retry_on_timeout': True,
        }

    def init_app(self, app):
        """Support flask deferred initialization

        Args:
            app (flask.Flask): An instance of a Flask object
        """
        self._generate_config(app)
        self._search_keys = app.config['SEARCHKEYS']

        try:
            super().__init__(
                search_keys=self._search_keys,
                **self.elastic_arguments)
        except RuntimeError:
            raise
        except Exception:
            raise
