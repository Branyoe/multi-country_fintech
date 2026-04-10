from abc import ABC, abstractmethod

from countries.validators.base import BankData


class BankProviderAdapter(ABC):
    @abstractmethod
    def parse(self, raw: dict) -> BankData: ...
