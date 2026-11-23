from funda_bot import scheduler


def test_schedule_scrapes_parsing(monkeypatch):
    called = []

    class DummyScheduler:
        def __init__(self, **kwargs):  # accepts timezone kwarg
            pass

        def add_job(self, callback, trigger, hour, minute=0):
            called.append((hour, minute))

        def start(self):
            called.append("started")

    monkeypatch.setattr(scheduler, "BackgroundScheduler", DummyScheduler)

    def noop():
        pass

    # mix ints and strings, with minutes/seconds
    scheduler.schedule_scrapes([7, "9", "12:15", "16:08:00"], noop)
    assert (7, 0) in called
    assert (9, 0) in called
    assert (12, 15) in called
    assert (16, 8) in called
    assert "started" in called


def test_schedule_scrapes_logs_one_summary_line(monkeypatch, caplog):
    """The schedule shows up as one INFO line, since APScheduler's own are muted."""
    class DummyScheduler:
        def __init__(self, **kwargs):
            pass

        def add_job(self, *args, **kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(scheduler, "BackgroundScheduler", DummyScheduler)
    with caplog.at_level("INFO", logger="funda_bot.scheduler"):
        scheduler.schedule_scrapes([7, "bad", "12:15"], lambda: None)
    assert "Scheduler started: 2 runs a day (Europe/Amsterdam) at 07:00, 12:15" in caplog.text


def test_out_of_range_time_is_skipped_not_fatal(monkeypatch, caplog):
    """'25:00' parses as numbers but APScheduler rejects it; skip it like a typo (C12)."""
    monkeypatch.setattr(scheduler.BackgroundScheduler, "start", lambda self: None)
    with caplog.at_level("INFO", logger="funda_bot.scheduler"):
        scheduler.schedule_scrapes(["7:00", "25:00", "9:61", "12:00"], lambda: None)
    assert "Skipping invalid schedule entry: '25:00'" in caplog.text
    assert "Skipping invalid schedule entry: '9:61'" in caplog.text
    assert "Scheduler started: 2 runs a day (Europe/Amsterdam) at 07:00, 12:00" in caplog.text


def test_apscheduler_info_is_muted_but_warnings_pass():
    """main.py silences APScheduler's per-run INFO lines, not its warnings/errors."""
    import logging
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import main  # noqa: F401 — importing configures logging

    log = logging.getLogger("apscheduler.executors.default")
    assert not log.isEnabledFor(logging.INFO)
    assert log.isEnabledFor(logging.WARNING)
    assert log.isEnabledFor(logging.ERROR)
