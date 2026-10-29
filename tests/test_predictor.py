"""Tests unitaires pour le service d'inférence (MLPredict)."""

import unittest

from livraison_express_lite.core.core import Core
from livraison_express_lite.domain.entities import OrderEntity, PredictionEntity


class TestPredictor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = Core(load_model=True)
        cls.predictor = cls.core.get_predict_service()
        cls.sample_order = OrderEntity(
            order_id="CMD-TEST-002",
            hour=14,
            day_of_week=2,
            weekend=0,
            distance_km=3.5,
            order_value_eur=89.9,
            weight_kg=2.4,
            stock_available=1,
            preparation_time_min=18.0,
            carrier_capacity=0.85,
            weather="normal",
            delivery_zone="centre",
            customer_type="premium",
        )

    def test_predict_contract(self):
        self.assertIsNotNone(self.predictor)
        result = self.predictor.predict(self.sample_order)

        self.assertIsInstance(result, PredictionEntity)
        self.assertIsInstance(result.express_eligible, bool)
        self.assertIn(result.decision, ["oui", "non"])
        self.assertGreaterEqual(result.probability, 0.0)
        self.assertLessEqual(result.probability, 1.0)
        self.assertEqual(result.model_version, "1.0.0")
        self.assertIsNotNone(result.prediction_timestamp)


if __name__ == "__main__":
    unittest.main()
