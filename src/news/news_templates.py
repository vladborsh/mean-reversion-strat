#!/usr/bin/env python3
"""
News Message Templates

This module provides templates for economic news notifications
with different formats for daily summaries and individual alerts.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class NewsMessageTemplates:
    """Templates for economic news notifications"""
    
    def __init__(self):
        """Initialize news templates"""
        self.impact_emojis = {
            'High': '🔴',
            'Medium': '🟡',
            'Low': '⚪'
        }
        
        self.currency_flags = {
            'USD': '🇺🇸',
            'EUR': '🇪🇺',
            'GBP': '🇬🇧',
            'JPY': '🇯🇵',
            'CAD': '🇨🇦',
            'AUD': '🇦🇺',
            'NZD': '🇳🇿',
            'CHF': '🇨🇭',
            'CNY': '🇨🇳',
            'HKD': '🇭🇰',
            'SGD': '🇸🇬',
            'SEK': '🇸🇪',
            'NOK': '🇳🇴',
            'MXN': '🇲🇽',
            'ZAR': '🇿🇦',
            'TRY': '🇹🇷',
            'BRL': '🇧🇷',
            'KRW': '🇰🇷',
            'INR': '🇮🇳',
            'RUB': '🇷🇺'
        }
    
    def get_daily_summary(self, events: List[Dict[str, Any]], 
                         date: Optional[datetime] = None) -> Dict[str, str]:
        """
        Get daily economic calendar summary message
        
        Args:
            events: List of today's events
            date: Optional date for the summary (defaults to today)
            
        Returns:
            Formatted message dictionary
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_str = date.strftime('%B %d, %Y')
        
        if not events:
            return {
                'text': f"📅 *Economic Calendar - {date_str}*\n\n"
                        f"No significant economic events scheduled for today.\n\n"
                        f"_Stay tuned for tomorrow's updates!_",
                'parse_mode': 'Markdown'
            }
        
        # Group events by impact level
        high_impact = [e for e in events if e.get('impact') == 'High']
        medium_impact = [e for e in events if e.get('impact') == 'Medium']
        low_impact = [e for e in events if e.get('impact') == 'Low']
        
        # Build message
        message = f"📅 *Economic Calendar - {date_str}*\n"
        message += f"_Total Events: {len(events)}_\n\n"
        
        # High impact events
        if high_impact:
            message += f"{self.impact_emojis['High']} *HIGH IMPACT ({len(high_impact)})*\n"
            for event in high_impact[:5]:  # Limit to 5 events per category
                message += self._format_event_line(event)
            if len(high_impact) > 5:
                message += f"_... and {len(high_impact) - 5} more_\n"
            message += "\n"
        
        # Medium impact events
        if medium_impact:
            message += f"{self.impact_emojis['Medium']} *MEDIUM IMPACT ({len(medium_impact)})*\n"
            for event in medium_impact[:3]:  # Limit to 3 events
                message += self._format_event_line(event)
            if len(medium_impact) > 3:
                message += f"_... and {len(medium_impact) - 3} more_\n"
            message += "\n"
        
        # Low impact summary
        if low_impact:
            message += f"{self.impact_emojis['Low']} *LOW IMPACT*: {len(low_impact)} events\n\n"
        
        # Footer
        message += "💡 _Focus on high impact events for major market movements_"
        
        return {
            'text': message,
            'parse_mode': 'Markdown'
        }
    
    def get_high_impact_alert(self, event: Dict[str, Any]) -> Dict[str, str]:
        """
        Get alert message for a single high-impact event
        
        Args:
            event: Event dictionary
            
        Returns:
            Formatted alert message
        """
        impact_emoji = self.impact_emojis.get(event.get('impact', 'Low'))
        currency = event.get('country', 'N/A')
        flag = self.currency_flags.get(currency, '🌍')
        
        # Parse event time
        try:
            event_datetime = datetime.fromisoformat(event.get('date', '').replace('Z', '+00:00'))
            time_str = event_datetime.strftime('%H:%M UTC')
        except:
            time_str = 'Time TBD'
        
        # Build message
        message = f"⚡ *HIGH IMPACT EVENT ALERT* ⚡\n\n"
        message += f"{impact_emoji} {flag} *{currency}* - {event.get('title', 'Unknown Event')}\n\n"
        message += f"🕐 *Time:* {time_str}\n"
        
        # Add forecast and previous if available
        forecast = event.get('forecast', '').strip()
        previous = event.get('previous', '').strip()
        
        if forecast or previous:
            message += f"📊 *Data:*\n"
            if forecast:
                message += f"  • Forecast: `{forecast}`\n"
            if previous:
                message += f"  • Previous: `{previous}`\n"
        
        message += f"\n⚠️ _Expect increased volatility in {currency} pairs_"
        
        return {
            'text': message,
            'parse_mode': 'Markdown'
        }
    
    def get_urgent_alert(self, event: Dict[str, Any], minutes: int = 5) -> Dict[str, str]:
        """
        Get urgent alert message for imminent events (5 minutes before)
        
        Args:
            event: Event dictionary
            minutes: Minutes until event (default 5)
            
        Returns:
            Formatted urgent alert message
        """
        # Parse event time
        try:
            event_datetime = datetime.fromisoformat(event.get('event_date', '').replace('Z', '+00:00'))
            time_str = event_datetime.strftime('%H:%M UTC')
        except:
            try:
                event_datetime = datetime.fromisoformat(event.get('date', '').replace('Z', '+00:00'))
                time_str = event_datetime.strftime('%H:%M UTC')
            except:
                time_str = 'Soon'
        
        # Get country flag
        country = event.get('country', '')
        flag = self.currency_flags.get(country, '🌍')
        
        # Get impact emoji
        impact = event.get('impact', 'High')
        impact_emoji = self.impact_emojis.get(impact, '🔴')
        
        # Build urgent message with attention-grabbing formatting
        message = f"🚨 *URGENT: EVENT IN {minutes} MINUTES!* 🚨\n"
        message += f"{'='*30}\n\n"
        
        message += f"{impact_emoji} *{event.get('title', 'Economic Event')}*\n"
        message += f"{flag} {country} • {time_str}\n\n"
        
        message += f"⏰ *STARTS IN: {minutes} MINUTES*\n\n"
        
        # Add forecast and previous if available
        forecast = event.get('forecast', '').strip()
        previous = event.get('previous', '').strip()
        
        if forecast or previous:
            message += f"📊 *Data:*\n"
            if forecast:
                message += f"   Forecast: `{forecast}`\n"
            if previous:
                message += f"   Previous: `{previous}`\n"
            message += "\n"
        
        # Add warning message
        message += f"⚠️ *Action Required:*\n"
        message += f"• Check open positions in {country} pairs\n"
        message += f"• Consider closing or adjusting positions\n"
        message += f"• High volatility expected!\n\n"
        
        message += f"_This is a {impact.lower()}-impact event_"
        
        return {
            'text': message.strip(),
            'parse_mode': 'Markdown'
        }
    
    def get_weekly_fetch_summary(self, fetch_result: Dict[str, int]) -> Dict[str, str]:
        """
        Get summary message for weekly news fetch operation
        
        Args:
            fetch_result: Dictionary with fetch statistics
            
        Returns:
            Formatted summary message
        """
        total = fetch_result.get('total', 0)
        saved = fetch_result.get('saved', 0)
        skipped = fetch_result.get('skipped', 0)
        errors = fetch_result.get('errors', 0)
        
        status_emoji = '✅' if errors == 0 else '⚠️' if errors < 5 else '❌'
        
        message = f"{status_emoji} *Weekly News Fetch Complete*\n\n"
        message += f"📊 *Statistics:*\n"
        message += f"  • Total Events: {total}\n"
        message += f"  • New Events: {saved}\n"
        message += f"  • Duplicates: {skipped}\n"
        
        if errors > 0:
            message += f"  • Errors: {errors}\n"
        
        message += f"\n_Next fetch scheduled for next week_"
        
        return {
            'text': message,
            'parse_mode': 'Markdown'
        }
    
    def get_upcoming_events(self, events: List[Dict[str, Any]], hours: int = 24) -> Dict[str, str]:
        """
        Get message for upcoming events in the next X hours
        
        Args:
            events: List of upcoming events
            hours: Number of hours ahead
            
        Returns:
            Formatted message
        """
        if not events:
            return {
                'text': f"📰 *Upcoming Events (Next {hours}h)*\n\n"
                        f"No significant events scheduled.",
                'parse_mode': 'Markdown'
            }
        
        message = f"📰 *Upcoming Events (Next {hours}h)*\n\n"
        
        # Group by time periods
        within_1h = []
        within_4h = []
        later = []
        
        now = datetime.now(timezone.utc)
        
        for event in events:
            try:
                event_time = datetime.fromisoformat(event.get('date', '').replace('Z', '+00:00'))
                hours_until = (event_time - now).total_seconds() / 3600
                
                if hours_until <= 1:
                    within_1h.append(event)
                elif hours_until <= 4:
                    within_4h.append(event)
                else:
                    later.append(event)
            except:
                later.append(event)
        
        # Format by urgency
        if within_1h:
            message += "🔥 *WITHIN 1 HOUR:*\n"
            for event in within_1h:
                message += self._format_event_line(event)
            message += "\n"
        
        if within_4h:
            message += "⏰ *Within 4 hours:*\n"
            for event in within_4h[:5]:
                message += self._format_event_line(event)
            message += "\n"
        
        if later:
            message += f"📋 *Later:* {len(later)} events\n"
        
        return {
            'text': message,
            'parse_mode': 'Markdown'
        }
    
    def _format_event_line(self, event: Dict[str, Any]) -> str:
        """
        Format a single event as a line item
        
        Args:
            event: Event dictionary
            
        Returns:
            Formatted line string
        """
        currency = event.get('country', 'N/A')
        flag = self.currency_flags.get(currency, '')
        title = event.get('title', 'Unknown')
        
        # Parse time
        try:
            event_datetime = datetime.fromisoformat(event.get('date', '').replace('Z', '+00:00'))
            time_str = event_datetime.strftime('%H:%M')
        except:
            time_str = 'TBD'
        
        # Build line
        line = f"  {flag} `{time_str}` - {currency}: {title}"
        
        # Add forecast if available for high impact
        if event.get('impact') == 'High' and event.get('forecast'):
            line += f" (f: {event.get('forecast')})"
        
        return line + "\n"
    
    def get_error_message(self, error_type: str, error_details: str) -> Dict[str, str]:
        """
        Get error notification message
        
        Args:
            error_type: Type of error
            error_details: Error details
            
        Returns:
            Formatted error message
        """
        return {
            'text': f"❌ *News System Error*\n\n"
                    f"*Type:* {error_type}\n"
                    f"*Details:* `{error_details}`\n\n"
                    f"_The system will retry automatically_",
            'parse_mode': 'Markdown'
        }
    
    def get_no_events_message(self) -> Dict[str, str]:
        """
        Get message when no events are available
        
        Returns:
            Formatted message
        """
        return {
            'text': "📅 *Economic Calendar*\n\n"
                    "No significant economic events today.\n"
                    "Markets may experience normal trading conditions.\n\n"
                    "_Check back tomorrow for updates!_",
            'parse_mode': 'Markdown'
        }