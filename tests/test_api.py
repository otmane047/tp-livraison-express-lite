"""Tests d'intégration des endpoints de l'API FastAPI (api/app.py).

Valide :
- /health
- /health/ready (modèle chargé ou non)
- /predict (format conforme au schéma OpenAPI)
"""

import unittest
from fastapi.testclient import TestClient

from livraison_express_lite.api.app import create_app
from livraison_express_lite.domain.entities import OrderEntity


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = TestClient(cls.app)
        cls.sample_payload = {
            "hour": 14,
            "day_of_week": 2,
            "weekend": 0,
            "distance_km": 3.5,
            "order_value_eur": 89.9,
            "weight_kg": 2.4,
            "stock_available": 1,
            "preparation_time_min": 18.0,
            "carrier_capacity": 0.85,
            "weather": "normal",
            "delivery_zone": "centre",
            "customer_type": "premium",
        }

    def test_health_endpoint(self):
        """Vérifie la sonde de vivacité (/health)."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_ready_endpoint(self):
        """Vérifie la sonde de disponibilité (/health/ready)."""
        response = self.client.get("/health/ready")
        self.assertIn(response.status_code, [200, 503])
        if response.status_code == 200:
            self.assertEqual(response.json(), {"status": "ready"})
        else:
            self.assertEqual(response.json()["status"], "not_ready")

    def test_predict_endpoint_success(self):
        """Vérifie la prédiction unitaire (/predict)."""
        response = self.client.post("/predict", json=self.sample_payload)
        if response.status_code == 200:
            data = response.json()
            self.assertIn("express_eligible", data)
            self.assertIsInstance(data["express_eligible"], bool)
            self.assertIn(data["decision"], ["oui", "non"])
            self.assertGreaterEqual(data["probability"], 0.0)
            self.assertLessEqual(data["probability"], 1.0)
            self.assertEqual(data["model_version"], "1.0.0")
            self.assertIn("prediction_timestamp", data)
        else:
            # 503 si modèle non encore entraîné
            self.assertEqual(response.status_code, 503)

    def test_predict_endpoint_invalid_payload(self):
        """Vérifie qu'un payload incomplet lève une 422 Unprocessable Entity."""
        bad_payload = {"hour": 14}
        response = self.client.post("/predict", json=bad_payload)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
