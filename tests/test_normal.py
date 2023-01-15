from time import sleep

import pytest


def test_passing():
    sleep(1)


def test_failing():
    sleep(2)
    assert False


@pytest.mark.skip()
def test_skipping():
    sleep(3)
