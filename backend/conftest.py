import pytest


@pytest.fixture(autouse=True)
def locmem_cache(settings):
    """Use in-memory cache for tests — no Redis required."""
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }


@pytest.fixture(autouse=True)
def setup_countries(db, locmem_cache):
    """Create Country records and clear cache for each test."""
    from django.core.cache import cache
    from applications.models import Country

    cache.clear()

    Country.objects.bulk_create([
        Country(
            code='MX', label='México', document_type='CURP',
            document_hint='18 caracteres alfanuméricos',
            document_example='PERJ800101HDFRZN09',
            document_regex=r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$',
            is_active=True,
        ),
        Country(
            code='CO', label='Colombia', document_type='CC',
            document_hint='Entre 6 y 10 dígitos numéricos',
            document_example='1234567890',
            document_regex=r'^\d{6,10}$',
            is_active=True,
        ),
    ])

    yield

    cache.clear()
