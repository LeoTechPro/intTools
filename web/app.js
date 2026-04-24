const referenceText = {
  Governance:
    "Governance-инструменты удерживают tracked changes управляемыми: scoped issue, согласованная спека при изменении поведения, lock на файлы и проверка перед публикацией.",
  Runtime:
    "Runtime-инструменты делают работу с окружением проверяемой: preflight checks, recovery bundles, удалённая диагностика и browser-proof без публикации приватной инфраструктуры.",
  DBA:
    "DBA-инструменты дают защищённые входные точки: read-only проверки источников, явные target-роли, migration helpers, smoke-тесты и понятный отчёт о проверках."
};

const referenceCopy = document.querySelector("#reference-copy");
const referenceButtons = document.querySelectorAll(".reference-item");

referenceButtons.forEach((button) => {
  button.addEventListener("click", () => {
    referenceButtons.forEach((item) => {
      item.classList.remove("is-open");
      item.setAttribute("aria-expanded", "false");
    });

    button.classList.add("is-open");
    button.setAttribute("aria-expanded", "true");
    const label = button.querySelector("span")?.textContent || "Governance";
    referenceCopy.textContent = referenceText[label] || referenceText.Governance;
  });
});

const revealTargets = document.querySelectorAll(".tool-card, .section, .status-panel");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);

revealTargets.forEach((target) => observer.observe(target));
