"""Tests for the Smart Envi config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smart_envi.api import EnviAuthenticationError
from custom_components.smart_envi.const import DOMAIN

from .conftest import PASSWORD, USERNAME


async def test_user_flow_success(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """A valid login creates an entry keyed on the lower-cased username."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": USERNAME.upper(), "password": PASSWORD}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == USERNAME
    assert result["data"] == {"username": USERNAME.upper(), "password": PASSWORD}


async def test_user_flow_invalid_auth(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """A rejected login shows the invalid_auth error."""
    mock_client.authenticate.side_effect = EnviAuthenticationError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": USERNAME, "password": PASSWORD}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """Any other error shows cannot_connect."""
    mock_client.authenticate.side_effect = TimeoutError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": USERNAME, "password": PASSWORD}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """The same account cannot be added twice."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": USERNAME, "password": PASSWORD}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
