from app import add, divide


def test_add_passes():
    assert add(2, 3) == 5


def test_divide_passes():
    assert divide(10, 2) == 5


def test_intentional_failure_for_evidence():
    assert add(2, 2) == 5
