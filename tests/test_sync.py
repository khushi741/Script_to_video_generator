import pytest
from src.sync import SyncEngine


def test_format_timestamp():
    # 0 seconds -> 00:00:00,000
    assert SyncEngine._format_timestamp(0.0) == "00:00:00,000"

    # 1.5 seconds -> 00:00:01,500
    assert SyncEngine._format_timestamp(1.5) == "00:00:01,500"

    # 65.25 seconds -> 00:01:05,250
    assert SyncEngine._format_timestamp(65.25) == "00:01:05,250"

    # 3661.123 seconds -> 01:01:01,123
    assert SyncEngine._format_timestamp(3661.123) == "01:01:01,123"


def test_calculate_sync_parameters():
    # Test safe duration calculation for a 10s audio clip with 3 visual items
    params = SyncEngine.calculate_sync_parameters(audio_duration=10.0, visual_complexity=3)
    assert "run_time_per_item" in params
    assert "hold_time" in params
    assert "target_duration" in params
    assert params["target_duration"] == 10.0
    # Hold duration should be positive
    assert params["hold_time"] > 0
    # Sum of active and hold should be close to total duration
    total_calc = (params["run_time_per_item"] * 3) + params["hold_time"]
    assert abs(total_calc - 10.0) < 0.01


def test_calculate_sync_parameters_minimum_duration():
    # Even if audio duration is very short (e.g., 1s), safety ensures at least 3.0s
    params = SyncEngine.calculate_sync_parameters(audio_duration=1.0, visual_complexity=2)
    assert params["target_duration"] >= 3.0
