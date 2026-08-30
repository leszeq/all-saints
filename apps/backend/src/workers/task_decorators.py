"""Typed adapters for third-party Celery decorators."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, Protocol, TypeVar, cast

from celery import shared_task
from celery.result import AsyncResult

P = ParamSpec("P")
R_co = TypeVar("R_co", covariant=True)


class TypedTask(Protocol[P, R_co]):
    """Callable Celery task with the dispatch method used by API routers."""

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R_co: ...

    def delay(self, *args: object, **kwargs: object) -> AsyncResult: ...


def typed_shared_task(
    **options: object,
) -> Callable[[Callable[P, R_co]], TypedTask[P, R_co]]:
    """Preserve a task function's signature across Celery's untyped decorator."""
    decorator = shared_task(**options)
    return cast(Callable[[Callable[P, R_co]], TypedTask[P, R_co]], decorator)
