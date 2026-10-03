"""Offline tests for examples/helpers.py: no API key, no network.

Run: python -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from stx.models import Market  # noqa: E402

from helpers import describe_market, find_resting_buy, resting_buy_price, would_rest  # noqa: E402


def market(**fields) -> Market:
    base = {
        "market_id": "m1",
        "event_title": "Away at Home",
        "title": "Home wins",
        "status": "open",
        "event_status": "scheduled",
        "max_price": "1.0000",
        "bids": [],
        "offers": [],
    }
    base.update(fields)
    return Market.model_validate(base)


class FakeClient:
    """Stands in for STX: iter_markets() yields the markets it was given."""

    def __init__(self, markets):
        self.markets = markets
        self.calls = []

    def iter_markets(self, **query):
        self.calls.append(query)
        return iter(self.markets)


class RestingBuyPrice(unittest.TestCase):
    def test_one_dollar_contract(self):
        self.assertEqual(resting_buy_price("1.0000"), "0.01")

    def test_hundred_dollar_contract(self):
        self.assertEqual(resting_buy_price("100.0000"), "1.00")

    def test_never_below_a_cent(self):
        self.assertEqual(resting_buy_price("0.50"), "0.01")

    def test_refuses_a_price_it_cannot_derive(self):
        with self.assertRaises(ValueError):
            resting_buy_price("0.01")


class WouldRest(unittest.TestCase):
    def test_no_offers(self):
        self.assertTrue(would_rest(market(), "0.01"))

    def test_offer_above_price(self):
        self.assertTrue(would_rest(market(offers=[{"price": "0.0200", "quantity": "1"}]), "0.01"))

    def test_offer_at_price_would_trade(self):
        self.assertFalse(would_rest(market(offers=[{"price": "0.0100", "quantity": "1"}]), "0.01"))


class DescribeMarket(unittest.TestCase):
    def test_bid_and_no_offer(self):
        m = market(bids=[{"price": "0.4200", "quantity": "5.00"}])
        self.assertEqual(describe_market(m), "Away at Home: Home wins  bid 0.4200  offer -")


class FindRestingBuy(unittest.TestCase):
    def test_skips_started_events_and_books_that_would_trade(self):
        started = market(market_id="live", event_status="live")
        crossed = market(market_id="crossed", offers=[{"price": "0.0100", "quantity": "1"}])
        good = market(market_id="good", max_price="100.0000")
        client = FakeClient([started, crossed, good])
        found = find_resting_buy(client, sport="Football")
        self.assertIsNotNone(found)
        self.assertEqual(found[0].market_id, "good")
        self.assertEqual(found[1], "1.00")
        self.assertEqual(client.calls[0]["sports"], ["Football"])

    def test_none_when_nothing_fits(self):
        self.assertIsNone(find_resting_buy(FakeClient([market(event_status="live")])))


if __name__ == "__main__":
    unittest.main()
