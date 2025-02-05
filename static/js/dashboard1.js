$(function() {
    "use strict";

    const monthlyData = generateMonthlyData(userData);
    Morris.Area({
        element: 'sales-chart',
        data: monthlyData,
        xkey: 'period',
        ykeys: ['Sales'],
        labels: ['Клиенты'],
        pointSize: 4,
        fillOpacity: 0.5,
        pointStrokeColors: ['#20aee3'],
        behaveLikeLine: true,
        gridLineColor: '#e0e0e0',
        lineWidth: 2,
        hideHover: 'auto',
        lineColors: ['#20aee3'],
        resize: true,
        yLabelFormat: function (y) {
            if (y === null) return 'Нет данных';
            return Math.round(y);
        },
        hoverCallback: function (index, options, content, row) {
            if (row.Sales === null) {
                return 'Период: ' + row.period + '<br>Клиенты: Нет данных';
            }
            return 'Период: ' + row.period + '<br>Клиенты: ' + row.Sales;
        }
    });

    var visitorChart = c3.generate({
        bindto: '#visitor',
        data: {
            columns: [
                ['Пользователи', userData.length],
                ['Постоянные пользователи', userDataCount.length]
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

    function generateMonthlyData(userData) {
        const data = [];
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth() + 1;

        const monthlyUsage = {};
        userData.forEach(item => {
            const date = new Date(item.month);
            const key = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
            monthlyUsage[key] = item.count;
        });

        for (let i = 0; i < 12; i++) {
            let year = currentYear;
            let month = currentMonth - i;

            if (month <= 0) {
                month += 12;
                year -= 1;
            }

            const key = `${year}-${month.toString().padStart(2, '0')}`;
            const value = monthlyUsage[key] || 0;

            data.unshift({
                period: key,
                Sales: value
            });
        }

        return data;
    }

    var salesDiffChart = c3.generate({
        bindto: '#sales',
        data: {
            columns: [
                ['One+', 50],
                ['T', 60],
                ['Samsung', 20]
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

    var predictionChart = c3.generate({
        bindto: '#prediction',
        data: {
            columns: [
                ['data', 91.4]
            ],
            type: 'gauge',
            onclick: function(d, i) { console.log("onclick", d, i); },
            onmouseover: function(d, i) { console.log("onmouseover", d, i); },
            onmouseout: function(d, i) { console.log("onmouseout", d, i); }
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
});