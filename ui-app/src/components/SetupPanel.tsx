import { LoginOutlined, UserAddOutlined } from "@ant-design/icons";
import { Button, Card, Form, Input, Tabs, Typography, message } from "antd";
import { useState } from "react";
import { TenantSession, authToSession, createTenant, login } from "../api/client";

interface SetupPanelProps {
  onComplete: (session: TenantSession) => void;
}

function SignUpForm({ onComplete }: SetupPanelProps) {
  const [loading, setLoading] = useState(false);

  const handleCreate = async (values: {
    name: string;
    email: string;
    password: string;
    confirm: string;
  }) => {
    if (values.password !== values.confirm) {
      message.error("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      const result = await createTenant(
        values.name.trim(),
        values.email.trim(),
        values.password
      );
      onComplete(authToSession(result));
      message.success("Workspace created");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to create workspace");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form layout="vertical" onFinish={handleCreate} requiredMark={false}>
      <Form.Item
        label="Company / workspace name"
        name="name"
        rules={[{ required: true, message: "Enter a workspace name" }]}
      >
        <Input size="large" placeholder="Acme Corp" />
      </Form.Item>
      <Form.Item
        label="Email"
        name="email"
        rules={[
          { required: true, message: "Enter your email" },
          { type: "email", message: "Enter a valid email" },
        ]}
      >
        <Input size="large" placeholder="you@company.com" />
      </Form.Item>
      <Form.Item
        label="Password"
        name="password"
        rules={[
          { required: true, message: "Enter a password" },
          { min: 8, message: "At least 8 characters" },
        ]}
      >
        <Input.Password size="large" placeholder="Min. 8 characters" />
      </Form.Item>
      <Form.Item
        label="Confirm password"
        name="confirm"
        dependencies={["password"]}
        rules={[{ required: true, message: "Confirm your password" }]}
      >
        <Input.Password size="large" placeholder="Repeat password" />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button
          type="primary"
          htmlType="submit"
          size="large"
          block
          loading={loading}
          icon={<UserAddOutlined />}
        >
          Create workspace
        </Button>
      </Form.Item>
    </Form>
  );
}

function SignInForm({ onComplete }: SetupPanelProps) {
  const [loading, setLoading] = useState(false);

  const handleLogin = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const result = await login(values.email.trim(), values.password);
      onComplete(authToSession(result));
      message.success("Signed in");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form layout="vertical" onFinish={handleLogin} requiredMark={false}>
      <Form.Item
        label="Email"
        name="email"
        rules={[
          { required: true, message: "Enter your email" },
          { type: "email", message: "Enter a valid email" },
        ]}
      >
        <Input size="large" placeholder="you@company.com" />
      </Form.Item>
      <Form.Item
        label="Password"
        name="password"
        rules={[{ required: true, message: "Enter your password" }]}
      >
        <Input.Password size="large" placeholder="Your password" />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button
          type="primary"
          htmlType="submit"
          size="large"
          block
          loading={loading}
          icon={<LoginOutlined />}
        >
          Sign in
        </Button>
      </Form.Item>
    </Form>
  );
}

export function SetupPanel({ onComplete }: SetupPanelProps) {
  return (
    <div className="app-bg setup-page">
      <div className="setup-card">
        <div className="setup-hero">
          <div className="brand-mark">
            <div className="brand-icon">V</div>
            <div>
              <p className="brand-title">Velora</p>
              <p className="brand-subtitle">Natural language analytics for your database</p>
            </div>
          </div>
        </div>

        <Card bordered={false} className="surface-card">
          <Tabs
            defaultActiveKey="signin"
            items={[
              {
                key: "signin",
                label: "Sign in",
                children: (
                  <>
                    <Typography.Paragraph type="secondary">
                      Sign in with your email and password to access your workspace.
                    </Typography.Paragraph>
                    <SignInForm onComplete={onComplete} />
                  </>
                ),
              },
              {
                key: "signup",
                label: "Create account",
                children: (
                  <>
                    <Typography.Paragraph type="secondary">
                      Create a new workspace. Use the same email to sign in later.
                    </Typography.Paragraph>
                    <SignUpForm onComplete={onComplete} />
                  </>
                ),
              },
            ]}
          />
        </Card>
      </div>
    </div>
  );
}
