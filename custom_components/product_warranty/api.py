"""Authenticated API views for Product Warranty."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any

from aiohttp import hdrs, web
from aiohttp.web_request import FileField

from homeassistant.components.http import KEY_HASS, HomeAssistantView, require_admin
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PRODUCT_NAME,
    CONF_PURCHASE_DATE,
    CONF_RECEIPT,
    CONF_WARRANTY_DURATION,
    DOMAIN,
)
from .helpers import (
    MAX_RECEIPT_SIZE,
    InvalidReceipt,
    receipt_file_path,
    store_receipt,
    warranty_end_date,
)

_RECEIPT_CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg"}


class ProductWarrantyProductsView(HomeAssistantView):
    """Return products and receipt availability to the integration panel."""

    url = "/api/product_warranty/products"
    name = "api:product_warranty:products"

    @require_admin
    async def get(self, request: web.Request) -> web.Response:
        """List configured products."""
        hass = request.app[KEY_HASS]
        today = dt_util.now().date()
        products = []
        for entry in hass.config_entries.async_entries(DOMAIN):
            product = {**entry.data, **entry.options}
            expiry = warranty_end_date(
                date.fromisoformat(product[CONF_PURCHASE_DATE]),
                product[CONF_WARRANTY_DURATION],
            )
            receipt = product.get(CONF_RECEIPT)
            has_receipt = isinstance(receipt, dict) and bool(receipt)
            products.append(
                {
                    "entry_id": entry.entry_id,
                    "product_name": product[CONF_PRODUCT_NAME],
                    "purchase_date": product[CONF_PURCHASE_DATE],
                    "warranty_duration_months": product[CONF_WARRANTY_DURATION],
                    "warranty_end_date": expiry.isoformat(),
                    "days_remaining": (expiry - today).days,
                    "receipt_filename": (
                        receipt.get("filename") if has_receipt else None
                    ),
                    "receipt_url": (
                        f"/api/product_warranty/receipt/{entry.entry_id}"
                        if has_receipt
                        else None
                    ),
                }
            )
        return self.json({"products": products})


class ProductWarrantyReceiptView(HomeAssistantView):
    """Upload and download a product's private receipt file."""

    url = "/api/product_warranty/receipt/{entry_id}"
    name = "api:product_warranty:receipt"
    requires_auth = True

    def __init__(self) -> None:
        """Initialize per-product upload locks."""
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, entry_id: str) -> asyncio.Lock:
        """Return the lock for one product."""
        if entry_id not in self._locks:
            self._locks[entry_id] = asyncio.Lock()
        return self._locks[entry_id]

    @require_admin
    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Store an uploaded receipt for a product."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise web.HTTPNotFound

        request._client_max_size = MAX_RECEIPT_SIZE + 64 * 1024  # noqa: SLF001
        fields = await request.post()
        uploaded_file = fields.get("file")
        if not isinstance(uploaded_file, FileField):
            raise web.HTTPBadRequest(text="Select a receipt file to upload.")

        async with self._lock_for(entry_id):
            storage_dir = hass.config.path(".storage", DOMAIN, entry_id)
            try:
                receipt = await hass.async_add_executor_job(
                    store_receipt,
                    storage_dir,
                    uploaded_file.file,
                    uploaded_file.filename or "",
                    uploaded_file.content_type,
                )
            except InvalidReceipt as err:
                raise web.HTTPBadRequest(text=str(err)) from err

            hass.config_entries.async_update_entry(
                entry,
                options={**entry.options, CONF_RECEIPT: receipt},
            )
        return self.json({"filename": receipt["filename"]})

    @require_admin
    async def get(self, request: web.Request, entry_id: str) -> web.StreamResponse:
        """Download a product's receipt."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise web.HTTPNotFound

        receipt: Any = entry.options.get(CONF_RECEIPT)
        if (
            not isinstance(receipt, dict)
            or receipt.get("content_type") not in _RECEIPT_CONTENT_TYPES
        ):
            raise web.HTTPNotFound

        path = receipt_file_path(hass.config.path(".storage", DOMAIN, entry_id))
        if not await hass.async_add_executor_job(path.is_file):
            raise web.HTTPNotFound
        return web.FileResponse(
            path,
            headers={
                hdrs.CONTENT_TYPE: receipt["content_type"],
                hdrs.CONTENT_DISPOSITION: 'attachment; filename="receipt"',
            },
        )
