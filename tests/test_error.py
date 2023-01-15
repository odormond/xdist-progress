from time import sleep

import pytest


@pytest.fixture
def setup_fail():
    assert False


def test_setup_failure(setup_fail):
    pass


@pytest.fixture
def teardown_fail():
    yield
    assert False


def test_teardown_failure(teardown_fail):
    sleep(6)
