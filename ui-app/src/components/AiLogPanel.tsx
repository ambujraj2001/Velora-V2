import { CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, RightOutlined } from "@ant-design/icons";
import { Alert, Collapse, Typography } from "antd";

export interface AiLogStep {
  id: string;
  tool: string;
  message: string;
  status: "running" | "done" | "failed";
}

interface AiLogPanelProps {
  steps: AiLogStep[];
  loading: boolean;
  expanded: boolean;
  error?: string | null;
  onExpandedChange: (expanded: boolean) => void;
}

export function AiLogPanel({
  steps,
  loading,
  expanded,
  error,
  onExpandedChange,
}: AiLogPanelProps) {
  if (steps.length === 0 && !loading && !error) {
    return null;
  }

  const header = error
    ? "Request failed"
    : loading
      ? "Velora is working…"
      : "AI Log";

  return (
    <div className={`ai-log-panel${error ? " ai-log-panel-error" : ""}`}>
      <Collapse
        bordered={false}
        activeKey={expanded ? ["ai-log"] : []}
        onChange={(keys) => onExpandedChange(keys.includes("ai-log"))}
        expandIcon={({ isActive }) => (
          <RightOutlined rotate={isActive ? 90 : 0} style={{ fontSize: 11 }} />
        )}
        items={[
          {
            key: "ai-log",
            label: (
              <span className="ai-log-header">
                {loading && !error && <LoadingOutlined spin style={{ marginRight: 8 }} />}
                {error && <CloseCircleOutlined style={{ marginRight: 8, color: "#ef4444" }} />}
                {header}
                {!loading && !error && steps.length > 0 && (
                  <Typography.Text type="secondary" className="ai-log-count">
                    {steps.length} step{steps.length === 1 ? "" : "s"}
                  </Typography.Text>
                )}
              </span>
            ),
            children: (
              <>
                <ul className="ai-log-list">
                  {steps.map((step) => (
                    <li key={step.id} className={`ai-log-item ${step.status}`}>
                      {step.status === "done" ? (
                        <CheckCircleOutlined className="ai-log-icon done" />
                      ) : step.status === "failed" ? (
                        <CloseCircleOutlined className="ai-log-icon failed" />
                      ) : (
                        <LoadingOutlined spin className="ai-log-icon running" />
                      )}
                      <span>{step.message}</span>
                    </li>
                  ))}
                  {loading && steps.length === 0 && !error && (
                    <li className="ai-log-item running">
                      <LoadingOutlined spin className="ai-log-icon running" />
                      <span>Starting agent…</span>
                    </li>
                  )}
                </ul>
                {error && (
                  <Alert
                    type="error"
                    showIcon
                    message="Error"
                    description={error}
                    className="ai-log-error-alert"
                  />
                )}
              </>
            ),
          },
        ]}
      />
    </div>
  );
}
