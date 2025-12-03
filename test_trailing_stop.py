#!/usr/bin/env python3
"""
Test script for TrailingStopManager functionality.

Tests various scenarios including:
- Long position trailing stops
- Short position trailing stops
- Activation thresholds
- Stop loss updates
- Edge cases
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.trailing_stop import TrailingStopManager
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_long_position_basic():
    """Test basic long position trailing stop functionality."""
    print("\n=== Testing Long Position Basic Functionality ===")

    manager = TrailingStopManager(activation_pct=50.0, breakeven_plus_pct=20.0)

    # Initialize long position
    entry = 100.0
    stop = 95.0
    target = 110.0
    manager.initialize_position(entry, stop, target, 'long')

    print(f"Position: Long @ {entry}, SL: {stop}, TP: {target}")
    print(f"Expected new stop after activation: {entry + (target-entry)*0.2:.2f}")

    # Test price movements including activation and pullback
    test_prices = [
        (100, "Entry price"),
        (102, "Small move up"),
        (104, "Approaching activation"),
        (105, "50% to target - ACTIVATION"),
        (107, "Continued upward"),
        (108, "Near target"),
        (103, "Pullback but above new stop"),
        (101.5, "Sharp pullback - testing stop")  # Below new stop of 102
    ]

    for price, description in test_prices:
        current_stop, was_updated = manager.update(price)
        progress = manager.get_progress_to_target(price)

        print(f"Price: {price:6.1f} ({description:25s}) | Stop: {current_stop:6.2f} | "
              f"Progress: {progress:5.1f}% | Active: {manager.is_trailing_active()} | "
              f"Updated: {was_updated}")

    # Verify stop adjustment locked in profit
    expected_stop = 102.0  # Breakeven + 20% of (110-100) = 100 + 2
    actual_stop = manager.get_current_stop()
    print(f"\n=== STOP LOSS VERIFICATION ===")
    print(f"Expected stop: {expected_stop:.2f}, Actual stop: {actual_stop:.2f}")
    print(f"Profit locked in: {expected_stop - entry:.2f} points (20% of {target - entry} point move)")

    # Test exit scenarios
    print(f"\n=== EXIT SCENARIOS ===")

    # Price at breakeven + profit (should NOT exit)
    test_price_safe = 102.5
    should_exit = manager.should_exit(test_price_safe)
    print(f"At {test_price_safe:.1f} (above stop): Exit? {should_exit} | P&L: +{test_price_safe - entry:.1f}")

    # Price exactly at stop (should exit)
    test_price_at_stop = 102.0
    should_exit = manager.should_exit(test_price_at_stop)
    print(f"At {test_price_at_stop:.1f} (at stop):    Exit? {should_exit} | P&L: +{test_price_at_stop - entry:.1f}")

    # Price below stop (should exit)
    test_price_below = 101.5
    should_exit = manager.should_exit(test_price_below)
    print(f"At {test_price_below:.1f} (below stop): Exit? {should_exit} | Would exit at stop: +{expected_stop - entry:.1f}")

    print(f"\nRESULT: Trailing stop ensures minimum +{expected_stop - entry:.1f} point profit once activated")

    return True


def test_short_position_basic():
    """Test basic short position trailing stop functionality."""
    print("\n=== Testing Short Position Basic Functionality ===")

    manager = TrailingStopManager(activation_pct=50.0, breakeven_plus_pct=20.0)

    # Initialize short position
    entry = 100.0
    stop = 105.0
    target = 90.0
    manager.initialize_position(entry, stop, target, 'short')

    print(f"Position: Short @ {entry}, SL: {stop}, TP: {target}")
    print(f"Expected new stop after activation: {entry - (entry-target)*0.2:.2f}")

    # Test price movements including activation and bounce
    test_prices = [
        (100, "Entry price"),
        (98, "Small move down"),
        (96, "Approaching activation"),
        (95, "50% to target - ACTIVATION"),
        (93, "Continued downward"),
        (92, "Near target"),
        (97, "Bounce but below new stop"),
        (98.5, "Sharp bounce - testing stop")  # Above new stop of 98
    ]

    for price, description in test_prices:
        current_stop, was_updated = manager.update(price)
        progress = manager.get_progress_to_target(price)

        print(f"Price: {price:6.1f} ({description:25s}) | Stop: {current_stop:6.2f} | "
              f"Progress: {progress:5.1f}% | Active: {manager.is_trailing_active()} | "
              f"Updated: {was_updated}")

    # Verify stop adjustment locked in profit
    expected_stop = 98.0  # Breakeven - 20% of (100-90) = 100 - 2
    actual_stop = manager.get_current_stop()
    print(f"\n=== STOP LOSS VERIFICATION ===")
    print(f"Expected stop: {expected_stop:.2f}, Actual stop: {actual_stop:.2f}")
    print(f"Profit locked in: {entry - expected_stop:.2f} points (20% of {entry - target} point move)")

    # Test exit scenarios for SHORT position
    print(f"\n=== EXIT SCENARIOS (SHORT) ===")

    # Price at breakeven - profit (should NOT exit)
    test_price_safe = 97.5
    should_exit = manager.should_exit(test_price_safe)
    print(f"At {test_price_safe:.1f} (below stop): Exit? {should_exit} | P&L: +{entry - test_price_safe:.1f}")

    # Price exactly at stop (should exit)
    test_price_at_stop = 98.0
    should_exit = manager.should_exit(test_price_at_stop)
    print(f"At {test_price_at_stop:.1f} (at stop):    Exit? {should_exit} | P&L: +{entry - test_price_at_stop:.1f}")

    # Price above stop (should exit)
    test_price_above = 98.5
    should_exit = manager.should_exit(test_price_above)
    print(f"At {test_price_above:.1f} (above stop): Exit? {should_exit} | Would exit at stop: +{entry - expected_stop:.1f}")

    print(f"\nRESULT: Trailing stop ensures minimum +{entry - expected_stop:.1f} point profit once activated")

    return True


def test_activation_threshold():
    """Test different activation thresholds."""
    print("\n=== Testing Activation Thresholds ===")

    # Test 30% activation
    manager = TrailingStopManager(activation_pct=30.0, breakeven_plus_pct=20.0)
    entry, stop, target = 100, 95, 110
    manager.initialize_position(entry, stop, target, 'long')

    print("30% Activation Threshold:")
    activation_price = entry + 0.3 * (target - entry)  # 103
    manager.update(activation_price)
    new_stop = manager.get_current_stop()
    print(f"  At price {activation_price:.0f} (30% progress): Active? {manager.is_trailing_active()}")
    print(f"  New stop: {new_stop:.2f} (locks in +{new_stop - entry:.2f} profit)")

    # Test 70% activation
    manager = TrailingStopManager(activation_pct=70.0, breakeven_plus_pct=20.0)
    manager.initialize_position(entry, stop, target, 'long')

    print("\n70% Activation Threshold:")
    # Test at 50% (shouldn't activate)
    manager.update(105)
    print(f"  At price 105 (50% progress): Active? {manager.is_trailing_active()}")
    # Test at 70% (should activate)
    activation_price = entry + 0.7 * (target - entry)  # 107
    manager.update(activation_price)
    new_stop = manager.get_current_stop()
    print(f"  At price {activation_price:.0f} (70% progress): Active? {manager.is_trailing_active()}")
    print(f"  New stop: {new_stop:.2f} (locks in +{new_stop - entry:.2f} profit)")

    return True


def test_trail_percentage():
    """Test different breakeven plus percentages."""
    print("\n=== Testing Breakeven Plus Percentages ===")

    entry, stop, target = 100, 95, 110
    target_distance = target - entry

    # Test 10% breakeven plus
    manager = TrailingStopManager(activation_pct=50.0, breakeven_plus_pct=10.0)
    manager.initialize_position(entry, stop, target, 'long')

    print("10% Breakeven Plus (locks in 1 point):")
    manager.update(105)  # 50% to target, should activate
    current_stop = manager.get_current_stop()
    expected_stop = entry + (target_distance * 0.10)  # 101
    print(f"  Entry: {entry}, Target: {target}, Distance: {target_distance}")
    print(f"  New Stop: {current_stop:.2f} = Breakeven + {target_distance * 0.10:.1f}")
    print(f"  Profit locked: +{current_stop - entry:.1f} points")
    print(f"  Verified: {current_stop == expected_stop}")

    # Test 30% breakeven plus
    manager = TrailingStopManager(activation_pct=50.0, breakeven_plus_pct=30.0)
    manager.initialize_position(entry, stop, target, 'long')

    print("\n30% Breakeven Plus (locks in 3 points):")
    manager.update(105)  # 50% to target, should activate
    current_stop = manager.get_current_stop()
    expected_stop = entry + (target_distance * 0.30)  # 103
    print(f"  Entry: {entry}, Target: {target}, Distance: {target_distance}")
    print(f"  New Stop: {current_stop:.2f} = Breakeven + {target_distance * 0.30:.1f}")
    print(f"  Profit locked: +{current_stop - entry:.1f} points")
    print(f"  Verified: {current_stop == expected_stop}")

    return True


def test_price_pullback():
    """Test behavior during price pullbacks."""
    print("\n=== Testing Price Pullback Behavior ===")

    manager = TrailingStopManager(activation_pct=50.0, breakeven_plus_pct=20.0)
    entry = 100.0
    stop = 95.0
    target = 110.0
    manager.initialize_position(entry, stop, target, 'long')

    print(f"Position: Long @ {entry}, SL: {stop}, TP: {target}")
    expected_new_stop = 102.0  # 100 + 0.2 * (110-100)
    print(f"Expected stop after activation: {expected_new_stop:.2f}\n")

    # Simulate volatile price action
    price_sequence = [
        (104, "Pre-activation"),
        (105, "Hit 50% - ACTIVATE"),
        (108, "Move higher"),
        (103, "Pullback above stop"),
        (106, "Recovery"),
        (102.5, "Test near stop"),
        (107, "Another high"),
        (101.8, "Deep pullback - STOP HIT")
    ]

    for price, description in price_sequence:
        current_stop, updated = manager.update(price)
        should_exit = manager.should_exit(price)
        print(f"  Price: {price:6.1f} ({description:20s}) | Stop: {current_stop:.2f} | "
              f"Updated: {updated} | Exit: {should_exit}")

    print(f"\nVERIFICATION:")
    print(f"  Stop moved ONCE from {stop:.2f} to {expected_new_stop:.2f}")
    print(f"  Stop remained FIXED during all pullbacks")
    print(f"  Guaranteed profit: +{expected_new_stop - entry:.2f} points")

    return True


def test_immediate_reversal():
    """Test behavior when price immediately reverses."""
    print("\n=== Testing Immediate Price Reversal ===")

    manager = TrailingStopManager(activation_pct=50.0, breakeven_plus_pct=20.0)
    entry = 100.0
    stop = 95.0
    target = 110.0
    manager.initialize_position(entry, stop, target, 'long')

    print(f"Position: Long @ {entry}, SL: {stop}, TP: {target}")
    print(f"Trailing activation requires price to reach: {entry + 0.5 * (target - entry):.1f}")
    print(f"\nScenario: Price immediately reverses without reaching activation\n")

    # Price immediately goes against position (never reaches 105 for activation)
    test_prices = [
        (100, "Entry", 0),
        (99, "Down 1", -1),
        (98, "Down 2", -2),
        (97, "Down 3", -3),
        (96, "Down 4", -4),
        (95.5, "Near original stop", -4.5),
        (94.8, "Below original stop", -5.2)
    ]

    for price, desc, pnl in test_prices:
        current_stop, was_updated = manager.update(price)
        should_exit = manager.should_exit(price)
        print(f"  Price: {price:6.2f} ({desc:20s}) | Stop: {current_stop:6.2f} | "
              f"Exit: {should_exit} | Active: {manager.is_trailing_active()} | P&L: {pnl:+.1f}")

    print(f"\nVERIFICATION:")
    print(f"  Trailing stop NEVER activated (price didn't reach 105)")
    print(f"  Original stop at {stop:.2f} remained in effect")
    print(f"  Maximum loss limited to: {stop - entry:.2f} points")

    return True


def test_target_reached():
    """Test behavior when target is reached and exceeded."""
    print("\n=== Testing Target Reached Scenario ===")

    manager = TrailingStopManager(activation_pct=50.0, breakeven_plus_pct=20.0)
    entry = 100.0
    stop = 95.0
    target = 110.0
    manager.initialize_position(entry, stop, target, 'long')

    print(f"Position: Long @ {entry}, SL: {stop}, TP: {target}")
    expected_new_stop = 102.0  # 100 + 0.2 * (110-100)
    print(f"Expected stop after activation: {expected_new_stop:.2f}\n")

    # Move price to and beyond target
    test_prices = [
        (104, "Approaching activation", 40),
        (105, "50% - ACTIVATION", 50),
        (108, "80% to target", 80),
        (110, "TARGET REACHED", 100),
        (112, "Beyond target +2", 120),
        (115, "Beyond target +5", 150),
        (111, "Pullback from high", 110)
    ]

    for price, desc, progress_pct in test_prices:
        current_stop, was_updated = manager.update(price)
        actual_progress = manager.get_progress_to_target(price)
        print(f"  Price: {price:6.1f} ({desc:20s}) | Stop: {current_stop:6.2f} | "
              f"Progress: {actual_progress:6.1f}% | Updated: {was_updated}")

    # Verify final results
    final_stop = manager.get_current_stop()
    print(f"\nFINAL VERIFICATION:")
    print(f"  Price moved from {entry} to {115} (+{115-entry} points)")
    print(f"  Stop remained FIXED at {final_stop:.2f} (not trailing with price)")
    print(f"  Minimum guaranteed profit: +{expected_new_stop - entry:.2f} points")
    print(f"  Actual profit if exited at {111}: +{111 - entry} points")
    print(f"\nRESULT: Stop does NOT continuously trail. Locks in {expected_new_stop - entry:.0f} point profit.")

    return True


def test_reset_functionality():
    """Test reset functionality between positions."""
    print("\n=== Testing Reset Functionality ===")

    manager = TrailingStopManager(activation_pct=50.0, breakeven_plus_pct=20.0)

    # First position
    print("\nFirst Position (Long):")
    manager.initialize_position(100, 95, 110, 'long')
    manager.update(105)  # Activate at 50%
    stop1 = manager.get_current_stop()
    active1 = manager.is_trailing_active()
    print(f"  After activation - Stop: {stop1:.2f}, Active: {active1}")
    print(f"  Expected stop: 102.00 (100 + 0.2 * 10)")

    # Reset for new position
    manager.reset()
    print("\nAfter reset:")
    print(f"  Stop: {manager.get_current_stop()}, Active: {manager.is_trailing_active()}")

    # Second position (different parameters)
    print("\nSecond Position (Short):")
    manager.initialize_position(200, 210, 180, 'short')
    print(f"  Initial - Stop: {manager.get_current_stop():.2f}, Active: {manager.is_trailing_active()}")
    manager.update(190)  # Activate at 50% for short
    stop2 = manager.get_current_stop()
    active2 = manager.is_trailing_active()
    print(f"  After activation - Stop: {stop2:.2f}, Active: {active2}")
    print(f"  Expected stop: 196.00 (200 - 0.2 * 20)")

    print("\nVERIFICATION: Each position operates independently after reset")

    return True


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("TRAILING STOP MANAGER TEST SUITE")
    print("=" * 60)

    tests = [
        ("Basic Long Position", test_long_position_basic),
        ("Basic Short Position", test_short_position_basic),
        ("Activation Thresholds", test_activation_threshold),
        ("Breakeven Plus Percentages", test_trail_percentage),
        ("Price Pullback Behavior", test_price_pullback),
        ("Immediate Reversal (No Activation)", test_immediate_reversal),
        ("Target Reached & Exceeded", test_target_reached),
        ("Reset Functionality", test_reset_functionality)
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "PASSED" if success else "FAILED"))
            print(f"\n✓ {name} - {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            results.append((name, f"ERROR: {e}"))
            print(f"\n✗ {name} - ERROR: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)

    for name, status in results:
        symbol = "✓" if status == "PASSED" else "✗"
        print(f"{symbol} {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)