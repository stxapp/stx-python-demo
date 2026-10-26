"""Offline tests for examples/helpers.py: no API key, no network.

Run: python -m unittest discover tests
"""

import asyncio
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from stx import ChannelMessage, STXComboException, STXComboPriceMovedException  # noqa: E402
from stx.combos import BestQuote, CashOut, ComboPlacement, NegotiationClosed, RfqOpened  # noqa: E402
from stx.models import Market  # noqa: E402

from helpers import (  # noqa: E402
    best_offer,
    cash_out_when_held,
    combo_stake,
    describe_market,
    find_resting_buy,
    maker_quote_amount,
    market_name,
    pick_combo_legs,
    resting_buy_price,
    take_best_quote,
    upcoming,
    upcoming_markets,
    would_rest,
)


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

    def test_lowest_offer_decides(self):
        # Offers run from the highest price to the lowest; the 0.01 offer would fill a 0.01 buy.
        offers = [{"price": "0.0500", "quantity": "1"}, {"price": "0.0100", "quantity": "1"}]
        self.assertFalse(would_rest(market(offers=offers), "0.01"))

    def test_offer_at_price_would_trade(self):
        self.assertFalse(would_rest(market(offers=[{"price": "0.0100", "quantity": "1"}]), "0.01"))


class DescribeMarket(unittest.TestCase):
    def test_bid_and_no_offer(self):
        m = market(bids=[{"price": "0.4200", "quantity": "5.00"}])
        self.assertEqual(describe_market(m), "Away at Home: Home wins  bid 0.4200  offer -")

    def test_best_offer_is_the_lowest(self):
        m = market(
            bids=[{"price": "0.4200", "quantity": "5.00"}, {"price": "0.4000", "quantity": "2.00"}],
            offers=[{"price": "0.4800", "quantity": "1.00"}, {"price": "0.4500", "quantity": "3.00"}],
        )
        self.assertEqual(best_offer(m), "0.4500")
        self.assertEqual(describe_market(m), "Away at Home: Home wins  bid 0.4200  offer 0.4500")

    def test_question_tells_markets_apart(self):
        home = market(title="Away @ Home", question="Will Home defeat Away?")
        away = market(title="Away @ Home", question="Will Away defeat Home?")
        self.assertEqual(market_name(home), "Away at Home: Will Home defeat Away?")
        self.assertNotEqual(market_name(home), market_name(away))


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

    def test_skips_a_scheduled_event_whose_start_has_passed(self):
        stale = market(market_id="stale", event_start=PAST)
        good = market(market_id="good", event_start=FUTURE)
        found = find_resting_buy(FakeClient([stale, good]), now=NOW)
        self.assertEqual(found[0].market_id, "good")


PAST = "2026-10-20T00:00:00.000000Z"
FUTURE = "2026-10-22T23:00:00.000000Z"
NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


class Upcoming(unittest.TestCase):
    def test_scheduled_event_in_the_future(self):
        self.assertTrue(upcoming(market(event_start=FUTURE), NOW))

    def test_scheduled_event_whose_start_has_passed(self):
        self.assertFalse(upcoming(market(event_start=PAST), NOW))

    def test_started_event(self):
        self.assertFalse(upcoming(market(event_start=FUTURE, event_status="in_progress"), NOW))

    def test_no_start_time(self):
        self.assertTrue(upcoming(market(), NOW))

    def test_first_upcoming_markets_only(self):
        markets = [
            market(market_id="stale1", event_start=PAST),
            market(market_id="a", event_start=FUTURE),
            market(market_id="stale2", event_start=PAST),
            market(market_id="b", event_start=FUTURE),
            market(market_id="c", event_start=FUTURE),
        ]
        shown = upcoming_markets(markets, count=2, now=NOW)
        self.assertEqual([m.market_id for m in shown], ["a", "b"])

    def test_scan_limit(self):
        markets = [market(market_id="stale", event_start=PAST), market(market_id="a", event_start=FUTURE)]
        self.assertEqual(upcoming_markets(markets, count=5, scan=1, now=NOW), [])


