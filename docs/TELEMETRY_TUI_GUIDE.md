# Telemetry & Terminal UI Monitor

## Overview

The trading bot now includes comprehensive telemetry collection and a real-time Terminal UI (TUI) monitor built with Textualize.

## Features

### Telemetry System
- **Thread-safe metric collection** - Counters, gauges, histograms, and timers
- **Ring buffer storage** - Memory-efficient time-series data
- **Periodic persistence** - JSON export to disk
- **Multiple metric types**:
  - Counters: Monotonically increasing values (signal counts, cycle totals)
  - Gauges: Point-in-time values (active strategies, current status)
  - Histograms: Distribution tracking (cycle durations)
  - Timers: Duration measurements

### Terminal UI Monitor
- **Real-time dashboard** - Live updates every second
- **Bot status panel** - Uptime, cycle info, trading hours
- **System metrics** - CPU and memory usage
- **Strategy metrics** - Signal distribution with bar charts
- **Signal history** - Recent trading signals in table format
- **Live log viewer** - Scrollable log output
- **Export functionality** - Save telemetry data to JSON

## Installation

### Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `textual>=0.47.0` - Terminal UI framework
- `psutil>=5.9.0` - System metrics
- `humanize>=4.9.0` - Human-readable numbers

### Configuration

Edit `bot_config.json` to enable telemetry:

```json
{
  "telemetry": {
    "enabled": true,
    "collection_interval_seconds": 10,
    "persistence": {
      "enabled": true,
      "output_path": "telemetry_data/",
      "persist_interval_minutes": 5
    },
    "metrics": {
      "system_metrics_enabled": true,
      "api_latency_tracking": true,
      "signal_history_retention": 500
    }
  }
}
```

## Usage

### Running the Bot with Telemetry

```bash
# Start the unified bot (telemetry is automatically enabled)
python unified_bot.py
```

The bot will now collect telemetry data and persist it to `telemetry_data/` directory.

### Launching the TUI Monitor

In a separate terminal:

```bash
# Start the TUI monitor
python bot_monitor_tui.py
```

### TUI Keyboard Shortcuts

- `Q` or `Esc` - Quit the monitor
- `R` - Manual refresh
- `E` - Export telemetry data to JSON file
- `↑` `↓` - Scroll through tables and logs

## TUI Layout

```
┌────────────────────────────────────────────────────────────────┐
│  🤖 Unified Trading Bot Monitor                    [Q]uit     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ╭──────────────────── Bot Status ──────────────╮╭─ System ─╮│
│  │ Uptime: 2d 14h 35m                           ││ CPU: 15% ││
│  │ Next Cycle: 00:02:45                         ││ MEM: 245M││
│  │ Trading Hours: ✅ Active (06:00-19:00 UTC)   │╰──────────╯│
│  │ Active Strategies: 2/2                       │            │
│  │ Last Cycle: ✅ Success (12.3s)               │            │
│  ╰──────────────────────────────────────────────╯            │
│                                                                 │
│  ╭───────────────── Strategy Performance ──────────────────╮  │
│  │ Strategy: All Strategies 📊                             │  │
│  │                                                          │  │
│  │ Signals (Total: 60):                                    │  │
│  │   🟢 Long:   12  ████████░░░░  40.0%                    │  │
│  │   🔴 Short:   8  █████░░░░░░░  26.7%                    │  │
│  │   ⚪ None:   40  ████████████  33.3%                    │  │
│  ╰──────────────────────────────────────────────────────────╯  │
│                                                                 │
│  Recent Signals:                                                │
│  ┌──────┬────────┬──────┬─────────┬──────────┬──────────────┐│
│  │ Time │ Symbol │ Type │ Entry   │ Strategy │ Status       ││
│  ├──────┼────────┼──────┼─────────┼──────────┼──────────────┤│
│  │14:35 │ EURUSD │🟢LONG│ 1.0850  │mean_rev  │📱 Notified   ││
│  │14:30 │ GBPUSD │🔴SHRT│ 1.2650  │mean_rev  │📱 Notified   ││
│  │14:25 │ XAUUSD │🟢LONG│ 2045.30 │custom    │📱 Notified   ││
│  └──────┴────────┴──────┴─────────┴──────────┴──────────────┘│
│                                                                 │
│  ╭──────────────────────── Live Log ───────────────────────╮  │
│  │ [14:35:15] 🚀 STRATEGY CYCLE START                      │  │
│  │ [14:35:16] ✅ Capital.com connection verified           │  │
│  │ [14:35:17] 📊 Executing mean_reversion...               │  │
│  │ [14:35:18]   🔍 Analyzing EURUSD...                     │  │
│  │ [14:35:19]     🚨 SIGNAL: LONG at 1.0850                │  │
│  │ [14:35:20]     📱 Telegram signal sent to 3 chats       │  │
│  ╰──────────────────────────────────────────────────────────╯  │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│ F1:Help  R:Refresh  E:Export  Q:Quit                          │
└────────────────────────────────────────────────────────────────┘
```

## Telemetry API

### Collecting Metrics

