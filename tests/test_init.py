"""The integration loads in Home Assistant."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

# Imported before Home Assistant puts its test config directory, which has a
# `custom_components` package of its own, on the path.
from custom_components import coop_dk

DOMAIN = "coop_dk"


@pytest.fixture(autouse=True)
def _custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load integrations from custom_components."""


async def test_setup(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    assert DOMAIN in hass.config.components


def test_has_a_config_schema() -> None:
    """hassfest rejects an integration with async_setup and no CONFIG_SCHEMA."""
    assert coop_dk.CONFIG_SCHEMA({}) == {}
