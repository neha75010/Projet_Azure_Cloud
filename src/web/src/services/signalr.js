import * as signalR from "@microsoft/signalr";

const GLOBAL_KEY = "__doc_pipeline_signalr__";

function getState() {
  if (!globalThis[GLOBAL_KEY]) {
    globalThis[GLOBAL_KEY] = {
      connectionPromise: null,
      listeners: new Set(),
      hubHandlerRegistered: false,
    };
  }
  return globalThis[GLOBAL_KEY];
}

function dispatchJobUpdate(data) {
  for (const listener of getState().listeners) {
    listener(data);
  }
}

function ensureHubHandler(connection) {
  const state = getState();
  if (state.hubHandlerRegistered) return;
  connection.on("jobUpdate", dispatchJobUpdate);
  state.hubHandlerRegistered = true;
}

function resolveHubUrl() {
  const base = import.meta.env.VITE_FUNCTIONS_BASE_URL?.replace(/\/$/, "");
  return base ? `${base}/api` : "/api";
}

export function getSignalRConnection() {
  const state = getState();
  if (!state.connectionPromise) {
    const connection = new signalR.HubConnectionBuilder()
      .withUrl(resolveHubUrl())
      .withAutomaticReconnect()
      .build();
    state.connectionPromise = connection
      .start()
      .then(() => {
        ensureHubHandler(connection);
        return connection;
      })
      .catch((err) => {
        state.connectionPromise = null;
        throw err;
      });
  }
  return state.connectionPromise;
}

/** Un seul handler hub ; plusieurs abonnés via Set (résistant au HMR Vite). */
export function subscribeJobUpdate(listener) {
  const state = getState();
  state.listeners.add(listener);

  getSignalRConnection().catch(() => {});

  return () => {
    state.listeners.delete(listener);
  };
}
