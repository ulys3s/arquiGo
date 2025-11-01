const API_BASE = "/api";

const state = {
  token: localStorage.getItem("cs_token") || "",
  user: JSON.parse(localStorage.getItem("cs_user") || "null"),
  currentProjectId: null,
  blueprintRooms: [],
  blueprintZoom: 1,
  providers: [],
  selectedProvider: null,
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
  authWarning: document.querySelector("#authWarning"),
  projectResults: document.querySelector("#projectResults"),
  viabilityScore: document.querySelector("#viabilityScore"),
  blueprint2D: document.querySelector("#blueprint2D"),
  blueprintCanvas: document.querySelector("#blueprintCanvas"),
  blueprintLegend: document.querySelector("#blueprintLegend"),
  blueprint3D: document.querySelector("#blueprint3D"),
  blueprintScale: document.querySelector("#blueprintScale"),
  blueprintOrientation: document.querySelector("#blueprintOrientation"),
  blueprintZoomSlider: document.querySelector("#blueprintZoom"),
  blueprintZoomValue: document.querySelector("#blueprintZoomValue"),
  blueprintDownloadPng: document.querySelector("#downloadPlanPng"),
  blueprintDownloadPdf: document.querySelector("#downloadPlanPdf"),
  roomGuide: document.querySelector("#roomGuide"),
  manualSteps: document.querySelector("#manualSteps"),
  materialList: document.querySelector("#materialList"),
  estimatedCost: document.querySelector("#estimatedCost"),
  alertList: document.querySelector("#alertList"),
  planOptions: document.querySelector("#planOptions"),
  manualLevels: document.querySelector("#manualLevels"),
  refreshManual: document.querySelector("#refreshManual"),
  downloadManual: document.querySelector("#downloadManual"),
  manualRecommended: document.querySelector("#manualRecommended"),
  projectList: document.querySelector("#projectList"),
  projectProgressBar: document.querySelector("#projectVideoProgress"),
  projectProgressText: document.querySelector("#projectProgressText"),
  dashboardRecommendations: document.querySelector("#dashboardRecommendations"),
  videoContainer: document.querySelector("#videoList"),
  videoFilterLevel: document.querySelector("#videoLevel"),
  videoFilterSearch: document.querySelector("#videoSearch"),
  learningVideos: document.querySelector("#learningVideos"),
  citySelect: document.querySelector("select[name='ciudad']"),
  localitySelect: document.querySelector("select[name='localidad']"),
  preferencesChips: document.querySelectorAll("input[name='preferencias']"),
  projectMap: document.querySelector("#projectMap"),
  solarOrientation: document.querySelector("#solarOrientation"),
  siteRecommendations: document.querySelector("#siteRecommendations"),
  providerList: document.querySelector("#providerList"),
  providerCity: document.querySelector("#providerCity"),
  providerType: document.querySelector("#providerType"),
  providerPriceMin: document.querySelector("#providerPriceMin"),
  providerPriceMax: document.querySelector("#providerPriceMax"),
  providerFilters: document.querySelector("#providerFilters"),
  hireModal: document.querySelector("#hireModal"),
  closeHireModal: document.querySelector("#closeHireModal"),
  hireForm: document.querySelector("#hireForm"),
  hireProviderName: document.querySelector("#hireProviderName"),
  hireProjectSelect: document.querySelector("#hireProject"),
  hireMessage: document.querySelector("#hireMessage"),
  hireRequestList: document.querySelector("#hireRequestList"),
};

let projectMapInstance;
let projectZoneLayer;

