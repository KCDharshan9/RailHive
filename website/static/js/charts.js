(function () {
  "use strict";

  var ChartLib = window.Chart;
  if (!ChartLib) {
    return;
  }

  var A = window.ANALYTICS || {};
  var RRA = window.RRA || {};
  var formatInt = RRA.number || function (value) {
    return String(Math.round(Number(value) || 0));
  };
  var formatDec = RRA.decimal || function (value) {
    return String(Number(value) || 0);
  };

  var colors = {
    navy: "#14304f",
    blue: "#1d4ed8",
    blueLight: "#93c5fd",
    teal: "#0f766e",
    tealLight: "#5eead4",
    amber: "#b45309",
    amberLight: "#f59e0b",
    slate: "#64748b",
    gray: "#94a3b8",
    indigo: "#3730a3",
    red: "#b91c1c",
    green: "#15803d"
  };

  var classColors = [
    colors.blue, colors.teal, colors.amber, colors.indigo, colors.slate, colors.amberLight
  ];

  ChartLib.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
  ChartLib.defaults.font.size = 12;
  ChartLib.defaults.color = "#475569";
  ChartLib.defaults.borderColor = "#e2e8f0";
  ChartLib.defaults.plugins.legend.labels.usePointStyle = true;
  ChartLib.defaults.plugins.legend.labels.boxWidth = 8;
  ChartLib.defaults.plugins.legend.labels.padding = 14;
  ChartLib.defaults.plugins.tooltip.backgroundColor = "#0f2742";
  ChartLib.defaults.plugins.tooltip.padding = 10;
  ChartLib.defaults.plugins.tooltip.cornerRadius = 6;

  function money(value) {
    if (RRA.money) {
      return RRA.money(value);
    }
    return "Rs " + formatInt(Math.round(Number(value) || 0));
  }

  function percent(value) {
    return formatDec(Number(value) || 0) + "%";
  }

  function hasRows(value) {
    return Array.isArray(value) && value.length > 0;
  }

  function draw(id, config) {
    var canvas = document.getElementById(id);
    if (!canvas) {
      return;
    }
    try {
      new ChartLib(canvas.getContext("2d"), config);
    } catch (error) {
      /* Tables remain readable when a chart cannot be drawn. */
    }
  }

  function legend(position, display) {
    return {
      display: display !== false,
      position: position || "bottom",
      labels: { usePointStyle: true, boxWidth: 8, padding: 14 }
    };
  }

  function doughnut(id, labels, values, options) {
    draw(id, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: classColors,
          borderColor: "#ffffff",
          borderWidth: 2,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: legend("bottom"),
          tooltip: {
            callbacks: {
              label: options && options.label ? options.label : function (context) {
                return context.label + ": " + formatInt(context.parsed);
              }
            }
          }
        }
      }
    });
  }

  function initMonthlyOverview() {
    if (!hasRows(A.monthly)) {
      return;
    }
    draw("chartMonthly", {
      type: "bar",
      data: {
        labels: A.monthly.map(function (row) { return row.month; }),
        datasets: [
          {
            type: "bar",
            label: "Bookings",
            data: A.monthly.map(function (row) { return row.bookings; }),
            backgroundColor: colors.blue,
            borderRadius: 3,
            maxBarThickness: 26,
            yAxisID: "y",
            order: 2
          },
          {
            type: "line",
            label: "Revenue",
            data: A.monthly.map(function (row) { return row.revenue / 10000000; }),
            borderColor: colors.amber,
            backgroundColor: colors.amber,
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 4,
            tension: 0.3,
            yAxisID: "y1",
            order: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: legend("bottom"),
          tooltip: {
            callbacks: {
              label: function (context) {
                if (context.dataset.yAxisID === "y1") {
                  return "Revenue: Rs " + formatDec(context.parsed.y) + " crore";
                }
                return "Bookings: " + formatInt(context.parsed.y);
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            title: { display: true, text: "Travel month" }
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: "Bookings" },
            ticks: { callback: function (value) { return formatInt(value); } }
          },
          y1: {
            beginAtZero: true,
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Revenue (Rs crore)" },
            ticks: { callback: function (value) { return formatDec(value); } }
          }
        }
      }
    });
  }

  function initClassRevenue(id) {
    if (!hasRows(A.class_revenue)) {
      return;
    }
    var total = A.class_revenue.reduce(function (sum, row) {
      return sum + Number(row.revenue || 0);
    }, 0);
    doughnut(
      id,
      A.class_revenue.map(function (row) { return row.travel_class; }),
      A.class_revenue.map(function (row) { return row.revenue; }),
      {
        label: function (context) {
          var share = total ? (context.parsed / total) * 100 : 0;
          return context.label + ": " + money(context.parsed) + " (" + percent(share) + ")";
        }
      }
    );
  }

  function initStatusMix() {
    if (!hasRows(A.status)) {
      return;
    }
    var totals = A.status.reduce(function (sum, row) {
      sum.confirmed += Number(row.confirmed || 0);
      sum.rac += Number(row.rac || 0);
      sum.waitlist += Number(row.waitlist || 0);
      sum.cancelled += Number(row.cancelled || 0);
      return sum;
    }, { confirmed: 0, rac: 0, waitlist: 0, cancelled: 0 });
    var labels = ["Confirmed", "RAC", "Waitlist", "Cancelled"];
    var values = [totals.confirmed, totals.rac, totals.waitlist, totals.cancelled];
    var total = values.reduce(function (sum, value) { return sum + value; }, 0);
    draw("chartStatusMix", {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: [colors.teal, colors.amberLight, colors.blue, colors.red],
          borderColor: "#ffffff",
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: legend("bottom"),
          tooltip: {
            callbacks: {
              label: function (context) {
                var share = total ? (context.parsed / total) * 100 : 0;
                return context.label + ": " + formatInt(context.parsed) + " (" + percent(share) + ")";
              }
            }
          }
        }
      }
    });
  }

  function initRoutes() {
    if (!hasRows(A.routes)) {
      return;
    }
    var routes = A.routes.slice(0, 12);
    draw("chartRoutes", {
      type: "bar",
      data: {
        labels: routes.map(function (row) { return row.route; }),
        datasets: [{
          data: routes.map(function (row) { return row.bookings; }),
          backgroundColor: colors.blue,
          borderRadius: 3,
          maxBarThickness: 20
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Bookings: " + formatInt(context.parsed.x);
              },
              afterLabel: function (context) {
                var row = routes[context.dataIndex];
                return row ? "Revenue: " + money(row.revenue) : "";
              }
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            title: { display: true, text: "Bookings" },
            ticks: { callback: function (value) { return formatInt(value); } }
          },
          y: {
            grid: { display: false },
            ticks: { autoSkip: false, font: { size: 11 } }
          }
        }
      }
    });
  }

  function initRevenueMonthly() {
    if (!hasRows(A.monthly)) {
      return;
    }
    draw("chartRevenueMonthly", {
      type: "line",
      data: {
        labels: A.monthly.map(function (row) { return row.month; }),
        datasets: [{
          label: "Revenue",
          data: A.monthly.map(function (row) { return row.revenue / 10000000; }),
          borderColor: colors.navy,
          backgroundColor: "rgba(20, 48, 79, 0.08)",
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 4,
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Revenue: Rs " + formatDec(context.parsed.y) + " crore";
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            title: { display: true, text: "Travel month" }
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: "Revenue (Rs crore)" },
            ticks: { callback: function (value) { return formatDec(value); } }
          }
        }
      }
    });
  }

  function initQuota() {
    if (!hasRows(A.quota_revenue)) {
      return;
    }
    var rows = A.quota_revenue;
    draw("chartRevenueQuota", {
      type: "bar",
      data: {
        labels: rows.map(function (row) { return row.quota; }),
        datasets: [{
          data: rows.map(function (row) { return row.revenue / 10000000; }),
          backgroundColor: colors.teal,
          borderRadius: 3,
          maxBarThickness: 34
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Revenue: Rs " + formatDec(context.parsed.y) + " crore";
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false }, title: { display: true, text: "Quota" } },
          y: {
            beginAtZero: true,
            title: { display: true, text: "Revenue (Rs crore)" },
            ticks: { callback: function (value) { return formatDec(value); } }
          }
        }
      }
    });
  }

  function initPayments() {
    if (!hasRows(A.payments)) {
      return;
    }
    var total = A.payments.reduce(function (sum, row) {
      return sum + Number(row.revenue || 0);
    }, 0);
    doughnut(
      "chartRevenuePayment",
      A.payments.map(function (row) { return row.payment_mode; }),
      A.payments.map(function (row) { return row.revenue; }),
      {
        label: function (context) {
          var share = total ? (context.parsed / total) * 100 : 0;
          return context.label + ": " + money(context.parsed) + " (" + percent(share) + ")";
        }
      }
    );
  }

  function initChannels() {
    if (!hasRows(A.channels)) {
      return;
    }
    var rows = A.channels;
    draw("chartRevenueChannel", {
      type: "bar",
      data: {
        labels: rows.map(function (row) { return row.channel; }),
        datasets: [{
          data: rows.map(function (row) { return row.bookings; }),
          backgroundColor: colors.indigo,
          borderRadius: 3,
          maxBarThickness: 34
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Bookings: " + formatInt(context.parsed.y);
              },
              afterLabel: function (context) {
                var row = rows[context.dataIndex];
                return row ? "Revenue: " + money(row.revenue) : "";
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false }, title: { display: true, text: "Channel" } },
          y: {
            beginAtZero: true,
            title: { display: true, text: "Bookings" },
            ticks: { callback: function (value) { return formatInt(value); } }
          }
        }
      }
    });
  }

  function initStatusByClass() {
    if (!hasRows(A.status)) {
      return;
    }
    var rows = A.status;
    draw("chartStatusByClass", {
      type: "bar",
      data: {
        labels: rows.map(function (row) { return row.travel_class; }),
        datasets: [
          {
            label: "Confirmed",
            data: rows.map(function (row) { return row.confirmed; }),
            backgroundColor: colors.teal,
            stack: "status",
            maxBarThickness: 48
          },
          {
            label: "RAC",
            data: rows.map(function (row) { return row.rac; }),
            backgroundColor: colors.amberLight,
            stack: "status",
            maxBarThickness: 48
          },
          {
            label: "Waitlist",
            data: rows.map(function (row) { return row.waitlist; }),
            backgroundColor: colors.blue,
            stack: "status",
            maxBarThickness: 48
          },
          {
            label: "Cancelled",
            data: rows.map(function (row) { return row.cancelled; }),
            backgroundColor: colors.red,
            stack: "status",
            maxBarThickness: 48
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: legend("bottom"),
          tooltip: {
            callbacks: {
              label: function (context) {
                return context.dataset.label + ": " + formatInt(context.parsed.y);
              }
            }
          }
        },
        scales: {
          x: { stacked: true, grid: { display: false }, title: { display: true, text: "Travel class" } },
          y: {
            stacked: true,
            beginAtZero: true,
            title: { display: true, text: "Passengers" },
            ticks: { callback: function (value) { return formatInt(value); } }
          }
        }
      }
    });
  }

  function initCancellations() {
    if (!hasRows(A.cancellations)) {
      return;
    }
    draw("chartCancellations", {
      type: "bar",
      data: {
        labels: A.cancellations.map(function (row) { return row.month; }),
        datasets: [
          {
            type: "bar",
            label: "Cancellations",
            data: A.cancellations.map(function (row) { return row.cancellations; }),
            backgroundColor: colors.red,
            borderRadius: 3,
            maxBarThickness: 24,
            yAxisID: "y"
          },
          {
            type: "line",
            label: "Cancellation rate",
            data: A.cancellations.map(function (row) { return row.cancellation_rate; }),
            borderColor: colors.amber,
            backgroundColor: colors.amber,
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3,
            yAxisID: "y1"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: legend("bottom"),
          tooltip: {
            callbacks: {
              label: function (context) {
                if (context.dataset.yAxisID === "y1") {
                  return "Cancellation rate: " + percent(context.parsed.y);
                }
                return "Cancellations: " + formatInt(context.parsed.y);
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false }, title: { display: true, text: "Travel month" } },
          y: {
            beginAtZero: true,
            title: { display: true, text: "Cancellations" },
            ticks: { callback: function (value) { return formatInt(value); } }
          },
          y1: {
            beginAtZero: true,
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Cancellation rate (%)" },
            ticks: { callback: function (value) { return formatDec(value) + "%"; } }
          }
        }
      }
    });
  }

  function initCancelReasons() {
    if (!hasRows(A.cancel_reasons)) {
      return;
    }
    var rows = A.cancel_reasons;
    draw("chartCancelReasons", {
      type: "bar",
      data: {
        labels: rows.map(function (row) { return row.reason; }),
        datasets: [{
          data: rows.map(function (row) { return row.count; }),
          backgroundColor: [colors.amber, colors.slate, colors.teal, colors.blue, colors.gray, colors.indigo],
          borderRadius: 3,
          maxBarThickness: 20
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Cancellations: " + formatInt(context.parsed.x);
              }
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            title: { display: true, text: "Cancellations" },
            ticks: { callback: function (value) { return formatInt(value); } }
          },
          y: {
            grid: { display: false },
            ticks: { autoSkip: false, font: { size: 11 } }
          }
        }
      }
    });
  }

  function initDelayType() {
    if (!hasRows(A.delay_by_type)) {
      return;
    }
    var rows = A.delay_by_type;
    draw("chartDelayType", {
      type: "bar",
      data: {
        labels: rows.map(function (row) { return row.train_type; }),
        datasets: [{
          data: rows.map(function (row) { return row.avg_delay; }),
          backgroundColor: colors.amber,
          borderRadius: 3,
          maxBarThickness: 38
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Average delay: " + formatDec(context.parsed.y) + " min";
              },
              afterLabel: function (context) {
                var row = rows[context.dataIndex];
                return row ? "Late share: " + percent(row.late_pct) : "";
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false }, title: { display: true, text: "Train type" } },
          y: {
            beginAtZero: true,
            title: { display: true, text: "Average delay (minutes)" },
            ticks: { callback: function (value) { return formatDec(value); } }
          }
        }
      }
    });
  }

  function initDelayZone() {
    if (!hasRows(A.delay_by_zone)) {
      return;
    }
    var rows = A.delay_by_zone;
    draw("chartDelayZone", {
      type: "bar",
      data: {
        labels: rows.map(function (row) { return row.zone; }),
        datasets: [{
          data: rows.map(function (row) { return row.avg_delay; }),
          backgroundColor: colors.teal,
          borderRadius: 3,
          maxBarThickness: 34
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Average delay: " + formatDec(context.parsed.y) + " min";
              },
              afterLabel: function (context) {
                var row = rows[context.dataIndex];
                return row ? "Late share: " + percent(row.late_pct) : "";
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false }, title: { display: true, text: "Railway zone" } },
          y: {
            beginAtZero: true,
            title: { display: true, text: "Average delay (minutes)" },
            ticks: { callback: function (value) { return formatDec(value); } }
          }
        }
      }
    });
  }

  function initDelayMonthly() {
    if (!hasRows(A.delay_monthly)) {
      return;
    }
    draw("chartDelayMonthly", {
      type: "line",
      data: {
        labels: A.delay_monthly.map(function (row) { return row.month; }),
        datasets: [
          {
            label: "Average delay",
            data: A.delay_monthly.map(function (row) { return row.avg_delay; }),
            borderColor: colors.navy,
            backgroundColor: colors.navy,
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 4,
            tension: 0.3,
            yAxisID: "y"
          },
          {
            label: "Late percentage",
            data: A.delay_monthly.map(function (row) { return row.late_pct; }),
            borderColor: colors.amber,
            backgroundColor: colors.amber,
            borderWidth: 2,
            pointRadius: 2,
            borderDash: [5, 3],
            tension: 0.3,
            yAxisID: "y1"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: legend("bottom"),
          tooltip: {
            callbacks: {
              label: function (context) {
                if (context.dataset.yAxisID === "y1") {
                  return "Late percentage: " + percent(context.parsed.y);
                }
                return "Average delay: " + formatDec(context.parsed.y) + " min";
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false }, title: { display: true, text: "Travel month" } },
          y: {
            beginAtZero: true,
            title: { display: true, text: "Average delay (minutes)" },
            ticks: { callback: function (value) { return formatDec(value); } }
          },
          y1: {
            beginAtZero: true,
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Late percentage (%)" },
            ticks: { callback: function (value) { return formatDec(value) + "%"; } }
          }
        }
      }
    });
  }

  function init() {
    initMonthlyOverview();
    initClassRevenue("chartClassRevenue");
    initClassRevenue("chartRevenueClass");
    initStatusMix();
    initRoutes();
    initRevenueMonthly();
    initQuota();
    initPayments();
    initChannels();
    initStatusByClass();
    initCancellations();
    initCancelReasons();
    initDelayType();
    initDelayZone();
    initDelayMonthly();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
