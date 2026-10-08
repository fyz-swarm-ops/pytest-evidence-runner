from app.calculator import add, divide, normalize_email


def test_adds_numbers():
    assert add(2, 3) == 5


def test_divides_numbers():
    assert divide(8, 2) == 4


def test_normalizes_email():
    assert normalize_email("  USER@Example.COM ") == "user@example.com"
