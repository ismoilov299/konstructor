$(function() {
    "use strict";

    // Debug logs
    console.log("Starting dashboard initialization...");

    // ===============================================================
    // Initial Data Check
    // ===============================================================
    const defaultData = {
        users: 0,
        activeUsers: 0
    };

    // ===============================================================
    // Visitor Chart (Donut)
    // ===============================================================
    if (document.getElementById('visitor')) {
        var chart = c3.generate({
            bindto: '#visitor',
            data: {
                columns: [
                    ['Все пользователи', defaultData.users],
                    ['Постоянные пользователи', defaultData.activeUsers]
                ],
                type: 'donut',
                empty: {
                    label: {
                        text: "Нет данных"
                    }
                }
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

        // Update chart if data exists
        if (typeof userData !== 'undefined' && typeof userDataCount !== 'undefined') {
            setTimeout(function() {
                if (Array.isArray(userData) && Array.isArray(userDataCount)) {
                    chart.load({
                        columns: [
                            ['Все пользователи', userData.length],
                            ['Постоянные пользователи', userDataCount.length]
                        ]
                    });
                }
            }, 1000);
        }
    }

    // ===============================================================
    // Sales Chart (Area)
    // ===============================================================
    if (document.getElementById('sales-chart')) {
        // Prepare monthly data with default values
        const monthlyData = [];
        const currentDate = new Date();

        // Generate last 12 months with default values
        for (let i = 11; i >= 0; i--) {
            const d = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
            monthlyData.push({
                period: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`,
                Sales: 0
            });
        }

        // Create Morris chart
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
    }

    // ===============================================================
    // Sales Different Chart
    // ===============================================================
    if (document.getElementById('sales')) {
        var salesDiffChart = c3.generate({
            bindto: '#sales',
            data: {
                columns: [
                    ['One+', 30],
                    ['T', 40],
                    ['Samsung', 30]
                ],
                type: 'donut',
                empty: {
                    label: {
                        text: "Нет данных"
                    }
                }
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

    // ===============================================================
    // Prediction Chart
    // ===============================================================
    if (document.getElementById('prediction')) {
        var predictionChart = c3.generate({
            bindto: '#prediction',
            data: {
                columns: [
                    ['data', 0]
                ],
                type: 'gauge',
                empty: {
                    label: {
                        text: "Нет данных"
                    }
                }
            },
            gauge: {
                width: 22,
                label: {
                    format: function(value, ratio) {
                        return value;
                    },
                    show: false
                },
                min: 0,
                max: 100,
                units: ' %'
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
});