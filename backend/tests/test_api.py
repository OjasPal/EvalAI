import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["USE_DUMMY_MODEL"] = "true"
os.environ["MODEL_PATH"] = "dummy"
os.environ["MODEL_LABEL_MAPPING"] = "A,B"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app, model  # noqa: E402
from app.routes import set_model  # noqa: E402


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        model.demo_mode = True
        set_model(model)
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_cm.__exit__(None, None, None)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["demo_mode"])

    def test_health_reports_degraded_model_state(self) -> None:
        from app.model import PreferenceModel
        from app.config import Settings

        bad_model = PreferenceModel(Settings(use_dummy_model=False, model_path="missing/checkpoint"))
        bad_model.load_error = "Configured model path does not exist: missing/checkpoint"
        bad_model.demo_mode = False
        set_model(bad_model)

        try:
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["status"], "degraded")
            self.assertIn("missing/checkpoint", body["error"])
        finally:
            set_model(model)

    def test_predict_validation(self) -> None:
        response = self.client.post(
            "/predict",
            json={"prompt": "   ", "response_a": "a", "response_b": "b"},
        )
        self.assertEqual(response.status_code, 422)

    @patch("app.routes.generate_responses", return_value=("A response", "B response"))
    def test_generate_shape(self, _mock_generate) -> None:
        response = self.client.post(
            "/generate",
            json={"prompt": "Explain machine learning in simple terms."},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["model_a"], "llama3.2")
        self.assertEqual(body["model_b"], "qwen2.5:3b")
        self.assertIn("A response", body["response_a"])
        self.assertIn("B response", body["response_b"])

    def test_predict_shape(self) -> None:
        response = self.client.post(
            "/predict",
            json={
                "prompt": "Explain machine learning",
                "response_a": "A short answer.",
                "response_b": "A much longer competing answer about ML.",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn(body["winner"], {"A", "B"})
        self.assertGreaterEqual(body["score_a"], 0.0)
        self.assertLessEqual(body["score_a"], 1.0)
        self.assertGreaterEqual(body["score_b"], 0.0)
        self.assertLessEqual(body["score_b"], 1.0)
        self.assertGreaterEqual(body["confidence"], 0.0)
        self.assertLessEqual(body["confidence"], 1.0)
        self.assertIn("request_id", body)

    def test_evaluation_rejects_dummy_model(self) -> None:
        response = self.client.post("/evaluation", json={})

        self.assertEqual(response.status_code, 503, response.text)
        self.assertIn("trained RoBERTa model", response.json()["detail"])

    def test_feedback(self) -> None:
        response = self.client.post(
            "/feedback",
            json={
                "prompt": "p",
                "response_a": "a",
                "response_b": "b",
                "human_preference": "A",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "saved")
        self.assertTrue(body["feedback_id"])


if __name__ == "__main__":
    unittest.main()
