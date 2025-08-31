"""
Tests for the CronParser module.

Tests cover:
- Valid cron expression parsing
- Invalid expression handling
- Special expression support
- Next execution time calculation
- Field validation
"""

import unittest
from datetime import datetime, timedelta
import tempfile
import os

# Add parent directory to path for imports
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.cron_parser import CronParser, CronExpression


class TestCronExpression(unittest.TestCase):
    """Test CronExpression dataclass validation."""

    def test_valid_cron_expression_creation(self):
        """Valid CronExpression should be created successfully."""
        expr = CronExpression(
            minute={0},
            hour={12},
            day={1},
            month={1},
            weekday={0},
            original_expression="0 12 1 1 0",
        )
        self.assertEqual(expr.minute, {0})

    def test_invalid_minute_raises_error(self):
        """Invalid minute value should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            CronExpression(
                minute={60},  # Invalid: max is 59
                hour={12},
                day={1},
                month={1},
                weekday={0},
                original_expression="60 12 1 1 0",
            )
        self.assertIn("minute", str(cm.exception))

    def test_invalid_hour_raises_error(self):
        """Invalid hour value should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            CronExpression(
                minute={0},
                hour={24},  # Invalid: max is 23
                day={1},
                month={1},
                weekday={0},
                original_expression="0 24 1 1 0",
            )
        self.assertIn("hour", str(cm.exception))

    def test_invalid_day_raises_error(self):
        """Invalid day value should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            CronExpression(
                minute={0},
                hour={12},
                day={32},  # Invalid: max is 31
                month={1},
                weekday={0},
                original_expression="0 12 32 1 0",
            )
        self.assertIn("day", str(cm.exception))

    def test_invalid_month_raises_error(self):
        """Invalid month value should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            CronExpression(
                minute={0},
                hour={12},
                day={1},
                month={13},  # Invalid: max is 12
                weekday={0},
                original_expression="0 12 1 13 0",
            )
        self.assertIn("month", str(cm.exception))

    def test_invalid_weekday_raises_error(self):
        """Invalid weekday value should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            CronExpression(
                minute={0},
                hour={12},
                day={1},
                month={1},
                weekday={7},  # Invalid: max is 6
                original_expression="0 12 1 1 7",
            )
        self.assertIn("weekday", str(cm.exception))


class TestCronParser(unittest.TestCase):
    """Test CronParser functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = CronParser()

    def test_parse_simple_expression(self):
        """Simple cron expression should parse correctly."""
        expr = self.parser.parse("30 14 1 1 0")
        self.assertEqual(expr.minute, {30})

    def test_parse_simple_expression_hour(self):
        """Simple cron expression hour should parse correctly."""
        expr = self.parser.parse("30 14 1 1 0")
        self.assertEqual(expr.hour, {14})

    def test_parse_simple_expression_day(self):
        """Simple cron expression day should parse correctly."""
        expr = self.parser.parse("30 14 1 1 0")
        self.assertEqual(expr.day, {1})

    def test_parse_simple_expression_month(self):
        """Simple cron expression month should parse correctly."""
        expr = self.parser.parse("30 14 1 1 0")
        self.assertEqual(expr.month, {1})

    def test_parse_simple_expression_weekday(self):
        """Simple cron expression weekday should parse correctly."""
        expr = self.parser.parse("30 14 1 1 0")
        self.assertEqual(expr.weekday, {0})

    def test_parse_wildcard_expression(self):
        """Wildcard cron expression should parse correctly."""
        expr = self.parser.parse("* * * * *")
        self.assertEqual(expr.minute, set(range(0, 60)))

    def test_parse_wildcard_expression_hour(self):
        """Wildcard cron expression hour should parse correctly."""
        expr = self.parser.parse("* * * * *")
        self.assertEqual(expr.hour, set(range(0, 24)))

    def test_parse_list_expression(self):
        """List cron expression should parse correctly."""
        expr = self.parser.parse("0,15,30,45 * * * *")
        self.assertEqual(expr.minute, {0, 15, 30, 45})

    def test_parse_range_expression(self):
        """Range cron expression should parse correctly."""
        expr = self.parser.parse("0 9-17 * * *")
        self.assertEqual(expr.hour, set(range(9, 18)))

    def test_parse_step_expression(self):
        """Step cron expression should parse correctly."""
        expr = self.parser.parse("*/15 * * * *")
        self.assertEqual(expr.minute, {0, 15, 30, 45})

    def test_parse_range_with_step_expression(self):
        """Range with step cron expression should parse correctly."""
        expr = self.parser.parse("0 9-17/2 * * *")
        self.assertEqual(expr.hour, {9, 11, 13, 15, 17})

    def test_parse_special_daily_expression(self):
        """Special @daily expression should parse correctly."""
        expr = self.parser.parse("@daily")
        self.assertEqual(expr.minute, {0})

    def test_parse_special_daily_expression_hour(self):
        """Special @daily expression hour should parse correctly."""
        expr = self.parser.parse("@daily")
        self.assertEqual(expr.hour, {0})

    def test_parse_special_hourly_expression(self):
        """Special @hourly expression should parse correctly."""
        expr = self.parser.parse("@hourly")
        self.assertEqual(expr.minute, {0})

    def test_parse_special_hourly_expression_hour(self):
        """Special @hourly expression hour should parse correctly."""
        expr = self.parser.parse("@hourly")
        self.assertEqual(expr.hour, set(range(0, 24)))

    def test_parse_special_weekly_expression(self):
        """Special @weekly expression should parse correctly."""
        expr = self.parser.parse("@weekly")
        self.assertEqual(expr.weekday, {0})  # Sunday

    def test_parse_special_monthly_expression(self):
        """Special @monthly expression should parse correctly."""
        expr = self.parser.parse("@monthly")
        self.assertEqual(expr.day, {1})

    def test_parse_special_yearly_expression(self):
        """Special @yearly expression should parse correctly."""
        expr = self.parser.parse("@yearly")
        self.assertEqual(expr.month, {1})

    def test_empty_expression_raises_error(self):
        """Empty cron expression should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.parser.parse("")
        self.assertIn("Empty", str(cm.exception))

    def test_invalid_field_count_raises_error(self):
        """Wrong number of fields should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.parser.parse("0 12 1 1")  # Missing weekday field
        self.assertIn("5 fields", str(cm.exception))

    def test_invalid_characters_raises_error(self):
        """Invalid characters should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.parser.parse("0 12 1 1 abc")
        self.assertIn("Invalid characters", str(cm.exception))

    def test_unknown_special_expression_raises_error(self):
        """Unknown special expression should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.parser.parse("@unknown")
        self.assertIn("Unknown special", str(cm.exception))

    def test_invalid_minute_value_raises_error(self):
        """Invalid minute value should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.parser.parse("60 12 1 1 0")
        self.assertIn("out of range", str(cm.exception))

    def test_invalid_step_value_raises_error(self):
        """Invalid step value should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.parser.parse("*/0 * * * *")  # Step cannot be 0
        self.assertIn("Invalid step value", str(cm.exception))

    def test_invalid_range_raises_error(self):
        """Invalid range should raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.parser.parse("0 17-9 * * *")  # Start > end
        self.assertIn("Invalid range", str(cm.exception))

    def test_validate_expression_returns_true_for_valid(self):
        """validate_expression should return True for valid expressions."""
        result = self.parser.validate_expression("0 12 * * *")
        self.assertTrue(result)

    def test_validate_expression_returns_false_for_invalid(self):
        """validate_expression should return False for invalid expressions."""
        result = self.parser.validate_expression("invalid")
        self.assertFalse(result)

    def test_next_execution_calculates_correctly(self):
        """next_execution should calculate next run time correctly."""
        expr = self.parser.parse("0 12 * * *")  # Daily at noon
        from_time = datetime(2024, 1, 1, 10, 0, 0)  # 10 AM
        next_time = self.parser.next_execution(expr, from_time)
        expected = datetime(2024, 1, 1, 12, 0, 0)  # Same day at noon
        self.assertEqual(next_time, expected)

    def test_next_execution_skips_to_next_day(self):
        """next_execution should skip to next day if time passed."""
        expr = self.parser.parse("0 12 * * *")  # Daily at noon
        from_time = datetime(2024, 1, 1, 14, 0, 0)  # 2 PM (after noon)
        next_time = self.parser.next_execution(expr, from_time)
        expected = datetime(2024, 1, 2, 12, 0, 0)  # Next day at noon
        self.assertEqual(next_time, expected)

    def test_weekday_conversion_sunday(self):
        """Weekday conversion should handle Sunday correctly."""
        # Cron uses 0=Sunday, Python uses 6=Sunday
        expr = self.parser.parse("0 12 * * 0")  # Sunday at noon
        # Test with a known Sunday: 2024-01-07
        from_time = datetime(2024, 1, 6, 10, 0, 0)  # Saturday
        next_time = self.parser.next_execution(expr, from_time)
        self.assertEqual(next_time.weekday(), 6)  # Sunday in Python weekday

    def test_weekday_conversion_monday(self):
        """Weekday conversion should handle Monday correctly."""
        # Cron uses 1=Monday, Python uses 0=Monday
        expr = self.parser.parse("0 12 * * 1")  # Monday at noon
        from_time = datetime(2024, 1, 6, 10, 0, 0)  # Saturday
        next_time = self.parser.next_execution(expr, from_time)
        self.assertEqual(next_time.weekday(), 0)  # Monday in Python weekday


if __name__ == "__main__":
    unittest.main()
