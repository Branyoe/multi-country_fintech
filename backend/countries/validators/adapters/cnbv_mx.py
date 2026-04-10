from .base import BankProviderAdapter
from countries.validators.base import BankData


class CNBVMXAdapter(BankProviderAdapter):
    def parse(self, raw: dict) -> BankData:
        return BankData(
            provider_name=raw['proveedor'],
            account_status=raw['estatus_cuenta'].lower(),
            total_debt=float(raw['deuda_total_mxn']),
            credit_score=int(raw['score_crediticio']),
            raw_response=raw,
        )
