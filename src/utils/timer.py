from __future__ import annotations

from time import perf_counter
from types import TracebackType


class Timer:
    def __enter__(self) -> "Timer":
        self.start = perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        elapsed = perf_counter() - self.start
        print(f"Elapsed: {elapsed:.2f} sec")