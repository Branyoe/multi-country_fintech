from .base import BaseCountryValidator
from .mx import MXCountryValidator
from .co import COCountryValidator

COUNTRY_REGISTRY: dict[str, type[BaseCountryValidator]] = {
    'MX': MXCountryValidator,
    'CO': COCountryValidator,
}


def get_validator(country_code: str) -> BaseCountryValidator:
    cls = COUNTRY_REGISTRY.get(country_code.upper())
    if cls is None:
        raise ValueError(f'País no soportado: {country_code}')
    return cls()
