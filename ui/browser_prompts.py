"""Browser prompts via ui/app.html (Selenium)."""

from __future__ import annotations

import time
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver


class PromptCancelled(Exception):
    """User chose Cancel on a browser dialog."""


POLL_INTERVAL_S = 0.08
DEFAULT_TIMEOUT_S = 7200.0


def _wait_prompt_value(driver: WebDriver, *, timeout: float = DEFAULT_TIMEOUT_S) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = driver.execute_script("return window.__promptResult;")
        if state and state.get("done"):
            return state.get("value")
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError("Timed out waiting for a response in the browser.")


class WebPrompts:
    """Collects answers in Chrome using the prompt layer in app.html."""

    def __init__(self, driver: WebDriver) -> None:
        self._driver = driver
        self._buffer: list[str] = []

    def info(self, message: str) -> None:
        self._buffer.append(message)

    def _collect_detail(self) -> str:
        if not self._buffer:
            return ""
        detail = "\n".join(self._buffer)
        self._buffer.clear()
        return detail

    def text(self, message: str, *, placeholder: str = "", default: str = "") -> str:
        detail = self._collect_detail()
        self._driver.execute_script(
            """
            window.__promptResult = { done: false };
            window.App.showTextPrompt(arguments[0], arguments[1], arguments[2], arguments[3]);
            """,
            message,
            placeholder,
            default,
            detail,
        )
        value = _wait_prompt_value(self._driver)
        if value is None:
            raise PromptCancelled()
        return str(value)

    def yes_no(self, message: str) -> bool:
        detail = self._collect_detail()
        self._driver.execute_script(
            """
            window.__promptResult = { done: false };
            window.App.showYesNo(arguments[0], arguments[1]);
            """,
            message,
            detail,
        )
        value = _wait_prompt_value(self._driver)
        if value is None:
            raise PromptCancelled()
        return value == "yes"

    def choice(self, message: str, options: list[tuple[str, str]]) -> str:
        detail = self._collect_detail()
        choices_js = [{"id": oid, "label": lab} for oid, lab in options]
        self._driver.execute_script(
            """
            window.__promptResult = { done: false };
            window.App.showChoices(arguments[0], arguments[1], arguments[2]);
            """,
            message,
            detail,
            choices_js,
        )
        value = _wait_prompt_value(self._driver)
        if value is None:
            raise PromptCancelled()
        return str(value)
