"""Tests unitaires pour le générateur de commandes synthétiques (order_generator.py)."""

import unittest

from livraison_express_lite.domain.entities import OrderEntity
from livraison_express_lite.infrastructure.implementation.dev.order_generator import (
    generate_labeled_orders,
    generate_orders_dataset,
)


class TestDataGenerator(unittest.TestCase):
    def test_generate_labeled_orders(self):
        orders, labels = generate_labeled_orders(n_rows=100, random_state=42)

        self.assertEqual(len(orders), 100)
        self.assertEqual(len(labels), 100)

        first_order = orders[0]
        self.assertIsInstance(first_order, OrderEntity)
        self.assertTrue(first_order.order_id.startswith("CMD-"))
        self.assertIn(first_order.weather, ["normal", "pluie", "neige", "orage"])
        self.assertIn(first_order.delivery_zone, ["centre", "proche_banlieue", "banlieue", "rurale"])
        self.assertIn(first_order.customer_type, ["standard", "premium"])
        self.assertGreaterEqual(first_order.distance_km, 0.0)
        self.assertGreaterEqual(first_order.weight_kg, 0.0)
        self.assertTrue(0.0 <= first_order.carrier_capacity <= 1.0)
        self.assertIn(labels[0], [0, 1])

    def test_reproducibility_with_seed(self):
        orders1, labels1 = generate_labeled_orders(n_rows=50, random_state=42)
        orders2, labels2 = generate_labeled_orders(n_rows=50, random_state=42)

        self.assertEqual(labels1, labels2)
        self.assertEqual(orders1[0].distance_km, orders2[0].distance_km)
        self.assertEqual(orders1[0].order_value_eur, orders2[0].order_value_eur)

    def test_generate_orders_dataset(self):
        orders = generate_orders_dataset(n_rows=50, random_state=42)
        self.assertEqual(len(orders), 50)
        self.assertIsInstance(orders[0], OrderEntity)


if __name__ == "__main__":
    unittest.main()

