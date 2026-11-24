"""Sensors for Product Warranty."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PRODUCT_NAME,
    CONF_PURCHASE_DATE,
    CONF_RECEIPT,
    CONF_WARRANTY_DURATION,
    DOMAIN,
)
from .helpers import warranty_end_date


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a warranty sensor."""
    product = {**entry.data, **entry.options}
    async_add_entities([ProductWarrantySensor(entry, product)])


class ProductWarrantySensor(SensorEntity):
    """Report the number of days remaining on a product warranty."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry, product: dict[str, Any]) -> None:
        """Initialize the warranty sensor."""
        self._entry_id = entry.entry_id
        self._product = product
        self._attr_unique_id = entry.entry_id
        self._attr_name = "Warranty days remaining"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=product[CONF_PRODUCT_NAME],
        )

    async def async_added_to_hass(self) -> None:
        """Refresh the remaining-day count at local midnight."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._update_state, hour=0, minute=0, second=0
            )
        )

    def _update_state(self, _now: datetime) -> None:
        """Write the sensor state after the date changes."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        """Return days until the warranty end date."""
        end_date = warranty_end_date(
            date.fromisoformat(self._product[CONF_PURCHASE_DATE]),
            self._product[CONF_WARRANTY_DURATION],
        )
        return (end_date - dt_util.now().date()).days

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the product details and uploaded receipt information."""
        receipt = self._product.get(CONF_RECEIPT, {})
        return {
            CONF_PRODUCT_NAME: self._product[CONF_PRODUCT_NAME],
            CONF_PURCHASE_DATE: self._product[CONF_PURCHASE_DATE],
            CONF_WARRANTY_DURATION: self._product[CONF_WARRANTY_DURATION],
            "warranty_end_date": warranty_end_date(
                date.fromisoformat(self._product[CONF_PURCHASE_DATE]),
                self._product[CONF_WARRANTY_DURATION],
            ).isoformat(),
            "has_receipt": bool(receipt),
            "receipt_filename": receipt.get("filename"),
            "receipt_url": (
                f"/api/product_warranty/receipt/{self._entry_id}"
                if receipt
                else None
            ),
        }
