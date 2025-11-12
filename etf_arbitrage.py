"""
ETF Arbitrage Trading Algorithm
Citadel Engineering Challenge

This algorithm identifies and executes arbitrage opportunities between ETFs and their underlying equities.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
import heapq


class TradeType(Enum):
    """Type of arbitrage trade"""
    LONG_ETF_SHORT_BASKET = "LONG_ETF_SHORT_BASKET"  # ETF undervalued
    SHORT_ETF_LONG_BASKET = "SHORT_ETF_LONG_BASKET"  # ETF overvalued


@dataclass
class Equity:
    """Represents an equity security"""
    ticker: str
    price: float

    def __hash__(self):
        return hash(self.ticker)


@dataclass
class ETF:
    """Represents an ETF with its underlying basket"""
    ticker: str
    price: float
    holdings: Dict[str, float]  # ticker -> weight (as decimal, sum = 1.0)

    def calculate_nav(self, equity_prices: Dict[str, float]) -> float:
        """Calculate Net Asset Value from underlying equity prices"""
        nav = 0.0
        for ticker, weight in self.holdings.items():
            if ticker in equity_prices:
                nav += weight * equity_prices[ticker]
        return nav

    def get_arbitrage_opportunity(self, equity_prices: Dict[str, float],
                                  transaction_cost: float = 0.0) -> Optional[Tuple[TradeType, float]]:
        """
        Identify arbitrage opportunity and return (trade_type, profit_per_share)
        Returns None if no profitable opportunity exists
        """
        nav = self.calculate_nav(equity_prices)
        price_diff = self.price - nav

        # ETF trading above NAV -> Short ETF, Long Basket
        if price_diff > transaction_cost:
            return (TradeType.SHORT_ETF_LONG_BASKET, price_diff - transaction_cost)

        # ETF trading below NAV -> Long ETF, Short Basket
        elif price_diff < -transaction_cost:
            return (TradeType.LONG_ETF_SHORT_BASKET, -price_diff - transaction_cost)

        return None


@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity"""
    etf: ETF
    trade_type: TradeType
    profit_per_share: float
    nav: float
    spread_pct: float

    def __lt__(self, other):
        """For priority queue - higher profit has higher priority"""
        return self.profit_per_share > other.profit_per_share

    def __repr__(self):
        return (f"ArbitrageOpportunity({self.etf.ticker}, {self.trade_type.value}, "
                f"profit=${self.profit_per_share:.4f}, spread={self.spread_pct:.2%})")


