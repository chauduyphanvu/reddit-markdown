"""
Cron expression parser for scheduling tasks.

Supports standard 5-field cron format: minute hour day month weekday
Also supports special expressions like @daily, @hourly, @weekly, etc.
"""

import re
import calendar
from datetime import datetime, timedelta
from typing import List, Optional, Set, Union
from dataclasses import dataclass
from colored_logger import get_colored_logger

logger = get_colored_logger(__name__)


@dataclass
class CronExpression:
    """Represents a parsed cron expression with calculated next execution times."""

    minute: Set[int]
    hour: Set[int]
    day: Set[int]
    month: Set[int]
    weekday: Set[int]
    original_expression: str

    def __post_init__(self):
        """Validate parsed values are within valid ranges."""
        self._validate_field("minute", self.minute, 0, 59)
        self._validate_field("hour", self.hour, 0, 23)
        self._validate_field("day", self.day, 1, 31)
        self._validate_field("month", self.month, 1, 12)
        self._validate_field("weekday", self.weekday, 0, 6)

    def _validate_field(
        self, field_name: str, values: Set[int], min_val: int, max_val: int
    ):
        """Validate that field values are within acceptable ranges."""
        for value in values:
            if not min_val <= value <= max_val:
                raise ValueError(
                    f"Invalid {field_name} value: {value} (must be {min_val}-{max_val})"
                )


