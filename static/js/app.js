const monthlyPointChart = document.getElementById("monthlyPointChart");
const settingTargetChart = document.getElementById("settingTargetChart");

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
