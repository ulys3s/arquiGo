const API_BASE = "/api";

const state = {
  token: localStorage.getItem("cs_token") || "",
  user: JSON.parse(localStorage.getItem("cs_user") || "null"),
  currentProjectId: null,
  blueprintRooms: [],
};

const geoIndex = {
  "Ciudad de México": {
    Iztapalapa: { lat: 19.3579, lng: -99.0671 },
    Centro: { lat: 19.4326, lng: -99.1332 },
  },
  Guadalajara: {
    Tonalá: { lat: 20.624, lng: -103.233 },
    Centro: { lat: 20.6767, lng: -103.3475 },
  },
  Puebla: {
    Cholula: { lat: 19.0552, lng: -98.3003 },
    Centro: { lat: 19.0433, lng: -98.1987 },
  },
};

const elements = {
  loginForm: document.querySelector("#loginForm"),
  registerForm: document.querySelector("#registerForm"),
  logoutButton: document.querySelector("#logoutButton"),
  authModal: document.querySelector("#authModal"),
  authModalClose: document.querySelector("#closeAuthModal"),
  openLogin: document.querySelectorAll("[data-open-login]") || [],
  userName: document.querySelector("#userName"),
  projectForm: document.querySelector("#projectForm"),
  projectResults: document.querySelector("#projectResults"),
  viabilityScore: document.querySelector("#viabilityScore"),
  blueprint2D: document.querySelector("#blueprint2D"),
  blueprintLegend: document.querySelector("#blueprintLegend"),
  blueprint3D: document.querySelector("#blueprint3D"),
  roomGuide: document.querySelector("#roomGuide"),
  manualSteps: document.querySelector("#manualSteps"),
  materialList: document.querySelector("#materialList"),
  estimatedCost: document.querySelector("#estimatedCost"),
  alertList: document.querySelector("#alertList"),
  planOptions: document.querySelector("#planOptions"),
  manualLevels: document.querySelector("#manualLevels"),
  refreshManual: document.querySelector("#refreshManual"),
  downloadManual: document.querySelector("#downloadManual"),
  projectList: document.querySelector("#projectList"),
  projectProgressBar: document.querySelector("#projectVideoProgress"),
  projectProgressText: document.querySelector("#projectProgressText"),
  videoContainer: document.querySelector("#videoList"),
  videoFilterLevel: document.querySelector("#videoLevel"),
  videoFilterSearch: document.querySelector("#videoSearch"),
  citySelect: document.querySelector("select[name='ciudad']"),
  localitySelect: document.querySelector("select[name='localidad']"),
  preferencesChips: document.querySelectorAll("input[name='preferencias']"),
  projectMap: document.querySelector("#projectMap"),
  solarOrientation: document.querySelector("#solarOrientation"),
  siteRecommendations: document.querySelector("#siteRecommendations"),
};

let projectMapInstance;
let projectZoneLayer;

document.addEventListener("DOMContentLoaded", () => {
  attachAuthHandlers();
  attachProjectHandlers();
  attachVideoHandlers();
  hydrateAuthState();
  initLocationControls();
  initProjectMap();
  elements.refreshManual?.addEventListener("click", () => {
    if (ensureAuth()) loadManualLevels();
  });
});

function attachAuthHandlers() {
  elements.loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(elements.loginForm);
    await authenticateUser(`${API_BASE}/auth/login`, formData);
  });

  elements.registerForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(elements.registerForm);
    await authenticateUser(`${API_BASE}/auth/register`, formData);
  });

  elements.logoutButton?.addEventListener("click", async () => {
    if (!state.token) return;
    await fetchWithAuth(`${API_BASE}/auth/logout`, { method: "POST" });
    clearAuthState();
  });

  if (elements.authModalClose) {
    elements.authModalClose.addEventListener("click", () => toggleAuthModal(false));
  }

  elements.openLogin.forEach((trigger) =>
    trigger.addEventListener("click", () => toggleAuthModal(true))
  );
}

