from pydat.core.elastic.search.search_handler import SearchHandler


class FlaskElasticHandler(SearchHandler):
    """Wrapper class around SearchHandler that adds support for flask,
    including app initialization
    """
    def __init__(self):
        pass

    def _generate_config(self, app):
        # Collate elastic arguments
        elastic_config = app.config['ELASTICSEARCH']
        self.elastic_arguments = {
            'hosts': elastic_config['uri'],
            'username': elastic_config['user'],
            'password': elastic_config['pass'],
            'cacert': elastic_config['cacert'],
            'disable_sniffing': False,
            'indexPrefix':  elastic_config['indexPrefix'],
            'max_retries': 100,
            'retry_on_timeout': True,
        }

    def init_app(self, app):
        self._generate_config(app)
        self._search_keys = app.config['SEARCHKEYS']

        try:
            super().__init__(
                search_keys=self._search_keys,
                **self.elastic_arguments)
            self.connect()
        except RuntimeError:
            raise
        except Exception:
            raise
