# Telemetry & Terminal UI Monitor

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Session vs Lifetime Metrics](#session-vs-lifetime-metrics)
6. [Usage](#usage)
7. [TUI Layout](#tui-layout)
8. [Telemetry File Structure](#telemetry-file-structure)
9. [Telemetry API](#telemetry-api)
10. [Architecture](#architecture)
    - [Component Details](#component-details)
    - [Inter-Process Communication](#inter-process-communication-pattern)
    - [Data Flow Example](#data-flow-example)
    - [Thread Safety & Consistency](#thread-safety--consistency)
    - [Performance Characteristics](#performance-characteristics)
11. [Docker Integration](#docker-integration)
12. [Troubleshooting](#troubleshooting)
13. [Performance Impact](#performance-impact)
14. [Metrics Collected](#metrics-collected)
15. [Future Enhancements](#future-enhancements)
16. [Quick Reference](#quick-reference)
17. [Support](#support)

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

### Configuration

Edit `bot_config.json` to enable telemetry:

```json
{
  "telemetry": {
    "enabled": true,
    "reset_on_startup": true,
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
    },
    "description": "reset_on_startup: true = counters reset to 0 on each bot start (recommended)"
  }
}
```

### Session vs Lifetime Metrics

The `reset_on_startup` configuration option controls whether metrics persist across bot restarts:

**Recommended: `"reset_on_startup": true`** (Session Metrics)
- Counters reset to 0 every time the bot starts
- Shows clean metrics for current session only
- Easier to track "today's performance"
- Prevents accumulation of old test data
- **Use case**: Production trading, daily monitoring

```json
"telemetry": {
  "reset_on_startup": true  // ← Recommended
}
```

**Alternative: `"reset_on_startup": false`** (Lifetime Metrics)
- Counters persist across bot restarts
- Accumulates historical totals
- Shows "all-time" signal counts
- Useful for long-term statistics
- **Use case**: Research, backtesting, historical analysis

```json
"telemetry": {
  "reset_on_startup": false  // Cumulative totals
}
```

**Example Behavior**:
```
Day 1: Bot runs, generates 10 signals, stops
Day 2 with reset_on_startup: true  → Shows "0 signals" initially
Day 2 with reset_on_startup: false → Shows "10 signals" from yesterday
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
│  ╭──────────────────────── Bot Status ────────────────────────╮│
│  │ Uptime: 2d 14h 35m                                         ││
│  │ Next Cycle: 00:02:45                                       ││
│  │ Trading Hours: ✅ Active (06:00-19:00 UTC)                 ││
│  │ Active Strategies: 2/2                                     ││
│  │ Last Cycle: ✅ Success (12.3s)                             ││
│  ╰────────────────────────────────────────────────────────────╯│
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

## Telemetry File Structure

The telemetry system creates a structured directory with JSON files for inter-process communication:

```
telemetry_data/
├── metrics.json          # Current counters, gauges, histograms, timers
├── state.json           # Bot state: next_cycle_time, bot_start_time, etc.
├── manifest.json        # File index with modification times (for change detection)
├── signals/             # Individual timestamped signal files
│   ├── signal_20260107_143520_001.json
│   ├── signal_20260107_143525_002.json
│   └── ... (max 500 files, oldest compressed to .gz)
├── cycles/              # Cycle completion records
│   ├── cycle_20260107_143530_001.json
│   └── ... (max 100 files)
└── errors/              # Error logs
    ├── error_20260107_144032_001.json
    └── ... (max 200 files)
```

### File Formats

**metrics.json** (Updated on every metric change):
```json
{
  "timestamp": "2026-01-07T14:35:20.000000+00:00",
  "counters": {
    "signals.long": {
      "name": "signals.long",
      "type": "counter",
      "value": 12.0,
      "timestamp": "2026-01-07T14:35:20+00:00",
      "tags": {}
    }
  },
  "gauges": {
    "strategies.active": {
      "name": "strategies.active",
      "type": "gauge",
      "value": 2,
      "timestamp": "2026-01-07T14:35:20+00:00",
      "tags": {}
    }
  },
  "histograms": {},
  "timers": {}
}
```

**state.json** (Updated on state changes):
```json
{
  "timestamp": "2026-01-07T14:35:20.000000+00:00",
  "bot_start_time": "2026-01-07T14:30:00.000000+00:00",
  "next_cycle_time": "2026-01-07T14:40:15+00:00",
  "last_cycle_time": "2026-01-07T14:35:15+00:00",
  "is_running": true,
  "trading_hours_active": true,
  "run_interval_minutes": 5,
  "sync_second": 15
}
```

**manifest.json** (Index for change detection):
```json
{
  "last_updated": "2026-01-07T14:35:20.000000+00:00",
  "metrics_mtime": 1736258120.123456,
  "state_mtime": 1736258120.234567,
  "signal_count": 12,
  "cycle_count": 3,
  "error_count": 0,
  "latest_signals": [
    "signals/signal_20260107_143520_012.json"
  ],
  "latest_cycles": [
    "cycles/cycle_20260107_143515_003.json"
  ],
  "latest_errors": []
}
```

**signal file** (Individual signal records):
```json
{
  "timestamp": "2026-01-07T14:35:20.123456+00:00",
  "signal_type": "long",
  "symbol": "EURUSD",
  "price": 1.0850,
  "strategy": "mean_reversion",
  "indicators": {
    "rsi": 28.5,
    "bb_position": -1.8
  }
}
```

### File Rotation & Cleanup

- **Automatic rotation**: When retention limits reached, oldest files deleted
- **Compression**: Rotated files automatically compressed to `.gz` format
- **Retention limits**: Configurable in `bot_config.json`
  - Signals: 500 files (default)
  - Cycles: 100 files (default)
  - Errors: 200 files (default)
- **Disk usage**: Typically 5-50 MB depending on signal frequency

### Atomic File Writes

All file writes use atomic operations to prevent partial reads:

1. Write data to temporary file (e.g., `metrics.json.tmp`)
2. Sync to disk with `fsync()` to ensure durability
3. Atomic rename using `os.replace()` (POSIX compliant)
4. Update manifest with new modification time

This ensures TUI never reads corrupted or partial data.

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

### Overview

The telemetry system uses a **file-based inter-process communication (IPC)** architecture to enable real-time monitoring of the trading bot through a separate TUI process. This design allows the bot and monitor to run independently while sharing live data.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Trading Bot Process                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              BotOrchestrator                          │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │       TelemetryCollector (Singleton)            │  │  │
│  │  │                                                   │  │  │
│  │  │  In-Memory Storage (Fast Access):                │  │  │
│  │  │  • Ring buffers (events, signals, cycles)        │  │  │
│  │  │  • Metrics (counters, gauges, histograms)        │  │  │
│  │  │  • Bot state (timings, status)                   │  │  │
│  │  │                                                   │  │  │
│  │  │  File-Based Persistence (IPC):                   │  │  │
│  │  │  • Atomic writes on every update                 │  │  │
│  │  │  • Thread-safe operations                        │  │  │
│  │  │  • Structured JSON format                        │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓ (writes)
            ┌───────────────────────────────────┐
            │       Filesystem (IPC Layer)      │
            │                                   │
            │  telemetry_data/                  │
            │  ├── metrics.json                 │ ← Aggregated counters/gauges
            │  ├── state.json                   │ ← Bot state & timing
            │  ├── manifest.json                │ ← File index & mtimes
            │  ├── signals/                     │ ← Individual signal files
            │  │   └── signal_*.json            │
            │  ├── cycles/                      │ ← Cycle completion records
            │  │   └── cycle_*.json             │
            │  └── errors/                      │ ← Error logs
            │      └── error_*.json             │
            └───────────────────────────────────┘
                            ↑ (reads)
┌─────────────────────────────────────────────────────────────┐
│                    TUI Monitor Process                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           bot_monitor_tui.py                          │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │       TelemetryFileReader                       │  │  │
│  │  │                                                   │  │  │
│  │  │  Read-Only Access:                               │  │  │
│  │  │  • Monitors manifest.json for changes            │  │  │
│  │  │  • Caches data with modification time tracking   │  │  │
│  │  │  • Only refreshes when files change              │  │  │
│  │  │  • Handles compressed (.gz) files                │  │  │
│  │  │                                                   │  │  │
│  │  │  UI Components:                                  │  │  │
│  │  │  • BotStatusPanel (uptime, next cycle)          │  │  │
│  │  │  • SystemMetricsPanel (CPU, memory)             │  │  │
│  │  │  • StrategyMetricsPanel (signal charts)         │  │  │
│  │  │  • SignalHistoryTable (recent signals)          │  │  │
│  │  │  • LogViewer (live log tail)                    │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. TelemetryCollector (Write Side)

**Location**: `src/bot/telemetry/collector.py`

The collector is a singleton that runs in the bot process and handles:

- **In-Memory Storage**: Fast ring buffers for events, signals, cycles, and errors
- **Metric Collection**: Thread-safe counters, gauges, histograms, and timers
- **File Writing**: Atomic writes to telemetry files on every update
- **File Rotation**: Automatic cleanup of old files with compression

**Key Methods**:
```python
# Metric collection
increment(name, amount, tags)       # Increment counters
set_gauge(name, value, tags)        # Set point-in-time values
record_timing(name, duration)       # Track durations

# Event recording
record_signal(signal_data)          # Record trading signal
record_cycle(cycle_data)            # Record cycle completion
record_error(error_type, message)   # Record errors

# Bot state management
set_bot_state(...)                  # Initialize bot state with reset option
set_next_cycle_time(timestamp)      # Update next cycle timing
set_trading_hours_active(bool)      # Update trading status
```

**File Writing Strategy**:
- **Atomic writes**: Uses temp file + `os.replace()` to prevent partial reads
- **Immediate persistence**: Every metric update triggers file write
- **Thread-safe**: All operations protected by locks
- **Structured format**: Consistent JSON schema across all files

#### 2. TelemetryFileReader (Read Side)

**Location**: `src/bot/telemetry/file_reader.py`

The reader is a read-only interface for the TUI that handles:

- **Change Detection**: Monitors `manifest.json` modification time
- **Lazy Loading**: Only reads files when changes detected
- **Caching**: Stores last-read data and timestamps
- **Compression Support**: Reads both regular and gzip-compressed files

**Key Methods**:
```python
read_metrics()      # Get current counters/gauges/histograms/timers
read_state()        # Get bot state (timings, status)
read_signals()      # Get recent signal files
read_cycles()       # Get recent cycle files
read_errors()       # Get recent error files
has_updates()       # Check if any files changed
```

**Optimization Features**:
- Uses manifest file as single point of change detection
- Caches file contents with modification timestamps
- Only re-reads files that have actually changed
- Handles missing files gracefully

#### 3. File Structure

**Core Files** (always present):

| File | Purpose | Update Frequency | Size |
|------|---------|------------------|------|
| `metrics.json` | Current metric values | Every metric update | ~5-10 KB |
| `state.json` | Bot state & timing | Every state change | ~500 bytes |
| `manifest.json` | File index & mtimes | Every file write | ~1-5 KB |

**Event Files** (timestamped):

| Directory | File Pattern | Retention | Purpose |
|-----------|--------------|-----------|---------|
| `signals/` | `signal_YYYYMMDD_HHMMSS_###.json` | 500 files | Individual signal records |
| `cycles/` | `cycle_YYYYMMDD_HHMMSS_###.json` | 100 files | Cycle completion records |
| `errors/` | `error_YYYYMMDD_HHMMSS_###.json` | 200 files | Error logs |

**File Rotation**:
- Old files automatically compressed to `.gz` format
- Oldest files deleted when retention limit reached
- Manifest updated after each rotation

#### 4. Inter-Process Communication Pattern

**Write Path** (Bot → Filesystem):
```
Metric Update
    ↓
TelemetryCollector._write_metrics()
    ↓
file_utils.atomic_write_json()
    ↓
1. Write to temp file
2. Sync to disk (fsync)
3. Atomic rename (os.replace)
4. Update manifest
```

**Read Path** (Filesystem → TUI):
```
TUI Refresh Timer (1 second)
    ↓
TelemetryFileReader.has_updates()
    ↓
Check manifest.json mtime
    ↓
If changed:
  1. Read manifest.json
  2. Check individual file mtimes
  3. Read only changed files
  4. Update cache
  5. Return new data
```

### Data Flow Example

**Scenario**: Bot generates a LONG signal for EURUSD

1. **Bot Process**:
   ```python
   # Orchestrator records signal
   telemetry.record_signal({
       'signal_type': 'long',
       'symbol': 'EURUSD',
       'price': 1.0850,
       'strategy': 'mean_reversion'
   })
   
   # Orchestrator increments counter
   telemetry.increment('signals.long', amount=1)
   ```

2. **TelemetryCollector** (writes):
   ```python
   # Write signal file
   → signals/signal_20260107_143520_001.json
   
   # Update metrics
   → metrics.json (signals.long: 12 → 13)
   
   # Update manifest
   → manifest.json (add signal file, update mtimes)
   ```

3. **Filesystem** (atomic operations):
   ```
   → Create temp file with new data
   → fsync() to ensure disk write
   → os.replace() for atomic rename
   → File immediately available to readers
   ```

4. **TelemetryFileReader** (reads):
   ```python
   # TUI refresh timer fires
   has_updates() → checks manifest.json mtime → CHANGED
   
   # Reload data
   read_metrics() → load updated metrics.json
   read_signals() → load new signal file
   
   # Update cache
   → Store new data with current mtimes
   ```

5. **TUI Display** (renders):
   ```
   → Update signal counter: 12 → 13
   → Add new row to signal history table
   → Update bar chart percentages
   → Refresh display
   ```

### Thread Safety & Consistency

**Bot Side (TelemetryCollector)**:
- All methods protected by `threading.Lock`
- In-memory updates happen first, then file writes
- File write failures don't affect in-memory state
- Retries on transient errors

**Filesystem**:
- Atomic writes prevent partial reads
- No file locking needed (writer owns files)
- Readers never block writers
- Safe for multiple simultaneous reads

**TUI Side (TelemetryFileReader)**:
- Read-only access, no locks needed
- Tolerates missing/incomplete files
- Handles both regular and compressed files
- Caching prevents excessive disk I/O

### Performance Characteristics

**Write Performance** (Bot):
- **Latency**: ~1-2ms per metric update (includes file write)
- **Throughput**: ~500-1000 updates/second
- **Overhead**: <5% CPU, <20 MB memory
- **Impact**: Minimal; most writes happen between strategy cycles

**Read Performance** (TUI):
- **Latency**: ~5-10ms when files changed, <1ms when cached
- **Refresh Rate**: 1 Hz (configurable)
- **Overhead**: <3% CPU, <10 MB memory
- **Optimization**: Only reads when manifest indicates changes

**Scalability**:
- Handles 10,000+ signals without performance degradation
- File compression keeps disk usage bounded
- Ring buffers ensure bounded memory
- No database or complex IPC needed

### Error Handling

**Bot Side**:
```python
# File write failures don't crash bot
try:
    atomic_write_json(filepath, data)
except Exception as e:
    logger.error(f"Failed to write telemetry: {e}")
    # In-memory data still available
    # Bot continues operating normally
```

**TUI Side**:
```python
# Missing files handled gracefully
try:
    data = read_json(filepath)
except FileNotFoundError:
    return {}  # Return empty data, show "No data" in UI
except json.JSONDecodeError:
    logger.warning(f"Corrupt file: {filepath}")
    return cached_data  # Use cached data if available
```

### Configuration Options

**Bot Config** (`bot_config.json`):
```json
{
  "telemetry": {
    "enabled": true,
    "reset_on_startup": true,  // Reset counters on bot restart
    "persistence": {
      "enabled": true,
      "output_path": "telemetry_data/",
      "persist_interval_minutes": 5  // Legacy; now writes immediately
    },
    "metrics": {
      "signal_history_retention": 500,  // Max signal files
      "cycle_history_retention": 100,   // Max cycle files
      "error_history_retention": 200    // Max error files
    }
  }
}
```

**Session vs Lifetime Metrics**:
- `reset_on_startup: true` - Counters reset to 0 on every bot restart (recommended)
- `reset_on_startup: false` - Counters persist across restarts (lifetime totals)

### Advantages of File-Based IPC

✅ **Simplicity**: No database, message queue, or complex IPC mechanisms
✅ **Portability**: Works across all platforms (Linux, macOS, Windows)
✅ **Debugging**: Easy to inspect data (human-readable JSON)
✅ **Reliability**: Atomic writes prevent corruption
✅ **Independence**: Bot and TUI are completely decoupled
✅ **Export**: Telemetry data is already in standard format
✅ **Docker-Friendly**: Easy to mount as shared volume

### Limitations & Trade-offs

⚠️ **Not Real-Time**: 1-second update granularity (acceptable for monitoring)
⚠️ **File I/O**: More disk writes than memory-only solution
⚠️ **No Backpressure**: High-frequency updates could stress filesystem
⚠️ **Single Writer**: Only one bot instance should write to directory

### Future Enhancements

Potential improvements for future versions:

1. **Watchdog Integration**: Use filesystem events instead of polling
2. **Binary Format**: Use MessagePack or Protocol Buffers for smaller files
3. **Time-Series DB**: Optional integration with InfluxDB/Prometheus
4. **Multi-Bot Support**: Namespace directories for multiple bot instances
5. **Compression**: Real-time compression for all files (not just rotated)
6. **Streaming**: WebSocket server for real-time push to web dashboard

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

## Quick Reference

### Common Commands

```bash
# Start the bot
python unified_bot.py

# Launch TUI monitor (separate terminal)
python bot_monitor_tui.py

# View raw telemetry data
cat telemetry_data/metrics.json | jq
cat telemetry_data/state.json | jq

# Clean telemetry data (fresh start)
rm -rf telemetry_data/signals/*.json
rm -rf telemetry_data/cycles/*.json
rm -rf telemetry_data/errors/*.json
```

### TUI Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Q` or `Esc` | Quit the monitor |
| `R` | Manual refresh |
| `E` | Export telemetry to JSON |
| `↑` `↓` | Scroll tables/logs |

### Important File Locations

| Path | Description |
|------|-------------|
| `telemetry_data/metrics.json` | Current counters, gauges, timers |
| `telemetry_data/state.json` | Bot state and timing info |
| `telemetry_data/manifest.json` | File index and change detection |
| `telemetry_data/signals/` | Individual signal files |
| `bot_config.json` | Main configuration file |
| `live_logs/` | Bot log files |

### Configuration Quick Settings

**Reset metrics on startup** (recommended for production):
```json
"telemetry": { "reset_on_startup": true }
```

**Keep lifetime metrics** (for historical tracking):
```json
"telemetry": { "reset_on_startup": false }
```

**Adjust file retention**:
```json
"metrics": {
  "signal_history_retention": 1000,  // Keep more signal files
  "cycle_history_retention": 200     // Keep more cycle files
}
```

### Troubleshooting Quick Checks

```bash
# Check if bot is collecting telemetry
grep "Telemetry collector initialized" live_logs/*.log

# Check telemetry directory size
du -sh telemetry_data/

# Count signal files
ls telemetry_data/signals/*.json 2>/dev/null | wc -l

# View latest signal
ls -t telemetry_data/signals/*.json | head -1 | xargs cat | jq

# Check if TUI can read files
python3 -c "from src.bot.telemetry import TelemetryFileReader; r=TelemetryFileReader('telemetry_data'); print(r.read_metrics())"
```

## Support

For issues or questions:
1. Check the logs in `live_logs/`
2. Review telemetry data in `telemetry_data/`
3. Enable debug logging in bot_config.json

## License

Same as the main trading bot project.