class ComboStake(unittest.TestCase):
    def test_two_decimals(self):
        self.assertEqual(combo_stake("2"), "2.00")
        self.assertEqual(combo_stake("2.5"), "2.50")
        self.assertEqual(combo_stake(" 5.25 "), "5.25")

    def test_refuses_what_the_exchange_would(self):
        for bad in ("0", "5.001", "-1", "five", "1e3"):
            with self.assertRaises(ValueError, msg=bad):
                combo_stake(bad)


class FakeAsyncClient:
    """Stands in for AsyncSTX: iter_markets() yields the markets it was given."""

    def __init__(self, markets):
        self.markets = markets
        self.calls = []

    async def _iter(self):
        for m in self.markets:
            yield m

    def iter_markets(self, **query):
        self.calls.append(query)
        return self._iter()


class PickComboLegs(unittest.TestCase):
    FUTURE = FUTURE
    NOW = NOW

    def leg(self, market_id, event_id, **fields):
        return market(**{"market_id": market_id, "event_id": event_id, "event_start": self.FUTURE, **fields})

    def test_one_open_future_non_combo_market_per_event(self):
        client = FakeAsyncClient(
            [
                self.leg("a1", "e1"),
                self.leg("a2", "e1"),  # same event as a1
                self.leg("old", "e2", event_start="2026-10-19T00:00:00Z"),  # already started
                self.leg("live", "e3", event_status="in_progress"),
                self.leg("combo", "e4", event_type="combo"),
                self.leg("gone", "e5", archived=True),
                self.leg("b1", "e6"),
                self.leg("c1", "e7"),
            ]
        )
        legs = asyncio.run(pick_combo_legs(client, count=2, sport="Football", now=self.NOW))
        self.assertEqual([m.market_id for m in legs], ["a1", "b1"])
        self.assertEqual(client.calls[0], {"status": "open", "trading": True, "sports": ["Football"]})

    def test_fewer_than_asked_when_the_scan_runs_out(self):
        client = FakeAsyncClient([self.leg("a1", "e1"), self.leg("b1", "e2")])
        legs = asyncio.run(pick_combo_legs(client, count=3, now=self.NOW))
        self.assertEqual([m.market_id for m in legs], ["a1", "b1"])


def push(event, data):
    return ChannelMessage(topic="rfq:u1", event=event, payload=data.model_dump(), data=data)


def best(rfq_id, quote_id, amount):
    return push("best_quote", BestQuote(rfq_id=rfq_id, quote_id=quote_id, amount=amount))


PLACEMENT = ComboPlacement(rfq_id="r1", market_id="combo-1", order_id="o1", quantity="7.00", price="0.2858")


class FakeRfq:
    """Stands in for RfqChannel: next() hands out `messages` in order, then times out."""

    def __init__(self, messages, accept=None):
        self.messages = list(messages)
        self.accepted = []
        self._accept = accept or (lambda *args: PLACEMENT)

    async def next(self, timeout=None):
        if not self.messages:
            raise asyncio.TimeoutError
        return self.messages.pop(0)

    async def accept(self, rfq_id, quote_id, amount):
        self.accepted.append((rfq_id, quote_id, amount))
        return self._accept(rfq_id, quote_id, amount)


