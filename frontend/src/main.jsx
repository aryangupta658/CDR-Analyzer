import React from "react";
import ReactDOM from "react-dom/client";

import { BrowserRouter } from "react-router";

import { ToastContainer } from "react-toastify";

import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { CaseProvider } from "./context/CaseContext";

import "leaflet/dist/leaflet.css";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <CaseProvider>
          <App />

          <ToastContainer
            position="top-right"
            autoClose={3500}
            newestOnTop
            closeOnClick
            pauseOnHover
          />
        </CaseProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
