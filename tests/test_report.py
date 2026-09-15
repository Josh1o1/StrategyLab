import unittest
from datetime import datetime, timedelta

from analysis.report import ResearchReport
from engine.backtest import BacktestResult, EquityPoint, Trade
from research.returns import PeriodicMetricConfig
from research.statistics import sharpe_ratio, sortino_ratio


class TestResearchReport(unittest.TestCase):
    def make_result(self):
        start = datetime(2026, 1, 1)

        trades = [
            Trade(
                direction="long",
                entry_time=start,
                entry_price=100.0,
                exit_time=start + timedelta(days=1),
                exit_price=104.0,
                size=1.0,
                pnl=4.0,
                exit_reason="target",
                initial_risk=2.0,
            ),
            Trade(
                direction="long",
                entry_time=start + timedelta(days=2),
                entry_price=100.0,
                exit_time=start + timedelta(days=3),
                exit_price=98.0,
                size=1.0,
                pnl=-2.0,
                exit_reason="stop",
                initial_risk=2.0,
            ),
            Trade(
                direction="long",
                entry_time=start + timedelta(days=4),
                entry_price=100.0,
                exit_time=start + timedelta(days=5),
                exit_price=102.0,
                size=1.0,
                pnl=2.0,
                exit_reason="target",
                initial_risk=2.0,
            ),
        ]

        curve = [
            EquityPoint(
                time=trades[0].exit_time,
                equity=10004.0,
                trade_pnl=4.0,
                cumulative_pnl=4.0,
            ),
            EquityPoint(
                time=trades[1].exit_time,
                equity=10002.0,
                trade_pnl=-2.0,
                cumulative_pnl=2.0,
            ),
            EquityPoint(
                time=trades[2].exit_time,
                equity=10004.0,
                trade_pnl=2.0,
                cumulative_pnl=4.0,
            ),
        ]

        return BacktestResult(
            starting_equity=10000.0,
            ending_equity=10004.0,
            trades=trades,
            equity_curve=curve,
        )

    def test_report_from_backtest(self):
        report = ResearchReport.from_backtest(
            self.make_result()
        )

        self.assertEqual(report.trade_count, 3)
        self.assertAlmostEqual(report.net_pnl, 4.0)
        self.assertAlmostEqual(report.return_pct, 0.04)

    def test_report_win_rate(self):
        report = ResearchReport.from_backtest(
            self.make_result()
        )

        self.assertAlmostEqual(
            report.win_rate,
            2 / 3,
        )

    def test_report_profit_factor(self):
        report = ResearchReport.from_backtest(
            self.make_result()
        )

        self.assertAlmostEqual(
            report.profit_factor,
            3.0,
        )

    def test_report_average_r(self):
        report = ResearchReport.from_backtest(
            self.make_result()
        )

        # R values: +2, -1, +1
        self.assertAlmostEqual(
            report.average_r,
            2 / 3,
        )

    def test_report_drawdown(self):
        report = ResearchReport.from_backtest(
            self.make_result()
        )

        self.assertAlmostEqual(
            report.max_drawdown,
            2.0,
        )

    def test_ci_fields_exist(self):
        report = ResearchReport.from_backtest(
            self.make_result()
        )

        self.assertLessEqual(
            report.mean_r_ci_lower,
            report.mean_r_ci_upper,
        )


if __name__ == "__main__":
    unittest.main()


