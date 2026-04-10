from __future__ import annotations

from .base import BaseWorkflow

WORKFLOW_REGISTRY: dict[str, BaseWorkflow] = {}
_INITIALIZED = False


def register(workflow_cls: type[BaseWorkflow]) -> None:
    workflow = workflow_cls()
    WORKFLOW_REGISTRY[workflow.get_country_code()] = workflow


def _bootstrap() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    from .co import ColombiaWorkflow
    from .mx import MexicoWorkflow

    register(MexicoWorkflow)
    register(ColombiaWorkflow)
    _INITIALIZED = True


def get_workflow(country_code: str) -> BaseWorkflow:
    _bootstrap()
    code = country_code.strip().upper()
    try:
        return WORKFLOW_REGISTRY[code]
    except KeyError as exc:
        raise KeyError(f'Workflow no registrado para país: {country_code}') from exc
