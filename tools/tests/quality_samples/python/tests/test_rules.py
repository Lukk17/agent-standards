from sample.rules import countdown, is_adult, order_total, shipping_cost


def test_thirty_is_an_adult():
    assert is_adult(30)


def test_five_is_not_an_adult():
    assert not is_adult(5)


def test_a_light_parcel_at_home_costs_the_base_rate():
    assert shipping_cost(1.0, express=False, country="PL") == 5.0


def test_order_total_adds_the_prices():
    assert order_total([1.5, 2.25]) == 3.75


def test_countdown_stops_at_zero():
    assert countdown(3) == 0
