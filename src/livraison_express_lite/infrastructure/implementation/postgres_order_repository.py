"""Implémentation PostgreSQL de l'abstraction OrderRepository via psycopg 3."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import psycopg
from psycopg.rows import dict_row

from ...domain.entities import OrderEntity
from ..order_repository import OrderRepository

logger = logging.getLogger(__name__)


class PostgresOrderRepository(OrderRepository):
    """Adaptateur de persistance PostgreSQL pour les commandes."""

    def __init__(self, dsn: str, auto_create_table: bool = True) -> None:
        self.dsn = dsn
        self._connection: psycopg.Connection[Any] | None = None
        if auto_create_table:
            self._ensure_schema()
        logger.info("PostgresOrderRepository initialisé")

    def _get_connection(self) -> psycopg.Connection[Any]:
        if self._connection is None or self._connection.closed:
            self._connection = psycopg.connect(self.dsn, row_factory=dict_row)
        return self._connection

    def _ensure_schema(self) -> None:
        """Garantit la présence de la table orders et des index."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    order_date DATE,
                    hour INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    weekend INTEGER,
                    distance_km DOUBLE PRECISION NOT NULL,
                    order_value_eur DOUBLE PRECISION NOT NULL,
                    weight_kg DOUBLE PRECISION NOT NULL,
                    stock_available INTEGER NOT NULL,
                    preparation_time_min DOUBLE PRECISION,
                    carrier_capacity DOUBLE PRECISION NOT NULL,
                    weather TEXT NOT NULL,
                    delivery_zone TEXT NOT NULL,
                    customer_type TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date);
                """
            )
        conn.commit()

    @staticmethod
    def _row_to_entity(row: dict[str, Any]) -> OrderEntity:
        """Convertit une ligne PostgreSQL en OrderEntity avec gestion des valeurs nullables historiques."""
        day_of_week = int(row["day_of_week"])
        # Dérivation si la colonne weekend était NULL (historique avant 2015)
        weekend = int(row["weekend"]) if row.get("weekend") is not None else int(day_of_week >= 5)
        # Complétion si la colonne preparation_time_min était NULL (historique avant 2017)
        prep_time = (
            float(row["preparation_time_min"])
            if row.get("preparation_time_min") is not None
            else 25.0
        )

        return OrderEntity(
            order_id=str(row["order_id"]),
            hour=int(row["hour"]),
            day_of_week=day_of_week,
            weekend=weekend,
            distance_km=float(row["distance_km"]),
            order_value_eur=float(row["order_value_eur"]),
            weight_kg=float(row["weight_kg"]),
            stock_available=int(row["stock_available"]),
            preparation_time_min=prep_time,
            carrier_capacity=float(row["carrier_capacity"]),
            weather=str(row["weather"]),
            delivery_zone=str(row["delivery_zone"]),
            customer_type=str(row["customer_type"]),
        )

    def save(self, order: OrderEntity) -> None:
        """Enregistre ou met à jour une commande dans PostgreSQL."""
        conn = self._get_connection()
        query = """
            INSERT INTO orders (
                order_id, hour, day_of_week, weekend, distance_km,
                order_value_eur, weight_kg, stock_available,
                preparation_time_min, carrier_capacity, weather,
                delivery_zone, customer_type
            ) VALUES (
                %(order_id)s, %(hour)s, %(day_of_week)s, %(weekend)s, %(distance_km)s,
                %(order_value_eur)s, %(weight_kg)s, %(stock_available)s,
                %(preparation_time_min)s, %(carrier_capacity)s, %(weather)s,
                %(delivery_zone)s, %(customer_type)s
            )
            ON CONFLICT (order_id) DO UPDATE SET
                hour = EXCLUDED.hour,
                day_of_week = EXCLUDED.day_of_week,
                weekend = EXCLUDED.weekend,
                distance_km = EXCLUDED.distance_km,
                order_value_eur = EXCLUDED.order_value_eur,
                weight_kg = EXCLUDED.weight_kg,
                stock_available = EXCLUDED.stock_available,
                preparation_time_min = EXCLUDED.preparation_time_min,
                carrier_capacity = EXCLUDED.carrier_capacity,
                weather = EXCLUDED.weather,
                delivery_zone = EXCLUDED.delivery_zone,
                customer_type = EXCLUDED.customer_type;
        """
        params = {
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
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()

    def get(self, order_id: str) -> OrderEntity | None:
        """Récupère une commande par son identifiant unique."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_entity(row)

    def get_all(self, limit: int | None = None) -> list[OrderEntity]:
        """Retourne l'ensemble des commandes."""
        conn = self._get_connection()
        query = "SELECT * FROM orders ORDER BY order_id"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            return [self._row_to_entity(row) for row in rows]

    def count(self) -> int:
        """Retourne le nombre total de commandes."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM orders")
            row = cur.fetchone()
            return int(row["count"]) if row else 0

    def get_training_data(self, max_rows: int = 10000) -> tuple[list[OrderEntity], list[int]]:
        """Extrait les commandes de PostgreSQL et calcule les étiquettes métier pour l'entraînement."""
        orders = self.get_all(limit=max_rows)
        if not orders:
            return [], []

        # Calcul vectoriel de l'éligibilité basé sur la règle métier
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

        logger.info("Données extraites de PostgreSQL (commandes=%d, labels=%d)", len(orders), len(labels))
        return orders, labels

    def close(self) -> None:
        if self._connection and not self._connection.closed:
            self._connection.close()

