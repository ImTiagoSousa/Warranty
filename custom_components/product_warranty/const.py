"""Constants for the Product Warranty integration."""

from homeassistant.const import Platform

DOMAIN = "product_warranty"
PLATFORMS = [Platform.SENSOR]

CONF_PRODUCT_NAME = "product_name"
CONF_PURCHASE_DATE = "purchase_date"
CONF_WARRANTY_DURATION = "warranty_duration_months"
CONF_RECEIPT = "receipt"

DEFAULT_WARRANTY_DURATION = 12
MIN_WARRANTY_DURATION = 1
MAX_WARRANTY_DURATION = 1200
