"""Push alerts. ntfy by default (no account needed); an Apprise URL overrides."""

from __future__ import annotations

import logging
import os
import time

import requests

log = logging.getLogger(__name__)

TITLE = "R2 Waiting Room"


def _ntfy_url() -> str | None:
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    return f"{server}/{topic}" if topic else None


def _post(url: str, **kw) -> None:
    """POST with one retry, so a blip on ntfy.sh doesn't drop an alert."""
    for attempt in (1, 2):
        try:
            requests.post(url, timeout=15, **kw).raise_for_status()
            return
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(3)


def send(headline: str, body: str, priority: str = "default", tags: str = "", title: str = TITLE) -> bool:
    """Returns True if an alert went out. Never raises; a dead notifier must not fail a poll."""
    apprise = os.environ.get("APPRISE_URL", "").strip()
    url = _ntfy_url()
    text = f"{headline}\n{body}".strip()
    try:
        if apprise:
            _post(apprise, json={"title": title, "body": text, "type": "warning" if priority == "high" else "info"})
            log.info("alert sent via apprise: %s", headline)
            return True
        if url:
            headers = {"Title": f"{title}: {headline}", "Priority": priority}
            if tags:
                headers["Tags"] = tags
            _post(url, data=text.encode("utf-8"), headers=headers)
            log.info("alert sent via ntfy (%s): %s", priority, headline)
            return True
        log.info("no NTFY_TOPIC or APPRISE_URL set; alert not sent: %s", headline)
        return False
    except requests.RequestException as e:
        log.error("ALERT NOT DELIVERED (%s): %s", headline, e)
        return False


def format_changes(public_changes: list[dict], rung_now: int, newly: list[int], rung_names: dict[int, str]) -> tuple[str, str, str]:
    """(headline, body, priority) for a poll that found something."""
    if newly:
        headline = rung_names[max(newly)]
        priority = "high"
    else:
        n = len(public_changes)
        headline = f"{n} field{'s' if n != 1 else ''} changed"
        priority = "default"
    lines = []
    for c in public_changes[:5]:
        lines.append(f"{c['path']}: {c['old']} → {c['new']}")
    if len(public_changes) > 5:
        lines.append(f"+{len(public_changes) - 5} more")
    lines.append(f"Rung {rung_now} of {len(rung_names)}")
    return headline, "\n".join(lines), priority


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ok = send("Test alert", "If you can read this, ntfy delivery works.", priority="high", tags="bell")
    raise SystemExit(0 if ok else 1)