```python
from src.bot.telemetry import TelemetryCollector

# Get collector instance (singleton)
telemetry = TelemetryCollector.instance()

# Increment counters
telemetry.increment("signals.long", strategy="mean_reversion")
telemetry.increment("signals.short", amount=2)

# Set gauges
telemetry.set_gauge("strategies.active", 2)
telemetry.set_gauge("bot.health_score", 95.5)

# Record timing
telemetry.record_timing("cycle.duration", 12.3)

# Record events
telemetry.record_event("cycle_start", {"timestamp": "2026-01-03T14:35:00Z"})

# Record signals
telemetry.record_signal({
    "strategy": "mean_reversion",
    "symbol": "EURUSD",
    "signal_type": "long",
    "entry_price": 1.0850
})

# Record errors
telemetry.record_error("api_connection", "Connection timeout", context={"retry": 3})
```

### Retrieving Data

```python
# Get recent signals
signals = telemetry.get_recent_signals(limit=50)

# Get recent cycles
cycles = telemetry.get_recent_cycles(limit=24)

# Get all metrics
metrics = telemetry.get_all_metrics()

# Get summary
summary = telemetry.get_summary()

# Export to JSON
telemetry.export_to_json("export.json")
```

## Docker Integration

The TUI can run alongside the bot in Docker:

### Option 1: Run TUI on Host

```bash
# Run bot in Docker
docker-compose up unified-bot

# Run TUI on host (connects to telemetry data via volume)
python bot_monitor_tui.py
```

### Option 2: Run TUI in Container (for remote servers)

Edit `docker-compose.yml`:

```yaml
services:
  unified-bot-monitor:
    build:
      context: .
      dockerfile: Dockerfile.bot
    container_name: mean-reversion-bot-monitor
    command: ["python", "bot_monitor_tui.py"]
    stdin_open: true
    tty: true
    volumes:
      - ./live_logs:/app/live_logs:ro
      - ./telemetry_data:/app/telemetry_data:ro
    depends_on:
      - unified-bot
```

Then run:
```bash
docker-compose up unified-bot unified-bot-monitor
docker attach mean-reversion-bot-monitor
```

## Troubleshooting

### TUI Not Showing Data

1. **Check if bot is running with telemetry enabled**:
   ```bash
   # Look for telemetry initialization message
   grep "Telemetry collector initialized" live_logs/*.log
   ```

2. **Check telemetry data directory**:
   ```bash
   ls -la telemetry_data/
   ```

3. **Verify bot_config.json**:
   ```json
   "telemetry": {
     "enabled": true,  // Must be true
     ...
   }
   ```

### High Memory Usage

Telemetry uses ring buffers with these default limits:
- Events: 1000 items
- Signals: 500 items
- Cycles: 100 items
- Errors: 200 items

These limits ensure bounded memory usage (~10-20 MB typical).

### TUI Performance Issues

If the TUI feels sluggish:

1. Increase refresh interval in `bot_monitor_tui.py`:
   ```python
   self.refresh_interval = 2  # seconds (default: 1)
   ```

2. Reduce signal history limit:
   ```python
   signals = telemetry.get_recent_signals(10)  # Show fewer signals
   ```

## Architecture

```
┌────────────────────────────────────────────┐
│         Unified Bot (unified_bot.py)       │
│  ┌──────────────────────────────────────┐  │
│  │      BotOrchestrator                 │  │
│  │  ┌────────────────────────────────┐  │  │
│  │  │  TelemetryCollector (Singleton)│  │  │
│  │  │  - In-memory ring buffers      │  │  │
│  │  │  - Thread-safe operations      │  │  │
│  │  │  - Periodic JSON persistence   │  │  │
│  │  └────────────────────────────────┘  │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
                    ↓
         ┌──────────────────────┐
         │  telemetry_data/     │
         │  - JSON files        │
         └──────────────────────┘
                    ↓
         ┌──────────────────────┐
         │  Bot Monitor TUI      │
         │  (bot_monitor_tui.py)│
         │  - Real-time display  │
         │  - Live updates       │
         └──────────────────────┘
```

## Performance Impact

Telemetry collection is designed to have minimal performance impact:

- **Overhead**: < 5% CPU and < 20 MB memory
- **Thread-safe**: Uses locks only during metric updates
- **Ring buffers**: Bounded memory usage
- **Async persistence**: Non-blocking file writes
- **Configurable**: Can be disabled via config

## Metrics Collected

### Bot Metrics
- `cycles.total` - Total cycles executed
- `cycles.skipped_outside_hours` - Cycles skipped (non-trading hours)
- `strategies.active` - Number of active strategies

### Signal Metrics
- `signals.long` - Long signals generated
- `signals.short` - Short signals generated
- `signals.none` - No signal outcomes
- `signals.errors` - Signal generation errors
- `signals.duplicate` - Duplicate signals prevented

### API Metrics
- `api.connection_success` - Successful API connections
- `api.connection_failed` - Failed API connections

### Timing Metrics
- `cycle.duration` - Full cycle duration (histogram)

### Error Tracking
- Error type, message, timestamp, and context for all failures

## Future Enhancements

Planned features for future versions:

1. **Historical Analysis** - Trend graphs and time-series visualization
2. **Alert System** - Configurable alerts for errors and thresholds
3. **Multiple Bot Support** - Monitor multiple bot instances
4. **Web Dashboard** - Browser-based alternative to TUI
5. **Prometheus Export** - Integration with monitoring tools
6. **Performance Profiling** - Detailed bottleneck analysis

## Support

For issues or questions:
1. Check the logs in `live_logs/`
2. Review telemetry data in `telemetry_data/`
3. Enable debug logging in bot_config.json

## License

Same as the main trading bot project.
