const monthlyPointChart = document.getElementById("monthlyPointChart");
const settingTargetChart = document.getElementById("settingTargetChart");
const monthlyRevenueChart = document.getElementById("monthlyRevenueChart");
const yearlyRevenueChart = document.getElementById("yearlyRevenueChart");

if (monthlyPointChart && window.Chart) {
    const labels = JSON.parse(monthlyPointChart.dataset.labels || "[]");
    const values = JSON.parse(monthlyPointChart.dataset.values || "[]");

    new Chart(monthlyPointChart, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Total Point",
                    data: values,
                    backgroundColor: "#c5162e",
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } },
        },
    });
}

if (settingTargetChart && window.Chart) {
    const labels = JSON.parse(settingTargetChart.dataset.labels || "[]");
    const values = JSON.parse(settingTargetChart.dataset.values || "[]");
    const colors = JSON.parse(settingTargetChart.dataset.colors || "[]");
    const userDatasets = labels.map((label, index) => ({
        label,
        data: values.map((value, valueIndex) => (valueIndex === index ? value : null)),
        backgroundColor: colors[index] || "#6C757D",
        borderRadius: 6,
    }));

    new Chart(settingTargetChart, {
        type: "bar",
        data: {
            labels,
            datasets: userDatasets,
        },
        options: {
            responsive: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            return `${context.dataset.label}: ${context.raw} total point setting`;
                        },
                    },
                },
            },
            scales: { y: { beginAtZero: true } },
        },
    });
}

if (monthlyRevenueChart && window.Chart) {
    const labels = JSON.parse(monthlyRevenueChart.dataset.labels || "[]");
    const values = JSON.parse(monthlyRevenueChart.dataset.values || "[]");

    new Chart(monthlyRevenueChart, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Omset",
                    data: values,
                    backgroundColor: "#c5162e",
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    ticks: {
                        callback: (value) =>
                            new Intl.NumberFormat("id-ID", {
                                style: "currency",
                                currency: "IDR",
                                maximumFractionDigits: 0,
                            }).format(value),
                    },
                },
            },
        },
    });
}

if (yearlyRevenueChart && window.Chart) {
    const labels = JSON.parse(yearlyRevenueChart.dataset.labels || "[]");
    const values = JSON.parse(yearlyRevenueChart.dataset.values || "[]");

    new Chart(yearlyRevenueChart, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Omset Tahunan",
                    data: values,
                    borderColor: "#20242a",
                    backgroundColor: "rgba(197, 22, 46, 0.12)",
                    tension: 0.25,
                    fill: true,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
        },
    });
}
