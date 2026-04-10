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
    from countries.models import Country

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


@pytest.fixture(autouse=True)
def setup_statuses(db, setup_countries):
    """Create CountryStatus and StatusTransition records for MX and CO."""
    from countries.models import Country, CountryStatus, StatusTransition

    mx = Country.objects.get(code='MX')
    co = Country.objects.get(code='CO')

    # MX statuses
    mx_pending      = CountryStatus.objects.create(country=mx, code='pending',      label='Pendiente',   is_initial=True,  is_terminal=False, order=1)
    mx_under_review = CountryStatus.objects.create(country=mx, code='under_review', label='En revisión', is_initial=False, is_terminal=False, order=2)
    mx_approved     = CountryStatus.objects.create(country=mx, code='approved',     label='Aprobada',    is_initial=False, is_terminal=True,  order=3)
    mx_rejected     = CountryStatus.objects.create(country=mx, code='rejected',     label='Rechazada',   is_initial=False, is_terminal=True,  order=4)

    # MX transitions
    StatusTransition.objects.bulk_create([
        StatusTransition(from_status=mx_pending,      to_status=mx_under_review, triggers_task='process_application_mx'),
        StatusTransition(from_status=mx_pending,      to_status=mx_rejected,     triggers_task=''),
        StatusTransition(from_status=mx_under_review, to_status=mx_approved,     triggers_task=''),
        StatusTransition(from_status=mx_under_review, to_status=mx_rejected,     triggers_task=''),
    ])

    # CO statuses
    co_pending      = CountryStatus.objects.create(country=co, code='pending',           label='Pendiente',            is_initial=True,  is_terminal=False, order=1)
    co_buro         = CountryStatus.objects.create(country=co, code='verificacion_buro', label='Verificación en Buró', is_initial=False, is_terminal=False, order=2)
    co_under_review = CountryStatus.objects.create(country=co, code='under_review',      label='En revisión',          is_initial=False, is_terminal=False, order=3)
    co_approved     = CountryStatus.objects.create(country=co, code='approved',          label='Aprobada',             is_initial=False, is_terminal=True,  order=4)
    co_rejected     = CountryStatus.objects.create(country=co, code='rejected',          label='Rechazada',            is_initial=False, is_terminal=True,  order=5)

    # CO transitions
    StatusTransition.objects.bulk_create([
        StatusTransition(from_status=co_pending,      to_status=co_buro,         triggers_task='consulta_buro_co'),
        StatusTransition(from_status=co_pending,      to_status=co_rejected,     triggers_task=''),
        StatusTransition(from_status=co_buro,         to_status=co_under_review, triggers_task=''),
        StatusTransition(from_status=co_buro,         to_status=co_rejected,     triggers_task=''),
        StatusTransition(from_status=co_under_review, to_status=co_approved,     triggers_task=''),
        StatusTransition(from_status=co_under_review, to_status=co_rejected,     triggers_task=''),
    ])
