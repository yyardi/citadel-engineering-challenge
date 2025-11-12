"""
Unit tests for ETF Arbitrage Algorithm
"""

import unittest
from etf_arbitrage import (
    ETF, Equity, ETFArbitrageEngine, TradeType,
    AutomatedArbitrageStrategy, create_sample_etf
)


class TestETF(unittest.TestCase):
    """Test ETF class functionality"""

    def setUp(self):
        self.etf = ETF(
            ticker="SPY",
            price=100.0,
            holdings={"AAPL": 0.5, "MSFT": 0.5}
        )

    def test_calculate_nav(self):
        """Test NAV calculation"""
        prices = {"AAPL": 100.0, "MSFT": 200.0}
        nav = self.etf.calculate_nav(prices)
        # NAV = 0.5 * 100 + 0.5 * 200 = 150
        self.assertEqual(nav, 150.0)

    def test_calculate_nav_missing_equity(self):
        """Test NAV with missing equity price"""
        prices = {"AAPL": 100.0}  # MSFT missing
        nav = self.etf.calculate_nav(prices)
        # Should only include AAPL
        self.assertEqual(nav, 50.0)

    def test_arbitrage_opportunity_etf_overpriced(self):
        """Test detecting overpriced ETF"""
        prices = {"AAPL": 80.0, "MSFT": 80.0}
        # NAV = 0.5*80 + 0.5*80 = 80
        # ETF = 100, so overpriced by 20
        result = self.etf.get_arbitrage_opportunity(prices, transaction_cost=1.0)

        self.assertIsNotNone(result)
        trade_type, profit = result
        self.assertEqual(trade_type, TradeType.SHORT_ETF_LONG_BASKET)
        self.assertGreater(profit, 0)

    def test_arbitrage_opportunity_etf_underpriced(self):
        """Test detecting underpriced ETF"""
        self.etf.price = 80.0
        prices = {"AAPL": 100.0, "MSFT": 100.0}
        # NAV = 100, ETF = 80, underpriced by 20
        result = self.etf.get_arbitrage_opportunity(prices, transaction_cost=1.0)

        self.assertIsNotNone(result)
        trade_type, profit = result
        self.assertEqual(trade_type, TradeType.LONG_ETF_SHORT_BASKET)
        self.assertGreater(profit, 0)

    def test_no_arbitrage_opportunity(self):
        """Test when no arbitrage exists"""
        self.etf.price = 100.0
        prices = {"AAPL": 100.0, "MSFT": 100.0}
        # NAV = 100, ETF = 100, no opportunity
        result = self.etf.get_arbitrage_opportunity(prices, transaction_cost=1.0)

        self.assertIsNone(result)


class TestETFArbitrageEngine(unittest.TestCase):
    """Test ETF Arbitrage Engine"""

    def setUp(self):
        self.engine = ETFArbitrageEngine(
            initial_capital=1_000_000,
            transaction_cost_pct=0.001,
            min_spread_threshold=0.01
        )

        self.etf = create_sample_etf(
            "SPY",
            price=110.0,  # Overpriced
            holdings={"AAPL": 0.5, "MSFT": 0.5}
        )
        self.engine.add_etf(self.etf)

        # Set prices so NAV = 100
        self.engine.update_equity_price("AAPL", 100.0)
        self.engine.update_equity_price("MSFT", 100.0)

    def test_add_etf(self):
        """Test adding ETF to engine"""
        self.assertIn("SPY", self.engine.etfs)
        self.assertEqual(self.engine.etfs["SPY"], self.etf)

    def test_update_prices(self):
        """Test batch price update"""
        self.engine.update_prices({
            "AAPL": 150.0,
            "MSFT": 200.0,
            "SPY": 120.0
        })

        self.assertEqual(self.engine.equity_prices["AAPL"], 150.0)
        self.assertEqual(self.engine.equity_prices["MSFT"], 200.0)
        self.assertEqual(self.engine.etfs["SPY"].price, 120.0)

    def test_scan_opportunities(self):
        """Test opportunity scanning"""
        opportunities = self.engine.scan_opportunities()

        self.assertGreater(len(opportunities), 0)
        self.assertEqual(opportunities[0].etf.ticker, "SPY")
        self.assertEqual(opportunities[0].trade_type, TradeType.SHORT_ETF_LONG_BASKET)

    def test_execute_arbitrage(self):
        """Test executing an arbitrage trade"""
        opportunities = self.engine.scan_opportunities()
        self.assertGreater(len(opportunities), 0)

        initial_capital = self.engine.capital
        trade = self.engine.execute_arbitrage(opportunities[0], notional=10_000)

        self.assertIsNotNone(trade)
        self.assertEqual(len(self.engine.active_trades), 1)
        self.assertLess(self.engine.capital, initial_capital)
        self.assertGreater(trade.expected_profit, 0)

    def test_close_trade(self):
        """Test closing a trade"""
        opportunities = self.engine.scan_opportunities()
        trade = self.engine.execute_arbitrage(opportunities[0], notional=10_000)

        # Simulate price convergence (ETF drops to NAV)
        self.engine.update_etf_price("SPY", 100.0)

        pnl = self.engine.close_trade(trade)

        self.assertEqual(len(self.engine.active_trades), 0)
        self.assertEqual(len(self.engine.closed_trades), 1)
        self.assertGreater(pnl, 0)  # Should be profitable

    def test_get_unrealized_pnl(self):
        """Test unrealized PnL calculation"""
        opportunities = self.engine.scan_opportunities()
        self.engine.execute_arbitrage(opportunities[0], notional=10_000)

        # Before convergence, should have some unrealized PnL
        unrealized = self.engine.get_unrealized_pnl()
        self.assertIsInstance(unrealized, float)

    def test_get_performance_metrics(self):
        """Test performance metrics"""
        metrics = self.engine.get_performance_metrics()

        self.assertIn('total_value', metrics)
        self.assertIn('capital', metrics)
        self.assertIn('realized_pnl', metrics)
        self.assertIn('unrealized_pnl', metrics)
        self.assertIn('total_return', metrics)
        self.assertIn('active_trades', metrics)
        self.assertIn('closed_trades', metrics)

    def test_insufficient_capital(self):
        """Test that trades fail with insufficient capital"""
        small_engine = ETFArbitrageEngine(initial_capital=100)
        small_engine.add_etf(self.etf)
        small_engine.update_equity_price("AAPL", 100.0)
        small_engine.update_equity_price("MSFT", 100.0)

        opportunities = small_engine.scan_opportunities()
        trade = small_engine.execute_arbitrage(opportunities[0], notional=100_000)

        self.assertIsNone(trade)  # Should fail due to insufficient capital


