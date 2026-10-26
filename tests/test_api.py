"""Tests for the Envi API client."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.smart_envi.api import EnviApiClient, EnviAuthenticationError
from custom_components.smart_envi.const import BASE_URL, ENDPOINTS

from .conftest import PASSWORD, USERNAME


async def test_authenticate_reports_server_message(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A rejected login surfaces Envi's msg/msgCode and never logs the password."""
    aioclient_mock.post(
        f"{BASE_URL}/{ENDPOINTS['auth_login']}",
        status=400,
        json={"msgCode": 5010, "msg": "Incorrect login credentials"},
    )
    client = EnviApiClient(async_get_clientsession(hass), USERNAME, PASSWORD)

    caplog.set_level(logging.INFO)
    with pytest.raises(
        EnviAuthenticationError, match="Incorrect login credentials"
    ) as exc:
        await client.authenticate()

    assert "HTTP 400" in str(exc.value)
    assert "5010" in str(exc.value)
    assert "Incorrect login credentials" in caplog.text
    assert PASSWORD not in caplog.text
    assert client.token is None
