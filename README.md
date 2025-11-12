# ETF Arbitrage Trading Algorithm

Citadel Engineering Challenge - ETF Arbitrage Trading Opportunity

## Overview

This algorithm identifies and executes arbitrage opportunities between ETFs (Exchange-Traded Funds) and their underlying equity baskets. When an ETF's market price diverges from its Net Asset Value (NAV), there's a profit opportunity.

## Strategy

### Core Concept
- **ETF Price > NAV**: Short ETF, Long underlying basket → Profit when prices converge
- **ETF Price < NAV**: Long ETF, Short underlying basket → Profit when prices converge

### Key Features
- Real-time NAV calculation from underlying equity prices
- Automated opportunity detection with configurable thresholds
- Transaction cost modeling
- Position tracking and PnL calculation
- Automated strategy execution with smart trade management
- Performance metrics and reporting

## Architecture

### Core Classes

1. **ETF**: Represents an ETF with its holdings and market price
2. **Equity**: Represents an underlying equity security
3. **ArbitrageOpportunity**: Detected arbitrage opportunity with profit metrics
4. **Trade**: Executed arbitrage position (both legs)
5. **ETFArbitrageEngine**: Main trading engine
6. **AutomatedArbitrageStrategy**: Automated execution strategy

## Usage

### Basic Example

```python
from etf_arbitrage import ETFArbitrageEngine, create_sample_etf

# Initialize engine
engine = ETFArbitrageEngine(
    initial_capital=1_000_000,
    transaction_cost_pct=0.001,      # 10 bps
    min_spread_threshold=0.002        # 20 bps minimum
)

# Create ETF
etf = create_sample_etf(
    ticker="SPY",
    price=450.0,
    holdings={
        "AAPL": 0.4,   # 40% weight
        "MSFT": 0.35,  # 35% weight
        "GOOGL": 0.25  # 25% weight
    }
)

engine.add_etf(etf)

# Update market prices
engine.update_equity_price("AAPL", 180.0)
engine.update_equity_price("MSFT", 380.0)
engine.update_equity_price("GOOGL", 560.0)

# Scan for opportunities
opportunities = engine.scan_opportunities()

# Execute best opportunity
if opportunities:
    trade = engine.execute_arbitrage(opportunities[0], notional=100_000)

# Monitor and close when profitable
pnl = engine.close_trade(trade)
engine.print_status()
```

### Automated Strategy

```python
from etf_arbitrage import AutomatedArbitrageStrategy

strategy = AutomatedArbitrageStrategy(
    engine,
    max_position_size=100_000,
    auto_close_threshold=0.5  # Close when spread narrows 50%
)

# Run strategy iteration
stats = strategy.run_iteration()
```

## Running Examples

```bash
python example_usage.py
```

This runs 4 comprehensive examples:
1. Basic single ETF arbitrage
2. Multiple ETFs with different opportunities
3. Automated strategy over multiple iterations
4. High-frequency stress test (100 iterations)

## Performance Metrics

The engine tracks:
- Total portfolio value
- Realized PnL
- Unrealized PnL
- Total return %
- Capital utilization
- Number of active/closed trades
- Win rate

## Configuration Parameters

### ETFArbitrageEngine
- `initial_capital`: Starting capital (default: $1M)
- `transaction_cost_pct`: Transaction costs as percentage (default: 0.1%)
- `min_spread_threshold`: Minimum spread to trade (default: 0.2%)

### AutomatedArbitrageStrategy
- `max_position_size`: Maximum notional per trade
- `auto_close_threshold`: Spread ratio threshold for closing (default: 0.5)

## Algorithm Optimization

### Speed Optimizations
- Efficient NAV calculation using vectorized operations
- Priority queue for opportunity ranking
- Batch price updates
- In-memory position tracking

### Risk Management
- Transaction cost modeling
- Minimum spread thresholds
- Capital limits per trade
- Automatic position closing

## Testing

Run comprehensive tests:
```bash
python test_etf_arbitrage.py
```

## Leaderboard Strategy

For competitive performance:
1. **Low latency**: Fast opportunity detection and execution
2. **Risk management**: Conservative position sizing, transaction cost awareness
3. **Capital efficiency**: Quick trade turnover when spreads narrow
4. **Multiple ETFs**: Diversification across different opportunities
5. **Parameter tuning**: Optimize thresholds based on market conditions

## Key Metrics for Competition
- **Total Return %**: Primary metric
- **Sharpe Ratio**: Risk-adjusted returns
- **Capital Efficiency**: Return per dollar deployed
- **Win Rate**: Percentage of profitable trades

## License

MIT License - Built for Citadel Engineering Challenge
