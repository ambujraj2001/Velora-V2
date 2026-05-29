import { theme } from "antd";

export const appTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: "#ffffff",
    colorInfo: "#ffffff",
    colorSuccess: "#ffffff",
    colorWarning: "#a3a3a3",
    colorError: "#ffffff",
    colorBgBase: "#000000",
    colorBgContainer: "#0a0a0a",
    colorBgElevated: "#111111",
    colorBorder: "#262626",
    colorBorderSecondary: "#1a1a1a",
    colorText: "#ffffff",
    colorTextSecondary: "#a3a3a3",
    colorTextTertiary: "#737373",
    borderRadius: 8,
    fontFamily:
      "'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
    colorPrimaryHover: "#e5e5e5",
    colorPrimaryActive: "#d4d4d4",
    colorTextLightSolid: "#000000",
  },
  components: {
    Layout: {
      bodyBg: "#000000",
      headerBg: "#0a0a0a",
      siderBg: "#0a0a0a",
    },
    Menu: {
      darkItemBg: "#0a0a0a",
      darkSubMenuItemBg: "#000000",
      darkItemColor: "#e5e5e5",
      darkItemSelectedBg: "#262626",
      darkItemSelectedColor: "#ffffff",
      darkItemHoverBg: "#1a1a1a",
      darkItemHoverColor: "#ffffff",
    },
    Card: {
      colorBgContainer: "#0a0a0a",
      colorBorderSecondary: "#262626",
    },
    Input: {
      colorBgContainer: "#000000",
      activeBorderColor: "#ffffff",
      hoverBorderColor: "#525252",
    },
    Select: {
      colorBgContainer: "#000000",
    },
    Button: {
      primaryShadow: "none",
      defaultBg: "#0a0a0a",
      defaultBorderColor: "#404040",
    },
    FloatButton: {
      colorBgElevated: "#111111",
    },
    Tag: {
      defaultBg: "#1a1a1a",
    },
    Descriptions: {
      colorSplit: "#262626",
    },
    Alert: {
      colorInfoBg: "#0a0a0a",
      colorInfoBorder: "#404040",
    },
  },
};
