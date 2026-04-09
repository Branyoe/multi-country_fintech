from django.core.cache import cache

CACHE_KEY = 'country_meta'


def get_countries_cached() -> dict:
    """Returns {code: Country} from cache. Populates from DB on miss."""
    data = cache.get(CACHE_KEY)
    if data is None:
        from .models import Country
        data = {c.code: c for c in Country.objects.filter(is_active=True)}
        cache.set(CACHE_KEY, data, timeout=None)
    return data


def invalidate_country_cache(sender, **kwargs):
    cache.delete(CACHE_KEY)


def connect_signals():
    from django.db.models.signals import post_save, post_delete
    from .models import Country
    post_save.connect(invalidate_country_cache, sender=Country)
    post_delete.connect(invalidate_country_cache, sender=Country)
