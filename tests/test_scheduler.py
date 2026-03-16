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

    monkeypatch.setattr(scheduler, "BlockingScheduler", DummyScheduler)

    def noop():
        pass

    # mix ints and strings, with minutes/seconds
    scheduler.schedule_scrapes([7, "9", "12:15", "16:08:00"], noop)
    assert (7, 0) in called
    assert (9, 0) in called
    assert (12, 15) in called
    assert (16, 8) in called
    assert "started" in called
