(function () {
  const totalField = document.getElementById("f-total");
  const calcFields = document.querySelectorAll(".calc-field");
  if (!totalField || !calcFields.length) return;

  let totalManuallyEdited = totalField.value !== "";

  totalField.addEventListener("input", () => {
    totalManuallyEdited = true;
  });

  function recalcTotal() {
    if (totalManuallyEdited) return;
    const subtotal = parseFloat(document.getElementById("f-subtotal").value) || 0;
    const discount = parseFloat(document.getElementById("f-discount").value) || 0;
    const delivery = parseFloat(document.getElementById("f-delivery").value) || 0;
    const platformFee = parseFloat(document.getElementById("f-platformfee").value) || 0;
    const tax = parseFloat(document.getElementById("f-tax").value) || 0;
    const total = subtotal + delivery + platformFee + tax - discount;
    if (subtotal || delivery || platformFee || tax || discount) {
      totalField.value = Math.max(total, 0).toFixed(2);
    }
  }

  calcFields.forEach((field) => field.addEventListener("input", recalcTotal));

  // A double-click on Total lets the user reset it back to auto-calculated.
  totalField.addEventListener("dblclick", () => {
    totalManuallyEdited = false;
    recalcTotal();
  });
})();
