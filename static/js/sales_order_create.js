(() => {
  const orderDateInput = document.querySelector("[data-order-date]");
  const productionDaysInput = document.querySelector("[data-production-days]");
  const deadlineTypeInput = document.querySelector("[data-deadline-type]");
  const flexibleDeadlineField = document.querySelector("[data-flexible-deadline-field]");
  const fixedDeadlineField = document.querySelector("[data-fixed-deadline-field]");
  const fixedDeadlineInput = document.querySelector("[data-fixed-deadline]");
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

  const ensureOrderDate = () => {
    if (!orderDateInput.value) orderDateInput.value = toDateValue(today);
  };

  const updateDeadlineFields = () => {
    const isFixed = deadlineTypeInput?.value === "fixed";
    flexibleDeadlineField?.classList.toggle("d-none", isFixed);
    fixedDeadlineField?.classList.toggle("d-none", !isFixed);
    if (productionDaysInput) productionDaysInput.required = !isFixed;
    if (fixedDeadlineInput) fixedDeadlineInput.required = isFixed;
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
    window.syncSalesOrderItemUploadFields?.();
  });

  designList?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-design]");
    if (!button) return;
    const sections = designList.querySelectorAll("[data-design-section]");
    if (sections.length <= 1) return;
    button.closest("[data-design-section]")?.remove();
    refreshDesignTitles();
  });

  orderDateInput?.addEventListener("change", ensureOrderDate);
  deadlineTypeInput?.addEventListener("change", updateDeadlineFields);
  brandSelect?.addEventListener("change", updateSellerField);
  ensureOrderDate();
  updateDeadlineFields();
  updateSellerField();
  refreshDesignTitles();
})();
