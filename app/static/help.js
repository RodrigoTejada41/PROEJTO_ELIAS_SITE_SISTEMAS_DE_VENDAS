const manual = document.getElementById("help-manual");
const helpOpen = document.getElementById("help-open");
const tour = document.getElementById("help-tour");
const title = document.getElementById("help-tour-title");
const instruction = document.getElementById("help-instruction");
const progress = document.getElementById("help-progress");
const previous = document.getElementById("help-previous");
const next = document.getElementById("help-next");
const topics = [...manual.querySelectorAll("[data-guide]")];
const guideHash = "#guia-";
let activeTopic;
let stepIndex = 0;
let target;

function positionTour() {
  if (tour.hidden) return;
  tour.removeAttribute("data-arrow");
  tour.style.removeProperty("top");
  tour.style.removeProperty("left");
  if (!target) return;

  const rect = target.getBoundingClientRect();
  const margin = 12;
  const gap = 14;
  const { offsetWidth: width, offsetHeight: height } = tour;
  const viewportWidth = document.documentElement.clientWidth;
  const viewportHeight = window.innerHeight;
  if (rect.bottom < 0 || rect.top > viewportHeight) return;

  const center = (rect.left + rect.right) / 2;
  const left = Math.max(margin, Math.min(center - width / 2, viewportWidth - width - margin));
  let top;
  if (rect.bottom + gap + height <= viewportHeight - margin) {
    top = rect.bottom + gap;
    tour.dataset.arrow = "top";
  } else if (rect.top - gap - height >= margin) {
    top = rect.top - gap - height;
    tour.dataset.arrow = "bottom";
  } else {
    return;
  }
  tour.style.left = left + "px";
  tour.style.top = top + "px";
  tour.style.setProperty("--help-arrow-offset", Math.max(18, Math.min(center - left, width - 18)) + "px");
}

function showStep() {
  const steps = activeTopic.querySelectorAll("li");
  const step = steps[stepIndex];
  target?.classList.remove("help-target");
  target = step.dataset.target ? document.querySelector(step.dataset.target) : null;
  if (target && !target.getClientRects().length) target = null;

  title.textContent = activeTopic.querySelector("summary").textContent;
  instruction.textContent = step.textContent;
  progress.textContent = tour.dataset.step + " " + (stepIndex + 1) + " / " + steps.length;
  previous.disabled = stepIndex === 0;
  next.textContent = stepIndex === steps.length - 1 ? tour.dataset.finish : tour.dataset.next;
  tour.hidden = false;
  target?.classList.add("help-target");
  target?.scrollIntoView({ block: "center", inline: "nearest" });
  positionTour();
}

function closeTour(restoreFocus = true) {
  target?.classList.remove("help-target");
  target = null;
  activeTopic = null;
  tour.hidden = true;
  if (window.location.hash.startsWith(guideHash)) {
    history.replaceState(null, "", window.location.pathname + window.location.search);
  }
  if (restoreFocus) helpOpen.focus({ preventScroll: true });
}

function openFromHash() {
  const key = window.location.hash.slice(guideHash.length);
  const topic = window.location.hash.startsWith(guideHash) &&
    topics.find((item) => item.dataset.guide === key && item.dataset.path === window.location.pathname);
  if (!topic) {
    if (activeTopic) closeTour(false);
    return;
  }
  if (manual.open) manual.close();
  activeTopic = topic;
  stepIndex = 0;
  showStep();
  title.focus({ preventScroll: true });
}

helpOpen.addEventListener("click", () => {
  if (activeTopic) closeTour(false);
  manual.showModal();
});
previous.addEventListener("click", () => {
  stepIndex -= 1;
  showStep();
  if (previous.disabled) next.focus({ preventScroll: true });
});
next.addEventListener("click", () => {
  if (stepIndex + 1 === activeTopic.querySelectorAll("li").length) {
    closeTour();
  } else {
    stepIndex += 1;
    showStep();
  }
});
document.getElementById("help-close").addEventListener("click", () => closeTour());
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && activeTopic) closeTour();
});
window.addEventListener("hashchange", openFromHash);
window.addEventListener("resize", positionTour);
window.addEventListener("scroll", positionTour, { passive: true });
openFromHash();
