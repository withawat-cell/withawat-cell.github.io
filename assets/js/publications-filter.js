(function () {
  "use strict";
  var yearFilter = document.getElementById("journal-year-filter");
  if (!yearFilter) return;
  var yearBlocks = document.querySelectorAll(".year-block");
  yearFilter.addEventListener("change", function () {
    var year = yearFilter.value;
    yearBlocks.forEach(function (b) {
      b.hidden = year !== "all" && b.getAttribute("data-year") !== year;
    });
  });
})();
