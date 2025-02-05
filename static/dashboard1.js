$(function() {
    "use strict";

    // Debug logs
    console.log("Starting dashboard initialization...");

    // ===============================================================
    // Data Initialization
    // ===============================================================
    const initData = function() {
        try {
            return {
                users: typeof userData !== 'undefined' ? (Array.isArray(userData) ? userData.length : 0) : 0,
                activeUsers: typeof userDataCount !== 'undefined' ? (Array.isArray(userDataCount) ? userDataCount.length : 0) : 0
            };
        } catch(e) {
            console.error("Error initializing data:", e);
            return { users: 0, activeUsers: 0 };
        }
    };

    const data = initData();
    console.log("Initialized data:", data);

    // ===============================================================
    // Visitor Chart (Donut)
    // ===============================================================
    if (document.getElementById('visitor')) {
        try {
            c3.generate({
                bindto: '#visitor',
                data: {
                    columns: [
                        ['Пользователи', data.users],
                        ['Постоянные пользователи', data.activeUsers]
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
                },
                size: {
                    height: 200
                }
            });
        } catch(e) {
            console.error("Error creating visitor chart:", e);
            $('#visitor').html('<div class="alert alert-warning p-3">Ошибка при загрузке диаграммы</div>');
        }
    }

    // ===============================================================
    // Monthly Data Preparation
    // ===============================================================
    function prepareMonthlyData() {
        try {
            if (!Array.isArray(userData)) {
                return [];
            }

            const currentDate = new Date();
            const result = [];

            for (let i = 11; i >= 0; i--) {
                const d = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
                const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;

                const monthData = userData.find(item => {
                    if (!item || !item.month) return false;
                    return item.month.startsWith(monthKey);
                });

                result.push({
                    period: monthKey,
                    Sales: monthData ? monthData.count : 0
                });
            }

            return result;
        } catch(e) {
            console.error("Error preparing monthly data:", e);
            return [];
        }
    }

    // ===============================================================
    // Sales Chart (Area)
    // ===============================================================
    if (document.getElementById('sales-chart')) {
        try {
            const monthlyData = prepareMonthlyData();
            console.log("Monthly data prepared:", monthlyData);

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
                $('#sales-chart').html('<div class="alert alert-info p-3">Нет данных для отображения</div>');
            }
        } catch(e) {
            console.error("Error creating sales chart:", e);
            $('#sales-chart').html('<div class="alert alert-warning p-3">Ошибка при загрузке графика</div>');
        }
    }

    // ===============================================================
    // Sales Different Chart (Optional)
    // ===============================================================
    if (document.getElementById('sales')) {
        try {
            c3.generate({
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
        } catch(e) {
            console.error("Error creating sales diff chart:", e);
        }
    }

    // ===============================================================
    // Prediction Chart (Optional)
    // ===============================================================
    if (document.getElementById('prediction')) {
        try {
            let chart = c3.generate({
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

            setTimeout(() => chart.load({columns: [['data', 10]]}), 1000);
            setTimeout(() => chart.load({columns: [['data', 50]]}), 2000);
            setTimeout(() => chart.load({columns: [['data', 70]]}), 3000);
        } catch(e) {
            console.error("Error creating prediction chart:", e);
        }
    }

    console.log("Dashboard initialization completed");
});