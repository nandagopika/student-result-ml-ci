import unittest

from app import app


class TestPredictionApplication(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_health_and_root_endpoints(self):
        for endpoint in ["/", "/health"]:
            response = self.client.get(endpoint)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["status"], "ok")
            self.assertIn("X-Request-ID", response.headers)

    def test_swagger_documentation_endpoints(self):
        docs = self.client.get("/docs")
        spec = self.client.get("/openapi.json")

        self.assertEqual(docs.status_code, 200)
        self.assertIn("swagger-ui", docs.get_data(as_text=True))
        self.assertEqual(spec.status_code, 200)
        self.assertIn("/predict", spec.get_json()["paths"])

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
        self.assertEqual(response.get_json()["prediction"], "PASS")

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
        self.assertEqual(response.get_json()["prediction"], "FAIL")

    def test_missing_field_validation(self):
        response = self.client.post(
            "/predict",
            json={
                "attendance": 90,
                "internal_marks": 85,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("missing_fields", response.get_json())

    def test_invalid_numeric_field_validation(self):
        response = self.client.post(
            "/predict",
            json={
                "attendance": "not-a-number",
                "internal_marks": 85,
                "assignment_marks": 88,
                "previous_score": 80,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid_fields", response.get_json())

    def test_prometheus_metrics_endpoint(self):
        self.client.get("/health")
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        metrics_text = response.get_data(as_text=True)
        self.assertIn("student_api_model_loaded", metrics_text)
        self.assertIn(
            'student_api_http_requests_total{method="GET",path="/health",status="200"}',
            metrics_text,
        )

    def test_unknown_route_returns_404(self):
        response = self.client.get("/not-a-real-route")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
