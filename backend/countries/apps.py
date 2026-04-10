from django.apps import AppConfig


class CountriesConfig(AppConfig):
    name = 'countries'

    def ready(self):
        from .cache import connect_signals
        connect_signals()
