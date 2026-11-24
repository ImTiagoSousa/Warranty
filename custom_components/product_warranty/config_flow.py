"""Config flow for Product Warranty."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_PRODUCT_NAME,
    CONF_PURCHASE_DATE,
    CONF_RECEIPT,
    CONF_WARRANTY_DURATION,
    DEFAULT_WARRANTY_DURATION,
    DOMAIN,
    MAX_WARRANTY_DURATION,
    MIN_WARRANTY_DURATION,
)


def _product_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Create the product details form."""
    defaults = defaults or {}
    fields = {
        vol.Required(
            CONF_PRODUCT_NAME, default=defaults.get(CONF_PRODUCT_NAME, "")
        ): selector.TextSelector(selector.TextSelectorConfig()),
        vol.Required(
            CONF_WARRANTY_DURATION,
            default=defaults.get(CONF_WARRANTY_DURATION, DEFAULT_WARRANTY_DURATION),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=MIN_WARRANTY_DURATION,
                max=MAX_WARRANTY_DURATION,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="months",
            )
        ),
    }
    if purchase_date := defaults.get(CONF_PURCHASE_DATE):
        fields[vol.Required(CONF_PURCHASE_DATE, default=purchase_date)] = (
            selector.DateSelector()
        )
    else:
        fields[vol.Required(CONF_PURCHASE_DATE)] = selector.DateSelector()
    return vol.Schema(fields)


def _normalize_input(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize strings and the numeric selector's value."""
    return {
        CONF_PRODUCT_NAME: user_input[CONF_PRODUCT_NAME].strip(),
        CONF_PURCHASE_DATE: user_input[CONF_PURCHASE_DATE],
        CONF_WARRANTY_DURATION: int(user_input[CONF_WARRANTY_DURATION]),
    }


class ProductWarrantyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a single product."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a product."""
        errors: dict[str, str] = {}
        if user_input is not None:
            normalized = _normalize_input(user_input)
            if not normalized[CONF_PRODUCT_NAME]:
                errors["base"] = "name_required"
            else:
                await self.async_set_unique_id(str(uuid4()))
                return self.async_create_entry(
                    title=normalized[CONF_PRODUCT_NAME], data=normalized
                )

        return self.async_show_form(
            step_id="user", data_schema=_product_schema(), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for an existing product."""
        return ProductWarrantyOptionsFlow()


class ProductWarrantyOptionsFlow(config_entries.OptionsFlow):
    """Edit a product's details."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Update product details."""
        errors: dict[str, str] = {}
        if user_input is not None:
            normalized = _normalize_input(user_input)
            if not normalized[CONF_PRODUCT_NAME]:
                errors["base"] = "name_required"
            else:
                if receipt := self.config_entry.options.get(CONF_RECEIPT):
                    normalized[CONF_RECEIPT] = receipt
                return self.async_create_entry(title="", data=normalized)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_product_schema(current),
            errors=errors,
        )
