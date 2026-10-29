"""Implémentation MongoDB de l'abstraction OrderRepository via pymongo."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from pymongo import MongoClient

from ...domain.entities import OrderEntity
from ..order_repository import OrderRepository

logger = logging.getLogger(__name__)


class MongoOrderRepository(OrderRepository):
    """Adaptateur de persistance MongoDB pour les commandes."""

    def __init__(self, uri: str, db_name: str = "livraison_express") -> None:
        self.uri = uri
        self.client: MongoClient[dict[str, Any]] = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db["orders"]
        self.collection.create_index("order_id", unique=True)
        logger.info("MongoOrderRepository initialisé (db=%s)", db_name)

    @staticmethod
    def _doc_to_entity(doc: dict[str, Any]) -> OrderEntity:
        day_of_week = int(doc["day_of_week"])
        weekend = int(doc["weekend"]) if doc.get("weekend") is not None else int(day_of_week >= 5)
        prep_time = (
            float(doc["preparation_time_min"])
            if doc.get("preparation_time_min") is not None
            else 25.0
        )
        return OrderEntity(
            order_id=str(doc["order_id"]),
            hour=int(doc["hour"]),
            day_of_week=day_of_week,
            weekend=weekend,
            distance_km=float(doc["distance_km"]),
            order_value_eur=float(doc["order_value_eur"]),
            weight_kg=float(doc["weight_kg"]),
            stock_available=int(doc["stock_available"]),
            preparation_time_min=prep_time,
            carrier_capacity=float(doc["carrier_capacity"]),
            weather=str(doc["weather"]),
            delivery_zone=str(doc["delivery_zone"]),
            customer_type=str(doc["customer_type"]),
        )

    def save(self, order: OrderEntity) -> None:
        doc = {
            "order_id": order.order_id or f"CMD-{abs(hash(order)):08d}",
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
        self.collection.replace_one({"order_id": doc["order_id"]}, doc, upsert=True)

    def get(self, order_id: str) -> OrderEntity | None:
        doc = self.collection.find_one({"order_id": order_id})
        if doc is None:
            return None
        return self._doc_to_entity(doc)

    def get_all(self, limit: int | None = None) -> list[OrderEntity]:
        cursor = self.collection.find()
        if limit:
            cursor = cursor.limit(limit)
        return [self._doc_to_entity(doc) for doc in cursor]

    def count(self) -> int:
        return self.collection.count_documents({})

    def get_training_data(self, max_rows: int = 10000) -> tuple[list[OrderEntity], list[int]]:
        orders = self.get_all(limit=max_rows)
        if not orders:
            return [], []

        labels: list[int] = []
        for o in orders:
            zone_pen = {"centre": 0.0, "suburb": 0.15, "proche_banlieue": 0.10, "banlieue": 0.25, "rural": 0.45}.get(o.delivery_zone, 0.1)
            weather_pen = {"clear": 0.0, "normal": 0.0, "rain": 0.10, "pluie": 0.10, "wind": 0.15, "snow": 0.25, "neige": 0.25, "orage": 0.30}.get(o.weather, 0.0)
            cust_bonus = 0.15 if o.customer_type in ("premium", "business") else 0.0

            score = (
                2.5
                - 0.18 * o.distance_km
                - 0.035 * o.preparation_time_min
                - 0.035 * o.weight_kg
                - zone_pen
                - weather_pen
                + 1.8 * o.stock_available
                + 1.3 * min(o.carrier_capacity, 1.0)
                + cust_bonus
                - 0.40 * o.weekend
                - 0.08 * max(o.hour - 18, 0)
            )
            prob = 1.0 / (1.0 + float(np.exp(-score)))
            labels.append(1 if prob >= 0.5 else 0)

        logger.info("Données extraites de MongoDB (commandes=%d, labels=%d)", len(orders), len(labels))
        return orders, labels

    def close(self) -> None:
        self.client.close()
