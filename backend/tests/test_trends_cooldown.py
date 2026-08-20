from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.services.trends.cooldown import (
    RATE_LIMIT_KEY,
    activate_rate_limit_cooldown,
    cooldown_remaining_seconds,
)


def _client() -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    return client


def test_cooldown_reports_only_positive_ttl() -> None:
    settings = Settings(_env_file=None)
    client = _client()
    with patch("app.services.trends.cooldown._redis_client", return_value=client):
        client.ttl.return_value = 412
        assert cooldown_remaining_seconds(settings) == 412
        client.ttl.return_value = -2
        assert cooldown_remaining_seconds(settings) == 0


def test_rate_limit_cooldown_uses_configured_ttl() -> None:
    settings = Settings(_env_file=None, trends_rate_limit_cooldown_seconds=720)
    client = _client()
    with patch("app.services.trends.cooldown._redis_client", return_value=client):
        assert activate_rate_limit_cooldown(settings) == 720
    client.set.assert_called_once_with(RATE_LIMIT_KEY, "1", ex=720)
