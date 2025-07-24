"""
Order Accumulator Module

This module handles accumulation and saving of orders from optimization runs
to CSV files with support for different transport backends (local/S3).

Features:
- Accumulate orders from multiple optimization runs
- Save orders to CSV files organized by asset and timeframe
- Support for local and S3 storage
- Consistent order data structure
- Optimization run tracking
"""

import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .transport_factory import create_optimization_transport

logger = logging.getLogger(__name__)


class OrderAccumulator:
    """
    Accumulates and manages order data from optimization runs
    """
    
    def __init__(self, 
                 symbol: str, 
                 timeframe: str,
                 transport_type: str = 'local',
                 output_dir: Optional[str] = None,
                 optimization_type: Optional[str] = None):
        """
        Initialize order accumulator
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD=X')
            timeframe: Trading timeframe (e.g., '15m', '1h')
            transport_type: Storage type ('local' or 's3')
            output_dir: Output directory for local storage (ignored for S3)
            optimization_type: Type of optimization (e.g., 'balanced', 'focused', 'risk')
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.transport_type = transport_type
        self.optimization_type = optimization_type
        
        # Initialize transport
        self.transport = create_optimization_transport(output_dir, transport_type)
        
        # Generate clean asset identifier for file naming
        self.asset_id = self._get_asset_identifier()
        
        # Generate CSV file path/key (include optimization type if provided)
        if optimization_type:
            csv_filename = f"{self.asset_id}_{self.timeframe}_{optimization_type}_orders.csv"
        else:
            csv_filename = f"{self.asset_id}_{self.timeframe}_orders.csv"
        self.csv_key = f"orders/{csv_filename}"
        
        # Track orders for current session (no longer buffering)
        self.session_order_count = 0
        
        logger.info(f"📋 OrderAccumulator initialized: {self.asset_id}_{self.timeframe}" + 
                   (f"_{self.optimization_type}" if self.optimization_type else ""))
        logger.info(f"💾 Transport: {type(self.transport).__name__}")
        logger.info(f"📄 CSV key: {self.csv_key}")
        
        # Print initialization for user visibility
        opt_type_str = f"_{self.optimization_type}" if self.optimization_type else ""
        print(f"📋 Order accumulator: {self.asset_id}_{self.timeframe}{opt_type_str} -> {self.csv_key}")
    
    def _get_asset_identifier(self) -> str:
        """Generate clean asset identifier for file names"""
        # Clean symbol for file naming (remove special characters, limit length)
        asset_clean = self.symbol.replace('=', '').replace('/', '').replace('-', '_').upper()
        # Limit to 10 characters to keep file names reasonable
        return asset_clean[:10]
    
    def add_optimization_run(self, 
                           run_number: int, 
                           order_log: List[Dict[str, Any]], 
                           optimization_params: Dict[str, Any]) -> None:
        """
        Add orders from a single optimization run and save immediately
        
        Args:
            run_number: Optimization run number/index
            order_log: List of order dictionaries from strategy
            optimization_params: Parameters used for this optimization run
        """
        if not order_log:
            logger.debug(f"No orders in run {run_number}")
            return
        
        logger.debug(f"📊 Processing {len(order_log)} orders from run {run_number}")
        
        # Process each order from the run
        new_orders = []
        for order in order_log:
            processed_order = self._process_order(run_number, order, optimization_params)
            new_orders.append(processed_order)
        
        # Save orders immediately
        self._save_orders_immediately(new_orders)
        self.session_order_count += len(new_orders)
        
        # Always show order saving progress (even in quiet mode)
        print(f"💾 Saved {len(new_orders)} orders from run {run_number} (total: {self.session_order_count})")
        
        logger.debug(f"📈 Saved {len(new_orders)} orders. Session total: {self.session_order_count}")
    
    def _process_order(self, 
                      run_number: int, 
                      order: Dict[str, Any], 
                      optimization_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single order and extract standardized information
        
        Args:
            run_number: Optimization run number
            order: Original order dictionary from strategy
            optimization_params: Parameters used for this optimization run
            
        Returns:
            Standardized order dictionary for CSV export
        """
        # Extract trade outcome info if available
        trade_outcome = order.get('trade_outcome', {})
        
        # Determine win/loss status
        pnl = trade_outcome.get('pnl', 0)
        win_loss = 'WIN' if pnl > 0 else 'LOSS' if pnl < 0 else 'BREAK_EVEN'
        
        # Determine direction from order type
        direction = 'LONG' if order.get('type') == 'BUY' else 'SHORT'
        
        # Create standardized order record
        processed_order = {
            # Optimization tracking
            'optimization_run': run_number,
            'asset': self.symbol,
            'timeframe': self.timeframe,
            
            # Order timing
            'date': order.get('date', ''),
            'time': order.get('time', ''),
            'exit_date': trade_outcome.get('exit_date', ''),
            'exit_time': trade_outcome.get('exit_time', ''),
            
            # Order details
            'direction': direction,
            'lot_size': order.get('position_size', 0),
            'entry_price': order.get('entry_price', 0),
            'stop_loss': order.get('stop_loss', 0),
            'take_profit': order.get('take_profit', 0),
            'exit_price': trade_outcome.get('exit_price', 0),
            
            # Trade outcome
            'win_loss': win_loss,
            'pnl': pnl,
            'exit_reason': trade_outcome.get('type', 'unknown'),
            
            # Risk management
            'atr_value': order.get('atr_value', 0),
            'risk_amount': order.get('risk_amount', 0),
            'reward_amount': order.get('reward_amount', 0),
            'risk_reward_ratio': order.get('risk_reward_ratio', 0),
            'account_risk_pct': order.get('account_risk_pct', 0),
            
            # Account tracking
            'deposit_before_trade': order.get('deposit_before_trade', 0),
            'deposit_after_trade': trade_outcome.get('deposit_after', 0),
            'deposit_change': trade_outcome.get('deposit_change', 0),
            
            # Strategy parameters (selected key ones)
            'bb_window': optimization_params.get('bb_window', 0),
            'bb_std': optimization_params.get('bb_std', 0),
            'vwap_window': optimization_params.get('vwap_window', 0),
            'vwap_std': optimization_params.get('vwap_std', 0),
            'risk_per_position_pct': optimization_params.get('risk_per_position_pct', 0),
            'stop_loss_atr_multiplier': optimization_params.get('stop_loss_atr_multiplier', 0),
            'risk_reward_ratio_param': optimization_params.get('risk_reward_ratio', 0),
            'require_reversal': optimization_params.get('require_reversal', False),
            
            # Additional metadata
            'order_id': order.get('order_id', ''),
            'reason': order.get('reason', ''),
        }
        
        return processed_order
    
    def _save_orders_immediately(self, new_orders: List[Dict[str, Any]]) -> bool:
        """
        Save new orders immediately by appending to existing CSV
        
        Args:
            new_orders: List of new order dictionaries to save
            
        Returns:
            True if save was successful, False otherwise
        """
        if not new_orders:
            logger.warning("No new orders to save")
            return True
        
        try:
            # Load existing data if available
            existing_df = self._load_existing_csv()
            
            # Create new DataFrame from new orders
            new_df = pd.DataFrame(new_orders)
            
            # Combine with existing data
            if existing_df is not None:
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                logger.debug(f"📊 Appending {len(new_df)} orders to existing {len(existing_df)} orders")
            else:
                combined_df = new_df
                logger.debug(f"📊 Creating new CSV with {len(new_df)} orders")
            
            # Sort by optimization run and date for consistency
            combined_df = combined_df.sort_values(['optimization_run', 'date', 'time'], ignore_index=True)
            
            # Save to transport
            success = self.transport.save_csv(self.csv_key, combined_df)
            
            if success:
                logger.debug(f"✅ Successfully saved {len(combined_df)} total orders to {self.csv_key}")
                return True
            else:
                logger.error(f"❌ Failed to save orders to {self.csv_key}")
                print(f"❌ Failed to save orders to {self.csv_key}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving orders immediately: {e}")
            print(f"❌ Error saving orders immediately: {e}")
            return False
    
    def save_to_csv(self) -> bool:
        """
        Legacy method for compatibility - orders are now saved immediately
        
        Returns:
            True (orders are saved immediately in add_optimization_run)
        """
        logger.info("📋 Orders are saved immediately after each optimization run")
        return True
    
    def _load_existing_csv(self) -> Optional[pd.DataFrame]:
        """
        Load existing CSV file if it exists
        
        Returns:
            DataFrame with existing orders or None if file doesn't exist
        """
        try:
            existing_df = self.transport.load_csv(self.csv_key)
            if existing_df is not None:
                logger.debug(f"📖 Loaded existing CSV with {len(existing_df)} orders")
                return existing_df
        except Exception as e:
            logger.debug(f"No existing CSV file found or error loading: {e}")
        
        return None
    
    def get_order_count(self) -> int:
        """Get number of orders saved in current session"""
        return self.session_order_count
    
    def clear_buffer(self) -> None:
        """Clear the session order count (legacy method for compatibility)"""
        self.session_order_count = 0
        logger.debug("🗑️ Session order count reset")
    
    def get_csv_info(self) -> Dict[str, Any]:
        """
        Get information about the CSV file
        
        Returns:
            Dictionary with CSV file information
        """
        try:
            existing_df = self._load_existing_csv()
            if existing_df is not None:
                return {
                    'csv_key': self.csv_key,
                    'total_orders': len(existing_df),
                    'unique_runs': existing_df['optimization_run'].nunique() if 'optimization_run' in existing_df.columns else 0,
                    'date_range': {
                        'first_order': existing_df['date'].min() if 'date' in existing_df.columns and len(existing_df) > 0 else None,
                        'last_order': existing_df['date'].max() if 'date' in existing_df.columns and len(existing_df) > 0 else None
                    },
                    'session_orders': self.session_order_count
                }
            else:
                return {
                    'csv_key': self.csv_key,
                    'total_orders': 0,
                    'unique_runs': 0,
                    'date_range': {'first_order': None, 'last_order': None},
                    'session_orders': self.session_order_count
                }
        except Exception as e:
            logger.error(f"Error getting CSV info: {e}")
            return {
                'csv_key': self.csv_key,
                'error': str(e),
                'session_orders': self.session_order_count
            }


def create_order_accumulator(symbol: str, 
                           timeframe: str, 
                           transport_type: str = 'local',
                           output_dir: Optional[str] = None,
                           optimization_type: Optional[str] = None) -> OrderAccumulator:
    """
    Factory function to create OrderAccumulator instance
    
    Args:
        symbol: Trading symbol
        timeframe: Trading timeframe
        transport_type: Storage type ('local' or 's3')
        output_dir: Output directory for local storage
        optimization_type: Type of optimization (e.g., 'balanced', 'focused', 'risk')
        
    Returns:
        OrderAccumulator instance
    """
    return OrderAccumulator(
        symbol=symbol,
        timeframe=timeframe,
        transport_type=transport_type,
        output_dir=output_dir,
        optimization_type=optimization_type
    )