@dataclass
class Position:
    """Represents a trading position"""
    ticker: str
    quantity: float  # positive for long, negative for short
    entry_price: float

    def calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL"""
        if self.quantity > 0:  # Long position
            return self.quantity * (current_price - self.entry_price)
        else:  # Short position
            return -self.quantity * (self.entry_price - current_price)


@dataclass
class Trade:
    """Represents an executed arbitrage trade"""
    etf_ticker: str
    trade_type: TradeType
    etf_quantity: float
    basket_positions: Dict[str, float]  # ticker -> quantity
    entry_nav: float
    entry_etf_price: float
    expected_profit: float

    def calculate_pnl(self, current_etf_price: float,
                     current_equity_prices: Dict[str, float]) -> float:
        """Calculate current PnL for this arbitrage trade"""
        pnl = 0.0

        if self.trade_type == TradeType.SHORT_ETF_LONG_BASKET:
            # Short ETF position
            pnl += self.etf_quantity * (self.entry_etf_price - current_etf_price)
            # Long basket positions
            for ticker, qty in self.basket_positions.items():
                if ticker in current_equity_prices:
                    entry_price = self.entry_nav * (qty / self.etf_quantity)
                    pnl += qty * (current_equity_prices[ticker] - entry_price)
        else:  # LONG_ETF_SHORT_BASKET
            # Long ETF position
            pnl += self.etf_quantity * (current_etf_price - self.entry_etf_price)
            # Short basket positions
            for ticker, qty in self.basket_positions.items():
                if ticker in current_equity_prices:
                    entry_price = self.entry_nav * (abs(qty) / self.etf_quantity)
                    pnl += abs(qty) * (entry_price - current_equity_prices[ticker])

        return pnl


class ETFArbitrageEngine:
    """Main ETF Arbitrage Trading Engine"""

    def __init__(self,
                 initial_capital: float = 1_000_000.0,
                 transaction_cost_pct: float = 0.001,  # 10 bps
                 min_spread_threshold: float = 0.002):  # 20 bps minimum spread
        """
        Initialize the arbitrage engine

        Args:
            initial_capital: Starting capital
            transaction_cost_pct: Transaction cost as percentage
            min_spread_threshold: Minimum spread to consider (as percentage)
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.transaction_cost_pct = transaction_cost_pct
        self.min_spread_threshold = min_spread_threshold

        self.etfs: Dict[str, ETF] = {}
        self.equity_prices: Dict[str, float] = {}
        self.active_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []
        self.total_pnl = 0.0

    def add_etf(self, etf: ETF):
        """Register an ETF for monitoring"""
        self.etfs[etf.ticker] = etf

    def update_equity_price(self, ticker: str, price: float):
        """Update equity price"""
        self.equity_prices[ticker] = price

    def update_etf_price(self, ticker: str, price: float):
        """Update ETF price"""
        if ticker in self.etfs:
            self.etfs[ticker].price = price

    def update_prices(self, prices: Dict[str, float]):
        """Batch update prices for both ETFs and equities"""
        for ticker, price in prices.items():
            if ticker in self.etfs:
                self.update_etf_price(ticker, price)
            else:
                self.update_equity_price(ticker, price)

    def scan_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Scan all ETFs for arbitrage opportunities
        Returns list of opportunities sorted by profit potential
        """
        opportunities = []

        for etf in self.etfs.values():
            nav = etf.calculate_nav(self.equity_prices)
            transaction_cost = (etf.price + nav) * self.transaction_cost_pct

            result = etf.get_arbitrage_opportunity(self.equity_prices, transaction_cost)

            if result:
                trade_type, profit = result
                spread_pct = abs(etf.price - nav) / nav

                # Only consider if spread exceeds minimum threshold
                if spread_pct >= self.min_spread_threshold:
                    opp = ArbitrageOpportunity(
                        etf=etf,
                        trade_type=trade_type,
                        profit_per_share=profit,
                        nav=nav,
                        spread_pct=spread_pct
                    )
                    opportunities.append(opp)

        # Sort by profit potential (descending)
        opportunities.sort(reverse=True)
        return opportunities

    def execute_arbitrage(self, opportunity: ArbitrageOpportunity,
                         notional: float) -> Optional[Trade]:
        """
        Execute an arbitrage trade

        Args:
            opportunity: The arbitrage opportunity to execute
            notional: Dollar amount to trade

        Returns:
            Trade object if executed, None if insufficient capital
        """
        etf = opportunity.etf

        # Check capital availability
        required_capital = notional * 2  # Need capital for both legs
        if required_capital > self.capital:
            return None

        # Calculate quantities
        etf_quantity = notional / etf.price

        # Build basket positions
        basket_positions = {}
        for ticker, weight in etf.holdings.items():
            if ticker in self.equity_prices:
                basket_value = notional * weight
                basket_qty = basket_value / self.equity_prices[ticker]

                # Sign depends on trade type
                if opportunity.trade_type == TradeType.SHORT_ETF_LONG_BASKET:
                    basket_positions[ticker] = basket_qty  # Long basket
                else:
                    basket_positions[ticker] = -basket_qty  # Short basket

        # Create trade
        trade = Trade(
            etf_ticker=etf.ticker,
            trade_type=opportunity.trade_type,
            etf_quantity=etf_quantity if opportunity.trade_type == TradeType.LONG_ETF_SHORT_BASKET
                        else -etf_quantity,
            basket_positions=basket_positions,
            entry_nav=opportunity.nav,
            entry_etf_price=etf.price,
            expected_profit=opportunity.profit_per_share * etf_quantity
        )

        # Update capital and positions
        self.capital -= required_capital
        self.active_trades.append(trade)

        return trade

    def close_trade(self, trade: Trade) -> float:
        """
        Close an arbitrage trade and realize PnL

        Returns:
            Realized PnL
        """
        if trade not in self.active_trades:
            return 0.0

        etf_price = self.etfs[trade.etf_ticker].price
        pnl = trade.calculate_pnl(etf_price, self.equity_prices)

        # Deduct transaction costs
        notional = abs(trade.etf_quantity) * etf_price
        transaction_cost = notional * 2 * self.transaction_cost_pct
        pnl -= transaction_cost

        # Update state
        self.active_trades.remove(trade)
        self.closed_trades.append(trade)
        self.total_pnl += pnl

        # Release capital
        self.capital += notional * 2 + pnl

        return pnl

    def close_all_trades(self) -> float:
        """Close all active trades and return total realized PnL"""
        total_pnl = 0.0
        trades_to_close = list(self.active_trades)  # Copy list

        for trade in trades_to_close:
            pnl = self.close_trade(trade)
            total_pnl += pnl

        return total_pnl

    def get_unrealized_pnl(self) -> float:
        """Calculate total unrealized PnL from active trades"""
        unrealized = 0.0

        for trade in self.active_trades:
            etf_price = self.etfs[trade.etf_ticker].price
            unrealized += trade.calculate_pnl(etf_price, self.equity_prices)

        return unrealized

    def get_total_value(self) -> float:
        """Get total portfolio value (capital + unrealized PnL + realized PnL)"""
        return self.capital + self.get_unrealized_pnl() + self.total_pnl

    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics"""
        total_value = self.get_total_value()

        return {
            'total_value': total_value,
            'capital': self.capital,
            'realized_pnl': self.total_pnl,
            'unrealized_pnl': self.get_unrealized_pnl(),
            'total_return': (total_value - self.initial_capital) / self.initial_capital,
            'total_return_pct': ((total_value - self.initial_capital) / self.initial_capital) * 100,
            'active_trades': len(self.active_trades),
            'closed_trades': len(self.closed_trades),
            'capital_utilization': (self.initial_capital - self.capital) / self.initial_capital
        }

    def print_status(self):
        """Print current engine status"""
        metrics = self.get_performance_metrics()

        print("=" * 70)
        print("ETF ARBITRAGE ENGINE STATUS")
        print("=" * 70)
        print(f"Total Value:        ${metrics['total_value']:,.2f}")
        print(f"Available Capital:  ${metrics['capital']:,.2f}")
        print(f"Realized PnL:       ${metrics['realized_pnl']:,.2f}")
        print(f"Unrealized PnL:     ${metrics['unrealized_pnl']:,.2f}")
        print(f"Total Return:       {metrics['total_return_pct']:.2f}%")
        print(f"Active Trades:      {metrics['active_trades']}")
        print(f"Closed Trades:      {metrics['closed_trades']}")
        print(f"Capital Util:       {metrics['capital_utilization']:.2%}")
        print("=" * 70)


