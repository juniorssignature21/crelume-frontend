/* ============================================================
   Crelume — checkout interactions
   ============================================================ */

(function () {
  "use strict";

  const checkoutForm = document.getElementById("checkoutForm");

  if (!checkoutForm) return;

  const priceKobo = Number(checkoutForm.dataset.price || 0);
  const quantityInput = document.getElementById("id_quantity");
  const totalTargets = [
    document.getElementById("payTotal"),
    document.getElementById("summaryTotal"),
  ].filter(Boolean);
  const quantityTarget = document.getElementById("summaryQuantity");
  const payButton = document.getElementById("payButton");

  const formatNaira = (kobo) =>
    "₦" + Math.round(kobo / 100).toLocaleString("en-NG");

  const getQuantity = () => {
    const value = Number.parseInt(quantityInput ? quantityInput.value : "1", 10);
    return Number.isFinite(value) && value > 0 ? value : 1;
  };

  const updateTotals = () => {
    const quantity = getQuantity();
    const total = formatNaira(priceKobo * quantity);
    totalTargets.forEach((target) => {
      target.textContent = total;
    });
    if (quantityTarget) quantityTarget.textContent = String(quantity);
  };

  const stepInput = (direction) => {
    if (!quantityInput) return;
    const min = Number.parseInt(quantityInput.min || "1", 10);
    const max = Number.parseInt(quantityInput.max || "10", 10);
    const next = Math.min(max, Math.max(min, getQuantity() + direction));
    quantityInput.value = String(next);
    updateTotals();
  };

  document.querySelectorAll("[data-quantity-step]").forEach((button) => {
    button.addEventListener("click", () => {
      stepInput(Number.parseInt(button.dataset.quantityStep, 10));
    });
  });

  if (quantityInput) {
    quantityInput.addEventListener("input", updateTotals);
    quantityInput.addEventListener("change", updateTotals);
  }

  checkoutForm.addEventListener("submit", () => {
    if (!payButton || payButton.disabled) return;
    payButton.dataset.label = payButton.textContent;
    payButton.textContent = "Redirecting to Paystack…";
    payButton.disabled = true;
  });

  updateTotals();
})();
