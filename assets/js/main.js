/* Small shared script. No framework, no build step. */

document.addEventListener("DOMContentLoaded", function () {
  // Mark the nav link that matches the current page.
  var current = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".site-nav a").forEach(function (link) {
    var target = link.getAttribute("href").split("/").pop();
    if (target === current) {
      link.setAttribute("aria-current", "page");
    }
  });
});
