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

  function closeMobileMenu() {
    if (!header || !header.classList.contains("open")) return;
    header.classList.remove("open");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
  }

  document.addEventListener("click", function (e) {
    if (!e.target.closest("nav.primary-nav")) closeAllSubmenus();
  });
  // pointerdown (not click) so a tap on empty page area closes the mobile menu on iOS too
  document.addEventListener("pointerdown", function (e) {
    if (!e.target.closest("nav.primary-nav") && !e.target.closest(".nav-toggle")) {
      closeMobileMenu();
      closeAllSubmenus();
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeAllSubmenus();
      closeMobileMenu();
    }
  });

  // Mark the current page's nav link.
  var here = window.location.pathname.replace(/\/index\.html$/, "/");
  document.querySelectorAll("nav.primary-nav a[href]").forEach(function (link) {
    var href = link.getAttribute("href");
    if (!href || href === "/") return;
    var normalized = href.replace(/\/index\.html$/, "/");
    if (here === normalized) {
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

  // Copy-to-clipboard buttons for addresses.
  document.querySelectorAll(".copy-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text;
      if (btn.hasAttribute("data-copy")) {
        text = btn.getAttribute("data-copy");
      } else {
        var address = btn.previousElementSibling;
        if (!address) return;
        text = Array.from(address.childNodes).map(function (node) {
          if (node.nodeType === Node.TEXT_NODE) return node.textContent;
          if (node.nodeName === "BR") return "\n";
          return "";
        }).join("").split("\n").map(function (line) {
          return line.replace(/\s+/g, " ").trim();
        }).filter(function (line) {
          return line.length > 0;
        }).join("\n");
      }
      navigator.clipboard.writeText(text).then(function () {
        var original = btn.innerHTML;
        var box = btn.getBoundingClientRect();
        var icon = btn.querySelector("svg");
        var size = icon ? icon.getAttribute("width") : "14";
        // keep the button the same size while the check shows, so neighbours don't shift
        btn.style.width = box.width + "px";
        btn.style.height = box.height + "px";
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="' + size + '" height="' + size + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
        btn.disabled = true;
        setTimeout(function () {
          btn.innerHTML = original;
          btn.disabled = false;
          btn.style.width = "";
          btn.style.height = "";
        }, 1500);
      });
    });
  });

  // Abstract toggle buttons.
  document.querySelectorAll(".abstract-toggle-btn").forEach(function (btn) {
    var panel = document.getElementById(btn.getAttribute("aria-controls"));
    if (!panel) return;
    btn.addEventListener("click", function () {
      var expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", expanded ? "false" : "true");
      panel.hidden = expanded;
      btn.title = expanded ? "Show abstract" : "Hide abstract";
    });
  });
})();
