import logging

from django.core.cache import cache

CACHE_KEY = 'country_meta'
logger = logging.getLogger(__name__)
_cache_unavailable_warned = False


def _warn_cache_unavailable_once() -> None:
    global _cache_unavailable_warned

    if _cache_unavailable_warned:
        return

    client_factory = getattr(cache, 'client', None)
    if client_factory is None or not hasattr(client_factory, 'get_client'):
        return

    try:
        client_factory.get_client(write=True).ping()
    except Exception:
        _cache_unavailable_warned = True
        logger.warning(
            'Country metadata cache is unavailable; falling back to the database.',
        )


def get_countries_cached() -> dict:
    """Returns {code: Country} from cache. Populates from DB on miss."""
    data = cache.get(CACHE_KEY)
    if data is None:
        _warn_cache_unavailable_once()
        from .models import Country
        data = {c.code: c for c in Country.objects.filter(is_active=True).prefetch_related('statuses')}
        cache.set(CACHE_KEY, data, timeout=None)
    return data


def invalidate_country_cache(sender, **kwargs):
    cache.delete(CACHE_KEY)


def connect_signals():
    from django.db.models.signals import post_save, post_delete
    from .models import Country
    post_save.connect(invalidate_country_cache, sender=Country)
    post_delete.connect(invalidate_country_cache, sender=Country)