class TestResearchReportRiskMetrics(unittest.TestCase):

    def make_hourly_result(self):
        start = datetime(2026, 1, 1)

        points = [
            EquityPoint(
                time=start + timedelta(hours=i),
                equity=equity,
                trade_pnl=0.0,
                cumulative_pnl=equity - 10000.0,
                mark_to_market_equity=equity,
            )
            for i, equity in enumerate(
                [10000.0, 10100.0, 10050.0, 10200.0, 10150.0]
            )
        ]

        return BacktestResult(
            starting_equity=10000.0,
            ending_equity=10150.0,
            trades=[],
            equity_curve=points,
        )

    def test_sharpe_uses_mtm_time_series(self):
        result = self.make_hourly_result()

        report = ResearchReport.from_backtest(
            result,
            interval_seconds=3600,
        )

        expected = __import__(
            "research.returns",
            fromlist=["periodic_sharpe"],
        ).periodic_sharpe(
            result.equity_curve,
            3600,
        )

        self.assertAlmostEqual(
            report.sharpe,
            expected,
        )

    def test_sortino_uses_mtm_time_series(self):
        result = self.make_hourly_result()

        report = ResearchReport.from_backtest(
            result,
            interval_seconds=3600,
        )

        expected = __import__(
            "research.returns",
            fromlist=["periodic_sortino"],
        ).periodic_sortino(
            result.equity_curve,
            3600,
        )

        self.assertAlmostEqual(
            report.sortino,
            expected,
        )

    def test_periodic_config_gap_tolerance_is_forwarded(self):
        from unittest.mock import patch

        result = self.make_hourly_result()
        config = PeriodicMetricConfig(
            interval_seconds=3600,
            gap_tolerance=2.5,
        )

        with patch(
            "analysis.report.periodic_sharpe",
            return_value=1.23,
        ) as mock_sharpe, patch(
            "analysis.report.periodic_sortino",
            return_value=0.45,
        ) as mock_sortino:
            report = ResearchReport.from_backtest(
                result,
                periodic_config=config,
            )

        self.assertAlmostEqual(report.sharpe, 1.23)
        self.assertAlmostEqual(report.sortino, 0.45)

        mock_sharpe.assert_called_once()
        self.assertEqual(mock_sharpe.call_args.args[1], 3600)
        self.assertEqual(
            mock_sharpe.call_args.kwargs["gap_tolerance"],
            2.5,
        )

        mock_sortino.assert_called_once()
        self.assertEqual(mock_sortino.call_args.args[1], 3600)
        self.assertEqual(
            mock_sortino.call_args.kwargs["gap_tolerance"],
            2.5,
        )

    def test_trade_level_metrics_are_preserved_separately(self):
        start = datetime(2026, 1, 1)

        trades = [
            Trade(
                direction="long",
                entry_time=start,
                entry_price=100.0,
                exit_time=start + timedelta(hours=1),
                exit_price=104.0,
                size=1.0,
                pnl=4.0,
                exit_reason="target",
                initial_risk=2.0,
            ),
            Trade(
                direction="long",
                entry_time=start + timedelta(hours=2),
                entry_price=100.0,
                exit_time=start + timedelta(hours=3),
                exit_price=98.0,
                size=1.0,
                pnl=-2.0,
                exit_reason="stop",
                initial_risk=2.0,
            ),
            Trade(
                direction="long",
                entry_time=start + timedelta(hours=4),
                entry_price=100.0,
                exit_time=start + timedelta(hours=5),
                exit_price=102.0,
                size=1.0,
                pnl=2.0,
                exit_reason="target",
                initial_risk=2.0,
            ),
        ]

        points = [
            EquityPoint(
                time=start + timedelta(hours=i),
                equity=equity,
                trade_pnl=0.0,
                cumulative_pnl=equity - 10000.0,
                mark_to_market_equity=equity,
            )
            for i, equity in enumerate(
                [10000.0, 10001.0, 10000.5, 10002.0, 10001.5, 10002.0]
            )
        ]

        result = BacktestResult(
            starting_equity=10000.0,
            ending_equity=10002.0,
            trades=trades,
            equity_curve=points,
        )

        report = ResearchReport.from_backtest(
            result,
            interval_seconds=3600,
        )

        r_values = [2.0, -1.0, 1.0]

        self.assertAlmostEqual(
            report.trade_sharpe,
            sharpe_ratio(r_values),
        )

        self.assertAlmostEqual(
            report.trade_sortino,
            sortino_ratio(r_values),
        )

        self.assertNotEqual(
            report.sharpe,
            report.trade_sharpe,
        )

    def test_irregular_curve_does_not_produce_time_series_metrics(self):
        start = datetime(2026, 1, 1)

        points = [
            EquityPoint(
                time=start + timedelta(hours=i),
                equity=equity,
                trade_pnl=0.0,
                cumulative_pnl=equity - 10000.0,
                mark_to_market_equity=equity,
            )
            for i, equity in [
                (0, 10000.0),
                (1, 10100.0),
                (5, 10200.0),
                (6, 10150.0),
            ]
        ]

        result = BacktestResult(
            starting_equity=10000.0,
            ending_equity=10150.0,
            trades=[],
            equity_curve=points,
        )

        report = ResearchReport.from_backtest(
            result,
            interval_seconds=3600,
        )

        self.assertEqual(report.sharpe, 0.0)
        self.assertEqual(report.sortino, 0.0)


if __name__ == "__main__":
    unittest.main()
