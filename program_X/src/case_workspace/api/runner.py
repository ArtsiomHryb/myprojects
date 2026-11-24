"""Запуск FastAPI в фоновом потоке."""

from __future__ import annotations

import threading
import time

import uvicorn


class ApiServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._thread: threading.Thread | None = None
        self._server: uvicorn.Server | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        from case_workspace.api.app import app as fastapi_app

        config = uvicorn.Config(
            fastapi_app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run, name="case-workspace-api", daemon=True
        )
        self._thread.start()
        # ждём до 3 сек, пока сервер поднимется
        for _ in range(30):
            if self._server.started:
                break
            time.sleep(0.1)

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._server = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
