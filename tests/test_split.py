from split import format_cents, friend_and_organizer_shares


def test_prd_expenses_split_equally_with_the_organizer_included():
    dinner_friend, dinner_organizer = friend_and_organizer_shares(12000, 2)
    snacks_friend, snacks_organizer = friend_and_organizer_shares(5000, 1)
    taxi_friend, taxi_organizer = friend_and_organizer_shares(9000, 3)

    assert format_cents(dinner_friend) == "40.00"
    assert format_cents(dinner_organizer) == "40.00"
    assert format_cents(snacks_friend) == "25.00"
    assert format_cents(snacks_organizer) == "25.00"
    assert format_cents(taxi_friend) == "22.50"
    assert format_cents(taxi_organizer) == "22.50"


def test_leftover_cents_stay_with_the_organizer():
    friend_share, organizer_share = friend_and_organizer_shares(100, 2)

    assert format_cents(friend_share) == "0.33"
    assert format_cents(organizer_share) == "0.34"
    assert friend_share * 2 + organizer_share == 100
