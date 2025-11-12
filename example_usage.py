"""
Example usage of the ETF Arbitrage Trading Algorithm

Demonstrates how to use the engine with sample data and scenarios
"""

from etf_arbitrage import (
    ETF, ETFArbitrageEngine, AutomatedArbitrageStrategy,
    create_sample_etf
)
import random


def example_1_basic_arbitrage():
    """Basic example: Single ETF with simple arbitrage opportunity"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic ETF Arbitrage")
    print("="*70 + "\n")

    # Initialize engine
    engine = ETFArbitrageEngine(
        initial_capital=1_000_000,
        transaction_cost_pct=0.001,
        min_spread_threshold=0.002
    )

    # Create ETF that tracks 3 stocks
    etf = create_sample_etf(
        ticker="SPY",
        price=450.0,  # ETF is overpriced
        holdings={
            "AAPL": 0.4,   # 40% weight
            "MSFT": 0.35,  # 35% weight
            "GOOGL": 0.25  # 25% weight
        }
    )

    # Add ETF to engine
    engine.add_etf(etf)

    # Set underlying equity prices (NAV should be ~445)
    engine.update_equity_price("AAPL", 180.0)   # Contributes 72.0 to NAV
    engine.update_equity_price("MSFT", 370.0)   # Contributes 129.5 to NAV
    engine.update_equity_price("GOOGL", 140.0)  # Contributes 35.0 to NAV
    # Total NAV = 236.5... wait that doesn't match

    # Let me recalculate: if NAV should be around 445
    # 0.4 * AAPL + 0.35 * MSFT + 0.25 * GOOGL = 445
    # Let's use: AAPL=180, MSFT=380, GOOGL=140
    # 0.4*180 + 0.35*380 + 0.25*140 = 72 + 133 + 35 = 240
    # That's still not right. Let me think about this differently...

    # Actually, for an ETF priced at $450, if the holdings have those weights,
    # then the NAV calculation works as: sum of (weight * underlying_price)
    # Let's set prices so NAV = 445 (5 dollar discount creates arbitrage)
    # 0.4 * 1112.5 + 0.35 * 1271.43 + 0.25 * 1780 = 445 + 445 + 445 = 1335
    # This is getting complicated. Let me just use realistic stock prices.

    engine.update_equity_price("AAPL", 1100.0)  # 0.4 * 1100 = 440
    engine.update_equity_price("MSFT", 1300.0)  # 0.35 * 1300 = 455
    engine.update_equity_price("GOOGL", 1400.0) # 0.25 * 1400 = 350
    # NAV = 440 + 455 + 350 = 1245
    # Hmm, this gives NAV of 1245, but ETF is priced at 450

    # OK let me think about this more carefully. The weights sum to 1.0.
    # If ETF price is $450, and it holds these stocks in certain quantities,
    # then NAV = sum of (quantity of each stock * price per stock) / shares of ETF
    # The weights represent the PROPORTION of value, not quantity.

    # Simplified approach: just make the NAV calculation work out
    # If ETF = 450, and we want NAV = 445 (ETF overpriced by $5)
    # Then: 0.4 * X + 0.35 * Y + 0.25 * Z = 445
    # Let's use simple numbers: X=1000, Y=1200, Z=1000
    # 400 + 420 + 250 = 1070 (not quite)

    # Actually, I think I'm overcomplicating this. Let me use simpler numbers:
    engine.update_equity_price("AAPL", 180.0)
    engine.update_equity_price("MSFT", 380.0)
    engine.update_equity_price("GOOGL", 560.0)
    # NAV = 0.4*180 + 0.35*380 + 0.25*560 = 72 + 133 + 140 = 345

    # So ETF at 450 vs NAV at 345 means ETF is overvalued by 105
    # That's a huge arbitrage opportunity (23% spread)

    print("Initial Setup:")
    print(f"ETF {etf.ticker} Price: ${etf.price:.2f}")
    nav = etf.calculate_nav(engine.equity_prices)
    print(f"Calculated NAV: ${nav:.2f}")
    print(f"Spread: ${etf.price - nav:.2f} ({((etf.price - nav) / nav * 100):.2f}%)")
    print()

    # Scan for opportunities
    opportunities = engine.scan_opportunities()
    print(f"Found {len(opportunities)} arbitrage opportunities:")
    for opp in opportunities:
        print(f"  {opp}")
    print()

    # Execute arbitrage
    if opportunities:
        opp = opportunities[0]
        trade = engine.execute_arbitrage(opp, notional=100_000)
        if trade:
            print(f"Executed trade: {trade.trade_type.value}")
            print(f"Expected profit: ${trade.expected_profit:.2f}")
            print()

    # Show status
    engine.print_status()

    # Simulate price convergence
    print("\nSimulating price convergence...")
    engine.update_etf_price("SPY", 350.0)  # ETF price moves toward NAV
    print(f"New ETF price: $350.00")
    print(f"NAV: ${nav:.2f}")

    # Close trade and realize profit
    if engine.active_trades:
        pnl = engine.close_trade(engine.active_trades[0])
        print(f"\nClosed trade with PnL: ${pnl:.2f}")

    # Final status
    engine.print_status()


def example_2_multiple_etfs():
    """Example with multiple ETFs being monitored"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Multiple ETFs with Different Opportunities")
    print("="*70 + "\n")

    engine = ETFArbitrageEngine(initial_capital=2_000_000)

    # Create multiple ETFs
    etfs = [
        create_sample_etf("QQQ", 380.0, {"AAPL": 0.12, "MSFT": 0.11, "AMZN": 0.08, "NVDA": 0.07}),
        create_sample_etf("XLF", 38.5, {"JPM": 0.11, "BAC": 0.08, "WFC": 0.07, "C": 0.06}),
        create_sample_etf("XLE", 85.0, {"XOM": 0.22, "CVX": 0.18, "COP": 0.08, "SLB": 0.07}),
    ]

    for etf in etfs:
        engine.add_etf(etf)

    # Set equity prices to create different arbitrage scenarios
    # QQQ components (tech stocks)
    engine.update_prices({
        "AAPL": 180.0, "MSFT": 380.0, "AMZN": 145.0, "NVDA": 480.0,
    })

    # XLF components (financials) - will make this one undervalued
    engine.update_prices({
        "JPM": 155.0, "BAC": 32.0, "WFC": 48.0, "C": 52.0,
    })

    # XLE components (energy)
    engine.update_prices({
        "XOM": 110.0, "CVX": 155.0, "COP": 115.0, "SLB": 55.0,
    })

    # Add more holdings to balance weights (simplified)
    for etf in etfs:
        remaining_weight = 1.0 - sum(etf.holdings.values())
        if remaining_weight > 0:
            etf.holdings["CASH"] = remaining_weight
            engine.update_equity_price("CASH", 1.0)

    print("Scanning for arbitrage opportunities across multiple ETFs...\n")
    opportunities = engine.scan_opportunities()

    print(f"Found {len(opportunities)} opportunities:")
    for i, opp in enumerate(opportunities, 1):
        print(f"{i}. {opp.etf.ticker}: {opp.trade_type.value}")
        print(f"   Spread: {opp.spread_pct:.3%}, Profit/share: ${opp.profit_per_share:.4f}")

    print("\nExecuting top 3 opportunities...")
    for opp in opportunities[:3]:
        trade = engine.execute_arbitrage(opp, notional=50_000)
        if trade:
            print(f"  Opened {trade.etf_ticker} arbitrage position")

    engine.print_status()


