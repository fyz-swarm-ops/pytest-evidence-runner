def add(left: int, right: int) -> int:
    return left + right


def divide(left: int, right: int) -> float:
    # Intentional regression for the comparison example.
    return left / (right + 1)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def multiply(left: int, right: int) -> int:
    return left * right
