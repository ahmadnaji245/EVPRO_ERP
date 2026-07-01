const notaForm = document.getElementById("notaForm");

if (notaForm) {
    const rupiah = (value) =>
        new Intl.NumberFormat("id-ID", {
            style: "currency",
            currency: "IDR",
            maximumFractionDigits: 0,
        }).format(value || 0);
    const products = JSON.parse(notaForm.dataset.products || "[]");
    const customers = JSON.parse(notaForm.dataset.customers || "[]");
    const productMap = new Map(products.map((product) => [String(product.code).toUpperCase(), product]));
    const tableBody = document.querySelector("#notaItemsTable tbody");
    const totalNode = document.getElementById("notaTotal");

    function updateRow(row) {
        const codeInput = row.querySelector(".product-code");
        const qtyInput = row.querySelector(".quantity");
        const descInput = row.querySelector(".description");
        const priceInput = row.querySelector(".price");
        const subtotalInput = row.querySelector(".subtotal");
        const product = productMap.get(String(codeInput.value).trim().toUpperCase());
        const quantity = Number(qtyInput.value || 0);

        if (!product) {
            descInput.value = "";
            priceInput.value = "";
            subtotalInput.value = "";
            updateTotal();
            return;
        }

        const price = Number(product.price || 0);
        const subtotal = price * quantity;
        descInput.value = product.description;
        priceInput.value = price;
        subtotalInput.value = subtotal;
        updateTotal();
    }

    function updateTotal() {
        let total = 0;
        tableBody.querySelectorAll(".subtotal").forEach((input) => {
            total += Number(input.value || 0);
        });
        totalNode.textContent = rupiah(total);
    }

    function bindRow(row) {
        row.querySelector(".product-code").addEventListener("input", () => updateRow(row));
        row.querySelector(".quantity").addEventListener("input", () => updateRow(row));
        row.querySelector(".remove-row").addEventListener("click", () => {
            if (tableBody.querySelectorAll(".item-row").length > 1) {
                row.remove();
                updateTotal();
            }
        });
        updateRow(row);
    }

    function addRow() {
        const first = tableBody.querySelector(".item-row");
        const clone = first.cloneNode(true);
        clone.querySelectorAll("input").forEach((input) => {
            input.value = "";
        });
        tableBody.appendChild(clone);
        bindRow(clone);
    }

    document.getElementById("addNotaItemRow").addEventListener("click", addRow);
    tableBody.querySelectorAll(".item-row").forEach(bindRow);

    const customerName = document.getElementById("customerName");
    const customerId = document.getElementById("customerId");
    const teamName = document.getElementById("teamName");
    const phone = document.getElementById("phone");
    const address = document.getElementById("address");

    customerName.addEventListener("change", () => {
        const found = customers.find((customer) => customer.name === customerName.value);
        if (!found) {
            customerId.value = "";
            return;
        }
        customerId.value = found.id;
        teamName.value = found.team_name || teamName.value;
        phone.value = found.phone || "";
        address.value = found.address || "";
    });

    if (window.Sortable && tableBody) {
        new Sortable(tableBody, {
            handle: ".drag-handle",
            animation: 150,
        });
    }
}
