import json
from pathlib import Path
from cbxtools.stats_tracker import StatsTracker


def test_stats_tracker_unicode_path(tmp_path):
    file_path = tmp_path / "данные.json"
    tracker = StatsTracker(file_path)
    tracker.add_run(1, 100, 50, 1.0)
    assert file_path.exists()
    tracker2 = StatsTracker(file_path)
    assert tracker2.stats["run_count"] == 1

