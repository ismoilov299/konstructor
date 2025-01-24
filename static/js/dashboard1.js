$(function() {
   "use strict";

   // Visitor donut chart
   var visitorChart = c3.generate({
       bindto: '#visitor',
       data: {
           columns: [
               ['Пользователи', userData.length],
               ['Постоянные пользователи', userDataCount.length]
           ],
           type: 'donut'
       },
       donut: {
           label: { show: false },
           title: "Статистика",
           width: 20
       },
       legend: { hide: true },
       color: {
           pattern: ['#6772e5', '#24d2b5']
       }
   });

   // Sales chart data generation
   function generateMonthlyData(userData) {
       const data = [];
       const currentDate = new Date();
       const currentYear = currentDate.getFullYear();
       const currentMonth = currentDate.getMonth() + 1;
       const monthlyUsage = {};

       userData.forEach(item => {
           const [year, month] = item.period.split('-');
           monthlyUsage[item.period] = item.Sales;
       });

       for (let i = 0; i < 12; i++) {
           let year = currentYear;
           let month = currentMonth - i;

           if (month <= 0) {
               month += 12;
               year -= 1;
           }

           const key = `${year}-${month.toString().padStart(2, '0')}`;
           data.unshift({
               period: key,
               Sales: monthlyUsage[key] || 0
           });
       }
       return data;
   }

   // Sales area chart
   Morris.Area({
       element: 'sales-chart',
       data: userData,
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
       parseTime: false,
       yLabelFormat: function(y) {
           return y === null ? 'Нет данных' : Math.round(y);
       },
       hoverCallback: function(index, options, content, row) {
           return 'Период: ' + row.period + '<br>Клиенты: ' +
                  (row.Sales === null ? 'Нет данных' : row.Sales);
       }
   });
});