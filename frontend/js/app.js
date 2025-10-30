import { loadProject, saveProject } from "./offline.js";

const projectForm = document.querySelector("#projectForm");
const projectResults = document.querySelector("#projectResults");
const blueprint2D = document.querySelector("#blueprint2D");
const blueprint3D = document.querySelector("#blueprint3D");
const manualSteps = document.querySelector("#manualSteps");
const materialList = document.querySelector("#materialList");
const estimatedCost = document.querySelector("#estimatedCost");
const viabilityScore = document.querySelector("#viabilityScore");
const alertList = document.querySelector("#alertList");
const planOptions = document.querySelector("#planOptions");
const manualLevels = document.querySelector("#manualLevels");
const videoList = document.querySelector("#videoList");
const financingList = document.querySelector("#financingList");
const financeResult = document.querySelector("#financeResult");
const architectList = document.querySelector("#architectList");
const supplierList = document.querySelector("#supplierList");
const testimonialList = document.querySelector("#testimonialList");
const downloadManual = document.querySelector("#downloadManual");
const assistanceButton = document.querySelector("#assistanceButton");
const contactArchitect = document.querySelector("#contactArchitect");
const loadOfflineProject = document.querySelector("#loadOfflineProject");

let currentProjectId = null;
let supplierMap;
let supplierLayer;

projectForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = extractFormData(new FormData(projectForm));
  try {
    const response = await fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "No se pudo generar el proyecto");
    }
    const data = await response.json();
    currentProjectId = data.project_id;
    renderProject(data);
    projectResults.classList.remove("hidden");
    saveProject(data);
    downloadManual.setAttribute("href", `/api/projects/${currentProjectId}/manual/pdf`);
  } catch (error) {
    alert(error.message);
  }
});

contactArchitect?.addEventListener("click", () => {
  if (!architectList.firstElementChild) {
    alert("Aún no hay arquitectos listados. Genera tu proyecto primero.");
    return;
  }
  alert("Se ha solicitado la asistencia de un arquitecto. Recibirás contacto en breve.");
});

assistanceButton?.addEventListener("click", () => {
  alert("Un arquitecto verificado se pondrá en contacto contigo en los próximos minutos.");
});

loadOfflineProject?.addEventListener("click", () => {
  const cached = loadProject();
  if (!cached) {
    alert("No hay proyectos guardados offline aún.");
    return;
  }
  currentProjectId = cached.project_id ?? currentProjectId;
  renderProject(cached);
  projectResults.classList.remove("hidden");
});

async function renderProject(data) {
  const { overview, plans, manual, materials, alerts, viability } = data;
  viabilityScore.textContent = `Viabilidad ${Math.round(viability.score * 100)}% · ${viability.message}`;

  blueprint2D.innerHTML = plans.selected.blueprint_2d.svg;
  blueprint3D.innerHTML = plans.selected.blueprint_3d.volumes
    .map((volume) => `<div><strong>${volume.label}</strong>: ${volume.footprint.width}m x ${volume.footprint.length}m · altura ${volume.height}m</div>`)
    .join("");

  manualSteps.innerHTML = manual.steps
    .map(
      (step) => `
        <li class="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
          <p class="font-semibold text-emerald-300">${step.title}</p>
          <p class="mt-1 text-sm">${step.description}</p>
          ${step.video ? `<a class="mt-2 inline-flex text-emerald-300" href="https://www.youtube.com/watch?v=${step.video.youtube_id}" target="_blank" rel="noopener">Ver video ›</a>` : ""}
        </li>
      `
    )
    .join("");

  materialList.innerHTML = materials.items
    .map(
      (item) => `
        <li class="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
          <div>
            <p class="font-semibold text-slate-100">${item.name}</p>
            <p class="text-xs text-slate-400">${item.quantity} ${item.unit}</p>
          </div>
          <span class="font-semibold text-emerald-300">$${item.unit_cost}</span>
        </li>
      `
    )
    .join("");
  estimatedCost.textContent = `Costo estimado total: $${materials.estimated_total}`;

  alertList.innerHTML = alerts.map((alert) => `<li>${alert}</li>`).join("");

  planOptions.innerHTML = plans.options
    .map(
      (option) => `
        <article class="card">
          <h5 class="text-lg font-semibold text-emerald-300">${option.name}</h5>
          <p class="mt-2 text-sm text-slate-300">${option.description}</p>
          <p class="mt-4 text-sm font-semibold text-emerald-200">Compatibilidad: ${Math.round(
            option.compatibility * 100
          )}%</p>
        </article>
      `
    )
    .join("");

  await Promise.all([loadVideos(), loadManualLevels(), loadMarketplace(), loadFinancing(), loadTestimonials()]);
  await loadSuppliersMap();
}

async function loadManualLevels() {
  const response = await fetch("/api/manual/steps");
  const { steps } = await response.json();
  manualLevels.innerHTML = steps
    .map(
      (level) => `
        <article class="card">
          <h3 class="text-lg font-semibold text-emerald-300">${level.title}</h3>
          <p class="mt-2 text-sm text-slate-300">${level.summary}</p>
          <div class="mt-4 space-y-2 text-sm">
            ${level.videos
              .map(
                (video) => `
                  <a class="block rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:border-emerald-300"
                    href="https://www.youtube.com/watch?v=${video.youtube_id}" target="_blank" rel="noopener">
                    <p class="font-semibold text-slate-100">${video.title}</p>
                    <p class="text-xs text-slate-400">${video.description}</p>
                  </a>`
              )
              .join("")}
          </div>
        </article>
      `
    )
    .join("");
}

