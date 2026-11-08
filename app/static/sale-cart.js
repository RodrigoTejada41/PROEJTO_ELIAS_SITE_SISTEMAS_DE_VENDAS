const form = document.getElementById("sale-cart");
const data = document.getElementById("cart-data");
const search = document.getElementById("product-search");
const results = document.getElementById("product-results");
const status = document.getElementById("product-status");
const items = document.getElementById("sale-items");
const totals = document.getElementById("sale-totals");
const discount = document.getElementById("discount");
const labels = JSON.parse(form.dataset.labels);
const cart = JSON.parse(data.value);
const locale = document.documentElement.lang;
const integers = new Intl.NumberFormat(locale);
const rate = form.dataset.rate.split(".");
let timer;
let searchRevision = 0;

function element(tag, text, className = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

function cents(value) {
  const match = /^([0-9]{1,16})(?:[.,]([0-9]{1,2}))?$/.exec(value.trim());
  return match ? BigInt(match[1]) * 100n + BigInt((match[2] || "").padEnd(2, "0")) : null;
}

function usd(value) {
  const sign = value < 0n ? "-" : "";
  const absolute = value < 0n ? -value : value;
  return `USD ${sign}${integers.format(absolute / 100n)},${String(absolute % 100n).padStart(2, "0")}`;
}

function pyg(value) {
  if (!rate[0]) return "";
  const factor = BigInt(rate.join(""));
  const denominator = 100n * 10n ** BigInt((rate[1] || "").length);
  const sign = value < 0n ? -1n : 1n;
  return `PYG ${integers.format(sign * ((sign * value * factor + denominator / 2n) / denominator))}`;
}

function lineTotal(item) {
  const price = cents(item.price);
  return price === null || !/^[0-9]{1,10}$/.test(item.quantity) ? null : price * BigInt(item.quantity);
}

function updateTotals() {
  const lines = cart.map(lineTotal);
  const complete = lines.every(value => value !== null);
  const gross = lines.reduce((sum, value) => sum + (value ?? 0n), 0n);
  const rebate = cents(discount.value);
  const net = gross - (rebate ?? 0n);
  const equivalent = complete && rebate !== null ? pyg(net) : "";
  totals.replaceChildren(
    element("div", `${labels.subtotal}: ${complete ? usd(gross) : "—"}`),
    element("div", `${labels.receipt_discount}: ${rebate !== null ? usd(rebate) : "—"}`),
    element("strong", `${labels.total}: ${complete && rebate !== null ? usd(net) : "—"}`),
  );
  if (equivalent) totals.append(element("div", `${labels.sale_estimate}: ${equivalent}`));
  form.querySelector('[value="confirm"]').disabled = !cart.length;
  data.value = JSON.stringify(cart);
}

function editField(item, key, labelText, subtotal) {
  const label = element("label", labelText, "mb-2 mr-2");
  const input = element("input", "", "form-control form-control-sm");
  input.type = key === "quantity" ? "number" : "text";
  input.inputMode = key === "quantity" ? "numeric" : "decimal";
  input.required = true;
  if (key === "quantity") {
    input.min = "1";
    input.max = "1000000000";
  } else {
    input.maxLength = 20;
    input.pattern = "[0-9]{1,16}([.,][0-9]{1,2})?";
  }
  input.value = item[key];
  input.addEventListener("input", () => {
    item[key] = input.value;
    const value = lineTotal(item);
    subtotal.textContent = value === null ? "—" : usd(value);
    updateTotals();
  });
  label.append(input);
  return label;
}

function drawCart() {
  items.replaceChildren();
  for (const item of cart) {
    const row = element("div", "", "border-bottom pb-2 mb-2");
    row.dataset.product = item.id;
    const heading = element("p", `${item.code} · ${item.description}`, "font-weight-bold text-break mb-1");
    const value = lineTotal(item);
    const subtotal = element("strong", value === null ? "—" : usd(value), "mr-3");
    const remove = element("button", labels.remove_item, "btn btn-sm btn-outline-danger");
    remove.type = "button";
    remove.addEventListener("click", () => {
      cart.splice(cart.indexOf(item), 1);
      drawCart();
      search.focus();
    });
    const fields = element("div", "", "d-flex flex-wrap align-items-center");
    fields.append(editField(item, "quantity", labels.quantity, subtotal),
      editField(item, "price", labels.receipt_unit_price + " USD", subtotal), subtotal, remove);
    row.append(heading, fields);
    items.append(row);
  }
  if (!cart.length) items.append(element("p", labels.sale_empty, "mb-2"));
  updateTotals();
}

function showProducts(products) {
  results.replaceChildren();
  status.textContent = products.length ? "" : labels.no_skus;
  for (const product of products) {
    const row = element("div", "", "list-group-item d-flex flex-wrap align-items-center");
    if (product.has_image) {
      const image = element("img", "", "rounded mr-3 mb-2");
      image.src = `/catalog/${product.id}/image`;
      image.alt = "";
      image.width = 64;
      image.height = 64;
      image.style.objectFit = "contain";
      row.append(image);
    }
    const amount = product.usd_price_minor === null ? null : BigInt(product.usd_price_minor);
    const text = element("div", "", "flex-grow-1 mr-2 text-break");
    text.append(element("strong", `${product.code} · ${product.description}`),
      element("div", `${labels.stock}: ${integers.format(product.balance)} · ${amount === null ? labels.sale_price : usd(amount) + (pyg(amount) ? " · " + pyg(amount) : "")}`));
    const add = element("button", labels.add_item, "btn btn-sm btn-outline-dark");
    add.type = "button";
    add.setAttribute("aria-label", `${labels.add_item}: ${product.description}`);
    add.addEventListener("click", () => {
      const previous = cart.find(item => item.id === product.id);
      if (previous) {
        previous.quantity = String(Math.min(1000000000, Number(previous.quantity || "0") + 1));
      } else {
        if (cart.length >= 200) {
          status.textContent = labels.sale_limit;
          return;
        }
        cart.push({ id: product.id, code: product.code, description: product.description, quantity: "1",
          price: amount === null ? "" : `${amount / 100n},${String(amount % 100n).padStart(2, "0")}` });
      }
      drawCart();
      status.textContent = `${labels.sale_added}: ${product.description}`;
      const current = cart.find(item => item.id === product.id);
      if (!current.price) items.querySelector(`[data-product="${product.id}"] input[type="text"]`).focus();
      else search.focus();
    });
    row.append(text, add);
    results.append(row);
  }
}

async function findProducts(revision) {
  const query = search.value.trim();
  if (!query) return;
  status.textContent = labels.sale_loading;
  try {
    const response = await fetch("/sales/products?q=" + encodeURIComponent(query));
    if (!response.ok || response.redirected) throw new Error("search");
    const products = await response.json();
    if (revision === searchRevision) showProducts(products);
  } catch {
    if (revision === searchRevision) status.textContent = labels.sale_search_error;
  }
}

search.addEventListener("input", () => {
  clearTimeout(timer);
  const revision = ++searchRevision;
  results.replaceChildren();
  status.textContent = "";
  timer = setTimeout(() => findProducts(revision), 200);
});
search.addEventListener("keydown", event => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  const first = results.querySelector("button");
  if (first) first.focus();
  else {
    clearTimeout(timer);
    findProducts(++searchRevision);
  }
});
discount.addEventListener("input", updateTotals);
form.querySelector('[value="save"]').disabled = false;
drawCart();
