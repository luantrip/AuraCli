"""Deterministic fault injection for reliability tests."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Fault:
    name: str
    exception: BaseException
    remaining: int


class FaultInjector:
    """Inject named failures without changing production call sites."""

    def __init__(self) -> None:
        self._faults: dict[str, Fault] = {}

    def add(self, name: str, exception: BaseException, *, times: int = 1) -> None:
        if times < 1:
            raise ValueError("times must be >= 1")
        self._faults[name] = Fault(name, exception, times)

    def check(self, name: str) -> None:
        fault = self._faults.get(name)
        if fault is None:
            return
        if fault.remaining <= 1:
            self._faults.pop(name, None)
        else:
            self._faults[name] = Fault(fault.name, fault.exception, fault.remaining - 1)
        raise fault.exception

    def clear(self) -> None:
        self._faults.clear()

    @contextmanager
    def scenario(self, name: str, exception: BaseException, *, times: int = 1) -> Iterator[FaultInjector]:
        self.add(name, exception, times=times)
        try:
            yield self
        finally:
            self._faults.pop(name, None)
