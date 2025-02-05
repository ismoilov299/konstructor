$(function() {
    "use strict";

    // Debug logging
    console.log("Starting dashboard initialization...");

    // Check if required elements exist
    if (!document.getElementById('visitor') || !document.getElementById('sales-chart')) {
        console.error("Required chart containers not found");
        return;
    }

    // ===============================================================
    // Visitor Chart
    // ===============================================================
    try {
        var chart = c3.generate({
            bindto: '#visitor',
            data: {
                // Start with default values
                columns: [
                    ['Пользователи', 0],
                    ['Постоянные пользователи', 0]
                ],
                type: 'donut',
                onclick: function(d, i) { console.log("onclick", d, i); },
                onmouseover: function(d, i) { console.log("onmouseover", d, i); },
                onmouseout: function(d, i) { console.log("onmouseout", d, i); }
            },
            donut: {
                label: {
                    show: false
                },
                title: "Статистика",
                width: 20
            },
            legend: {
                hide: true
            },
            color: {
                pattern: ['#6772e5', '#24d2b5']
            }
        });

        // Update with actual data if available
        if (typeof userData !== 'undefined' && typeof userDataCount !== 'undefined') {
            setTimeout(function() {
                chart.load({
                    columns: [
                        ['Пользователи', Array.isArray(userData) ? userData.length : 0],
                        ['Постоянные пользователи', Array.isArray(userDataCount) ? userDataCount.length : 0]
                    ]
                });
            }, 1000);
        }
    } catch (error) {
        console.error("Error initializing visitor chart:", error);
        document.getElementById('visitor').innerHTML = '<div class="alert alert-warning">Ошибка при загрузке диаграммы</div>';
    }

    // ===============================================================
    // Sales chart
    // ===============================================================
    try {
        if (typeof userData !== 'undefined' && Array.isArray(userData)) {
            const monthlyData = prepareMonthlyData(userData);
            if (monthlyData.length > 0) {
                Morris.Area({
                    element: 'sales-chart',
                    data: monthlyData,
                    xkey: 'period',
                    ykeys: ['Sales'],
                    labels: ['Клиенты'],
                    pointSize: 0,
                    fillOpacity: 0.4,
                    pointStrokeColors: ['#20aee3'],
                    behaveLikeLine: true,
                    gridLineColor: '#e0e0e0',
                    lineWidth: 0,
                    smooth: true,
                    hideHover: 'auto',
                    lineColors: ['#20aee3'],
                    resize: true,
                    parseTime: false
                });
            } else {
                document.getElementById('sales-chart').innerHTML =
                    '<div class="alert alert-info mt-3">Нет данных для отображения</div>';
            }
        } else {
            console.warn("Invalid or missing userData for sales chart");
            document.getElementById('sales-chart').innerHTML =
                '<div class="alert alert-warning mt-3">Ошибка загрузки данных</div>';
        }
    } catch (error) {
        console.error("Error initializing sales chart:", error);
        document.getElementById('sales-chart').innerHTML =
            '<div class="alert alert-danger mt-3">Ошибка при создании графика</div>';
    }

    // ===============================================================
    // Helper Functions
    // ===============================================================
    function prepareMonthlyData(data) {
        const currentDate = new Date();
        const monthlyData = [];

        // Generate last 12 months of data
        for (let i = 11; i >= 0; i--) {
            const targetDate = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
            const monthStr = targetDate.toISOString().slice(0, 7); // YYYY-MM format

            // Find data for this month
            const monthData = data.find(item => {
                if (!item || !item.month) return false;
                return item.month.startsWith(monthStr);
            });

            monthlyData.push({
                period: monthStr,
                Sales: monthData ? monthData.count : 0
            });
        }

        return monthlyData;
    }

    // ===============================================================
    // Sales Different Chart
    // ===============================================================
    try {
        var salesDiffChart = c3.generate({
            bindto: '#sales',
            data: {
                columns: [
                    ['One+', 50],
                    ['T', 60],
                    ['Samsung', 20]
                ],
                type: 'donut'
            },
            donut: {
                label: {
                    show: false
                },
                title: "",
                width: 18
            },
            size: {
                height: 150
            },
            legend: {
                hide: true
            },
            color: {
                pattern: ['#eceff1', '#24d2b5', '#6772e5', '#20aee3']
            }
        });
    } catch (error) {
        console.error("Error initializing sales diff chart:", error);
    }

    // ===============================================================
    // Prediction Chart
    // ===============================================================
    try {
        var predictionChart = c3.generate({
            bindto: '#prediction',
            data: {
                columns: [
                    ['data', 0]
                ],
                type: 'gauge'
            },
            color: {
                pattern: ['#ff9041', '#20aee3', '#24d2b5', '#6772e5'],
                threshold: {
                    values: [30, 60, 90, 100]
                }
            },
            gauge: {
                width: 22
            },
            size: {
                height: 120,
                width: 150
            }
        });

        // Animated loading of prediction data
        setTimeout(function() {
            predictionChart.load({
                columns: [['data', 10]]
            });
        }, 1000);

        setTimeout(function() {
            predictionChart.load({
                columns: [['data', 50]]
            });
        }, 2000);

        setTimeout(function() {
            predictionChart.load({
                columns: [['data', 70]]
            });
        }, 3000);
    } catch (error) {
        console.error("Error initializing prediction chart:", error);
    }

    // Log completion
    console.log("Dashboard initialization completed");
});