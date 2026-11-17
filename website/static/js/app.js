(function () {
  "use strict";

  var numberFormat = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
  var decimalFormat = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 });

  function money(value) {
    return "Rs " + numberFormat.format(Math.round(Number(value) || 0));
  }

  function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  window.RRA = {
    number: function (value) { return numberFormat.format(Number(value) || 0); },
    decimal: function (value) { return decimalFormat.format(Number(value) || 0); },
    money: money,
    escapeHtml: escapeHtml
  };

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("explorerForm");
    if (!form) {
      return;
    }
    initExplorer(form);
  });

  function initExplorer(form) {
    var tbody = document.getElementById("explorerRows");
    var summary = document.getElementById("resultSummary");
    var info = document.getElementById("paginationInfo");
    var pagination = document.getElementById("explorerPagination");
    var download = document.getElementById("explorerDownload");
    var reset = document.getElementById("explorerReset");
    var modeChip = document.getElementById("dataMode");
    var state = { rows: [], total: 0, page: 1, pages: 1, size: 25 };
    var initialPage = parseInt(form.getAttribute("data-initial-page"), 10) || 1;

    var csvColumns = [
      "pnr", "train_number", "train_name", "train_type", "zone",
      "travel_date", "booking_date", "from_station_code", "from_station_name",
      "to_station_code", "to_station_name", "distance_km", "travel_class",
      "quota", "booking_status", "current_status", "waitlist_position",
      "fare", "refund_amount", "payment_mode", "channel", "passenger_age",
      "passenger_gender", "concession", "cancellation_flag",
      "cancellation_reason", "delay_minutes", "travel_month"
    ];

    if (modeChip && window.STATIC_MODE) {
      modeChip.textContent = "Offline sample";
    }

    function readParams() {
      var params = new URLSearchParams();
      var data = new FormData(form);
      data.forEach(function (value, key) {
        var text = String(value).trim();
        if (text !== "") {
          params.set(key, text);
        }
      });
      return params;
    }

    function statusBadge(status) {
      var value = String(status || "");
      var safe = value.toLowerCase().replace(/[^a-z]/g, "");
      return '<span class="status-badge status-' + safe + '">' + escapeHtml(value) + "</span>";
    }

    function rowsHtml(rows) {
      if (!rows.length) {
        return '<tr><td colspan="10"><div class="empty-state">No bookings match the current filters.</div></td></tr>';
      }
      var html = [];
      rows.forEach(function (row) {
        html.push(
          "<tr>" +
            '<td><span class="pnr-cell">' + escapeHtml(row.pnr) + "</span></td>" +
            "<td><div class=\"cell-primary\">" + escapeHtml(row.train_number) + "</div>" +
              '<div class="cell-secondary">' + escapeHtml(row.train_name) + "</div></td>" +
            "<td>" + escapeHtml(row.travel_date) + "</td>" +
            "<td><div class=\"cell-primary\">" + escapeHtml(row.from_station_code) + "</div>" +
              '<div class="cell-secondary">' + escapeHtml(row.from_station_name) + "</div></td>" +
            "<td><div class=\"cell-primary\">" + escapeHtml(row.to_station_code) + "</div>" +
              '<div class="cell-secondary">' + escapeHtml(row.to_station_name) + "</div></td>" +
            '<td><span class="class-tag">' + escapeHtml(row.travel_class) + "</span></td>" +
            '<td><span class="quota-tag">' + escapeHtml(row.quota) + "</span></td>" +
            "<td>" + statusBadge(row.current_status) + "</td>" +
            '<td class="text-end">' + money(row.fare) + "</td>" +
            '<td class="text-end">' + (Number(row.delay_minutes) > 0
              ? escapeHtml(row.delay_minutes) + " min"
              : "On time") + "</td>" +
          "</tr>"
        );
      });
      return html.join("");
    }

    function showRows() {
      tbody.innerHTML = rowsHtml(state.rows);
      if (state.total > 0) {
        var start = (state.page - 1) * state.size + 1;
        var end = Math.min(state.total, state.page * state.size);
        summary.textContent = "Showing " + numberFormat.format(start) + " to " +
          numberFormat.format(end) + " of " + numberFormat.format(state.total) +
          " records.";
      } else {
        summary.textContent = "No records match the current filters.";
      }
      info.textContent = "Page " + state.page + " of " + state.pages;
      renderPagination();
    }

    function pageButton(label, page, disabled, active) {
      var item = document.createElement("li");
      item.className = "page-item" + (disabled ? " disabled" : "") + (active ? " active" : "");
      var button = document.createElement("button");
      button.type = "button";
      button.className = "page-link";
      button.textContent = label;
      if (disabled) {
        button.disabled = true;
      } else {
        button.addEventListener("click", function () { load(page); });
      }
      item.appendChild(button);
      return item;
    }

    function renderPagination() {
      pagination.innerHTML = "";
      if (state.pages <= 1) {
        return;
      }
      pagination.appendChild(pageButton("Prev", state.page - 1, state.page === 1, false));
      var start = Math.max(1, state.page - 2);
      var end = Math.min(state.pages, start + 4);
      start = Math.max(1, end - 4);
      for (var page = start; page <= end; page += 1) {
        pagination.appendChild(pageButton(String(page), page, false, page === state.page));
      }
      pagination.appendChild(
        pageButton("Next", state.page + 1, state.page === state.pages, false)
      );
    }

    function renderError(message) {
      state.rows = [];
      state.total = 0;
      state.page = 1;
      state.pages = 1;
      tbody.innerHTML = '<tr><td colspan="10"><div class="empty-state">' +
        escapeHtml(message) + "</div></td></tr>";
      summary.textContent = message;
      info.textContent = "Page 1 of 1";
      pagination.innerHTML = "";
    }

    function applyStatic(params) {
      var rows = window.BOOKINGS_SAMPLE || [];
      var train = (params.get("train") || "").toLowerCase();
      var travelClass = (params.get("travel_class") || "").toUpperCase();
      var quota = (params.get("quota") || "").toUpperCase();
      var status = (params.get("status") || "").toUpperCase();
      var fromDate = params.get("from_date") || "";
      var toDate = params.get("to_date") || "";
      var station = (params.get("station") || "").toUpperCase();
      var pnr = params.get("pnr") || "";
      var size = Math.max(1, Math.min(200, parseInt(params.get("size"), 10) || 25));
      var page = Math.max(1, parseInt(params.get("page"), 10) || 1);

      var filtered = rows.filter(function (row) {
        var rowTrain = String(row.train_number || "");
        var rowName = String(row.train_name || "").toLowerCase();
        if (train && rowTrain !== train && rowName.indexOf(train) === -1) {
          return false;
        }
        if (travelClass && String(row.travel_class || "").toUpperCase() !== travelClass) {
          return false;
        }
        if (quota && String(row.quota || "").toUpperCase() !== quota) {
          return false;
        }
        if (status && String(row.current_status || "").toUpperCase() !== status) {
          return false;
        }
        if (fromDate && String(row.travel_date || "") < fromDate) {
          return false;
        }
        if (toDate && String(row.travel_date || "") > toDate) {
          return false;
        }
        if (station) {
          var fromCode = String(row.from_station_code || "").toUpperCase();
          var toCode = String(row.to_station_code || "").toUpperCase();
          if (station !== fromCode && station !== toCode) {
            return false;
          }
        }
        if (pnr && String(row.pnr || "") !== pnr) {
          return false;
        }
        return true;
      });

      filtered.sort(function (left, right) {
        var dateOrder = String(right.travel_date || "").localeCompare(String(left.travel_date || ""));
        if (dateOrder !== 0) {
          return dateOrder;
        }
        return String(right.pnr || "").localeCompare(String(left.pnr || ""));
      });

      var pages = Math.max(1, Math.ceil(filtered.length / size));
      page = Math.min(page, pages);
      var offset = (page - 1) * size;
      state.rows = filtered.slice(offset, offset + size);
      state.total = filtered.length;
      state.page = page;
      state.pages = pages;
      state.size = size;
      showRows();
    }

    function load(page) {
      var params = readParams();
      state.size = Math.max(1, Math.min(200, parseInt(params.get("size"), 10) || 25));
      params.set("page", String(page || 1));
      params.set("size", String(state.size));

      if (window.STATIC_MODE) {
        applyStatic(params);
        return;
      }

      summary.textContent = "Loading records...";
      fetch(window.BOOKINGS_ENDPOINT + "?" + params.toString(), {
        headers: { Accept: "application/json" }
      }).then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      }).then(function (data) {
        state.rows = Array.isArray(data.rows) ? data.rows : [];
        state.total = Number(data.total) || 0;
        state.page = Number(data.page) || 1;
        state.pages = Number(data.pages) || 1;
        showRows();
      }).catch(function () {
        renderError("Booking data could not be loaded. Check that the server is running.");
      });
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      load(1);
    });

    if (reset) {
      reset.addEventListener("click", function () {
        Array.prototype.forEach.call(form.elements, function (element) {
          if (element.tagName === "SELECT") {
            element.selectedIndex = 0;
          } else if (element.type !== "submit" && element.type !== "button") {
            element.value = "";
          }
        });
        load(1);
      });
    }

    function csvValue(value) {
      var text = value === null || value === undefined ? "" : String(value);
      if (/[",\r\n]/.test(text)) {
        return '"' + text.replace(/"/g, '""') + '"';
      }
      return text;
    }

    if (download) {
      download.addEventListener("click", function () {
        if (!state.rows.length) {
          return;
        }
        var lines = [csvColumns.join(",")];
        state.rows.forEach(function (row) {
          lines.push(csvColumns.map(function (column) {
            return csvValue(row[column]);
          }).join(","));
        });
        var blob = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
        var link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "bookings.csv";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
      });
    }

    load(initialPage);
  }
})();
