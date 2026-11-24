# Product Warranty for Home Assistant

A HACS custom integration for tracking product purchases and warranty expiry.
Each product is added as a separate integration entry and creates a sensor
showing the number of days remaining on its warranty.

## Tracked information

- Product name
- Purchase date
- Warranty duration in months
- An uploaded receipt file for each product
- Calculated warranty end date

The warranty end date is the purchase date plus the selected number of calendar
months. If the purchase day does not exist in the ending month, the last day of
that month is used.

## Installation

1. Install HACS in Home Assistant if it is not already installed. HACS is a
   community store, not part of the Home Assistant Core installation.
2. In HACS, open **Integrations**, choose the menu, and select **Custom
   repositories**.
3. Add this repository URL and select **Integration** as the category.
4. Install **Product Warranty**, then restart Home Assistant.
5. In **Settings → Devices & services**, choose **Add integration** and search
   for **Product Warranty**.

Until this project is published to a Git repository, install it manually by
copying `custom_components/product_warranty` into the Home Assistant
`custom_components` directory, then restart Home Assistant.

Before publishing the repository, replace the documentation URL in
`custom_components/product_warranty/manifest.json` with the repository's URL.

## Receipt files

Open the **Product Warranty** sidebar panel, choose a PDF, PNG, or JPEG for a
product, and select **Upload receipt**. The integration stores the file in
Home Assistant's private `.storage/product_warranty/` directory under that
product's entry ID; it does not place receipts in the public `/config/www/`
folder. Uploads are limited to 10 MB. The panel can download or replace the
receipt, and the entity exposes `has_receipt`, `receipt_filename`, and an
authenticated `receipt_url` attribute.

Receipt metadata is saved in the product's Home Assistant config-entry options,
so both the file and its product association survive integration reloads and
Home Assistant restarts. Re-uploading replaces that product's stored file.

## Sensor

Each product creates a **Warranty days remaining** sensor. Its state is the
number of days until the calculated warranty end date (negative after expiry).
Attributes include the product name, purchase date, warranty duration, end
date, and receipt availability and download URL.

Product details can be changed from the integration's **Configure** option.
