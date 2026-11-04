import unittest

from app import app


class TestPredictionApplication(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_health_endpoint(self):
        for endpoint in ["/", "/health"]:
            response = self.client.get(endpoint)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.get_json()["status"], "ok"
            )
            self.assertIn("X-Request-ID", response.headers)

    def test_high_performance_prediction(self):
        response = self.client.post(
            "/predict",
            json={
                "attendance": 90,
                "internal_marks": 85,
                "assignment_marks": 88,
                "previous_score": 80,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["prediction"], "PASS"
        )

    def test_low_performance_prediction(self):
        response = self.client.post(
            "/predict",
            json={
                "attendance": 55,
                "internal_marks": 30,
                "assignment_marks": 40,
                "previous_score": 35,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["prediction"], "FAIL"
        )

    def test_missing_field_validation(self):
        response = self.client.post(
            "/predict",
            json={
                "attendance": 90,
                "internal_marks": 85,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "missing_fields", response.get_json()
        )

    def test_prometheus_metrics_endpoint(self):
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "student_api_model_loaded",
            response.get_data(as_text=True),
        )

    def test_metrics_count_requests(self):
        self.client.get("/health")
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'student_api_http_requests_total{method="GET",path="/health",status="200"}',
            response.get_data(as_text=True),
        )

    def test_unknown_route_returns_404(self):
        response = self.client.get("/not-a-real-route")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
