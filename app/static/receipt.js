const printReceipt = () => window.print();
document.getElementById("receipt-print").addEventListener("click", printReceipt);
if (new URLSearchParams(window.location.search).get("print") === "1") {
  window.addEventListener("load", printReceipt, { once: true });
}
