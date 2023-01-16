from time import sleep

import pytest


@pytest.mark.parametrize("param", [1, "red", 2.3])
def test_parametrize(param):
    sleep(1)
    assert param in [1, "red", 2.3]
