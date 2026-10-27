import unittest
from datetime import date

from app.r1_profile import _date, _set_model


class Dummy:
    start_date = None
    end_date = None
    headline = None


class R1ProfileHelperTests(unittest.TestCase):
    def test_r1_date_normalization(self):
        self.assertEqual(_date("2021-01-15"), date(2021, 1, 15))
        self.assertEqual(_date("2021-01-15T00:00:00Z"), date(2021, 1, 15))
        self.assertIsNone(_date(""))
        self.assertIsNone(_date("not-a-date"))

    def test_r1_set_model_normalizes_dates(self):
        item = Dummy()
        _set_model(item, {"start_date": "2020-01-01", "end_date": "2021-01-01", "headline": "Backend Engineer"}, ("start_date", "end_date", "headline"))
        self.assertEqual(item.start_date, date(2020, 1, 1))
        self.assertEqual(item.end_date, date(2021, 1, 1))
        self.assertEqual(item.headline, "Backend Engineer")


if __name__ == "__main__":
    unittest.main()
