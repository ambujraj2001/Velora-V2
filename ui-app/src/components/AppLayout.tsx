import {
  ApiOutlined,
  CopyOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  MessageOutlined,
  RocketOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Typography, message } from "antd";
import { ReactNode } from "react";
import { TenantSession } from "../api/client";

const { Header, Sider, Content } = Layout;

export type AppStep = "connect" | "onboard" | "chat";

interface AppLayoutProps {
  session: TenantSession;
  step: AppStep;
  onStepChange: (step: AppStep) => void;
  onLogout: () => void;
  connectionStatus?: string;
  children: ReactNode;
}

const menuItems = [
  { key: "chat", icon: <MessageOutlined />, label: "Chat" },
  { key: "onboard", icon: <RocketOutlined />, label: "Index Schema" },
  { key: "connect", icon: <DatabaseOutlined />, label: "Connect Database" },
];

export function AppLayout({
  session,
  step,
  onStepChange,
  onLogout,
  connectionStatus,
  children,
}: AppLayoutProps) {
  return (
    <Layout className="app-shell app-bg">
      <Sider width={260} breakpoint="lg" collapsedWidth={0} className="app-sider">
        <div className="sidebar-inner">
          <div className="sidebar-brand">
            <div className="brand-mark">
              <div className="brand-icon">V</div>
              <div>
                <p className="brand-title">Velora</p>
                <p className="brand-subtitle">Chat over your data</p>
              </div>
            </div>
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[step]}
            items={menuItems}
            onClick={({ key }) => onStepChange(key as AppStep)}
            className="app-menu"
            style={{ borderInlineEnd: 0 }}
          />
          <div className="sidebar-footer">
          <Typography.Text className="sidebar-footer-label">Workspace</Typography.Text>
          <div style={{ marginTop: 4 }}>
            <Typography.Text strong style={{ color: "#ffffff" }}>
              {session.tenantName}
            </Typography.Text>
          </div>
          {session.email && (
            <Typography.Text className="sidebar-footer-meta">{session.email}</Typography.Text>
          )}
          {connectionStatus && (
            <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
              <span
                className={`status-dot ${
                  connectionStatus === "active"
                    ? "active"
                    : connectionStatus === "error"
                      ? "error"
                      : "pending"
                }`}
              />
              <Typography.Text className="sidebar-footer-meta">
                DB {connectionStatus}
              </Typography.Text>
            </div>
          )}
          </div>
        </div>
      </Sider>
      <Layout>
        <Header
          className="app-header"
          style={{
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography.Text style={{ color: "#a3a3a3" }}>
            <ApiOutlined style={{ marginRight: 8 }} />
            API connected
          </Typography.Text>
          <div className="app-header-actions">
            <Button
              icon={<CopyOutlined />}
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(session.tenantId);
                  message.success("Workspace ID copied");
                } catch {
                  message.error("Could not copy ID");
                }
              }}
            >
              Copy ID
            </Button>
            <Button icon={<LogoutOutlined />} onClick={onLogout}>
              Sign out
            </Button>
          </div>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
