const toggle = document.getElementById("menu-toggle");
const navigation = document.getElementById("navigation");
const mobileLayout = window.matchMedia("(max-width: 575px)");

function setNavigation(open) {
  navigation.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
}

setNavigation(!mobileLayout.matches);
mobileLayout.addEventListener("change", (event) => setNavigation(!event.matches));
toggle.addEventListener("click", () => setNavigation(navigation.hidden));