class AutomatedArbitrageStrategy:
    """Automated strategy that continuously monitors and executes arbitrage"""

    def __init__(self,
                 engine: ETFArbitrageEngine,
                 max_position_size: float = 50_000,
                 auto_close_threshold: float = 0.5):  # Close when spread narrows to 50% of entry
        """
        Args:
            engine: The arbitrage engine
            max_position_size: Maximum notional per trade
            auto_close_threshold: Threshold ratio for auto-closing positions
        """
        self.engine = engine
        self.max_position_size = max_position_size
        self.auto_close_threshold = auto_close_threshold
        self.entry_spreads: Dict[int, float] = {}  # Use id(trade) as key

    def run_iteration(self) -> Dict[str, any]:
        """
        Run one iteration of the strategy
        Returns statistics about actions taken
        """
        stats = {
            'opportunities_found': 0,
            'trades_opened': 0,
            'trades_closed': 0,
            'pnl_realized': 0.0
        }

        # Check for closing opportunities first
        trades_to_close = []
        for trade in self.engine.active_trades:
            etf = self.engine.etfs[trade.etf_ticker]
            current_nav = etf.calculate_nav(self.engine.equity_prices)
            current_spread = abs(etf.price - current_nav) / current_nav

            entry_spread = self.entry_spreads.get(id(trade), float('inf'))

            # Close if spread has narrowed significantly
            if current_spread < entry_spread * self.auto_close_threshold:
                trades_to_close.append(trade)

        # Close trades
        for trade in trades_to_close:
            pnl = self.engine.close_trade(trade)
            stats['trades_closed'] += 1
            stats['pnl_realized'] += pnl
            trade_id = id(trade)
            if trade_id in self.entry_spreads:
                del self.entry_spreads[trade_id]

        # Scan for new opportunities
        opportunities = self.engine.scan_opportunities()
        stats['opportunities_found'] = len(opportunities)

        # Execute top opportunities
        for opp in opportunities[:3]:  # Top 3 opportunities
            if self.engine.capital < self.max_position_size * 2:
                break

            trade = self.engine.execute_arbitrage(opp, self.max_position_size)
            if trade:
                self.entry_spreads[id(trade)] = opp.spread_pct
                stats['trades_opened'] += 1

        return stats


def create_sample_etf(ticker: str, price: float, holdings: Dict[str, float]) -> ETF:
    """Helper function to create an ETF"""
    return ETF(ticker=ticker, price=price, holdings=holdings)