async function loadVideos() {
  const category = document.querySelector("#videoCategory").value;
  const search = document.querySelector("#videoSearch").value;
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (search) params.set("search", search);

  const response = await fetch(`/api/videos?${params.toString()}`);
  const { videos } = await response.json();
  videoList.innerHTML = videos
    .map(
      (video) => `
        <article class="card">
          <iframe class="aspect-video w-full rounded-xl" src="https://www.youtube.com/embed/${video.youtube_id}" allowfullscreen loading="lazy"></iframe>
          <div class="mt-3">
            <h3 class="text-lg font-semibold text-emerald-300">${video.title}</h3>
            <p class="text-sm text-slate-400">${video.description}</p>
          </div>
        </article>
      `
    )
    .join("");
}

document.querySelector("#videoCategory")?.addEventListener("change", loadVideos);

document.querySelector("#videoSearch")?.addEventListener("input", debounce(loadVideos, 400));

document.querySelector("#refreshManual")?.addEventListener("click", loadManualLevels);

document.querySelector("#refreshFinancing")?.addEventListener("click", loadFinancing);

async function loadMarketplace() {
  const [architectResponse, supplierResponse] = await Promise.all([
    fetch("/api/marketplace/architects"),
    fetch("/api/marketplace/suppliers")
  ]);
  const { architects } = await architectResponse.json();
  const { suppliers } = await supplierResponse.json();

  architectList.innerHTML = architects
    .map(
      (architect) => `
        <article class="card">
          <h4 class="text-lg font-semibold text-emerald-300">${architect.name}</h4>
          <p class="text-sm text-slate-300">${architect.specialty}</p>
          <p class="text-xs text-slate-400">${architect.city} · ${architect.price_range}</p>
          <a class="mt-2 inline-flex text-sm text-emerald-300" href="${architect.portfolio_url}" target="_blank" rel="noopener">Ver portafolio</a>
        </article>
      `
    )
    .join("");

  supplierList.innerHTML = suppliers
    .map(
      (supplier) => `
        <article class="card">
          <h4 class="text-lg font-semibold text-emerald-300">${supplier.name}</h4>
          <p class="text-sm text-slate-300">${supplier.material_focus}</p>
          <p class="text-xs text-slate-400">${supplier.city} · ${supplier.address}</p>
          <p class="text-xs text-slate-400">Contacto: ${supplier.contact}</p>
        </article>
      `
    )
    .join("");
}

async function loadFinancing() {
  const productType = document.querySelector("#financingType").value;
  const params = new URLSearchParams();
  if (productType) params.set("type", productType);
  const response = await fetch(`/api/financing/products?${params.toString()}`);
  const { products } = await response.json();

  financingList.innerHTML = products
    .map(
      (product) => `
        <article class="card">
          <h4 class="text-lg font-semibold text-emerald-300">${product.name}</h4>
          <p class="text-sm text-slate-300">${product.provider}</p>
          <p class="text-xs text-slate-400">Tasa ${product.rate}% · Plazo ${product.term_months} meses</p>
          <p class="mt-2 text-xs text-slate-400">Requisitos: ${product.requirements}</p>
        </article>
      `
    )
    .join("");
}

async function loadSuppliersMap() {
  if (!supplierMap) {
    supplierMap = L.map("supplierMap").setView([23.6345, -102.5528], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap"
    }).addTo(supplierMap);
  }
  const response = await fetch("/api/maps/suppliers");
  const { markers } = await response.json();
  if (supplierLayer) {
    supplierLayer.remove();
  }
  supplierLayer = L.layerGroup(
    markers.map((marker) =>
      L.marker([marker.lat, marker.lng]).bindPopup(
        `<strong>${marker.name}</strong><br>${marker.material}<br>${marker.city}`
      )
    )
  ).addTo(supplierMap);
}

async function loadTestimonials() {
  const response = await fetch("/api/testimonials");
  const { testimonials } = await response.json();
  testimonialList.innerHTML = testimonials
    .map(
      (testimonial) => `
        <article class="card">
          <p class="text-sm text-slate-300">“${testimonial.quote}”</p>
          <p class="mt-2 text-xs text-emerald-300">${testimonial.author} · ${testimonial.location}</p>
        </article>
      `
    )
    .join("");
}

const financeSimulator = document.querySelector("#financeSimulator");
financeSimulator?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(financeSimulator);
  const amount = formData.get("amount");
  const months = formData.get("months");
  const rate = formData.get("rate");
  const params = new URLSearchParams({ amount, months, rate });
  const response = await fetch(`/api/financing/simulate?${params.toString()}`);
  const data = await response.json();
  financeResult.innerHTML = `
    <div class="notice">
      Pago mensual aproximado: <strong>$${data.monthly_payment}</strong><br />
      Total pagado: <strong>$${data.total_paid}</strong><br />
      Intereses: <strong>$${data.interest_paid}</strong>
    </div>
  `;
});

function extractFormData(formData) {
  const payload = {};
  for (const [key, value] of formData.entries()) {
    if (payload[key]) {
      if (Array.isArray(payload[key])) {
        payload[key].push(value);
      } else {
        payload[key] = [payload[key], value];
      }
    } else {
      payload[key] = value;
    }
  }
  ["necesidades", "preferencias", "espacios"].forEach((field) => {
    if (!Array.isArray(payload[field])) {
      payload[field] = payload[field] ? [payload[field]] : [];
    }
  });
  payload.presupuesto = Number(payload.presupuesto);
  payload.largo_terreno = Number(payload.largo_terreno);
  payload.ancho_terreno = Number(payload.ancho_terreno);
  payload.personas = Number(payload.personas);
  payload.plantas = Number(payload.plantas);
  return payload;
}

function debounce(fn, delay = 300) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}

loadManualLevels();
loadVideos();
loadMarketplace();
loadFinancing();
loadTestimonials();
loadSuppliersMap();
