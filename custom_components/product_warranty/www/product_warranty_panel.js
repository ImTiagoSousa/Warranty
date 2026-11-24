const API_BASE = "/api/product_warranty";
const RECEIPT_ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";

class ProductWarrantyPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._products = [];
    this._loading = false;
    this._loaded = false;
    this._message = "";
    this._messageIsError = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._loaded && !this._loading) {
      this._loadProducts();
    }
  }

  connectedCallback() {
    this._render();
    if (!this._loaded && !this._loading) {
      this._loadProducts();
    }
  }

  async _request(path, options = {}) {
    const token = this._hass?.auth?.data?.access_token;
    if (!token) {
      throw new Error("Home Assistant authentication is not ready.");
    }
    const response = await fetch(this._hass.hassUrl(path), {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed (${response.status}).`);
    }
    return response;
  }

  async _loadProducts() {
    if (!this._hass || this._loading) {
      return;
    }
    this._loading = true;
    try {
      const response = await this._request(`${API_BASE}/products`);
      const result = await response.json();
      this._products = result.products;
      this._loaded = true;
      this._message = "";
      this._messageIsError = false;
    } catch (error) {
      this._message = `Unable to load products: ${error.message}`;
      this._messageIsError = true;
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _uploadReceipt(product, file, button) {
    if (!file) {
      return;
    }
    button.disabled = true;
    this._message = `Uploading receipt for ${product.product_name}...`;
    this._messageIsError = false;
    this._render();
    try {
      const body = new FormData();
      body.append("file", file, file.name);
      await this._request(
        `${API_BASE}/receipt/${encodeURIComponent(product.entry_id)}`,
        { method: "POST", body },
      );
      this._message = `Receipt saved for ${product.product_name}.`;
      await this._loadProducts();
    } catch (error) {
      this._message = `Unable to upload receipt: ${error.message}`;
      this._messageIsError = true;
    } finally {
      this._render();
    }
  }

  async _downloadReceipt(product) {
    try {
      const response = await this._request(product.receipt_url);
      const objectUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = product.receipt_filename || "receipt";
      link.click();
      URL.revokeObjectURL(objectUrl);
    } catch (error) {
      this._message = `Unable to download receipt: ${error.message}`;
      this._messageIsError = true;
      this._render();
    }
  }

  _render() {
    const style = document.createElement("style");
    style.textContent = `
      :host { display: block; color: var(--primary-text-color); }
      main { max-width: 900px; margin: 0 auto; padding: 24px; }
      h1 { font-size: 1.6rem; margin: 0 0 8px; }
      .intro, .details, .empty { color: var(--secondary-text-color); }
      .products { display: grid; gap: 16px; margin-top: 20px; }
      article {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        padding: 20px;
      }
      h2 { font-size: 1.15rem; margin: 0 0 8px; }
      .details { margin: 4px 0; }
      .receipt { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
      input { max-width: 100%; }
      button {
        background: var(--primary-color);
        border: 0;
        border-radius: 6px;
        color: var(--text-primary-color, white);
        cursor: pointer;
        padding: 9px 14px;
      }
      button[disabled] { cursor: default; opacity: 0.6; }
      button.secondary {
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
      }
      .message { margin-top: 16px; }
      .error { color: var(--error-color); }
    `;

    const main = document.createElement("main");
    const heading = document.createElement("h1");
    heading.textContent = "Product Warranty";
    main.append(heading);

    const intro = document.createElement("p");
    intro.className = "intro";
    intro.textContent =
      "Track warranty dates and securely attach a receipt to each product.";
    main.append(intro);

    if (this._message) {
      const message = document.createElement("p");
      message.className = this._messageIsError ? "message error" : "message";
      message.setAttribute("role", this._messageIsError ? "alert" : "status");
      message.textContent = this._message;
      main.append(message);
    }

    if (this._loading && this._products.length === 0) {
      const loading = document.createElement("p");
      loading.textContent = "Loading products...";
      main.append(loading);
    } else if (this._products.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent =
        "No products yet. Add one from Settings > Devices & services > Add integration > Product Warranty.";
      main.append(empty);
    } else {
      const products = document.createElement("section");
      products.className = "products";
      for (const product of this._products) {
        products.append(this._renderProduct(product));
      }
      main.append(products);
    }

    this.shadowRoot.replaceChildren(style, main);
  }

  _renderProduct(product) {
    const card = document.createElement("article");
    const heading = document.createElement("h2");
    heading.textContent = product.product_name;
    card.append(heading);

    const details = document.createElement("p");
    details.className = "details";
    details.textContent =
      `Purchased ${product.purchase_date} · ` +
      `${product.warranty_duration_months} months · ` +
      `Expires ${product.warranty_end_date} · ` +
      `${product.days_remaining} days remaining`;
    card.append(details);

    const receiptControls = document.createElement("div");
    receiptControls.className = "receipt";
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = RECEIPT_ACCEPT;
    fileInput.setAttribute("aria-label", `Choose receipt for ${product.product_name}`);
    receiptControls.append(fileInput);

    const uploadButton = document.createElement("button");
    uploadButton.textContent = product.receipt_filename
      ? "Replace receipt"
      : "Upload receipt";
    uploadButton.disabled = true;
    let selectedFile;
    fileInput.addEventListener("change", () => {
      selectedFile = fileInput.files?.[0];
      uploadButton.disabled = !selectedFile;
    });
    uploadButton.addEventListener("click", () => {
      this._uploadReceipt(product, selectedFile, uploadButton);
    });
    receiptControls.append(uploadButton);

    if (product.receipt_filename) {
      const filename = document.createElement("span");
      filename.textContent = product.receipt_filename;
      receiptControls.append(filename);
      const downloadButton = document.createElement("button");
      downloadButton.className = "secondary";
      downloadButton.textContent = "Download";
      downloadButton.addEventListener("click", () => {
        this._downloadReceipt(product);
      });
      receiptControls.append(downloadButton);
    }

    card.append(receiptControls);
    return card;
  }
}

customElements.define("product-warranty-panel", ProductWarrantyPanel);
