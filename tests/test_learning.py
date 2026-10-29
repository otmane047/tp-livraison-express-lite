"""Tests unitaires pour les composants de machine learning (pipeline, features, splitter)."""

import unittest

from livraison_express_lite.core.learning.ml_pipeline import MLPipeline
from livraison_express_lite.core.learning.order_feature import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    orders_to_dataframe,
)
from livraison_express_lite.core.learning.train_test_splitter import TrainTestSplitter
from livraison_express_lite.infrastructure.implementation.dev.order_generator import (
    generate_labeled_orders,
)


class TestLearning(unittest.TestCase):
    def setUp(self):
        self.orders, self.labels = generate_labeled_orders(n_rows=50, random_state=42)

    def test_feature_columns_consistency(self):
        self.assertEqual(len(FEATURE_COLUMNS), len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES))
        self.assertEqual(set(FEATURE_COLUMNS), set(NUMERIC_FEATURES) | set(CATEGORICAL_FEATURES))

    def test_orders_to_dataframe(self):
        df = orders_to_dataframe(self.orders)
        self.assertEqual(len(df), len(self.orders))
        self.assertListEqual(list(df.columns), FEATURE_COLUMNS)

    def test_ml_pipeline_build(self):
        pipeline = MLPipeline(random_seed=42).get_model_pipeline()
        self.assertIsNotNone(pipeline)
        self.assertIn("preprocessor", pipeline.named_steps)
        self.assertIn("classifier", pipeline.named_steps)

    def test_train_test_splitter(self):
        splitter = TrainTestSplitter(random_seed=42)
        X_train, X_test, y_train, y_test = splitter.split(self.orders, self.labels)

        self.assertEqual(len(X_train), 40)
        self.assertEqual(len(X_test), 10)
        self.assertEqual(len(y_train), 40)
        self.assertEqual(len(y_test), 10)

    def test_splitter_mismatched_lengths_raises(self):
        splitter = TrainTestSplitter(random_seed=42)
        with self.assertRaises(ValueError):
            splitter.split(self.orders, self.labels[:-1])


if __name__ == "__main__":
    unittest.main()

