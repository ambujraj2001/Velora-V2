import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ConfigProvider } from "antd";
import App from "./App";
import { appTheme } from "./theme";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConfigProvider theme={appTheme}>
      <App />
    </ConfigProvider>
  </StrictMode>
);
