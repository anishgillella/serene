import './index.css';
import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

// Auth0 is disabled for now - will be enabled later
// TODO: Re-enable Auth0Provider and AuthProvider when ready

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