class TestAutomatedStrategy(unittest.TestCase):
    """Test Automated Strategy"""

    def setUp(self):
        self.engine = ETFArbitrageEngine(initial_capital=1_000_000)
        self.etf = create_sample_etf(
            "SPY",
            price=110.0,
            holdings={"AAPL": 0.5, "MSFT": 0.5}
        )
        self.engine.add_etf(self.etf)
        self.engine.update_equity_price("AAPL", 100.0)
        self.engine.update_equity_price("MSFT", 100.0)

        self.strategy = AutomatedArbitrageStrategy(
            self.engine,
            max_position_size=50_000,
            auto_close_threshold=0.5
        )

    def test_run_iteration(self):
        """Test running one strategy iteration"""
        stats = self.strategy.run_iteration()

        self.assertIn('opportunities_found', stats)
        self.assertIn('trades_opened', stats)
        self.assertIn('trades_closed', stats)
        self.assertIn('pnl_realized', stats)

        # Should have found opportunity and opened trade
        self.assertGreater(stats['opportunities_found'], 0)
        self.assertGreater(stats['trades_opened'], 0)

    def test_auto_close_on_convergence(self):
        """Test that strategy auto-closes when spread narrows"""
        # Open a trade
        stats1 = self.strategy.run_iteration()
        self.assertGreater(stats1['trades_opened'], 0)

        # Simulate price convergence
        self.engine.update_etf_price("SPY", 100.5)  # Almost at NAV

        # Should close the trade
        stats2 = self.strategy.run_iteration()
        self.assertGreater(stats2['trades_closed'], 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_empty_holdings(self):
        """Test ETF with no holdings"""
        etf = ETF("EMPTY", 100.0, {})
        nav = etf.calculate_nav({"AAPL": 100.0})
        self.assertEqual(nav, 0.0)

    def test_negative_prices(self):
        """Test handling of negative prices (should not occur in real markets)"""
        etf = ETF("TEST", 100.0, {"AAPL": 0.5, "MSFT": 0.5})
        # Algorithm should still calculate NAV mathematically
        nav = etf.calculate_nav({"AAPL": -10.0, "MSFT": 50.0})
        self.assertEqual(nav, 20.0)  # 0.5*(-10) + 0.5*50 = 20

    def test_weights_not_summing_to_one(self):
        """Test ETF with weights that don't sum to 1.0"""
        etf = ETF("TEST", 100.0, {"AAPL": 0.3, "MSFT": 0.3})  # Sum = 0.6
        nav = etf.calculate_nav({"AAPL": 100.0, "MSFT": 100.0})
        self.assertEqual(nav, 60.0)  # Should still work


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    print("Running ETF Arbitrage Algorithm Tests")
    print("=" * 70)
    run_tests()
