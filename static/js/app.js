const monthlyPointChart = document.getElementById("monthlyPointChart");
const dailySettingPointChart = document.getElementById("dailySettingPointChart");
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

if (dailySettingPointChart && window.Chart) {
    const labels = JSON.parse(dailySettingPointChart.dataset.labels || "[]");
    const values = JSON.parse(dailySettingPointChart.dataset.values || "[]");
    const tooltips = JSON.parse(dailySettingPointChart.dataset.tooltips || "[]");

    new Chart(dailySettingPointChart, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Poin Setting Harian",
                    data: values,
                    backgroundColor: "#c5162e",
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => {
                            const item = items[0] || {};
                            const tooltip = tooltips[item.dataIndex] || {};
                            return tooltip.date ? `Tanggal: ${tooltip.date}` : "";
                        },
                        label: (context) => {
                            const tooltip = tooltips[context.dataIndex] || {};
                            return [
                                `Hari: ${tooltip.day_name || "-"}`,
                                `Total poin: ${tooltip.total_point || 0}`,
                                `Jumlah SO yang dikerjakan: ${tooltip.so_count || 0}`,
                            ];
                        },
                    },
                },
            },
            scales: {
                x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 16 } },
                y: { beginAtZero: true },
            },
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
