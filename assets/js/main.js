(function () {
  "use strict";

  var header = document.querySelector(".site-header");
  var toggle = document.querySelector(".nav-toggle");

  if (toggle && header) {
    toggle.addEventListener("click", function () {
      var isOpen = header.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (!isOpen) closeAllSubmenus();
    });
  }

  function closeAllSubmenus(except) {
    document.querySelectorAll("li.has-children.open").forEach(function (li) {
      if (li !== except) {
        li.classList.remove("open");
        var btn = li.querySelector("button.nav-parent");
        if (btn) btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.querySelectorAll("button.nav-parent").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var li = btn.closest("li.has-children");
      var willOpen = !li.classList.contains("open");
      closeAllSubmenus(willOpen ? li : null);
      li.classList.toggle("open", willOpen);
      btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
    });
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest("nav.primary-nav")) closeAllSubmenus();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeAllSubmenus();
  });

  // Mark the current page's nav link.
  var here = window.location.pathname.replace(/\/index\.html$/, "/");
  document.querySelectorAll("nav.primary-nav a[href]").forEach(function (link) {
    var href = link.getAttribute("href");
    if (!href || href === "/") return;
    var normalized = href.replace(/\/index\.html$/, "/");
    if (here === normalized || here.indexOf(normalized) === 0) {
      link.setAttribute("aria-current", "page");
      var parentLi = link.closest("li.has-children");
      if (parentLi) {
        var parentBtn = parentLi.querySelector("button.nav-parent");
        if (parentBtn) parentBtn.setAttribute("aria-current", "page");
      }
    }
  });

  var year = document.querySelector("footer [data-copyright-year]");
  if (year) year.textContent = new Date().getFullYear();

  // Lightbox for click-to-enlarge photos.
  var lightboxLinks = document.querySelectorAll("a.lightbox-link");
  if (lightboxLinks.length) {
    var overlay = document.createElement("div");
    overlay.className = "lightbox-overlay";
    overlay.hidden = true;
    var overlayImg = document.createElement("img");
    overlay.appendChild(overlayImg);
    var closeBtn = document.createElement("button");
    closeBtn.className = "lightbox-close";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.hidden = true;
    closeBtn.textContent = "×";
    document.body.appendChild(overlay);
    document.body.appendChild(closeBtn);

    function openLightbox(href, alt) {
      overlayImg.src = href;
      overlayImg.alt = alt || "";
      overlay.hidden = false;
      closeBtn.hidden = false;
    }
    function closeLightbox() {
      overlay.hidden = true;
      closeBtn.hidden = true;
      overlayImg.src = "";
    }

    lightboxLinks.forEach(function (link) {
      link.addEventListener("click", function (e) {
        e.preventDefault();
        var img = link.querySelector("img");
        openLightbox(link.getAttribute("href"), img ? img.alt : "");
      });
    });
    overlay.addEventListener("click", closeLightbox);
    closeBtn.addEventListener("click", closeLightbox);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeLightbox();
    });
  }
})();
