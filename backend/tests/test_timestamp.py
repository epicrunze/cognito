"""
Tests for timestamp utilities.

Unit tests for the centralized timestamp handling module.
"""

from datetime import datetime, timezone, timedelta

import pytest

from app.utils.timestamp import (
    utc_now,
    utc_now_aware,
    ensure_utc,
    parse_iso_timestamp,
    compare_timestamps,
    to_iso_string,
)


class TestUtcNow:
    """Tests for utc_now function."""

    def test_returns_naive_datetime_for_database_storage(self):
        """utc_now() should return a naive datetime (for database storage)."""
        result = utc_now()
        assert result.tzinfo is None  # Naive datetime

    def test_returns_current_utc_time(self):
        """utc_now() should return approximately current UTC time."""
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        result = utc_now()
        after = datetime.now(timezone.utc).replace(tzinfo=None)
        assert before <= result <= after


class TestUtcNowAware:
    """Tests for utc_now_aware function."""

    def test_returns_timezone_aware_datetime(self):
        """utc_now_aware() should return a timezone-aware datetime."""
        result = utc_now_aware()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc


class TestEnsureUtc:
    """Tests for ensure_utc function."""

    def test_adds_utc_to_naive_datetime(self):
        """ensure_utc() should add UTC timezone to naive datetime."""
        naive = datetime(2024, 12, 30, 12, 0, 0)
        result = ensure_utc(naive)
        assert result.tzinfo == timezone.utc
        assert result.hour == 12  # Time should not change

    def test_returns_none_for_none(self):
        """ensure_utc() should return None when given None."""
        assert ensure_utc(None) is None

    def test_converts_aware_to_utc(self):
        """ensure_utc() should convert aware datetime to UTC."""
        aware = datetime(2024, 12, 30, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_utc(aware)
        assert result.tzinfo == timezone.utc


class TestParseIsoTimestamp:
    """Tests for parse_iso_timestamp function."""

    def test_parse_with_z_suffix(self):
        """Should parse ISO timestamp with Z suffix."""
        result = parse_iso_timestamp("2024-12-30T12:00:00Z")
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 30
        assert result.hour == 12
        assert result.tzinfo == timezone.utc

    def test_parse_with_positive_offset(self):
        """Should parse ISO timestamp with positive offset and convert to UTC."""
        result = parse_iso_timestamp("2024-12-30T17:00:00+05:00")
        # 17:00 in +05:00 = 12:00 UTC
        assert result.hour == 12
        assert result.tzinfo == timezone.utc

    def test_parse_with_negative_offset(self):
        """Should parse ISO timestamp with negative offset and convert to UTC."""
        result = parse_iso_timestamp("2024-12-30T07:00:00-05:00")
        # 07:00 in -05:00 = 12:00 UTC
        assert result.hour == 12
        assert result.tzinfo == timezone.utc

    def test_parse_naive_datetime(self):
        """Should treat naive datetime as UTC."""
        result = parse_iso_timestamp("2024-12-30T12:00:00")
        assert result.hour == 12
        assert result.tzinfo == timezone.utc

    def test_parse_invalid_timestamp_raises_error(self):
        """Should raise ValueError for invalid timestamp."""
        with pytest.raises(ValueError, match="Cannot parse timestamp"):
            parse_iso_timestamp("not-a-timestamp")


class TestCompareTimestamps:
    """Tests for compare_timestamps function."""

    def test_client_newer_returns_true(self):
        """Client change should apply when client timestamp is newer."""
        # Server is 1 hour ago
        server_dt = utc_now() - timedelta(hours=1)
        # Client is now
        client_ts = utc_now().isoformat()
        
        result = compare_timestamps(client_ts, server_dt)
        assert result is True

    def test_server_newer_returns_false(self):
        """Client change should be skipped when server timestamp is newer."""
        # Server is now
        server_dt = utc_now()
        # Client is 1 hour ago
        client_ts = (utc_now() - timedelta(hours=1)).isoformat()
        
        result = compare_timestamps(client_ts, server_dt)
        assert result is False

    def test_equal_timestamps_returns_true(self):
        """Client change should apply when timestamps are equal."""
        now = utc_now()
        server_dt = now
        client_ts = now.isoformat()
        
        result = compare_timestamps(client_ts, server_dt)
        assert result is True

    def test_none_client_timestamp_returns_true(self):
        """Should return True when client timestamp is None."""
        server_dt = utc_now()
        
        result = compare_timestamps(None, server_dt)
        assert result is True

    def test_empty_client_timestamp_returns_true(self):
        """Should return True when client timestamp is empty string."""
        server_dt = utc_now()
        
        result = compare_timestamps("", server_dt)
        assert result is True

    def test_naive_server_datetime_treated_as_utc(self):
        """Naive server datetime should be treated as UTC."""
        # Naive datetime 1 hour ago
        server_dt = datetime.utcnow() - timedelta(hours=1)
        # Client is now (with timezone)
        client_ts = utc_now().isoformat()
        
        result = compare_timestamps(client_ts, server_dt)
        assert result is True

    def test_client_with_z_suffix(self):
        """Should handle client timestamp with Z suffix."""
        server_dt = datetime(2024, 12, 29, 12, 0, 0, tzinfo=timezone.utc)
        client_ts = "2024-12-30T12:00:00Z"  # Day later
        
        result = compare_timestamps(client_ts, server_dt)
        assert result is True

    def test_client_with_offset(self):
        """Should handle client timestamp with timezone offset."""
        server_dt = datetime(2024, 12, 30, 12, 0, 0, tzinfo=timezone.utc)
        # 17:00 in +05:00 = 12:00 UTC (equal)
        client_ts = "2024-12-30T17:00:00+05:00"
        
        result = compare_timestamps(client_ts, server_dt)
        assert result is True


class TestToIsoString:
    """Tests for to_iso_string function."""

    def test_none_returns_none(self):
        """Should return None for None input."""
        result = to_iso_string(None)
        assert result is None

    def test_aware_datetime_to_utc(self):
        """Should convert aware datetime to UTC ISO string."""
        # Create a datetime in EST (-05:00)
        est = timezone(timedelta(hours=-5))
        dt = datetime(2024, 12, 30, 12, 0, 0, tzinfo=est)
        
        result = to_iso_string(dt)
        # Should be 17:00 UTC
        assert "17:00:00" in result
        assert "+00:00" in result

    def test_naive_datetime_assumed_utc(self):
        """Should treat naive datetime as UTC."""
        dt = datetime(2024, 12, 30, 12, 0, 0)
        
        result = to_iso_string(dt)
        assert "12:00:00" in result
        assert "+00:00" in result
