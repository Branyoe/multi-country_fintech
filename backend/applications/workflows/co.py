from __future__ import annotations

from applications.models import CreditApplication
from countries.validators.registry import get_validator

from .base import BaseWorkflow


class ColombiaWorkflow(BaseWorkflow):
    def get_country_code(self) -> str:
        return 'CO'

    def on_enter(self, state_code: str, application: CreditApplication) -> None:
        from applications.tasks import (
            fetching_bank_data_task,
            notify_final_decision_task,
            validate_country_rules_task,
        )

        if state_code == 'fetching_bank_data':
            fetching_bank_data_task.delay(str(application.id))
        elif state_code == 'validate_country_rules':
            validate_country_rules_task.delay(str(application.id))
        elif state_code in {'approved', 'rejected'}:
            notify_final_decision_task.delay(str(application.id))

    def validate(self, application: CreditApplication, bank_data) -> tuple[bool, str]:
        validator = get_validator(application.country)
        amount = float(application.amount_requested)
        income = float(application.monthly_income)
        valid, message, _field = validator.validate_financial_rules(
            amount,
            income,
            bank_data,
        )
        return valid, message
