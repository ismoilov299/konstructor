$(function() {
    "use strict";

    try {
        console.log("Debug - Starting dashboard initialization");
        console.log("userData:", userData);
        console.log("userDataCount:", userDataCount);

        // ===============================================================
        // Our Visitor Chart
        // ===============================================================
        const visitorChart = c3.generate({
            bindto: '#visitor',
            data: {
                columns: [
                    ['Пользователи', Array.isArray(userData) ? userData.length : 0],
                    ['Постоянные пользователи', Array.isArray(userDataCount) ? userDataCount.length : 0]
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

        // ===============================================================
        // Sales Chart - Monthly Data Processing
        // ===============================================================
        function generateMonthlyData(data) {
            if (!Array.isArray(data)) {
                console.error("Invalid userData format:", data);
                return [];
            }

            const currentDate = new Date();
            const monthlyUsage = {};

            // Process existing data
            data.forEach(item => {
                if (item && item.month) {
                    const date = new Date(item.month);
                    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
                    monthlyUsage[key] = item.count || 0;
                }
            });

            const result = [];
            // Generate last 12 months data
            for (let i = 11; i >= 0; i--) {
                const d = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
                const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;

                result.push({
                    period: key,
                    Sales: monthlyUsage[key] || 0
                });
            }

            return result;
        }

        // ===============================================================
        // Sales Chart Creation
        // ===============================================================
        const monthlyData = generateMonthlyData(userData);
        console.log("Generated monthly data:", monthlyData);

        if (monthlyData.length > 0) {
            Morris.Area({
                element: 'sales-chart',
                data: monthlyData,
                xkey: 'period',
                ykeys: ['Sales'],
                labels: ['Клиенты'],
                pointSize: 3,
                fillOpacity: 0.6,
                pointStrokeColors: ['#20aee3'],
                behaveLikeLine: true,
                gridLineColor: '#e0e0e0',
                lineWidth: 3,
                hideHover: 'auto',
                lineColors: ['#20aee3'],
                resize: true,
                parseTime: false,
                yLabelFormat: function (y) {
                    return Math.round(y);
                },
                hoverCallback: function (index, options, content, row) {
                    return 'Период: ' + row.period + '<br>Клиенты: ' + row.Sales;
                }
            });
        } else {
            console.warn("No monthly data available for Morris chart");
            document.getElementById('sales-chart').innerHTML =
                '<div class="text-center p-4">Нет данных для отображения</div>';
        }

        // ===============================================================
        // Sales Different Chart (if needed)
        // ===============================================================
        const salesDiffChart = c3.generate({
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

        // ===============================================================
        // Prediction Chart (if needed)
        // ===============================================================
        const predictionChart = c3.generate({
            bindto: '#prediction',
            data: {
                columns: [
                    ['data', 91.4]
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

        // Prediction chart animations
        setTimeout(() => {
            predictionChart.load({
                columns: [['data', 10]]
            });
        }, 1000);

        setTimeout(() => {
            predictionChart.load({
                columns: [['data', 50]]
            });
        }, 2000);

        setTimeout(() => {
            predictionChart.load({
                columns: [['data', 70]]
            });
        }, 3000);

    } catch (error) {
        console.error("Error in dashboard initialization:", error);
    }
});