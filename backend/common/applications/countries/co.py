import re
from .base import BaseCountryValidator, BankData

_CC_RE = re.compile(r'^\d{6,10}$')


class COCountryValidator(BaseCountryValidator):

    def get_document_type(self) -> str:
        return 'CC'

    def validate_document(self, document: str) -> tuple[bool, str]:
        if not _CC_RE.match(document.strip()):
            return False, 'Cédula inválida — debe tener entre 6 y 10 dígitos'
        return True, ''

    def fetch_bank_data(self, document: str) -> BankData:
        return BankData(
            provider_name='DATACREDITO_CO',
            account_status='active',
            total_debt=2000.0,
            credit_score=None,
            raw_response={
                'cc':         document.strip(),
                'deuda_total': 2000.0,
                'estado':     'activo',
            },
        )

    def validate_financial_rules(
        self, amount: float, income: float, bank_data: BankData
    ) -> tuple[bool, str]:
        if bank_data.total_debt is not None and bank_data.total_debt > income * 0.4:
            return False, 'Deuda total supera el 40% del ingreso mensual'
        return True, ''

    def get_validation_rules(self) -> list[str]:
        return ['cc_format', 'deuda_40pct_ingreso']
