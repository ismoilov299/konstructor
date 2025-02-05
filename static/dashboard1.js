$(function() {
    "use strict";

    console.log("Starting dashboard initialization...");

    // Ensure data is properly initialized
    const defaultData = {
        users: Array.isArray(window.userData) ? window.userData.length : 0,
        activeUsers: Array.isArray(window.userDataCount) ? window.userDataCount.length : 0
    };

    // ===============================================================
    // Visitor Chart
    // ===============================================================
    try {
        var visitorChart = c3.generate({
            bindto: '#visitor',
            data: {
                columns: [
                    ['Пользователи', defaultData.users],
                    ['Постоянные пользователи', defaultData.activeUsers]
                ],
                type: 'donut'
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
    } catch (error) {
        console.error("Error initializing visitor chart:", error);
        $('#visitor').html('<div class="alert alert-warning">Ошибка при загрузке диаграммы</div>');
    }

    // ===============================================================
    // Sales Chart
    // ===============================================================
    try {
        function prepareMonthlyData() {
            if (!Array.isArray(window.userData)) {
                return [];
            }

            const currentDate = new Date();
            const monthlyData = [];

            // Generate last 12 months of data
            for (let i = 11; i >= 0; i--) {
                const d = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
                const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;

                const monthData = window.userData.find(item => {
                    if (!item || !item.month) return false;
                    return item.month.startsWith(monthKey);
                });

                monthlyData.push({
                    period: monthKey,
                    Sales: monthData ? monthData.count : 0
                });
            }

            return monthlyData;
        }

        const chartData = prepareMonthlyData();
        console.log("Prepared monthly data:", chartData);

        if (chartData.length > 0 && document.getElementById('sales-chart')) {
            Morris.Area({
                element: 'sales-chart',
                data: chartData,
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
            $('#sales-chart').html('<div class="alert alert-info">Нет данных для отображения</div>');
        }
    } catch (error) {
        console.error("Error initializing sales chart:", error);
        $('#sales-chart').html('<div class="alert alert-warning">Ошибка при загрузке графика</div>');
    }

    // ===============================================================
    // Sales Different Chart
    // ===============================================================
    try {
        if (document.getElementById('sales')) {
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
        }
    } catch (error) {
        console.error("Error initializing sales diff chart:", error);
    }

    // ===============================================================
    // Prediction Chart
    // ===============================================================
    try {
        if (document.getElementById('prediction')) {
            var predictionChart = c3.generate({
                bindto: '#prediction',
                data: {
                    columns: [
                        ['data', 0]
                    ],
                    type: 'gauge'
                },
                gauge: {
                    width: 22
                },
                color: {
                    pattern: ['#ff9041', '#20aee3', '#24d2b5', '#6772e5'],
                    threshold: {
                        values: [30, 60, 90, 100]
                    }
                },
                size: {
                    height: 120,
                    width: 150
                }
            });

            // Animate gauge
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
        }
    } catch (error) {
        console.error("Error initializing prediction chart:", error);
    }

    console.log("Dashboard initialization completed");
});