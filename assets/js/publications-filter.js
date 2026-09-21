(function () {
  "use strict";
  var yearFilter = document.getElementById("journal-year-filter");
  if (!yearFilter) return;
  var yearBlocks = document.querySelectorAll(".year-block");
  var topicButtons = document.querySelectorAll(".topic-filter-btn");
  var activeTopics = [];

  function applyFilters() {
    var year = yearFilter.value;
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
})();