document.addEventListener("DOMContentLoaded", () => {
  attachAuthHandlers();
  attachProjectHandlers();
  attachVideoHandlers();
  attachBlueprintToolbar();
  attachMarketplaceHandlers();
  hydrateAuthState();
  initLocationControls();
  initProjectMap();
  loadProviders().catch(console.error);
  setBlueprintZoom(state.blueprintZoom);
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
      state.blueprintZoom = 1;
      renderProject(data);
      await Promise.all([loadProjects(), loadDashboard()]);
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

function attachBlueprintToolbar() {
  elements.blueprintZoomSlider?.addEventListener("input", (event) => {
    const value = Number(event.target.value);
    setBlueprintZoom(value);
  });
  elements.blueprintDownloadPng?.addEventListener("click", () => downloadBlueprint("png"));
  elements.blueprintDownloadPdf?.addEventListener("click", () => downloadBlueprint("pdf"));
}

function attachMarketplaceHandlers() {
  const filterElements = [
    elements.providerCity,
    elements.providerType,
    elements.providerPriceMin,
    elements.providerPriceMax,
  ];
  filterElements.forEach((input) =>
    input?.addEventListener("change", () => loadProviders().catch(console.error))
  );
  elements.providerFilters?.addEventListener("submit", (event) => {
    event.preventDefault();
    loadProviders().catch(console.error);
  });
  elements.closeHireModal?.addEventListener("click", () => closeHireModal());
  elements.hireModal?.addEventListener("click", (event) => {
    if (event.target === elements.hireModal) closeHireModal();
  });
  elements.hireForm?.addEventListener("submit", handleHireSubmit);
}

async function authenticateUser(endpoint, formData) {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(formData)),
      credentials: "include",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "No se pudo iniciar sesión");
    setAuthState(data.token, data.user);
    toggleAuthModal(false);
    await Promise.all([loadProjects(), loadManualLevels(), loadVideos(), loadDashboard()]);
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
  Promise.all([loadProjects(), loadManualLevels(), loadVideos(), loadDashboard()]).catch((error) => {
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
  displayAuthWarning(false);
}

function clearAuthState() {
  state.token = "";
  state.user = null;
  state.currentProjectId = null;
  localStorage.removeItem("cs_token");
  localStorage.removeItem("cs_user");
  updateUserBadge();
  displayAuthWarning(false);
  elements.projectResults?.classList.add("hidden");
  elements.projectList && (elements.projectList.innerHTML = "");
  if (elements.projectProgressBar) elements.projectProgressBar.style.width = "0%";
  if (elements.projectProgressText) elements.projectProgressText.textContent = "0%";
  if (elements.manualRecommended)
    elements.manualRecommended.innerHTML =
      '<p class="text-sm text-slate-400">Inicia sesión para ver videos personalizados.</p>';
  if (elements.dashboardRecommendations)
    elements.dashboardRecommendations.innerHTML =
      '<p class="text-sm text-slate-400">Genera tu primer proyecto para recibir recomendaciones.</p>';
  if (elements.hireRequestList)
    elements.hireRequestList.innerHTML =
      '<p class="text-sm text-slate-400">Inicia sesión para llevar control de tus solicitudes.</p>';
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

function displayAuthWarning(visible, message = "Autenticación requerida. Inicia sesión para continuar.") {
  if (!elements.authWarning) return;
  elements.authWarning.textContent = message;
  elements.authWarning.classList.toggle("hidden", !visible);
}

function toggleAuthModal(show) {
  if (!elements.authModal) return alert("Inicia sesión para continuar");
  elements.authModal.classList.toggle("hidden", !show);
}

function ensureAuth(showDialog = true) {
  if (state.token) return true;
  if (showDialog) {
    displayAuthWarning(true);
    toggleAuthModal(true);
  }
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
  config.credentials = "include";
  config.headers = {
    ...(options.headers || {}),
  };
  if (state.token) {
    config.headers.Authorization = `Bearer ${state.token}`;
  }
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
  const data = await response.json();
  if (!response.ok || !data.success) throw new Error(data.error || "No se pudieron cargar los proyectos");
  const { projects } = data;
  renderProjectList(projects);
  updateHireProjectOptions(projects);
  if (projects.length && !state.currentProjectId) {
    state.currentProjectId = projects[0].id;
    renderProject(projects[0].plan_data);
  }
}

async function loadDashboard() {
  if (!ensureAuth(false)) return;
  const response = await fetchWithAuth(`${API_BASE}/dashboard`);
  const data = await response.json();
  if (!data.success) return;
  renderDashboard(data);
}

function renderDashboard(data) {
  if (elements.projectProgressBar) {
    const progress = Math.round((data.progress?.percentage || 0) * 100);
    elements.projectProgressBar.style.width = `${progress}%`;
  }
  if (elements.projectProgressText) {
    const progress = Math.round((data.progress?.percentage || 0) * 100);
    elements.projectProgressText.textContent = `${progress}%`;
  }
  if (elements.dashboardRecommendations) {
    renderPlaylist(elements.dashboardRecommendations, data.recommended_videos, {
      compact: true,
      emptyMessage: "Genera tu primer proyecto para recibir recomendaciones.",
    });
  }
  if (elements.hireRequestList) {
    const requests = data.hire_requests || [];
    elements.hireRequestList.innerHTML = requests.length
      ? requests
          .map(
            (request) => `
              <li class="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 text-sm">
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <span class="font-semibold text-emerald-200">${request.provider_name}</span>
                  <span class="text-xs uppercase tracking-wide text-slate-400">${request.status}</span>
                </div>
                <p class="mt-1 text-xs text-slate-400">Proyecto #${request.project_id} · ${new Date(request.created_at).toLocaleDateString()}</p>
                <p class="mt-2 text-xs text-slate-500">Contacto: ${request.contact || "En revisión"}</p>
              </li>
            `
          )
          .join("")
      : '<p class="text-sm text-slate-400">Todavía no has enviado solicitudes. Usa el botón "Contratar" en el marketplace.</p>';
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
    setBlueprintZoom(state.blueprintZoom);
    attachRoomInteractions();
  }
  if (elements.blueprintLegend) renderBlueprintLegend();
  if (elements.blueprintScale) {
    elements.blueprintScale.textContent = data.plans.selected.blueprint_2d.scale || "Escala gráfica 1:50";
  }
  if (elements.blueprintOrientation) {
    elements.blueprintOrientation.textContent = data.plans.selected.blueprint_2d.orientation || "NORTE";
  }
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
            ${step.video ? `<a class="mt-2 inline-flex items-center text-xs text-emerald-300" href="${step.video.url || `https://www.youtube.com/watch?v=${step.video.youtube_id}` }" target="_blank" rel="noopener">Ver guía en YouTube</a>` : ""}
          </li>
        `
      )
      .join("");
  }

  if (elements.manualRecommended) {
    renderPlaylist(elements.manualRecommended, data.manual?.recommended_videos, {
      emptyMessage: "Genera tu proyecto para recibir videos por etapa.",
    });
  }

  if (elements.dashboardRecommendations) {
    renderPlaylist(elements.dashboardRecommendations, data.manual?.recommended_videos, {
      compact: true,
      emptyMessage: "Genera tu primer proyecto para recibir recomendaciones.",
    });
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
          <iframe class="aspect-video w-full" src="${video.embed_url || `https://www.youtube.com/embed/${video.youtube_id}` }" title="${video.title}" allowfullscreen loading="lazy"></iframe>
        </div>
        <button class="mt-3 rounded-full bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950" data-watch-video="${video.id}">Marcar como visto</button>
      ` : ""}
    </div>
  `;
  attachWatchButtons(elements.roomGuide);
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
  const data = await response.json();
  if (!response.ok || !data.success) return;
  const { steps } = data;
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
                  <a class="block rounded-xl border border-slate-800 bg-slate-900/40 p-3 text-sm text-slate-200 hover:border-emerald-400" href="${video.url || `https://www.youtube.com/watch?v=${video.youtube_id}` }" target="_blank" rel="noopener">
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
  const query = params.toString();
  const response = await fetchWithAuth(`${API_BASE}/videos${query ? `?${query}` : ""}`);
  const data = await response.json();
  if (!response.ok || !data.success) return;
  const { videos } = data;
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
      (group) => `
        <section class="space-y-4">
          <header class="flex flex-wrap items-center justify-between gap-3">
            <h3 class="text-xl font-semibold text-emerald-300">${group.label}</h3>
            <span class="text-xs uppercase tracking-wider text-slate-400">${group.videos.length} videos</span>
          </header>
          <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            ${group.videos
              .map(
                (video) => `
                  <article class="rounded-3xl border border-slate-800 bg-slate-900/60 p-4">
                    <header class="flex items-center justify-between gap-3">
                      <h4 class="text-lg font-semibold text-slate-100">${video.title}</h4>
                      <span class="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">${group.label}</span>
                    </header>
                    <div class="mt-3 overflow-hidden rounded-xl">
                      <iframe class="aspect-video w-full" src="${video.embed_url || `https://www.youtube.com/embed/${video.youtube_id}` }" allowfullscreen loading="lazy" title="${video.title}"></iframe>
                    </div>
                    <p class="mt-3 text-sm text-slate-300">${video.description || ""}</p>
                    <p class="mt-2 text-xs text-slate-400">Etapa: ${video.stage || "General"}</p>
                    <p class="text-xs text-slate-500">Manual: ${(video.manual_step || "general").replace(/_/g, " ")}</p>
                    <button class="mt-3 w-full rounded-full ${video.watched ? "bg-slate-800 text-emerald-200" : "bg-emerald-500 text-slate-950"} px-4 py-2 text-sm font-semibold" data-watch-video="${video.id}">
                      ${video.watched ? "Marcado como visto" : "Marcar como visto"}
                    </button>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>
      `
    )
    .join("");
  attachWatchButtons(elements.videoContainer);
}

function renderPlaylist(container, playlist, { compact = false, emptyMessage = "" } = {}) {
  if (!container) return;
  if (!playlist || !playlist.length) {
    container.innerHTML = emptyMessage
      ? `<p class="text-sm text-slate-400">${emptyMessage}</p>`
      : "";
    return;
  }
  container.innerHTML = playlist
    .map(
      (group) => `
        <article class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h5 class="text-sm font-semibold uppercase tracking-wide text-emerald-200">${group.stage}</h5>
          <div class="mt-3 space-y-3">
            ${group.videos
              .map((video) =>
                compact
                  ? `
                      <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
                        <p class="text-sm font-semibold text-slate-100">${video.title}</p>
                        <p class="text-xs text-slate-400">${video.description}</p>
                        <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                          <a class="text-emerald-300" href="${video.url || `https://www.youtube.com/watch?v=${video.youtube_id}` }" target="_blank" rel="noopener">Ver en YouTube</a>
                          <button class="rounded-full border border-emerald-400/40 px-3 py-1 text-emerald-200" data-watch-video="${video.id}">Marcar como visto</button>
                        </div>
                      </div>
                    `
                  : `
                      <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-3">
                        <p class="text-sm font-semibold text-slate-100">${video.title}</p>
                        <p class="text-xs text-slate-400">${video.description}</p>
                        <div class="mt-3 overflow-hidden rounded-xl">
                          <iframe class="aspect-video w-full" src="${video.embed_url || `https://www.youtube.com/embed/${video.youtube_id}` }" title="${video.title}" allowfullscreen loading="lazy"></iframe>
                        </div>
                        <button class="mt-3 rounded-full bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950" data-watch-video="${video.id}">Marcar como visto</button>
                      </div>
                    `
              )
              .join("")}
          </div>
        </article>
      `
    )
    .join("");
  attachWatchButtons(container);
}

function attachWatchButtons(root) {
  if (!root) return;
  root.querySelectorAll("[data-watch-video]").forEach((button) => {
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
  loadDashboard().catch(console.error);
}

function setBlueprintZoom(value) {
  state.blueprintZoom = Number(value) || 1;
  if (elements.blueprintZoomSlider && Number(elements.blueprintZoomSlider.value) !== state.blueprintZoom) {
    elements.blueprintZoomSlider.value = state.blueprintZoom;
  }
  if (elements.blueprintZoomValue) {
    elements.blueprintZoomValue.textContent = `${Math.round(state.blueprintZoom * 100)}%`;
  }
  const svg = elements.blueprint2D?.querySelector("svg");
  if (svg) {
    svg.style.transformOrigin = "0 0";
    svg.style.transform = `scale(${state.blueprintZoom})`;
  }
}

async function downloadBlueprint(format) {
  const svg = elements.blueprint2D?.querySelector("svg");
  if (!svg) {
    alert("Genera un proyecto para descargar el plano.");
    return;
  }
  try {
    const { dataUrl, width, height } = await convertSvgToPng(svg);
    if (format === "png") {
      downloadDataUrl(dataUrl, `plano_2d_${Date.now()}.png`);
      return;
    }
    openPdfPreview(dataUrl, width, height);
  } catch (error) {
    console.error(error);
    alert("No pudimos exportar el plano. Intenta nuevamente.");
  }
}

function convertSvgToPng(svg) {
  return new Promise((resolve, reject) => {
    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svg);
    const viewBox = (svg.getAttribute("viewBox") || `0 0 ${svg.clientWidth || 1024} ${svg.clientHeight || 768}`).split(" ");
    const width = Number(viewBox[2]);
    const height = Number(viewBox[3]);
    const canvas = document.createElement("canvas");
    const scale = window.devicePixelRatio > 1 ? 2 : 1.5;
    canvas.width = width * scale;
    canvas.height = height * scale;
    const context = canvas.getContext("2d");
    const image = new Image();
    image.onload = () => {
      context.fillStyle = "#f8fafc";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      resolve({ dataUrl: canvas.toDataURL("image/png"), width, height });
    };
    image.onerror = (error) => reject(error);
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(source)}`;
  });
}

function downloadDataUrl(url, filename) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}

function openPdfPreview(imageDataUrl, width, height) {
  const popup = window.open("", "_blank", "noopener");
  if (!popup) {
    alert("Habilita las ventanas emergentes para exportar a PDF.");
    return;
  }
  popup.document.write(`
    <html>
      <head>
        <title>Plano 2D - Exportación PDF</title>
        <style>
          body { margin: 0; padding: 24px; background: #f8fafc; font-family: 'Inter', sans-serif; color: #1f2937; }
          img { width: 100%; max-width: ${width}px; height: auto; box-shadow: 0 20px 40px rgba(15,23,42,0.15); border-radius: 16px; }
          footer { margin-top: 16px; font-size: 14px; }
        </style>
      </head>
      <body>
        <img src="${imageDataUrl}" alt="Plano 2D" />
        <footer>Utiliza el comando <strong>Imprimir &gt; Guardar como PDF</strong> de tu navegador para descargar este plano.</footer>
      </body>
    </html>
  `);
  popup.document.close();
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

async function loadProviders() {
  const params = new URLSearchParams();
  if (elements.providerCity?.value) params.set("city", elements.providerCity.value);
  if (elements.providerType?.value) params.set("type", elements.providerType.value);
  if (elements.providerPriceMin?.value) params.set("min_price", elements.providerPriceMin.value);
  if (elements.providerPriceMax?.value) params.set("max_price", elements.providerPriceMax.value);
  const query = params.toString();
  const response = await fetch(`${API_BASE}/marketplace/providers${query ? `?${query}` : ""}`);
  const data = await response.json();
  if (!data.success) return;
  state.providers = data.providers || [];
  renderProviders(state.providers);
}

function renderProviders(providers) {
  if (!elements.providerList) return;
  if (!providers.length) {
    elements.providerList.innerHTML = `<p class="text-sm text-slate-400">No encontramos proveedores con esos filtros.</p>`;
    return;
  }
  elements.providerList.innerHTML = providers
    .map(
      (provider) => `
        <article class="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
          <header class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 class="text-lg font-semibold text-emerald-300">${provider.name}</h3>
              <p class="text-xs uppercase tracking-wider text-slate-400">${capitalize(provider.type || "")} · ${provider.city}${provider.locality ? `, ${provider.locality}` : ""}</p>
            </div>
            <span class="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">⭐ ${Number(provider.rating || 0).toFixed(1)}</span>
          </header>
          <p class="mt-3 text-sm text-slate-300">${provider.specialty || ""}</p>
          <p class="mt-2 text-xs text-slate-400">${provider.description || ""}</p>
          <div class="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400">
            <span>Honorarios: ${
              provider.price_min
                ? `$${Number(provider.price_min).toLocaleString()}${provider.price_max ? ` - $${Number(provider.price_max).toLocaleString()}` : ""}`
                : "A convenir"
            }</span>
            ${provider.experience_years ? `<span>${provider.experience_years} años de experiencia</span>` : ""}
            ${provider.contact ? `<span>Contacto: ${provider.contact}</span>` : ""}
          </div>
          <div class="mt-4 flex flex-wrap items-center gap-3">
            ${provider.portfolio_url ? `<a class="action-secondary" href="${provider.portfolio_url}" target="_blank" rel="noopener">Ver portafolio</a>` : ""}
            <button class="action-button" data-hire="${provider.id}">Contratar / Solicitar cotización</button>
          </div>
        </article>
      `
    )
    .join("");

  elements.providerList
    .querySelectorAll("[data-hire]")
    .forEach((button) =>
      button.addEventListener("click", () => {
        const providerId = Number(button.dataset.hire);
        openHireModal(providerId);
      })
    );
}

function openHireModal(providerId) {
  if (!ensureAuth()) return;
  const provider = state.providers.find((item) => item.id === providerId);
  if (!provider || !elements.hireModal) return;
  state.selectedProvider = providerId;
  if (elements.hireProviderName) {
    elements.hireProviderName.textContent = `${provider.name} · ${provider.city}`;
  }
  elements.hireModal.classList.remove("hidden");
  elements.hireModal.classList.add("flex");
  elements.hireMessage && (elements.hireMessage.value = "Hola, me gustaría recibir una cotización para mi proyecto generado en ConstruyeSeguro.");
}

function closeHireModal() {
  if (!elements.hireModal) return;
  elements.hireModal.classList.add("hidden");
  elements.hireModal.classList.remove("flex");
  elements.hireForm?.reset();
  state.selectedProvider = null;
}

async function handleHireSubmit(event) {
  event.preventDefault();
  if (!ensureAuth()) return;
  if (!state.selectedProvider) {
    alert("Selecciona un proveedor antes de enviar la solicitud.");
    return;
  }
  const projectId = Number(elements.hireProjectSelect?.value);
  if (!projectId) {
    alert("Selecciona uno de tus proyectos.");
    return;
  }
  const payload = {
    provider_id: state.selectedProvider,
    project_id: projectId,
    message: elements.hireMessage?.value || "",
  };
  const response = await fetchWithAuth(`${API_BASE}/marketplace/hire`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.success) {
    alert(data.error || "No pudimos enviar la solicitud");
    return;
  }
  closeHireModal();
  loadDashboard().catch(console.error);
  alert(data.message || "Solicitud enviada correctamente");
}

function updateHireProjectOptions(projects) {
  if (!elements.hireProjectSelect) return;
  if (!projects.length) {
    elements.hireProjectSelect.innerHTML = "<option value=''>Genera un proyecto para contratar</option>";
    return;
  }
  elements.hireProjectSelect.innerHTML = projects
    .map((project) => `<option value="${project.id}">${project.title}</option>`)
    .join("");
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
