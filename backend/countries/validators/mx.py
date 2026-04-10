from .base import BaseCountryValidator, BankData


class MXCountryValidator(BaseCountryValidator):

    def get_country_code(self) -> str:
        return 'MX'

    def get_document_type(self) -> str:
        return 'CURP'

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

    def get_initial_task(self) -> str:
        return 'process_application_mx'

    def get_validation_rules(self) -> list[str]:
        return ['curp_format', 'monto_5x_ingreso']
