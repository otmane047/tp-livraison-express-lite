"""Tests unitaires pour l'orchestrateur de réentraînement continu."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from livraison_express_lite.core.orchestrator import ModelRetrainOrchestrator


class TestModelRetrainOrchestrator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "orchestrator_state.json"

        self.mock_core = MagicMock()
        self.mock_repo = MagicMock()
        self.mock_core.get_order_repository.return_value = self.mock_repo

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_evaluate_and_retrain_insufficient_orders(self):
        self.mock_repo.count.return_value = 20  # Moins que le seuil de 50
        orchestrator = ModelRetrainOrchestrator(
            core=self.mock_core,
            min_new_orders=50,
            state_file=self.state_file,
        )

        retrained = orchestrator.evaluate_and_retrain(force=False)
        self.assertFalse(retrained)
        self.assertFalse(self.mock_core.train_model.called)

    def test_evaluate_and_retrain_triggers_when_threshold_reached(self):
        self.mock_repo.count.return_value = 120
        self.mock_core.train_model.return_value = (
            "run-abc-123",
            {"accuracy": 0.88, "f1_score": 0.85, "precision": 0.86, "recall": 0.84},
            [1, 0],
            [0.9, 0.1],
        )

        orchestrator = ModelRetrainOrchestrator(
            core=self.mock_core,
            min_new_orders=50,
            min_f1_threshold=0.70,
            state_file=self.state_file,
        )

        retrained = orchestrator.evaluate_and_retrain(force=False)
        self.assertTrue(retrained)
        self.assertTrue(self.mock_core.train_model.called)

        # Vérification de l'état persisté
        state = orchestrator._load_state()
        self.assertEqual(state["last_trained_order_count"], 120)
        self.assertEqual(state["last_run_id"], "run-abc-123")
        self.assertEqual(state["status"], "success")

    def test_evaluate_and_retrain_force(self):
        self.mock_repo.count.return_value = 5  # En dessous du seuil
        self.mock_core.train_model.return_value = (
            "run-forced",
            {"f1_score": 0.80},
            [],
            [],
        )

        orchestrator = ModelRetrainOrchestrator(
            core=self.mock_core,
            min_new_orders=50,
            state_file=self.state_file,
        )

        retrained = orchestrator.evaluate_and_retrain(force=True)
        self.assertTrue(retrained)
        self.assertTrue(self.mock_core.train_model.called)

    def test_evaluate_and_retrain_rejects_degraded_model(self):
        self.mock_repo.count.return_value = 100
        # F1 = 0.50 < threshold 0.70
        self.mock_core.train_model.return_value = (
            "run-degraded",
            {"f1_score": 0.50},
            [],
            [],
        )

        orchestrator = ModelRetrainOrchestrator(
            core=self.mock_core,
            min_new_orders=50,
            min_f1_threshold=0.70,
            state_file=self.state_file,
        )

        retrained = orchestrator.evaluate_and_retrain(force=False)
        self.assertFalse(retrained)
        # État non mis à jour vers success
        state = orchestrator._load_state()
        self.assertNotEqual(state.get("last_run_id"), "run-degraded")

    def test_run_loop_stops_with_max_iterations(self):
        self.mock_repo.count.return_value = 10
        orchestrator = ModelRetrainOrchestrator(
            core=self.mock_core,
            state_file=self.state_file,
        )
        orchestrator.run_loop(interval_seconds=0, max_iterations=2)
        self.assertEqual(self.mock_repo.count.call_count, 2)


if __name__ == "__main__":
    unittest.main()
