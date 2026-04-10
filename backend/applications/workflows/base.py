from __future__ import annotations

from abc import ABC, abstractmethod

from applications.models import CreditApplication


class BaseWorkflow(ABC):
    @abstractmethod
    def get_country_code(self) -> str:
        """Return ISO-like country code for this workflow."""

    def get_bootstrap_state(self) -> str:
        """Return the first processing state code to auto-transition into after creation.

        Override in country-specific subclasses when the initial pipeline step differs.
        """
        return 'fetching_bank_data'

    @abstractmethod
    def on_enter(self, state_code: str, application: CreditApplication) -> None:
        """Trigger side effects when entering a state.

        Implementations must not mutate state directly.
        """

    @abstractmethod
    def validate(self, application: CreditApplication, bank_data) -> bool:
        """Run country-specific decision validation.

        Returns True for approval and False for rejection.
        """
