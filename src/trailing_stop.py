"""
Trailing Stop Manager Module

Handles dynamic trailing stop functionality for active positions.
Activates trailing stops after reaching profit thresholds.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TrailingStopManager:
    """
    Manages trailing stop logic for individual positions.

    Features:
    - Activates after reaching X% of target profit
    - Trails stop loss to protect profits
    - Maintains minimum risk/reward ratio
    """

    def __init__(self, activation_pct: float = 50.0, breakeven_plus_pct: float = 20.0):
        """
        Initialize trailing stop manager.

        Args:
            activation_pct: Percentage of target to reach before activating trailing stop
            breakeven_plus_pct: Percentage of target distance to add to breakeven for new stop
        """
        self.activation_pct = activation_pct
        self.breakeven_plus_pct = breakeven_plus_pct

        # Position tracking
        self.entry_price = None
        self.initial_stop = None
        self.take_profit = None
        self.position_type = None  # 'long' or 'short'

        # Trailing stop state
        self.is_activated = False
        self.current_stop = None
        self.highest_price = None  # For long positions
        self.lowest_price = None   # For short positions
        self.stop_adjusted = False  # Track if stop has been adjusted

        logger.debug(f"TrailingStopManager initialized: activation={activation_pct}%, breakeven+={breakeven_plus_pct}%")

    def initialize_position(self, entry_price: float, stop_loss: float,
                          take_profit: float, position_type: str) -> None:
        """
        Initialize trailing stop for a new position.

        Args:
            entry_price: Entry price of the position
            stop_loss: Initial stop loss price
            take_profit: Target take profit price
            position_type: 'long' or 'short'
        """
        self.entry_price = entry_price
        self.initial_stop = stop_loss
        self.take_profit = take_profit
        self.position_type = position_type
        self.current_stop = stop_loss

        self.is_activated = False
        self.stop_adjusted = False
        self.highest_price = entry_price if position_type == 'long' else None
        self.lowest_price = entry_price if position_type == 'short' else None

        logger.debug(f"Position initialized: {position_type} @ {entry_price:.4f}, "
                    f"SL: {stop_loss:.4f}, TP: {take_profit:.4f}")

    def update(self, current_price: float) -> Tuple[float, bool]:
        """
        Update trailing stop based on current price.

        Args:
            current_price: Current market price

        Returns:
            Tuple of (new_stop_price, was_updated)
        """
        if not self.entry_price:
            return self.current_stop, False

        was_updated = False

        if self.position_type == 'long':
            was_updated = self._update_long_position(current_price)
        elif self.position_type == 'short':
            was_updated = self._update_short_position(current_price)

        return self.current_stop, was_updated

    def _update_long_position(self, current_price: float) -> bool:
        """
        Update trailing stop for long position.

        Args:
            current_price: Current market price

        Returns:
            True if stop was updated
        """
        was_updated = False

        # Only check for activation if not already activated and adjusted
        if not self.is_activated and not self.stop_adjusted:
            target_distance = self.take_profit - self.entry_price
            current_distance = current_price - self.entry_price
            progress_pct = (current_distance / target_distance * 100) if target_distance > 0 else 0

            if progress_pct >= self.activation_pct:
                self.is_activated = True

                # One-time adjustment to breakeven + percentage of target distance
                target_distance = self.take_profit - self.entry_price
                adjustment = target_distance * (self.breakeven_plus_pct / 100)
                new_stop = self.entry_price + adjustment

                # Only update if new stop is better than current
                if new_stop > self.current_stop:
                    old_stop = self.current_stop
                    self.current_stop = new_stop
                    self.stop_adjusted = True
                    was_updated = True
                    logger.info(f"Trailing stop ACTIVATED at {progress_pct:.1f}% of target")
                    logger.info(f"Stop moved to breakeven + {self.breakeven_plus_pct}%: "
                               f"{old_stop:.4f} -> {new_stop:.4f}")

        return was_updated

    def _update_short_position(self, current_price: float) -> bool:
        """
        Update trailing stop for short position.

        Args:
            current_price: Current market price

        Returns:
            True if stop was updated
        """
        was_updated = False

        # Only check for activation if not already activated and adjusted
        if not self.is_activated and not self.stop_adjusted:
            target_distance = self.entry_price - self.take_profit
            current_distance = self.entry_price - current_price
            progress_pct = (current_distance / target_distance * 100) if target_distance > 0 else 0

            if progress_pct >= self.activation_pct:
                self.is_activated = True

                # One-time adjustment to breakeven - percentage of target distance
                target_distance = self.entry_price - self.take_profit
                adjustment = target_distance * (self.breakeven_plus_pct / 100)
                new_stop = self.entry_price - adjustment

                # Only update if new stop is better than current (lower for shorts)
                if new_stop < self.current_stop:
                    old_stop = self.current_stop
                    self.current_stop = new_stop
                    self.stop_adjusted = True
                    was_updated = True
                    logger.info(f"Trailing stop ACTIVATED at {progress_pct:.1f}% of target")
                    logger.info(f"Stop moved to breakeven + {self.breakeven_plus_pct}%: "
                               f"{old_stop:.4f} -> {new_stop:.4f}")

        return was_updated

    def should_exit(self, current_price: float) -> bool:
        """
        Check if position should exit based on trailing stop.

        Args:
            current_price: Current market price

        Returns:
            True if stop has been hit
        """
        if not self.current_stop:
            return False

        if self.position_type == 'long':
            return current_price <= self.current_stop
        elif self.position_type == 'short':
            return current_price >= self.current_stop

        return False

    def get_current_stop(self) -> Optional[float]:
        """Get current stop loss price."""
        return self.current_stop

    def is_trailing_active(self) -> bool:
        """Check if trailing stop is currently active."""
        return self.is_activated

    def get_progress_to_target(self, current_price: float) -> float:
        """
        Get progress towards target as percentage.

        Args:
            current_price: Current market price

        Returns:
            Progress percentage (0-100+)
        """
        if not self.entry_price or not self.take_profit:
            return 0.0

        if self.position_type == 'long':
            target_distance = self.take_profit - self.entry_price
            current_distance = current_price - self.entry_price
        else:  # short
            target_distance = self.entry_price - self.take_profit
            current_distance = self.entry_price - current_price

        if target_distance > 0:
            return (current_distance / target_distance) * 100
        return 0.0

    def reset(self) -> None:
        """Reset trailing stop manager for new position."""
        self.entry_price = None
        self.initial_stop = None
        self.take_profit = None
        self.position_type = None
        self.is_activated = False
        self.current_stop = None
        self.highest_price = None
        self.lowest_price = None
        self.stop_adjusted = False