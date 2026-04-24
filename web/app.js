const referenceText = {
  Spec:
    "Spec фиксирует требование до реализации: что меняется, почему это нужно, где границы и какие проверки доказывают результат.",
  Lock:
    "Lock защищает рабочую зону от конфликтов: агент правит только согласованные tracked-файлы и не трогает несвязанный owner-state.",
  Verify:
    "Verify закрывает цикл: тесты, smoke, статический сайт, git-состояние и публикация проверяются как факты, а не как предположение."
};

const categoryLabels = {
  governance: "Governance",
  runtime: "Runtime",
  dba: "DBA",
  delivery: "Delivery",
  adapter: "Адаптер",
  interface: "Интерфейс",
  reference: "Референс"
};

const catalogGrid = document.querySelector("#catalog-grid");
const filterButtons = document.querySelectorAll(".filter-button");
let catalogItems = [];
let activeFilter = "all";

function renderCatalog() {
  if (!catalogGrid) return;

  const visibleItems =
    activeFilter === "all"
      ? catalogItems
      : catalogItems.filter((item) => item.category === activeFilter);

  catalogGrid.innerHTML = visibleItems
    .map((item, index) => {
      const tags = item.tags.map((tag) => `<span>${tag}</span>`).join("");
      const label = categoryLabels[item.category] || item.category;
      return `
        <article class="catalog-card ${item.kind === "reference" ? "is-reference" : ""}" style="--delay:${index * 45}ms">
          <div class="catalog-card-top">
            <span class="card-code">${String(index + 1).padStart(2, "0")}</span>
            <span class="category-pill">${label}</span>
          </div>
          <h3>${item.name}</h3>
          <p class="catalog-path">${item.root}</p>
          <p>${item.summary}</p>
          <div class="tag-row">${tags}</div>
        </article>`;
    })
    .join("");

  if (!visibleItems.length) {
    catalogGrid.innerHTML = '<p class="catalog-loading">В этой категории пока нет элементов.</p>';
  }

  document.querySelectorAll(".catalog-card").forEach((card) => {
    card.classList.add("is-visible");
  });
}

async function loadCatalog() {
  if (!catalogGrid) return;

  try {
    const response = await fetch("./tools.catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`catalog http ${response.status}`);
    const data = await response.json();
    catalogItems = data.tools || [];
    renderCatalog();
  } catch (error) {
    catalogGrid.innerHTML =
      '<p class="catalog-loading">Каталог не загрузился. Проверьте tools.catalog.json рядом со статикой сайта.</p>';
  }
}

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    filterButtons.forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    activeFilter = button.dataset.filter || "all";
    renderCatalog();
  });
});

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
    const label = button.querySelector("span")?.textContent || "Spec";
    referenceCopy.textContent = referenceText[label] || referenceText.Spec;
  });
});

const revealTargets = document.querySelectorAll(".section, .status-panel");

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
loadCatalog();
