from .base import BaseCountryValidator, BankData


class COCountryValidator(BaseCountryValidator):

    def get_country_code(self) -> str:
        return 'CO'

    def get_document_type(self) -> str:
        return 'CC'

    def fetch_bank_data(self, document: str) -> BankData:
        return BankData(
            provider_name='DATACREDITO_CO',
            account_status='active',
            total_debt=2000.0,
            credit_score=None,
            raw_response={
                'cc':          document.strip(),
                'deuda_total': 2000.0,
                'estado':      'activo',
            },
        )

    def validate_financial_rules(
        self, amount: float, income: float, bank_data: BankData
    ) -> tuple[bool, str, str]:
        if bank_data.total_debt is not None and bank_data.total_debt > income * 0.4:
            return False, 'Tu deuda registrada supera el 40% del ingreso mensual', 'non_field_errors'
        return True, '', ''

    def get_validation_rules(self) -> list[str]:
        return ['cc_format', 'deuda_40pct_ingreso']
