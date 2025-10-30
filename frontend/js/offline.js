const CACHE_KEY = "construyeseguro:lastProject";

export function saveProject(data) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
  } catch (error) {
    console.warn("No se pudo guardar el proyecto offline", error);
  }
}

export function loadProject() {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    return cached ? JSON.parse(cached) : null;
  } catch (error) {
    console.warn("No se pudo leer el proyecto offline", error);
    return null;
  }
}

export function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/service-worker.js").catch((error) => {
      console.warn("SW registration failed", error);
    });
  }
}

registerServiceWorker();
