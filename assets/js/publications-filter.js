(function () {
  "use strict";
  var yearFilter = document.getElementById("journal-year-filter");
  if (!yearFilter) return;
  var searchBox = document.getElementById("journal-search");
  var status = document.getElementById("journal-search-status");
  var noResults = document.getElementById("journal-no-results");
  var yearBlocks = document.querySelectorAll(".year-block");
  var entries = document.querySelectorAll(".pub-entry");
  var topicButtons = document.querySelectorAll(".topic-filter-btn");
  var activeTopics = [];

  // lower-case, accent-free text of every entry (citation and abstract), for the search box
  function plain(text) {
    return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }
  var haystack = new Map();
  entries.forEach(function (entry) { haystack.set(entry, plain(entry.textContent)); });

  function applyFilters() {
    var year = yearFilter.value;
    var words = searchBox ? plain(searchBox.value).split(/\s+/).filter(Boolean) : [];
    yearFilter.classList.toggle("active", year !== "all");
    var shown = 0;
    yearBlocks.forEach(function (block) {
      var yearMatches = year === "all" || block.getAttribute("data-year") === year;
      var visibleEntries = 0;
      block.querySelectorAll(".pub-entry").forEach(function (entry) {
        var entryTopics = (entry.getAttribute("data-topics") || "").split(",");
        var topicMatches = activeTopics.length === 0 || activeTopics.some(function (t) {
          return entryTopics.indexOf(t) !== -1;
        });
        var text = haystack.get(entry);
        var searchMatches = words.every(function (w) { return text.indexOf(w) !== -1; });
        var show = yearMatches && topicMatches && searchMatches;
        entry.hidden = !show;
        if (show) visibleEntries++;
      });
      block.hidden = visibleEntries === 0;
      shown += visibleEntries;
    });
    var filtered = words.length || activeTopics.length || year !== "all";
    if (status) status.textContent = filtered ? shown + " of " + entries.length + " articles" : "";
    if (noResults) noResults.hidden = shown !== 0;
    syncUrl();
  }

  // Mirror the active filters into the query string (?topic=a,b&year=2023&q=words)
  // so a filtered view can be shared as a link.
  function syncUrl() {
    var params = new URLSearchParams();
    if (activeTopics.length) params.set("topic", activeTopics.join(","));
    if (yearFilter.value !== "all") params.set("year", yearFilter.value);
    if (searchBox && searchBox.value.trim()) params.set("q", searchBox.value.trim());
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
    if (searchBox && params.get("q")) searchBox.value = params.get("q");
  }

  yearFilter.addEventListener("change", applyFilters);
  if (searchBox) searchBox.addEventListener("input", applyFilters);
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
  if (activeTopics.length || yearFilter.value !== "all" || (searchBox && searchBox.value)) applyFilters();
})();
