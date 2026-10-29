"""Tests unitaires pour les adaptateurs d'infrastructure (OrderRepository et ModelRepository)."""

import tempfile
import unittest
from pathlib import Path

from livraison_express_lite.domain.entities import ModelEntity, OrderEntity
from livraison_express_lite.infrastructure.implementation.dev.in_memory_model_repository import (
    FileModelRepository,
)
from livraison_express_lite.infrastructure.implementation.dev.in_memory_order_repository import (
    InMemoryOrderRepository,
)


class TestInfra(unittest.TestCase):
    def setUp(self):
        self.sample_order = OrderEntity(
            order_id="CMD-TEST-001",
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

    def test_in_memory_order_repository_empty(self):
        repo = InMemoryOrderRepository(generated=False)
        self.assertEqual(repo.count(), 0)
        self.assertIsNone(repo.get("CMD-NONE"))

        repo.save(self.sample_order)
        self.assertEqual(repo.count(), 1)
        self.assertEqual(repo.get("CMD-TEST-001"), self.sample_order)
        self.assertEqual(len(repo.get_all()), 1)

        repo.clear()
        self.assertEqual(repo.count(), 0)

    def test_in_memory_order_repository_generated(self):
        repo = InMemoryOrderRepository(generated=True)
        self.assertEqual(repo.count(), 6000)
        orders, labels = repo.get_training_data()
        self.assertEqual(len(orders), 6000)
        self.assertEqual(len(labels), 6000)

    def test_file_model_repository(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_file = Path(tmp_dir) / "test_model.joblib"
            repo = FileModelRepository(str(model_file))

            # Initialement absent
            self.assertIsNone(repo.load())

            # Sauvegarde d'un objet factice et de sa model_card
            dummy_model = {"pipeline": "mock"}
            card = ModelEntity(
                project="test-project",
                model_version="1.0.0",
                model_type="LogisticRegression",
                task="classification",
                target="express_eligible",
                threshold=0.5,
                features=["f1", "f2"],
                metrics={"accuracy": 0.8},
            )
            repo.save(dummy_model, card)

            self.assertTrue(model_file.exists())
            self.assertTrue((model_file.parent / "metrics.json").exists())
            self.assertTrue((model_file.parent / "features.json").exists())

            loaded = repo.load()
            self.assertEqual(loaded, dummy_model)


if __name__ == "__main__":
    unittest.main()
