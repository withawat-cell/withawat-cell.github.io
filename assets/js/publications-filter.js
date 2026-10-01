(function () {
  "use strict";
  var yearFilter = document.getElementById("journal-year-filter");
  if (!yearFilter) return;
  var yearBlocks = document.querySelectorAll(".year-block");
  var topicButtons = document.querySelectorAll(".topic-filter-btn");
  var activeTopics = [];

  function applyFilters() {
    var year = yearFilter.value;
    yearFilter.classList.toggle("active", year !== "all");
    yearBlocks.forEach(function (block) {
      var yearMatches = year === "all" || block.getAttribute("data-year") === year;
      var visibleEntries = 0;
      block.querySelectorAll(".pub-entry").forEach(function (entry) {
        var entryTopics = (entry.getAttribute("data-topics") || "").split(",");
        var topicMatches = activeTopics.length === 0 || activeTopics.some(function (t) {
          return entryTopics.indexOf(t) !== -1;
        });
        var show = yearMatches && topicMatches;
        entry.hidden = !show;
        if (show) visibleEntries++;
      });
      block.hidden = visibleEntries === 0;
    });
    syncUrl();
  }

  // Mirror the active filters into the query string (?topic=a,b&year=2023)
  // so a filtered view can be shared as a link.
  function syncUrl() {
    var params = new URLSearchParams();
    if (activeTopics.length) params.set("topic", activeTopics.join(","));
    if (yearFilter.value !== "all") params.set("year", yearFilter.value);
    var query = params.toString().replace(/%2C/g, ",");
    var url = window.location.pathname + (query ? "?" + query : "") + window.location.hash;
    try { history.replaceState(null, "", url); } catch (e) {}
  }

  function restoreFromUrl() {
    var params = new URLSearchParams(window.location.search);
    var topics = (params.get("topic") || "").split(",");
    topicButtons.forEach(function (btn) {
      var topic = btn.getAttribute("data-topic");
      if (topics.indexOf(topic) !== -1) {
        btn.setAttribute("aria-pressed", "true");
        activeTopics.push(topic);
      }
    });
    var year = params.get("year");
    if (year && Array.prototype.some.call(yearFilter.options, function (o) { return o.value === year; })) {
      yearFilter.value = year;
    }
  }

  yearFilter.addEventListener("change", applyFilters);
  topicButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var topic = btn.getAttribute("data-topic");
      var pressed = btn.getAttribute("aria-pressed") === "true";
      btn.setAttribute("aria-pressed", pressed ? "false" : "true");
      if (pressed) {
        activeTopics = activeTopics.filter(function (t) { return t !== topic; });
      } else {
        activeTopics.push(topic);
      }
      applyFilters();
    });
  });

  restoreFromUrl();
  if (activeTopics.length || yearFilter.value !== "all") applyFilters();
})();
