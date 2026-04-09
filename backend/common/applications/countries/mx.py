import re
from .base import BaseCountryValidator, BankData

_CURP_RE = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$')


class MXCountryValidator(BaseCountryValidator):

    def get_document_type(self) -> str:
        return 'CURP'

    def validate_document(self, document: str) -> tuple[bool, str]:
        normalized = document.strip().upper()
        if not _CURP_RE.match(normalized):
            return False, 'Formato de CURP incorrecto'
        return True, ''

    def fetch_bank_data(self, document: str) -> BankData:
        return BankData(
            provider_name='CNBV_MX',
            account_status='active',
            total_debt=5000.0,
            credit_score=720,
            raw_response={
                'curp':  document.strip().upper(),
                'score': 720,
                'deuda': 5000.0,
            },
        )

    def validate_financial_rules(
        self, amount: float, income: float, bank_data: BankData
    ) -> tuple[bool, str, str]:
        if amount > income * 5:
            return False, 'El monto supera el límite permitido (máx. 5× el ingreso mensual)', 'amount_requested'
        return True, '', ''

    def get_validation_rules(self) -> list[str]:
        return ['curp_format', 'monto_5x_ingreso']
