from .base import BankProviderAdapter
from countries.validators.base import BankData


class DataCreditoCOAdapter(BankProviderAdapter):
    def parse(self, raw: dict) -> BankData:
        return BankData(
            provider_name=raw['entidad'],
            account_status=raw['estadoCuenta'],
            total_debt=float(raw['totalObligaciones']),
            credit_score=int(raw['puntajeRiesgo']) if raw.get('puntajeRiesgo') is not None else None,
            raw_response=raw,
        )
