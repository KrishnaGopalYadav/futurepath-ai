from datetime import date

from app.r1_profile import _date, _set_model


class Dummy:
    start_date = None
    end_date = None
    headline = None


def test_r1_date_normalization():
    assert _date("2021-01-15") == date(2021, 1, 15)
    assert _date("2021-01-15T00:00:00Z") == date(2021, 1, 15)
    assert _date("") is None
    assert _date("not-a-date") is None


def test_r1_set_model_normalizes_dates():
    item = Dummy()
    _set_model(item, {"start_date": "2020-01-01", "end_date": "2021-01-01", "headline": "Backend Engineer"}, ("start_date", "end_date", "headline"))
    assert item.start_date == date(2020, 1, 1)
    assert item.end_date == date(2021, 1, 1)
    assert item.headline == "Backend Engineer"
