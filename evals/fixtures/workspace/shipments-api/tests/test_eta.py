import unittest

from src.shipments.eta import eta_days


class EtaTest(unittest.TestCase):
    def test_ac1_one_day_per_started_500_km(self):
        self.assertEqual(eta_days(1000), 2)

    def test_ac2_at_least_one_day(self):
        self.assertEqual(eta_days(0), 1)
