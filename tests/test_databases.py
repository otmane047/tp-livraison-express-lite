"""Tests unitaires pour les adaptateurs de base de données PostgreSQL et MongoDB."""

import unittest
from unittest.mock import MagicMock, patch

from livraison_express_lite.domain.entities import OrderEntity
from livraison_express_lite.infrastructure.implementation.mongo_order_repository import (
    MongoOrderRepository,
)
from livraison_express_lite.infrastructure.implementation.postgres_order_repository import (
    PostgresOrderRepository,
)


class TestDatabaseRepositories(unittest.TestCase):
    def setUp(self):
        self.sample_order = OrderEntity(
            order_id="ERP-00000001",
            hour=10,
            day_of_week=1,
            weekend=0,
            distance_km=12.5,
            order_value_eur=95.0,
            weight_kg=3.2,
            stock_available=1,
            preparation_time_min=20.0,
            carrier_capacity=0.8,
            weather="normal",
            delivery_zone="centre",
            customer_type="premium",
        )

    @patch("livraison_express_lite.infrastructure.implementation.postgres_order_repository.psycopg.connect")
    def test_postgres_order_repository_get_and_count(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Simulation d'une ligne avec weekend et prep_time nuls (historique ancien)
        mock_cursor.fetchone.side_effect = [
            {
                "order_id": "ERP-00000001",
                "hour": 10,
                "day_of_week": 6,  # Dimanche
                "weekend": None,  # Test de la dérivation automatique
                "distance_km": 12.5,
                "order_value_eur": 95.0,
                "weight_kg": 3.2,
                "stock_available": 1,
                "preparation_time_min": None,  # Test de la valeur par défaut
                "carrier_capacity": 0.8,
                "weather": "normal",
                "delivery_zone": "centre",
                "customer_type": "premium",
            },
            {"count": 42},  # pour count()
        ]

        repo = PostgresOrderRepository("postgresql://livraison:livraison@localhost:5432/livraison_express")
        order = repo.get("ERP-00000001")

        self.assertIsNotNone(order)
        self.assertEqual(order.order_id, "ERP-00000001")
        self.assertEqual(order.weekend, 1)  # Dérivé car day_of_week=6 >= 5
        self.assertEqual(order.preparation_time_min, 25.0)  # Complété par défaut
        self.assertEqual(repo.count(), 42)

    @patch("livraison_express_lite.infrastructure.implementation.postgres_order_repository.psycopg.connect")
    def test_postgres_order_repository_save(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        repo = PostgresOrderRepository("postgresql://livraison:livraison@localhost:5432/livraison_express")
        repo.save(self.sample_order)

        self.assertTrue(mock_cursor.execute.called)
        self.assertTrue(mock_conn.commit.called)

    @patch("livraison_express_lite.infrastructure.implementation.mongo_order_repository.MongoClient")
    def test_mongo_order_repository_get_and_save(self, mock_mongo_client):
        mock_client_inst = MagicMock()
        mock_collection = MagicMock()
        mock_client_inst.__getitem__.return_value.__getitem__.return_value = mock_collection
        mock_mongo_client.return_value = mock_client_inst

        mock_collection.find_one.return_value = {
            "order_id": "ERP-00000001",
            "hour": 10,
            "day_of_week": 2,
            "weekend": 0,
            "distance_km": 12.5,
            "order_value_eur": 95.0,
            "weight_kg": 3.2,
            "stock_available": 1,
            "preparation_time_min": 20.0,
            "carrier_capacity": 0.8,
            "weather": "normal",
            "delivery_zone": "centre",
            "customer_type": "premium",
        }
        mock_collection.count_documents.return_value = 100

        repo = MongoOrderRepository("mongodb://localhost:27017")
        order = repo.get("ERP-00000001")

        self.assertIsNotNone(order)
        self.assertEqual(order.order_id, "ERP-00000001")
        self.assertEqual(repo.count(), 100)

        repo.save(self.sample_order)
        self.assertTrue(mock_collection.replace_one.called)

    @patch("livraison_express_lite.infrastructure.implementation.postgres_order_repository.psycopg.connect")
    def test_postgres_get_training_data_and_prediction(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Simulation de plusieurs lignes retournées par get_all / fetchall
        mock_cursor.fetchall.return_value = [
            {
                "order_id": f"ERP-0000000{i}",
                "hour": 10 + i,
                "day_of_week": i % 7,
                "weekend": 1 if (i % 7) >= 5 else 0,
                "distance_km": 5.0 * (i + 1),
                "order_value_eur": 50.0 + 10 * i,
                "weight_kg": 2.0 + i,
                "stock_available": 1,
                "preparation_time_min": 15.0 + i,
                "carrier_capacity": 0.9,
                "weather": "clear",
                "delivery_zone": "centre",
                "customer_type": "premium",
            }
            for i in range(10)
        ]

        repo = PostgresOrderRepository("postgresql://livraison:livraison@localhost:5432/livraison_express")
        orders, labels = repo.get_training_data(max_rows=10)

        self.assertEqual(len(orders), 10)
        self.assertEqual(len(labels), 10)
        self.assertIn(labels[0], (0, 1))

    @patch("livraison_express_lite.infrastructure.implementation.postgres_order_repository.psycopg.connect")
    def test_api_predict_with_database_order(self, mock_connect):
        from fastapi.testclient import TestClient

        from livraison_express_lite.api.app import create_app
        from livraison_express_lite.core.core import Core

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            "order_id": "ERP-00000099",
            "hour": 14,
            "day_of_week": 2,
            "weekend": 0,
            "distance_km": 8.0,
            "order_value_eur": 120.0,
            "weight_kg": 4.5,
            "stock_available": 1,
            "preparation_time_min": 18.0,
            "carrier_capacity": 0.85,
            "weather": "normal",
            "delivery_zone": "centre",
            "customer_type": "premium",
        }

        # Récupération de l'entité depuis le repo
        repo = PostgresOrderRepository("postgresql://livraison:livraison@localhost:5432/livraison_express")
        order = repo.get("ERP-00000099")
        self.assertIsNotNone(order)

        # Envoi à l'API
        core = Core(load_model=False)
        app = create_app()
        app.state.predict_service = core.get_predict_service()
        client = TestClient(app)

        payload = {
            "order_id": order.order_id,
            "hour": order.hour,
            "day_of_week": order.day_of_week,
            "weekend": order.weekend,
            "distance_km": order.distance_km,
            "order_value_eur": order.order_value_eur,
            "weight_kg": order.weight_kg,
            "stock_available": order.stock_available,
            "preparation_time_min": order.preparation_time_min,
            "carrier_capacity": order.carrier_capacity,
            "weather": order.weather,
            "delivery_zone": order.delivery_zone,
            "customer_type": order.customer_type,
        }
        response = client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("express_eligible", data)
        self.assertIn("probability", data)
        self.assertIn("decision", data)
        self.assertTrue(isinstance(data["express_eligible"], bool))


if __name__ == "__main__":
    unittest.main()
