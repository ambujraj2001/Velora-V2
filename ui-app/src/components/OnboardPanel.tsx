import { ReloadOutlined, RocketOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Spin, Tag, Typography, message } from "antd";
import { useEffect, useRef, useState } from "react";
import {
  OnboardStatus,
  TenantSession,
  getOnboardStatus,
  startOnboarding,
} from "../api/client";

interface OnboardPanelProps {
  session: TenantSession;
  hasConnection: boolean;
  onStatusChange: (status: string) => void;
  onRefreshConnection?: () => void;
}

const statusColor: Record<string, string> = {
  pending: "warning",
  active: "success",
  error: "error",
};

export function OnboardPanel({
  session,
  hasConnection,
  onStatusChange,
  onRefreshConnection,
}: OnboardPanelProps) {
  const [status, setStatus] = useState<OnboardStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<number | null>(null);

  const fetchStatus = async () => {
    try {
      const result = await getOnboardStatus(session.tenantId, session.apiKey);
      setStatus(result);
      onStatusChange(result.status);
      return result;
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load status");
      return null;
    }
  };

  useEffect(() => {
    if (hasConnection) {
      fetchStatus();
    }
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [hasConnection, session.tenantId]);

  const startPolling = () => {
    setPolling(true);
    pollRef.current = window.setInterval(async () => {
      const result = await fetchStatus();
      if (result && (result.status === "active" || result.status === "error")) {
        if (pollRef.current) window.clearInterval(pollRef.current);
        setPolling(false);
        if (result.status === "active") {
          message.success("Schema indexed — ready to chat");
          onRefreshConnection?.();
        }
      }
    }, 3000);
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      await startOnboarding(session.tenantId, session.apiKey);
      message.info("Indexing started in background");
      await fetchStatus();
      startPolling();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to start indexing");
    } finally {
      setLoading(false);
    }
  };

  if (!hasConnection) {
    return (
      <div>
        <div className="page-header">
          <h2>Index schema</h2>
          <p>Connect a database first, then index its schema for AI retrieval.</p>
        </div>
        <Alert type="warning" showIcon message="Connect a database to continue" />
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h2>Index schema</h2>
        <p>Scan tables, generate descriptions, and build the vector knowledge base.</p>
      </div>

      <Card className="surface-card">
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          {status ? (
            <div>
              <Typography.Text type="secondary">Current status</Typography.Text>
              <div style={{ marginTop: 8 }}>
                <Tag color={statusColor[status.status] ?? "default"}>
                  {status.status.toUpperCase()}
                </Tag>
                <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
                  {status.message}
                </Typography.Paragraph>
                {status.onboarded_at && (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    Indexed at {new Date(status.onboarded_at).toLocaleString()}
                  </Typography.Text>
                )}
              </div>
            </div>
          ) : (
            <Spin />
          )}

          <Space wrap>
            <Button
              type="primary"
              icon={<RocketOutlined />}
              loading={loading}
              onClick={handleStart}
              disabled={polling}
            >
              {status?.status === "active" ? "Re-index schema" : "Start indexing"}
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchStatus}>
              Refresh status
            </Button>
          </Space>

          {polling && (
            <Alert
              type="info"
              showIcon
              message="Indexing in progress…"
              description="This may take a few minutes depending on schema size and NVIDIA API latency."
            />
          )}
        </Space>
      </Card>
    </div>
  );
}
