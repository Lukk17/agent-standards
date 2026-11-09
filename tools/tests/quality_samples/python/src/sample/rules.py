"""Rules with one planted gap each: an untested boundary, an untested function, a duplicate and a loop."""

ADULT_AGE = 18
HOME_COUNTRY = "PL"


def is_adult(age: int) -> bool:
    """The tests never try 18, so the mutant that turns >= into > survives."""
    return age >= ADULT_AGE


def shipping_cost(weight: float, express: bool, country: str) -> float:
    """Branchy and barely tested, so its CRAP score is high."""
    if weight <= 0:
        raise ValueError("weight must be positive")
    cost = 5.0
    if weight > 10:
        cost += 10.0
    elif weight > 2:
        cost += 4.0
    if express:
        cost *= 2
    if country != HOME_COUNTRY:
        cost += 7.5
    return cost


def order_total(prices: list[float]) -> float:
    """The same shape as basket_total, so dryer reports the pair."""
    total = 0.0
    for price in prices:
        if price < 0:
            raise ValueError("price must not be negative")
        total += price
    return round(total, 2)


def basket_total(amounts: list[float]) -> float:
    """Never tested, so every one of its mutants is uncovered."""
    running = 0.0
    for amount in amounts:
        if amount < 0:
            raise ValueError("amount must not be negative")
        running += amount
    return round(running, 2)


def countdown(steps: int) -> int:
    """The mutant that turns - into + never ends, so mutator has to stop it at its timeout."""
    while steps > 0:
        steps = steps - 1
    return steps