function attachProjectHandlers() {
  elements.projectForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!ensureAuth()) return;
    const payload = formDataToJSON(new FormData(elements.projectForm));
    try {
      const response = await fetchWithAuth(`${API_BASE}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "No se pudo generar el proyecto");
      state.currentProjectId = data.project_id;
      renderProject(data);
      await loadProjects();
    } catch (error) {
      console.error(error);
      alert(error.message);
    }
  });

  elements.preferencesChips?.forEach((chip) => {
    chip.addEventListener("change", () => {
      if (!ensureAuth(false)) return;
    });
  });
}

function attachVideoHandlers() {
  if (elements.videoFilterLevel) {
    elements.videoFilterLevel.addEventListener("change", () => loadVideos());
  }
  if (elements.videoFilterSearch) {
    elements.videoFilterSearch.addEventListener("input", debounce(loadVideos, 350));
  }
}

async function authenticateUser(endpoint, formData) {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(formData)),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "No se pudo iniciar sesión");
    setAuthState(data.token, data.user);
    toggleAuthModal(false);
    await Promise.all([loadProjects(), loadManualLevels(), loadVideos()]);
  } catch (error) {
    console.error(error);
    alert(error.message);
  }
}

function hydrateAuthState() {
  if (!state.token || !state.user) {
    clearAuthState();
    return;
  }
  updateUserBadge();
  Promise.all([loadProjects(), loadManualLevels(), loadVideos()]).catch((error) => {
    console.error(error);
    if (error.status === 401) clearAuthState();
  });
}

function setAuthState(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("cs_token", token);
  localStorage.setItem("cs_user", JSON.stringify(user));
  updateUserBadge();
}

function clearAuthState() {
  state.token = "";
  state.user = null;
  state.currentProjectId = null;
  localStorage.removeItem("cs_token");
  localStorage.removeItem("cs_user");
  updateUserBadge();
  elements.projectResults?.classList.add("hidden");
  elements.projectList && (elements.projectList.innerHTML = "");
  if (elements.projectProgressBar) elements.projectProgressBar.style.width = "0%";
  if (elements.projectProgressText) elements.projectProgressText.textContent = "0%";
}

function updateUserBadge() {
  if (!elements.userName) return;
  if (state.user) {
    elements.userName.textContent = state.user.full_name || state.user.email;
    elements.userName.classList.remove("hidden");
    elements.logoutButton?.classList.remove("hidden");
  } else {
    elements.userName.textContent = "";
    elements.userName.classList.add("hidden");
    elements.logoutButton?.classList.add("hidden");
  }
}

function toggleAuthModal(show) {
  if (!elements.authModal) return alert("Inicia sesión para continuar");
  elements.authModal.classList.toggle("hidden", !show);
}

function ensureAuth(showDialog = true) {
  if (state.token) return true;
  if (showDialog) toggleAuthModal(true);
  return false;
}

function formDataToJSON(formData) {
  const payload = {};
  for (const [key, value] of formData.entries()) {
    if (payload[key]) {
      if (!Array.isArray(payload[key])) payload[key] = [payload[key]];
      payload[key].push(value);
    } else {
      payload[key] = value;
    }
  }
  ["necesidades", "preferencias", "espacios"].forEach((field) => {
    if (payload[field]) payload[field] = [].concat(payload[field]);
    else payload[field] = [];
  });
  ["presupuesto", "largo_terreno", "ancho_terreno", "personas", "plantas"].forEach((field) => {
    if (payload[field] !== undefined) payload[field] = Number(payload[field]);
  });
  return payload;
}

async function fetchWithAuth(url, options = {}) {
  const config = { ...options };
  config.headers = {
    ...(options.headers || {}),
    Authorization: state.token ? `Bearer ${state.token}` : undefined,
  };
  const response = await fetch(url, config);
  if (response.status === 401) {
    clearAuthState();
    throw Object.assign(new Error("Sesión expirada"), { status: 401 });
  }
  return response;
}

async function loadProjects() {
  if (!ensureAuth(false)) return;
  const response = await fetchWithAuth(`${API_BASE}/projects`);
  const { projects } = await response.json();
  renderProjectList(projects);
  if (projects.length && !state.currentProjectId) {
    state.currentProjectId = projects[0].id;
    renderProject(projects[0].plan_data);
  }
  if (elements.projectProgressBar && projects.length) {
    const progress = Math.round(projects[0].video_progress * 100);
    elements.projectProgressBar.style.width = `${progress}%`;
    if (elements.projectProgressText) elements.projectProgressText.textContent = `${progress}%`;
  }
}

function renderProjectList(projects) {
  if (!elements.projectList) return;
  elements.projectList.innerHTML = projects
    .map(
      (project) => `
        <article class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <header class="flex items-center justify-between gap-3">
            <h3 class="font-semibold text-emerald-300">${project.title}</h3>
            <span class="text-xs text-slate-400">${new Date(project.created_at).toLocaleDateString()}</span>
          </header>
          <p class="mt-2 text-sm text-slate-400">Estado: ${project.status}</p>
          <div class="mt-3 flex items-center gap-2 text-xs">
            <span class="rounded-full bg-emerald-500/10 px-2 py-1 text-emerald-300">Videos vistos: ${project.videos_watched}/${project.total_videos}</span>
            <button class="rounded-full border border-emerald-400/50 px-3 py-1 text-emerald-200" data-open-project="${project.id}">Abrir</button>
          </div>
        </article>
      `
    )
    .join("");

  elements.projectList
    .querySelectorAll("[data-open-project]")
    .forEach((button) =>
      button.addEventListener("click", async () => {
        const id = Number(button.dataset.openProject);
        const response = await fetchWithAuth(`${API_BASE}/projects/${id}`);
        const data = await response.json();
        state.currentProjectId = id;
        renderProject(data.plan_data || data);
      })
    );
}

function renderProject(data) {
  elements.projectResults?.classList.remove("hidden");
  elements.viabilityScore.textContent = `Viabilidad ${Math.round(
    data.viability.score * 100
  )}% · ${data.viability.message}`;

  if (elements.blueprint2D) {
    elements.blueprint2D.innerHTML = data.plans.selected.blueprint_2d.svg;
    state.blueprintRooms = data.plans.selected.blueprint_2d.rooms;
    attachRoomInteractions();
  }
  if (elements.blueprintLegend) renderBlueprintLegend();
  if (elements.blueprint3D) {
    elements.blueprint3D.innerHTML = data.plans.selected.blueprint_3d.volumes
      .map(
        (volume) => `
          <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm">
            <p class="font-semibold text-slate-100">${volume.label}</p>
            <p class="text-slate-400">${volume.footprint.width}m x ${volume.footprint.length}m · ${volume.height}m alto</p>
          </div>
        `
      )
      .join("");
  }

  if (elements.manualSteps) {
    elements.manualSteps.innerHTML = data.manual.steps
      .map(
        (step) => `
          <li class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <h5 class="text-emerald-300">${step.title}</h5>
            <p class="mt-1 text-sm text-slate-300">${step.description}</p>
            ${step.video ? `<a class="mt-2 inline-flex items-center text-xs text-emerald-300" href="https://www.youtube.com/watch?v=${step.video.youtube_id}" target="_blank" rel="noopener">Ver guía en YouTube</a>` : ""}
          </li>
        `
      )
      .join("");
  }

  if (elements.materialList) {
    elements.materialList.innerHTML = data.materials.items
      .map(
        (item) => `
          <li class="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm">
            <div>
              <p class="font-semibold text-slate-100">${item.name}</p>
              <p class="text-xs text-slate-400">${item.quantity} ${item.unit}</p>
            </div>
            <span class="text-emerald-300">$${item.unit_cost}</span>
          </li>
        `
      )
      .join("");
  }

  if (elements.estimatedCost) {
    elements.estimatedCost.textContent = `Costo estimado total: $${data.materials.estimated_total}`;
  }

  if (elements.alertList) {
    elements.alertList.innerHTML = data.alerts
      .map((alert) => `<li>${alert}</li>`)
      .join("");
  }

  if (elements.planOptions) {
    elements.planOptions.innerHTML = data.plans.options
      .map(
        (option) => `
          <article class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <h5 class="text-emerald-300">${option.name}</h5>
            <p class="mt-2 text-sm text-slate-300">${option.description}</p>
            <p class="mt-3 text-xs text-emerald-200">Compatibilidad: ${Math.round(option.compatibility * 100)}%</p>
            <p class="text-xs text-slate-400">Orientación solar: ${option.solar_orientation || data.site.solar}</p>
          </article>
        `
      )
      .join("");
  }

  if (elements.downloadManual) {
    elements.downloadManual.href = `/api/projects/${state.currentProjectId}/manual/pdf`;
  }

  updateProjectMap(data.site, data.overview?.terrain);
}

function attachRoomInteractions() {
  if (!elements.blueprint2D) return;
  const svg = elements.blueprint2D.querySelector("svg");
  if (!svg) return;
  const roomMap = new Map();
  state.blueprintRooms.forEach((room) => roomMap.set(room.name.toLowerCase(), room));
  svg.querySelectorAll(".room").forEach((roomNode) => {
    const key = roomNode.dataset.room?.toLowerCase();
    const roomData = roomMap.get(key);
    roomNode.addEventListener("click", () => renderRoomGuide(roomData));
  });
}

function renderRoomGuide(room) {
  if (!elements.roomGuide || !room) return;
  const video = room.guide?.video;
  const manualStep = room.guide?.manual_step || "";
  elements.roomGuide.innerHTML = `
    <div class="rounded-2xl border border-emerald-500/30 bg-slate-900/70 p-4">
      <h4 class="text-lg font-semibold text-emerald-300">${room.name}</h4>
      <p class="mt-1 text-sm text-slate-300">Área estimada: ${room.area} m²</p>
      ${manualStep ? `<p class="mt-2 text-xs uppercase tracking-wide text-emerald-200">Guía vinculada: ${manualStep.replace(/_/g, " ")}</p>` : ""}
      ${video ? `
        <div class="mt-3 overflow-hidden rounded-xl">
          <iframe class="aspect-video w-full" src="https://www.youtube.com/embed/${video.youtube_id}" title="${video.title}" allowfullscreen loading="lazy"></iframe>
        </div>
        <button class="mt-3 rounded-full bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950" data-watch-video="${video.id}">Marcar como visto</button>
      ` : ""}
    </div>
  `;

  elements.roomGuide
    .querySelectorAll("[data-watch-video]")
    .forEach((button) =>
      button.addEventListener("click", () => {
        const videoId = Number(button.dataset.watchVideo);
        markVideoAsWatched(videoId);
      })
    );
}

function renderBlueprintLegend() {
  if (!elements.blueprintLegend) return;
  elements.blueprintLegend.innerHTML = state.blueprintRooms
    .map(
      (room) => `
        <li class="flex items-center gap-3 text-xs">
          <span class="h-3 w-3 rounded-full" style="background:${room.style.fill}"></span>
          <span>${room.name}</span>
        </li>
      `
    )
    .join("");
}

async function loadManualLevels() {
  if (!ensureAuth(false)) return;
  const response = await fetchWithAuth(`${API_BASE}/manual/steps`);
  const { steps } = await response.json();
  if (!elements.manualLevels) return;
  elements.manualLevels.innerHTML = steps
    .map(
      (step) => `
        <article class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <header class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-emerald-300">${step.title}</h3>
            <span class="text-xs uppercase tracking-wide text-slate-400">${step.level}</span>
          </header>
          <p class="mt-2 text-sm text-slate-300">${step.summary}</p>
          <div class="mt-4 space-y-2">
            ${step.videos
              .map(
                (video) => `
                  <a class="block rounded-xl border border-slate-800 bg-slate-900/40 p-3 text-sm text-slate-200 hover:border-emerald-400" href="https://www.youtube.com/watch?v=${video.youtube_id}" target="_blank" rel="noopener">
                    <p class="font-semibold text-emerald-200">${video.title}</p>
                    <p class="text-xs text-slate-400">${video.description}</p>
                  </a>
                `
              )
              .join("")}
          </div>
        </article>
      `
    )
    .join("");
}

async function loadVideos() {
  if (!ensureAuth(false)) return;
  const params = new URLSearchParams();
  if (elements.videoFilterLevel?.value) params.set("level", elements.videoFilterLevel.value);
  if (elements.videoFilterSearch?.value) params.set("search", elements.videoFilterSearch.value);
  const response = await fetchWithAuth(`${API_BASE}/videos?${params.toString()}`);
  const { videos } = await response.json();
  renderVideoLibrary(videos);
}

function renderVideoLibrary(videos) {
  if (!elements.videoContainer) return;
  if (!videos.length) {
    elements.videoContainer.innerHTML = `<p class="text-sm text-slate-400">No encontramos videos con esos filtros.</p>`;
    return;
  }
  elements.videoContainer.innerHTML = videos
    .map(
      (video) => `
        <article class="rounded-3xl border border-slate-800 bg-slate-900/60 p-4">
          <header class="flex items-center justify-between gap-3">
            <h3 class="text-lg font-semibold text-emerald-300">${video.title}</h3>
            <span class="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">${capitalize(video.level)}</span>
          </header>
          <div class="mt-3 overflow-hidden rounded-xl">
            <iframe class="aspect-video w-full" src="https://www.youtube.com/embed/${video.youtube_id}" allowfullscreen loading="lazy" title="${video.title}"></iframe>
          </div>
          <p class="mt-3 text-sm text-slate-300">${video.description}</p>
          <p class="mt-2 text-xs text-slate-400">Paso del manual: ${video.manual_step.replace(/_/g, " ")}</p>
          <button class="mt-3 w-full rounded-full ${video.watched ? "bg-slate-800 text-emerald-200" : "bg-emerald-500 text-slate-950"} px-4 py-2 text-sm font-semibold" data-watch-video="${video.id}">
            ${video.watched ? "Marcado como visto" : "Marcar como visto"}
          </button>
        </article>
      `
    )
    .join("");

  elements.videoContainer.querySelectorAll("[data-watch-video]").forEach((button) => {
    button.addEventListener("click", () => {
      const videoId = Number(button.dataset.watchVideo);
      markVideoAsWatched(videoId, button);
    });
  });
}

async function markVideoAsWatched(videoId, button) {
  if (!ensureAuth()) return;
  const response = await fetchWithAuth(`${API_BASE}/videos/${videoId}/watch`, { method: "POST" });
  if (!response.ok) return;
  if (button) {
    button.textContent = "Marcado como visto";
    button.classList.remove("bg-emerald-500", "text-slate-950");
    button.classList.add("bg-slate-800", "text-emerald-200");
  }
  const { progress } = await response.json();
  if (elements.projectProgressBar) elements.projectProgressBar.style.width = `${Math.round(progress * 100)}%`;
  if (elements.projectProgressText) elements.projectProgressText.textContent = `${Math.round(progress * 100)}%`;
}

function initLocationControls() {
  if (!elements.citySelect || !elements.localitySelect) return;
  elements.citySelect.addEventListener("change", () => populateLocalities());
  populateLocalities();
}

function populateLocalities() {
  if (!elements.citySelect || !elements.localitySelect) return;
  const city = elements.citySelect.value;
  const localities = geoIndex[city] ? Object.keys(geoIndex[city]) : [];
  elements.localitySelect.innerHTML = ["<option value=''>Selecciona</option>", ...localities.map((loc) => `<option value="${loc}">${loc}</option>`)].join("");
}

function initProjectMap() {
  if (!elements.projectMap || typeof L === "undefined") return;
  projectMapInstance = L.map(elements.projectMap).setView([19.4326, -99.1332], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
  }).addTo(projectMapInstance);
  projectZoneLayer = L.layerGroup().addTo(projectMapInstance);
}

function updateProjectMap(site, terrain) {
  if (!projectMapInstance || !site) return;
  const { lat, lng } = site.coordinates;
  projectMapInstance.setView([lat, lng], 15);
  projectZoneLayer.clearLayers();
  const radius = Math.max(Math.sqrt((terrain?.area || 90) * 0.8), 30) * 1.5;
  L.circle([lat, lng], {
    radius,
    color: "#22c55e",
    fillColor: "#22c55e",
    fillOpacity: 0.15,
    weight: 2,
  }).addTo(projectZoneLayer);
  L.marker([lat, lng], { title: "Zona de construcción" }).addTo(projectZoneLayer);
  L.polyline(
    [
      [lat + 0.002, lng - 0.002],
      [lat, lng],
      [lat + 0.002, lng + 0.002],
    ],
    { color: "#fbbf24", weight: 3, dashArray: "8,6" }
  ).addTo(projectZoneLayer);
  if (elements.solarOrientation) {
    elements.solarOrientation.textContent = site.solar;
  }
  if (elements.siteRecommendations) {
    elements.siteRecommendations.innerHTML = site.recommendations
      .map((tip) => `<li>${tip}</li>`)
      .join("");
  }
}

function debounce(fn, wait) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(null, args), wait);
  };
}

function capitalize(text) {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "";
}
