/* Small shared script. No framework, no build step. */

document.addEventListener("DOMContentLoaded", function () {
  markCurrentNavLink();
  setUpPassagePicker();
});

function markCurrentNavLink() {
  var current = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".site-nav a").forEach(function (link) {
    if (link.getAttribute("href").split("/").pop() === current) {
      link.setAttribute("aria-current", "page");
    }
  });
}

/* One passage at a time: the picker lists them, the chosen one opens below.
   Without JavaScript every passage stays visible, so nothing is lost. */
function setUpPassagePicker() {
  var picker = document.querySelector(".picker");
  var passages = Array.prototype.slice.call(document.querySelectorAll(".piska"));
  if (!picker || !passages.length) {
    return;
  }
  var links = Array.prototype.slice.call(picker.querySelectorAll(".picker__item"));

  function show(id, scroll) {
    var found = false;
    passages.forEach(function (section) {
      var match = section.id === id;
      section.hidden = !match;
      if (match) {
        found = true;
      }
    });
    links.forEach(function (link) {
      var match = link.getAttribute("href") === "#" + id;
      link.classList.toggle("is-open", match);
      if (match) {
        link.setAttribute("aria-current", "true");
      } else {
        link.removeAttribute("aria-current");
      }
    });
    if (found && scroll) {
      document.getElementById(id).scrollIntoView({ block: "start", behavior: "smooth" });
    }
    return found;
  }

  links.forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      var id = link.getAttribute("href").slice(1);
      history.replaceState(null, "", "#" + id);
      show(id, true);
    });
  });

  window.addEventListener("hashchange", function () {
    show(window.location.hash.slice(1), true);
  });

  var initial = window.location.hash.slice(1);
  if (!initial || !show(initial, false)) {
    show(passages[0].id, false);
  }
}
