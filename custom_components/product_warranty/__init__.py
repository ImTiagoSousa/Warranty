"""Product Warranty integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api import ProductWarrantyProductsView, ProductWarrantyReceiptView
from .const import PLATFORMS

PANEL_URL = "/product_warranty_static"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the receipt API and the management panel."""
    hass.http.register_view(ProductWarrantyProductsView())
    hass.http.register_view(ProductWarrantyReceiptView())
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_URL,
                str(Path(__file__).parent / "www"),
                cache_headers=False,
            )
        ]
    )
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path="product-warranty",
        webcomponent_name="product-warranty-panel",
        module_url=f"{PANEL_URL}/product_warranty_panel.js",
        sidebar_title="Product Warranty",
        sidebar_icon="mdi:shield-check",
        require_admin=True,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a product warranty entry."""
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a product warranty entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
