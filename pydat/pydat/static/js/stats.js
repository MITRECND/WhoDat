$(document).ready(function() {

    var regChartctx = $("#regChart").get(0).getContext("2d");
    var regChart = new Chart(regChartctx).Bar(chartData, {
                                                legendTemplate: 
"<div class=\"chartLegend\"><% for (var i=0; i<datasets.length; i++){%><div class=\"legendEntry\"><div class=\"legendContainer\"><div class=\"legendColor\" style=\"background-color:<%=datasets[i].fillColor%>\"></div><div class=\"legendName\"><span><%if(datasets[i].label){%><%=datasets[i].label%><%}%></span></div></div></div><%}%></div>",
                                                responsive: true
                                                });
    legendtxt = regChart.generateLegend();
    $("#regChartLegend").html(legendtxt);

    var ltChartctx = $("#ltChart").get(0).getContext("2d"); 
    var ltChart = new Chart(ltChartctx).Bar(ltData, {
                                                legendTemplate: 
"<div class=\"chartLegend\"><% for (var i=0; i<datasets.length; i++){%><div class=\"legendEntry\"><div class=\"legendContainer\"><div class=\"legendColor\" style=\"background-color:<%=datasets[i].fillColor%>\"></div><div class=\"legendName\"><span><%if(datasets[i].label){%><%=datasets[i].label%><%}%></span></div></div></div><%}%></div>",
                                                responsive: true
                                            });
    ltlegendtxt = ltChart.generateLegend();
    $("#ltChartLegend").html(ltlegendtxt);


});
