import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class BankData:
    provider_name:  str
    account_status: str
    total_debt:     float | None = None
    credit_score:   int   | None = None
    raw_response:   dict         = field(default_factory=dict)


class BaseCountryValidator(ABC):

    @abstractmethod
    def get_country_code(self) -> str: ...

    @abstractmethod
    def get_document_type(self) -> str: ...

    @abstractmethod
    def fetch_bank_data(self, document: str) -> BankData: ...

    @abstractmethod
    def validate_financial_rules(
        self, amount: float, income: float, bank_data: BankData
    ) -> tuple[bool, str, str]:
        """Returns (valid, message, error_field).
        error_field is the serializer field name to attach the error to,
        or 'non_field_errors' for cross-field / external-data errors.
        """
        ...

    def validate_document(self, document: str) -> tuple[bool, str]:
        from countries.cache import get_countries_cached
        meta = get_countries_cached().get(self.get_country_code())
        if meta is None:
            return False, 'País no configurado'
        if not re.match(meta.document_regex, document.strip().upper()):
            return False, meta.document_hint
        return True, ''

    def get_initial_status(self) -> str:
        return 'pending'

    def get_validation_rules(self) -> list[str]:
        return []
