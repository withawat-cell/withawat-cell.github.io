(function () {
  "use strict";
  var tabs = document.querySelectorAll(".filter-tab");
  var sections = document.querySelectorAll(".pub-section");
  if (!tabs.length) return;

  function applyFilter(filter) {
    sections.forEach(function (s) {
      s.hidden = filter !== "all" && s.getAttribute("data-type") !== filter;
    });
    tabs.forEach(function (t) {
      t.setAttribute("aria-pressed", t.getAttribute("data-filter") === filter ? "true" : "false");
    });
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      var filter = tab.getAttribute("data-filter");
      applyFilter(filter);
      history.replaceState(null, "", filter === "all" ? location.pathname : "#" + filter);
    });
  });

  var initial = location.hash.replace("#", "");
  var valid = Array.prototype.some.call(tabs, function (t) { return t.getAttribute("data-filter") === initial; });
  if (valid) applyFilter(initial);

  var yearFilter = document.getElementById("journal-year-filter");
  if (yearFilter) {
    var yearBlocks = document.querySelectorAll('.pub-section[data-type="journal"] .year-block');
    yearFilter.addEventListener("change", function () {
      var year = yearFilter.value;
      yearBlocks.forEach(function (b) {
        b.hidden = year !== "all" && b.getAttribute("data-year") !== year;
      });
    });
  }
})();
