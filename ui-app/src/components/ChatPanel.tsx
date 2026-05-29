import { ClearOutlined, SendOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Input, Space, Typography, message } from "antd";
import { useEffect, useRef, useState } from "react";
import { ChatStreamEvent, TenantSession, streamChat } from "../api/client";
import { getChatSessionId, resetChatSessionId } from "../session";
import { AiLogPanel, AiLogStep } from "./AiLogPanel";
import { MarkdownMessage } from "./MarkdownMessage";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatPanelProps {
  session: TenantSession;
  dbStatus?: string;
}

function upsertStep(steps: AiLogStep[], event: ChatStreamEvent): AiLogStep[] {
  if (event.type !== "step") return steps;

  if (event.status === "start") {
    return [
      ...steps,
      {
        id: `${event.tool}-${steps.length}`,
        tool: event.tool,
        message: event.message ?? event.tool,
        status: "running",
      },
    ];
  }

  const next = [...steps];
  for (let i = next.length - 1; i >= 0; i -= 1) {
    if (next[i].tool === event.tool && next[i].status === "running") {
      next[i] = { ...next[i], status: "done" };
      return next;
    }
  }
  return next;
}

function markStepsFailed(steps: AiLogStep[]): AiLogStep[] {
  return steps.map((step) =>
    step.status === "running" ? { ...step, status: "failed" as const } : step
  );
}

export function ChatPanel({ session, dbStatus }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [aiLogSteps, setAiLogSteps] = useState<AiLogStep[]>([]);
  const [aiLogExpanded, setAiLogExpanded] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(getChatSessionId(session.tenantId));
  }, [session.tenantId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading, aiLogSteps, aiLogExpanded, chatError]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setAiLogSteps([]);
    setChatError(null);
    setAiLogExpanded(true);

    let finished = false;
    let errorMessage: string | null = null;

    const reportError = (msg: string) => {
      errorMessage = msg;
      setChatError(msg);
      setAiLogSteps((prev) => markStepsFailed(prev));
      setAiLogExpanded(true);
      message.error(msg);
    };

    try {
      await streamChat(
        session.tenantId,
        session.apiKey,
        text,
        sessionId,
        (event) => {
          if (event.type === "step") {
            setAiLogSteps((prev) => upsertStep(prev, event));
          } else if (event.type === "done") {
            finished = true;
            setAiLogSteps((prev) =>
              prev.map((step) => ({ ...step, status: "done" as const }))
            );
            setMessages((prev) => [...prev, { role: "assistant", content: event.answer }]);
            setAiLogExpanded(false);
          } else if (event.type === "error") {
            finished = true;
            reportError(event.message);
          }
        }
      );

      if (!finished && !errorMessage) {
        reportError("The request ended unexpectedly. Please try again.");
      }
    } catch (err) {
      reportError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = () => {
    resetChatSessionId(session.tenantId);
    setSessionId(getChatSessionId(session.tenantId));
    setMessages([]);
    setAiLogSteps([]);
    setChatError(null);
    setAiLogExpanded(false);
    message.info("New chat session started");
  };

  if (dbStatus !== "active") {
    return (
      <div>
        <div className="page-header">
          <h2>Chat with your data</h2>
          <p>Ask questions in natural language — answers come from your connected database.</p>
        </div>
        <Alert
          type="warning"
          showIcon
          message="Database not ready"
          description="Complete schema indexing first. Status must be active before chatting."
        />
      </div>
    );
  }

  return (
    <div className="chat-panel">
      <div className="page-header chat-panel-header">
        <div>
          <h2>Chat with your data</h2>
          <p>Ask questions in natural language — answers come from your connected database.</p>
        </div>
        <Button icon={<ClearOutlined />} onClick={handleNewSession}>
          New session
        </Button>
      </div>

      <Card
        className="surface-card chat-card"
        styles={{ body: { padding: 0 } }}
      >
        <div className="chat-scroll" ref={scrollRef}>
          {messages.length === 0 && !loading && !chatError && (
            <Typography.Text type="secondary" style={{ textAlign: "center", marginTop: 40 }}>
              Try: &quot;What tables do we have?&quot; or &quot;How many rows in users?&quot;
            </Typography.Text>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`chat-bubble ${msg.role}`}>
              {msg.role === "assistant" ? (
                <MarkdownMessage content={msg.content} />
              ) : (
                msg.content
              )}
            </div>
          ))}
          {chatError && (
            <Alert
              type="error"
              showIcon
              message="Something went wrong"
              description={chatError}
              className="chat-error-alert"
            />
          )}
        </div>

        {(loading || aiLogSteps.length > 0 || chatError) && (
          <AiLogPanel
            steps={aiLogSteps}
            loading={loading}
            expanded={aiLogExpanded}
            error={chatError}
            onExpandedChange={setAiLogExpanded}
          />
        )}

        <div className="chat-input-bar">
          <Space.Compact block size="large">
            <Input.TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your data…"
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={loading}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={loading}
              onClick={handleSend}
            >
              Send
            </Button>
          </Space.Compact>
        </div>
      </Card>
    </div>
  );
}