class TakeBestQuote(unittest.TestCase):
    def test_accepts_the_first_live_quote_at_its_exact_amount(self):
        seen = []
        rfq = FakeRfq([best("other", "q0", "9.0000"), best("r1", None, None), best("r1", "q1", "5.0000")])
        outcome = asyncio.run(take_best_quote(rfq, "r1", 1, lambda q: seen.append(q.amount)))
        self.assertIs(outcome.placement, PLACEMENT)
        self.assertEqual(outcome.amount, "5.0000")
        self.assertEqual(rfq.accepted, [("r1", "q1", "5.0000")])  # another request's quote is ignored
        self.assertEqual(seen, [None, "5.0000"])

    def test_takes_the_live_best_when_the_price_moved(self):
        calls = []

        def accept(rfq_id, quote_id, amount):
            calls.append(quote_id)
            if len(calls) == 1:
                moved = BestQuote(quote_id="q2", amount="4.8000")
                raise STXComboPriceMovedException("accept", reply={"reason": "price_moved"}, best_quote=moved)
            return PLACEMENT

        rfq = FakeRfq([best("r1", "q1", "5.0000")], accept)
        outcome = asyncio.run(take_best_quote(rfq, "r1", 1))
        self.assertIs(outcome.placement, PLACEMENT)
        self.assertEqual(rfq.accepted, [("r1", "q1", "5.0000"), ("r1", "q2", "4.8000")])

    def test_refused_accept_is_reported_with_its_reason(self):
        def accept(*args):
            raise STXComboException("accept", reply={"reason": "player_refused:nothing_to_sell"})

        outcome = asyncio.run(take_best_quote(FakeRfq([best("r1", "q1", "1.7900")], accept), "r1", 1))
        self.assertIsNone(outcome.placement)
        self.assertEqual(outcome.reason, "player_refused (nothing_to_sell)")

    def test_no_quote(self):
        outcome = asyncio.run(take_best_quote(FakeRfq([]), "r1", 1))
        self.assertIsNone(outcome.placement)
        self.assertIsNone(outcome.reason)

    def test_request_closed(self):
        closed = push("negotiation_closed", NegotiationClosed(rfq_id="r1", reason="expired"))
        outcome = asyncio.run(take_best_quote(FakeRfq([closed]), "r1", 1))
        self.assertIsNone(outcome.placement)
        self.assertEqual(outcome.reason, "expired")


class FakeCashOut:
    def __init__(self, refusals, reason="nothing_to_sell"):
        self.refusals = refusals
        self.reason = reason
        self.calls = 0

    async def cash_out(self, market_id):
        self.calls += 1
        if self.calls <= self.refusals:
            raise STXComboException("cash_out", reply={"reason": self.reason})
        return CashOut(rfq_id="r2", market_id=market_id, quantity="7.00")


class CashOutWhenHeld(unittest.TestCase):
    def test_retries_nothing_to_sell(self):
        rfq = FakeCashOut(refusals=2)
        out = asyncio.run(cash_out_when_held(rfq, "combo-1", delay=0))
        self.assertEqual(out.quantity, "7.00")
        self.assertEqual(rfq.calls, 3)

    def test_gives_up_after_its_attempts(self):
        rfq = FakeCashOut(refusals=99)
        with self.assertRaises(STXComboException):
            asyncio.run(cash_out_when_held(rfq, "combo-1", attempts=2, delay=0))
        self.assertEqual(rfq.calls, 2)

    def test_other_refusals_are_not_retried(self):
        rfq = FakeCashOut(refusals=1, reason="market_not_quotable")
        with self.assertRaises(STXComboException):
            asyncio.run(cash_out_when_held(rfq, "combo-1", delay=0))
        self.assertEqual(rfq.calls, 1)


def opened(**fields) -> RfqOpened:
    base = {"rfq_id": "r1", "side": "buy", "amount": "2.0000", "max_price": "1.0000", "tick_size": "0.0001000"}
    base.update(fields)
    return RfqOpened.model_validate(base)


class MakerQuoteAmount(unittest.TestCase):
    def test_buy_is_the_stake_times_the_multiple(self):
        self.assertEqual(maker_quote_amount(opened(), "9", "0.08"), "18.00")

    def test_buy_rounds_down_to_whole_cents(self):
        self.assertEqual(maker_quote_amount(opened(amount="2.5000"), "1.333", "0.08"), "3.33")

    def test_buy_that_buys_no_whole_contract_is_skipped(self):
        # 0.50 / (0.50 + 0.01) prices at 0.9804: 0.50 buys no whole contract.
        self.assertIsNone(maker_quote_amount(opened(amount="0.5000"), "0.02", "0.08"))

    def test_zero_multiple_is_skipped(self):
        self.assertIsNone(maker_quote_amount(opened(), "0", "0.08"))

    def test_cash_out_pays_the_price_for_the_whole_size(self):
        sell = opened(side="sell", amount=None, quantity="17.00", market_id="c1")
        self.assertEqual(maker_quote_amount(sell, "9", "0.08"), "1.36")

    def test_cash_out_at_or_above_max_price_is_skipped(self):
        sell = opened(side="sell", amount=None, quantity="14.00", market_id="c1")
        self.assertIsNone(maker_quote_amount(sell, "9", "1.50"))
        self.assertIsNone(maker_quote_amount(sell, "9", "1.00"))


if __name__ == "__main__":
    unittest.main()
