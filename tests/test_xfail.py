from time import sleep

import pytest


@pytest.mark.xfail()
def test_xpassing():
    sleep(4)


@pytest.mark.xfail()
def test_xfailing():
    sleep(5)
    assert False