class CronParser:
    """
    Parses cron expressions safely and efficiently.

    Supports:
    - Standard 5-field format: minute hour day month weekday
    - Special expressions: @yearly, @monthly, @weekly, @daily, @hourly
    - Wildcards: *
    - Lists: 1,3,5
    - Ranges: 1-5
    - Steps: */15, 1-10/2
    """

    # Special expressions mapping
    SPECIAL_EXPRESSIONS = {
        "@yearly": "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
        "@monthly": "0 0 1 * *",
        "@weekly": "0 0 * * 0",
        "@daily": "0 0 * * *",
        "@midnight": "0 0 * * *",
        "@hourly": "0 * * * *",
    }

    # Field constraints
    FIELD_RANGES = {
        0: (0, 59),  # minute
        1: (0, 23),  # hour
        2: (1, 31),  # day
        3: (1, 12),  # month
        4: (0, 6),  # weekday (0 = Sunday)
    }

    def __init__(self):
        """Initialize the cron parser."""
        self._compiled_regex = re.compile(r"^[0-9*,\-/\s]+$")

    def parse(self, expression: str) -> CronExpression:
        """
        Parse a cron expression into a CronExpression object.

        Args:
            expression: The cron expression string

        Returns:
            CronExpression object with parsed fields

        Raises:
            ValueError: If the expression is invalid or unsafe
        """
        expression = expression.strip()

        if not expression:
            raise ValueError("Empty cron expression")

        # Handle special expressions
        if expression.startswith("@"):
            if expression not in self.SPECIAL_EXPRESSIONS:
                raise ValueError(f"Unknown special expression: {expression}")
            expression = self.SPECIAL_EXPRESSIONS[expression]

        # Basic validation - only allow safe characters
        if not self._compiled_regex.match(expression):
            raise ValueError(f"Invalid characters in cron expression: {expression}")

        # Split into fields
        fields = expression.split()
        if len(fields) != 5:
            raise ValueError(
                f"Cron expression must have exactly 5 fields, got {len(fields)}"
            )

        try:
            parsed_fields = []
            original_expression = expression

            for i, field in enumerate(fields):
                min_val, max_val = self.FIELD_RANGES[i]
                parsed_values = self._parse_field(field, min_val, max_val)
                parsed_fields.append(parsed_values)

            return CronExpression(
                minute=parsed_fields[0],
                hour=parsed_fields[1],
                day=parsed_fields[2],
                month=parsed_fields[3],
                weekday=parsed_fields[4],
                original_expression=original_expression,
            )

        except Exception as e:
            raise ValueError(
                f"Failed to parse cron expression '{expression}': {str(e)}"
            )

    def _parse_field(self, field: str, min_val: int, max_val: int) -> Set[int]:
        """
        Parse a single field of a cron expression.

        Args:
            field: The field string (e.g., "*/15", "1-5", "1,3,5")
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Set of integer values for this field
        """
        if field == "*":
            return set(range(min_val, max_val + 1))

        values = set()

        # Handle comma-separated values
        for part in field.split(","):
            part = part.strip()
            if not part:
                continue

            # Handle step values (e.g., "*/15" or "1-10/2")
            step = 1
            if "/" in part:
                part, step_str = part.split("/", 1)
                try:
                    step = int(step_str)
                    if step <= 0:
                        raise ValueError(f"Step must be positive, got {step}")
                except ValueError as e:
                    raise ValueError(f"Invalid step value: {step_str}")

            # Handle ranges (e.g., "1-5")
            if "-" in part:
                try:
                    start_str, end_str = part.split("-", 1)
                    start = int(start_str) if start_str != "*" else min_val
                    end = int(end_str) if end_str != "*" else max_val

                    if start > end:
                        raise ValueError(f"Invalid range: {start}-{end}")

                    for val in range(start, end + 1, step):
                        if min_val <= val <= max_val:
                            values.add(val)

                except ValueError as e:
                    if "invalid literal" in str(e):
                        raise ValueError(f"Invalid range format: {part}")
                    raise

            # Handle wildcard with step (e.g., "*/15")
            elif part == "*":
                for val in range(min_val, max_val + 1, step):
                    values.add(val)

            # Handle single values
            else:
                try:
                    val = int(part)
                    if min_val <= val <= max_val:
                        values.add(val)
                    else:
                        raise ValueError(
                            f"Value {val} out of range [{min_val}-{max_val}]"
                        )
                except ValueError as e:
                    if "invalid literal" in str(e):
                        raise ValueError(f"Invalid field value: {part}")
                    raise

        if not values:
            raise ValueError(f"No valid values parsed from field: {field}")

        return values

    def next_execution(
        self, cron_expr: CronExpression, from_time: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate the next execution time for a cron expression.

        Args:
            cron_expr: The parsed cron expression
            from_time: Calculate from this time (defaults to now)

        Returns:
            The next execution time
        """
        if from_time is None:
            from_time = datetime.now()

        # Start from the next minute to avoid immediate execution
        next_time = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Find the next valid time (limit iterations to prevent infinite loops)
        max_iterations = 366 * 24 * 60  # Max 1 year of minutes
        iterations = 0

        while iterations < max_iterations:
            if self._matches_cron(next_time, cron_expr):
                return next_time

            next_time += timedelta(minutes=1)
            iterations += 1

        raise RuntimeError("Could not find next execution time within reasonable limit")

    def _matches_cron(self, dt: datetime, cron_expr: CronExpression) -> bool:
        """Check if a datetime matches a cron expression."""
        return (
            dt.minute in cron_expr.minute
            and dt.hour in cron_expr.hour
            and dt.day in cron_expr.day
            and dt.month in cron_expr.month
            and dt.weekday() in self._convert_weekday(cron_expr.weekday)
        )

    def _convert_weekday(self, cron_weekdays: Set[int]) -> Set[int]:
        """Convert cron weekday format (0=Sunday) to Python format (0=Monday)."""
        python_weekdays = set()
        for cron_day in cron_weekdays:
            # Cron: 0=Sunday, 1=Monday, ..., 6=Saturday
            # Python: 0=Monday, 1=Tuesday, ..., 6=Sunday
            if cron_day == 0:  # Sunday
                python_weekdays.add(6)
            else:
                python_weekdays.add(cron_day - 1)
        return python_weekdays

    def validate_expression(self, expression: str) -> bool:
        """
        Validate a cron expression without parsing it fully.

        Args:
            expression: The cron expression to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            self.parse(expression)
            return True
        except ValueError:
            return False
