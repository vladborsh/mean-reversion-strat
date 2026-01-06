#!/usr/bin/env python3
"""
Bot Monitor TUI (Terminal UI)

Real-time monitoring dashboard for the unified trading bot using Textualize.
Displays live metrics, signals, logs, and system status.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import psutil
import humanize
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, VerticalScroll
from textual.widget import Widget
from textual.widgets import Header, Footer, Static, DataTable, RichLog, TabbedContent, TabPane, Label
from textual.reactive import reactive
from textual import work
from textual.worker import Worker, WorkerState
from rich.text import Text

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.bot.telemetry import TelemetryFileReader

logger = logging.getLogger(__name__)


class BotStatusPanel(Widget):
    """Widget displaying bot status information"""
    
    DEFAULT_CSS = """
    BotStatusPanel {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    
    BotStatusPanel Static {
        margin: 0 1;
    }
    
    BotStatusPanel .status-label {
        color: $text-muted;
    }
    """
    
    uptime = reactive("")
    next_cycle = reactive("")
    trading_hours_status = reactive("⏸️  Inactive")
    active_strategies = reactive("0/0")
    last_cycle_status = reactive("⏳ Waiting...")
    last_cycle_duration = reactive("N/A")
    
    def compose(self) -> ComposeResult:
        yield Static("Bot Status", classes="status-label")
        yield Static(f"Uptime: {self.uptime}", id="uptime")
        yield Static(f"Next Cycle: {self.next_cycle}", id="next-cycle")
        yield Static(f"Trading Hours: {self.trading_hours_status}", id="trading-hours")
        yield Static(f"Active Strategies: {self.active_strategies}", id="active-strategies")
        yield Static(f"Last Cycle: {self.last_cycle_status}", id="last-cycle-status")
    
    def update_status(self, telemetry: TelemetryFileReader, bot_start_time: Optional[datetime] = None):
        """Update bot status from telemetry"""
        # Read state from file
        state = telemetry.read_state()
        
        # Calculate uptime from state if bot_start_time not provided
        if bot_start_time is None:
            bot_start_str = state.get('bot_start_time')
            if bot_start_str:
                try:
                    bot_start_time = datetime.fromisoformat(bot_start_str.replace('Z', '+00:00'))
                except:
                    bot_start_time = datetime.now(timezone.utc)
            else:
                bot_start_time = datetime.now(timezone.utc)
        
        uptime_delta = datetime.now(timezone.utc) - bot_start_time
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.uptime = f"{days}d {hours}h {minutes}m {seconds}s"
        
        # Get next cycle time and calculate countdown
        next_cycle_str = state.get('next_cycle_time')
        if next_cycle_str:
            try:
                next_cycle_time = datetime.fromisoformat(next_cycle_str.replace('Z', '+00:00'))
                time_until = next_cycle_time - datetime.now(timezone.utc)
                
                if time_until.total_seconds() > 0:
                    minutes_until = int(time_until.total_seconds() // 60)
                    seconds_until = int(time_until.total_seconds() % 60)
                    self.next_cycle = f"in {minutes_until}m {seconds_until}s"
                else:
                    self.next_cycle = "Running now..."
            except:
                self.next_cycle = "N/A"
        else:
            self.next_cycle = "N/A"
        
        # Get trading hours status
        trading_active = state.get('trading_hours_active', False)
        self.trading_hours_status = "✅ Active" if trading_active else "⏸️  Inactive"
        
        # Get active strategies
        active = telemetry.get_gauge('strategies.active')
        self.active_strategies = f"{int(active)}/{int(active)}"
        
        # Get last cycle info
        recent_cycles = telemetry.get_recent_cycles(1)
        if recent_cycles:
            cycle = recent_cycles[0]  # Most recent is first
            duration = cycle.get('duration', 0)
            self.last_cycle_duration = f"{duration:.1f}s"
            
            # Determine status based on signals
            signals = cycle.get('signals', {})
            if signals.get('error', 0) > 0:
                self.last_cycle_status = f"⚠️  Partial ({self.last_cycle_duration})"
            else:
                self.last_cycle_status = f"✅ Success ({self.last_cycle_duration})"
        
        # Update display
        self.query_one("#uptime", Static).update(f"Uptime: {self.uptime}")
        self.query_one("#next-cycle", Static).update(f"Next Cycle: {self.next_cycle}")
        self.query_one("#trading-hours", Static).update(f"Trading Hours: {self.trading_hours_status}")
        self.query_one("#active-strategies", Static).update(f"Active Strategies: {self.active_strategies}")
        self.query_one("#last-cycle-status", Static).update(f"Last Cycle: {self.last_cycle_status}")


class SystemMetricsPanel(Widget):
    """Widget displaying system metrics"""
    
    DEFAULT_CSS = """
    SystemMetricsPanel {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    
    SystemMetricsPanel Static {
        margin: 0 1;
    }
    
    SystemMetricsPanel .metrics-title {
        color: $text-muted;
    }
    """
    
    cpu_percent = reactive(0.0)
    memory_used = reactive("0 MB")
    memory_percent = reactive(0.0)
    
    def compose(self) -> ComposeResult:
        yield Static("System", classes="metrics-title")
        yield Static(f"CPU: {self.cpu_percent:.1f}%", id="cpu")
        yield Static(f"MEM: {self.memory_used}", id="memory")
        yield Static(f"     ({self.memory_percent:.1f}%)", id="memory-percent")
    
    def update_metrics(self):
        """Update system metrics"""
        try:
            # Get current process
            process = psutil.Process()
            
            # CPU usage
            self.cpu_percent = process.cpu_percent(interval=0.1)
            
            # Memory usage
            mem_info = process.memory_info()
            self.memory_used = humanize.naturalsize(mem_info.rss, binary=True)
            
            # System memory percent
            system_mem = psutil.virtual_memory()
            self.memory_percent = system_mem.percent
            
            # Update display
            self.query_one("#cpu", Static).update(f"CPU: {self.cpu_percent:.1f}%")
            self.query_one("#memory", Static).update(f"MEM: {self.memory_used}")
            self.query_one("#memory-percent", Static).update(f"     ({self.memory_percent:.1f}%)")
        
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")


class SignalHistoryTable(Widget):
    """Widget displaying recent trading signals"""
    
    DEFAULT_CSS = """
    SignalHistoryTable {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    
    SignalHistoryTable .section-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    
    SignalHistoryTable VerticalScroll {
        height: 15;
    }
    
    SignalHistoryTable DataTable {
        height: auto;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("Recent Signals:", classes="section-title")
        with VerticalScroll():
            yield DataTable(id="signals-table")
    
    def on_mount(self) -> None:
        """Initialize the data table"""
        table = self.query_one("#signals-table", DataTable)
        table.add_columns("Time", "Symbol", "Type", "Entry", "Strategy", "Status")
        table.cursor_type = "row"
    
    def update_signals(self, telemetry: TelemetryFileReader):
        """Update signal history"""
        table = self.query_one("#signals-table", DataTable)
        table.clear()
        
        # Signals are already in reverse chronological order (newest first) from file reader
        signals = telemetry.get_recent_signals(20)
        for signal in signals:  # Already sorted newest first
            try:
                timestamp = signal.get('timestamp', '')
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                else:
                    time_str = timestamp.strftime('%H:%M:%S') if hasattr(timestamp, 'strftime') else 'N/A'
                
                symbol = signal.get('symbol', 'N/A')
                signal_type = signal.get('signal_type', 'N/A').upper()
                entry_price = signal.get('entry_price', 0)
                strategy = signal.get('strategy', 'N/A')
                
                # Format type with color
                if signal_type == 'LONG':
                    type_display = "🟢 LONG"
                elif signal_type == 'SHORT':
                    type_display = "🔴 SHORT"
                else:
                    type_display = signal_type
                
                status = "📱 Notified"
                
                table.add_row(
                    time_str,
                    symbol,
                    type_display,
                    f"{entry_price:.4f}" if isinstance(entry_price, (int, float)) else str(entry_price),
                    strategy,
                    status
                )
            except Exception as e:
                logger.error(f"Error adding signal row: {e}")


class LiveLogViewer(Widget):
    """Widget for displaying live log output"""
    
    DEFAULT_CSS = """
    LiveLogViewer {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    
    LiveLogViewer .log-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    
    LiveLogViewer VerticalScroll {
        height: 12;
        border: none;
    }
    
    LiveLogViewer RichLog {
        height: auto;
        background: $surface;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("Live Log", classes="log-title")
        with VerticalScroll():
            yield RichLog(id="live-log", wrap=True, highlight=True, markup=True)
    
    def on_mount(self) -> None:
        """Initialize log viewer"""
        log = self.query_one("#live-log", RichLog)
        log.write("Bot Monitor TUI initialized")
        log.write("Connecting to telemetry collector...")
    
    def add_log(self, message: str, level: str = "INFO"):
        """Add a log message"""
        log = self.query_one("#live-log", RichLog)
        
        timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        # Color code by level
        if level == "ERROR":
            prefix = f"[red][{timestamp}] ❌"
        elif level == "WARNING":
            prefix = f"[yellow][{timestamp}] ⚠️ "
        elif level == "SUCCESS":
            prefix = f"[green][{timestamp}] ✅"
        else:
            prefix = f"[cyan][{timestamp}]"
        
        log.write(f"{prefix} {message}")


class StrategyMetricsPanel(Widget):
    """Panel showing strategy-specific metrics"""
    
    DEFAULT_CSS = """
    StrategyMetricsPanel {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    
    StrategyMetricsPanel .strategy-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    
    StrategyMetricsPanel Static {
        margin: 0 1;
    }
    
    StrategyMetricsPanel VerticalScroll {
        height: 8;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("Strategy Performance 📊", classes="strategy-title")
        with VerticalScroll():
            yield Static("Strategy: All Strategies", id="strategy-header")
            yield Static("", id="strategy-status")
            yield Static("", id="signal-summary")
    
    def update_metrics(self, telemetry: TelemetryFileReader):
        """Update strategy metrics"""
        # Get signal counts
        long_signals = telemetry.get_counter('signals.long')
        short_signals = telemetry.get_counter('signals.short')
        no_signals = telemetry.get_counter('signals.none')
        
        total = long_signals + short_signals + no_signals
        
        if total > 0:
            long_pct = (long_signals / total) * 100
            short_pct = (short_signals / total) * 100
            no_signal_pct = (no_signals / total) * 100
            
            # Create bar visualization
            bar_length = 20
            long_bar = '█' * int(long_pct * bar_length / 100)
            short_bar = '█' * int(short_pct * bar_length / 100)
            no_signal_bar = '█' * int(no_signal_pct * bar_length / 100)
            
            summary = f"""
Signals (Total: {int(total)}):
  🟢 Long:  {int(long_signals):3d}  {long_bar:<{bar_length}} {long_pct:.1f}%
  🔴 Short: {int(short_signals):3d}  {short_bar:<{bar_length}} {short_pct:.1f}%
  ⚪ None:  {int(no_signals):3d}  {no_signal_bar:<{bar_length}} {no_signal_pct:.1f}%
"""
        else:
            summary = "\nNo signals generated yet..."
        
        # Update display
        self.query_one("#signal-summary", Static).update(summary)


class BotMonitorApp(App):
    """Main Bot Monitor TUI Application"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    Horizontal {
        height: auto;
        margin: 1 2;
    }
    
    Vertical {
        height: auto;
        margin: 0;
    }
    
    #bot-status-container {
        width: 2fr;
    }
    
    #system-metrics-container {
        width: 1fr;
    }
    
    #strategy-metrics-container {
        margin: 1 2;
        height: auto;
    }
    
    #signals-table-container {
        margin: 1 2;
        height: auto;
    }
    
    #live-log-container {
        margin: 1 2;
        height: auto;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("e", "export", "Export Data"),
    ]
    
    TITLE = "🤖 Unified Trading Bot Monitor"
    SUB_TITLE = "Real-time Telemetry Dashboard"
    
    def __init__(self):
        super().__init__()
        self.telemetry = TelemetryFileReader('telemetry_data')
        self.bot_start_time = datetime.now(timezone.utc)
        self.refresh_interval = 1  # seconds
    
    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header()
        
        with Horizontal():
            with Vertical(id="bot-status-container"):
                yield BotStatusPanel(id="bot-status")
            with Vertical(id="system-metrics-container"):
                yield SystemMetricsPanel(id="system-metrics")
        
        with Vertical(id="strategy-metrics-container"):
            yield StrategyMetricsPanel(id="strategy-metrics")
        
        with Vertical(id="signals-table-container"):
            yield SignalHistoryTable(id="signal-history")
        
        with Vertical(id="live-log-container"):
            yield LiveLogViewer(id="live-log")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Start background update task"""
        self.set_interval(self.refresh_interval, self.update_dashboard)
        
        # Initial log message
        log_viewer = self.query_one("#live-log", LiveLogViewer)
        log_viewer.add_log("Connected to telemetry collector", "SUCCESS")
        log_viewer.add_log(f"Refresh interval: {self.refresh_interval}s", "INFO")
    
    def update_dashboard(self) -> None:
        """Update all dashboard components"""
        try:
            # Check if telemetry has updates before refreshing
            if not self.telemetry.has_updates():
                return  # Skip update if no new data
            
            # Update bot status
            bot_status = self.query_one("#bot-status", BotStatusPanel)
            bot_status.update_status(self.telemetry, None)  # None = read from state file
            
            # Update system metrics
            system_metrics = self.query_one("#system-metrics", SystemMetricsPanel)
            system_metrics.update_metrics()
            
            # Update strategy metrics
            strategy_metrics = self.query_one("#strategy-metrics", StrategyMetricsPanel)
            strategy_metrics.update_metrics(self.telemetry)
            
            # Update signal history
            signal_history = self.query_one("#signal-history", SignalHistoryTable)
            signal_history.update_signals(self.telemetry)
            
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            log_viewer = self.query_one("#live-log", LiveLogViewer)
            log_viewer.add_log(f"Update error: {e}", "ERROR")
    
    def action_refresh(self) -> None:
        """Manual refresh action"""
        self.update_dashboard()
        log_viewer = self.query_one("#live-log", LiveLogViewer)
        log_viewer.add_log("Dashboard manually refreshed", "SUCCESS")
    
    def action_export(self) -> None:
        """Export telemetry data"""
        try:
            import json
            import shutil
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            export_dir = Path(f"telemetry_export_{timestamp}")
            
            # Copy entire telemetry directory
            telemetry_path = Path('telemetry_data')
            if telemetry_path.exists():
                shutil.copytree(telemetry_path, export_dir)
                log_viewer = self.query_one("#live-log", LiveLogViewer)
                log_viewer.add_log(f"Data exported to {export_dir}/", "SUCCESS")
            else:
                log_viewer = self.query_one("#live-log", LiveLogViewer)
                log_viewer.add_log("No telemetry data found", "ERROR")
        except Exception as e:
            log_viewer = self.query_one("#live-log", LiveLogViewer)
            log_viewer.add_log(f"Export failed: {e}", "ERROR")


def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check if telemetry data directory exists
    telemetry_path = Path("telemetry_data")
    if not telemetry_path.exists():
        print("⚠️  Warning: telemetry_data directory not found.")
        print("   Make sure the unified bot is running with telemetry enabled.")
        print("")
    
    # Run the TUI app
    app = BotMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
