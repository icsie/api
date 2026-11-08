import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.core.request_logging import RequestLoggingMiddleware


class RequestLoggingTests(unittest.TestCase):
    def setUp(self):
        self.writer = AsyncMock()
        self.writer_patch = patch("app.core.request_logging.write_request", self.writer)
        self.writer_patch.start()
        self.secret_patch = patch("app.core.request_logging.SESSION_SECRET_KEY", "test-secret")
        self.secret_patch.start()
        self.app = FastAPI()
        self.app.add_middleware(RequestLoggingMiddleware)

        @self.app.get("/api/test")
        async def normal(request: Request):
            request.state.mid = 42
            return {"ok": True}

        @self.app.get("/api/fail")
        async def fail():
            raise RuntimeError("secret database credentials")

        @self.app.get("/api/denied")
        async def denied():
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})

        @self.app.post("/api/logout")
        async def logout(request: Request):
            request.state.api_session_ended = True
            return {"ok": True}

        @self.app.get("/public")
        async def public():
            return {"ok": True}

    def tearDown(self):
        self.writer_patch.stop()
        self.secret_patch.stop()

    def test_session_cookie_links_requests_and_hides_query(self):
        with TestClient(self.app, base_url="https://testserver") as client:
            self.assertEqual(client.get("/api/test?token=secret").status_code, 200)
            first = self.writer.call_args.args
            client.get("/api/test")
            self.assertIsInstance(first[0], UUID)
            self.assertEqual(first[0], self.writer.call_args.args[0])
            self.assertEqual(first[1], 42)
            self.assertEqual(first[4], "/api/test")
            client.cookies.set("api_session", "forged")
            client.get("/api/test")
            self.assertNotEqual(first[0], self.writer.call_args.args[0])

    def test_errors_and_database_failure(self):
        with TestClient(self.app, base_url="https://testserver") as client:
            with self.assertLogs("app.core.request_logging", level="ERROR"):
                response = client.get("/api/fail")
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(), {"detail": "Internal server error"})
            self.assertEqual(self.writer.call_args.args[6], "Internal server error")
            response = client.get("/api/denied")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")
            self.writer.side_effect = RuntimeError("DB unavailable")
            with self.assertLogs("app.core.request_logging", level="ERROR"):
                self.assertEqual(client.get("/api/test").status_code, 200)

    def test_logout_rotates_session_and_static_is_excluded(self):
        with TestClient(self.app, base_url="https://testserver") as client:
            client.get("/api/test")
            old_id = self.writer.call_args.args[0]
            client.post("/api/logout")
            self.assertTrue(self.writer.call_args.args[7])
            self.assertNotIn("api_session", client.cookies)
            client.get("/api/test")
            self.assertNotEqual(old_id, self.writer.call_args.args[0])
            self.writer.reset_mock()
            client.get("/public")
            self.writer.assert_not_called()

    def test_write_happens_after_response_body(self):
        from app.core.request_logging import RequestLoggingMiddleware

        async def run():
            events = []

            async def app(scope, receive, send):
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"ok"})

            async def send(event):
                events.append(event["type"])

            async def write(*args):
                self.assertEqual(events[-1], "http.response.body")

            self.writer.side_effect = write
            scope = {"type": "http", "path": "/api/test", "method": "GET", "headers": [], "client": ("::1", 123)}
            await RequestLoggingMiddleware(app)(scope, AsyncMock(), send)
            self.assertEqual(self.writer.call_args.args[2], "::1")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
