import hashlib
import json
from pathlib import Path

from .adapters.datacredito_co import DataCreditoCOAdapter
from .base import BaseCountryValidator, BankData

_PROFILES_PATH = Path(__file__).parent / 'providers' / 'datacredito_co.json'


class COCountryValidator(BaseCountryValidator):

    def get_country_code(self) -> str:
        return 'CO'

    def get_document_type(self) -> str:
        return 'CC'

    def fetch_bank_data(self, document: str) -> BankData:
        profiles = json.loads(_PROFILES_PATH.read_text(encoding='utf-8'))
        idx = int(hashlib.md5(document.encode()).hexdigest(), 16) % len(profiles)
        raw = profiles[idx].copy()
        raw['numeroDocumento'] = document.strip()
        return DataCreditoCOAdapter().parse(raw)

    def validate_financial_rules(
        self, amount: float, income: float, bank_data: BankData
    ) -> tuple[bool, str, str]:
        if bank_data.total_debt is not None and bank_data.total_debt > income * 0.4:
            return False, 'Tu deuda registrada supera el 40% del ingreso mensual', 'non_field_errors'
        return True, '', ''

    def get_validation_rules(self) -> list[str]:
        return ['cc_format', 'deuda_40pct_ingreso']
