from typing import Any

import pytest

from koan.cexceptions import (
    KX,
    FileNotFoundException,
    InfoException,
    KoanException,
    OVZCreateException,
    VirtCreateException,
)


@pytest.mark.parametrize(
    "cls",
    [KoanException, KX, FileNotFoundException, InfoException],
)
def test_koan_style_exception_without_args(cls: Any) -> None:
    exc = cls("plain message")

    assert exc.value == "plain message"
    assert exc.from_koan == 1
    assert str(exc) == repr("plain message")


@pytest.mark.parametrize(
    "cls",
    [KoanException, KX, FileNotFoundException, InfoException],
)
def test_koan_style_exception_with_args(cls: Any) -> None:
    exc = cls("msg %s %d", "foo", 3)

    assert exc.value == "msg foo 3"
    assert exc.from_koan == 1
    assert str(exc) == repr("msg foo 3")


@pytest.mark.parametrize("cls", [KX, FileNotFoundException])
def test_koan_exception_subclasses_are_koan_exceptions(cls: Any) -> None:
    exc = cls("boom")

    assert isinstance(exc, KoanException)


@pytest.mark.parametrize("cls", [VirtCreateException, OVZCreateException])
def test_plain_exception_subclasses(cls: Any) -> None:
    exc = cls("boom")

    assert isinstance(exc, Exception)
    assert str(exc) == "boom"
    assert not hasattr(exc, "value")
    assert not hasattr(exc, "from_koan")
