import hashlib
import json
from pathlib import Path

from .adapters.cnbv_mx import CNBVMXAdapter
from .base import BaseCountryValidator, BankData

_PROFILES_PATH = Path(__file__).parent / 'providers' / 'cnbv_mx.json'


class MXCountryValidator(BaseCountryValidator):

    def get_country_code(self) -> str:
        return 'MX'

    def get_document_type(self) -> str:
        return 'CURP'

    def fetch_bank_data(self, document: str) -> BankData:
        profiles = json.loads(_PROFILES_PATH.read_text(encoding='utf-8'))
        idx = int(hashlib.md5(document.encode()).hexdigest(), 16) % len(profiles)
        raw = profiles[idx].copy()
        raw['curp'] = document.strip().upper()
        return CNBVMXAdapter().parse(raw)

    def validate_financial_rules(
        self, amount: float, income: float, bank_data: BankData
    ) -> tuple[bool, str, str]:
        if amount > income * 5:
            return False, 'El monto supera el límite permitido (máx. 5× el ingreso mensual)', 'amount_requested'
        return True, '', ''

    def get_validation_rules(self) -> list[str]:
        return ['curp_format', 'monto_5x_ingreso']