def example_3_automated_strategy():
    """Example using the automated strategy"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Automated Arbitrage Strategy")
    print("="*70 + "\n")

    engine = ETFArbitrageEngine(initial_capital=5_000_000)

    # Create ETF
    etf = create_sample_etf(
        "SPY",
        price=450.0,
        holdings={
            "AAPL": 0.25, "MSFT": 0.20, "GOOGL": 0.15,
            "AMZN": 0.15, "NVDA": 0.10, "TSLA": 0.10, "META": 0.05
        }
    )
    engine.add_etf(etf)

    # Initialize equity prices
    equity_prices = {
        "AAPL": 180.0, "MSFT": 380.0, "GOOGL": 140.0,
        "AMZN": 145.0, "NVDA": 480.0, "TSLA": 250.0, "META": 320.0
    }
    engine.update_prices(equity_prices)

    # Create automated strategy
    strategy = AutomatedArbitrageStrategy(
        engine,
        max_position_size=100_000,
        auto_close_threshold=0.5
    )

    print("Running automated strategy over 10 iterations...\n")

    for iteration in range(10):
        # Simulate price movements
        etf_price_change = random.uniform(-2, 2)
        engine.update_etf_price("SPY", engine.etfs["SPY"].price + etf_price_change)

        for ticker in equity_prices:
            equity_prices[ticker] *= random.uniform(0.98, 1.02)
            engine.update_equity_price(ticker, equity_prices[ticker])

        # Run strategy iteration
        stats = strategy.run_iteration()

        nav = etf.calculate_nav(engine.equity_prices)
        spread = abs(engine.etfs["SPY"].price - nav) / nav

        print(f"Iteration {iteration + 1}:")
        print(f"  ETF Price: ${engine.etfs['SPY'].price:.2f}, NAV: ${nav:.2f}, Spread: {spread:.3%}")
        print(f"  Opportunities: {stats['opportunities_found']}, "
              f"Opened: {stats['trades_opened']}, Closed: {stats['trades_closed']}")
        if stats['pnl_realized'] != 0:
            print(f"  Realized PnL: ${stats['pnl_realized']:.2f}")
        print()

    print("\nFinal Results:")
    engine.print_status()

    metrics = engine.get_performance_metrics()
    print(f"\nSharpe-like metric: {metrics['total_return_pct'] / max(len(engine.closed_trades), 1):.2f}% per trade")


def example_4_stress_test():
    """Stress test with high-frequency updates"""
    print("\n" + "="*70)
    print("EXAMPLE 4: High-Frequency Stress Test")
    print("="*70 + "\n")

    engine = ETFArbitrageEngine(
        initial_capital=10_000_000,
        transaction_cost_pct=0.0005,  # Lower costs for HFT
        min_spread_threshold=0.001    # Tighter threshold
    )

    # Create multiple ETFs
    etf_configs = [
        ("SPY", 450.0, {"AAPL": 0.3, "MSFT": 0.3, "GOOGL": 0.4}),
        ("QQQ", 380.0, {"AAPL": 0.35, "MSFT": 0.35, "NVDA": 0.3}),
        ("IWM", 195.0, {"XOM": 0.25, "JPM": 0.25, "BAC": 0.25, "WFC": 0.25}),
    ]

    for ticker, price, holdings in etf_configs:
        etf = create_sample_etf(ticker, price, holdings)
        engine.add_etf(etf)

    # Initialize prices
    base_prices = {
        "AAPL": 180.0, "MSFT": 380.0, "GOOGL": 140.0,
        "NVDA": 480.0, "XOM": 110.0, "JPM": 155.0,
        "BAC": 32.0, "WFC": 48.0
    }
    engine.update_prices(base_prices)

    strategy = AutomatedArbitrageStrategy(engine, max_position_size=200_000)

    print("Running 100 iterations of high-frequency trading...\n")

    iterations = 100
    profitable_iterations = 0

    for i in range(iterations):
        # Rapid price updates
        for etf_ticker in ["SPY", "QQQ", "IWM"]:
            etf = engine.etfs[etf_ticker]
            etf.price += random.uniform(-1.0, 1.0)

        for ticker in base_prices:
            base_prices[ticker] *= random.uniform(0.999, 1.001)
            engine.update_equity_price(ticker, base_prices[ticker])

        # Run strategy
        stats = strategy.run_iteration()
        if stats['pnl_realized'] > 0:
            profitable_iterations += 1

        if (i + 1) % 20 == 0:
            metrics = engine.get_performance_metrics()
            print(f"After {i + 1} iterations:")
            print(f"  Total Value: ${metrics['total_value']:,.2f}")
            print(f"  Return: {metrics['total_return_pct']:.2f}%")
            print(f"  Active Trades: {metrics['active_trades']}")

    print("\n" + "="*70)
    print("STRESS TEST RESULTS")
    print("="*70)
    engine.print_status()
    print(f"\nProfitable Iterations: {profitable_iterations}/{iterations}")
    print(f"Win Rate: {profitable_iterations/iterations*100:.1f}%")


if __name__ == "__main__":
    # Run all examples
    example_1_basic_arbitrage()
    example_2_multiple_etfs()
    example_3_automated_strategy()
    example_4_stress_test()

    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)
