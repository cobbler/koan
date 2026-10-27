from contextlib import contextmanager
from typing import Generator


@contextmanager
def does_not_raise() -> Generator[None, None, None]:
    yield
