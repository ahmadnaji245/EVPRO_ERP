(() => {
  const orderDateInput = document.querySelector("[data-order-date]");
  const productionDaysInput = document.querySelector("[data-production-days]");
  const deadlineInput = document.querySelector("[data-deadline]");
  const designList = document.querySelector("[data-design-list]");
  const designTemplate = document.querySelector("[data-design-template]");
  const addButton = document.querySelector("[data-add-design]");
  const brandSelect = document.querySelector("[data-brand-select]");
  const sellerField = document.querySelector("[data-seller-field]");
  const sellerInput = document.querySelector("[data-seller-input]");

  const today = new Date();
  const toDateValue = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const updateDeadline = () => {
    if (!orderDateInput || !productionDaysInput || !deadlineInput) return;
    if (!orderDateInput.value) orderDateInput.value = toDateValue(today);
    const days = Number.parseInt(productionDaysInput.value || "0", 10);
    if (!days || days < 1) return;
    const date = new Date(`${orderDateInput.value}T00:00:00`);
    date.setDate(date.getDate() + days);
    deadlineInput.value = toDateValue(date);
  };

  const refreshDesignTitles = () => {
    if (!designList) return;
    const sections = designList.querySelectorAll("[data-design-section]");
    sections.forEach((section, index) => {
      const title = section.querySelector(".section-title");
      const removeButton = section.querySelector("[data-remove-design]");
      if (title) title.textContent = `Desain ${index + 1}`;
      if (removeButton) removeButton.disabled = sections.length === 1;
    });
  };

  const updateSellerField = () => {
    if (!brandSelect || !sellerField || !sellerInput) return;
    const selectedOption = brandSelect.options[brandSelect.selectedIndex];
    const isEvpro = selectedOption?.dataset.isEvpro === "true";
    sellerField.classList.toggle("d-none", !isEvpro);
    sellerInput.required = isEvpro;
    if (!isEvpro) sellerInput.value = "";
  };

  addButton?.addEventListener("click", () => {
    if (!designList || !designTemplate) return;
    const clone = designTemplate.content.firstElementChild.cloneNode(true);
    designList.appendChild(clone);
    refreshDesignTitles();
  });

  designList?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-design]");
    if (!button) return;
    const sections = designList.querySelectorAll("[data-design-section]");
    if (sections.length <= 1) return;
    button.closest("[data-design-section]")?.remove();
    refreshDesignTitles();
  });

  orderDateInput?.addEventListener("change", updateDeadline);
  productionDaysInput?.addEventListener("input", updateDeadline);
  brandSelect?.addEventListener("change", updateSellerField);
  updateDeadline();
  updateSellerField();
  refreshDesignTitles();
})();
