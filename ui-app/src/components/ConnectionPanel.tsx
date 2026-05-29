import { LinkOutlined, DisconnectOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  Popconfirm,
  Select,
  message,
} from "antd";
import { useEffect, useState } from "react";
import {
  ConnectionInfo,
  TenantSession,
  connectDatabase,
  disconnectDatabase,
  getConnection,
} from "../api/client";

interface ConnectionPanelProps {
  session: TenantSession;
  onConnectionChange: (info: ConnectionInfo | null) => void;
}

export function ConnectionPanel({ session, onConnectionChange }: ConnectionPanelProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [connection, setConnection] = useState<ConnectionInfo | null>(null);

  const loadConnection = async () => {
    try {
      const info = await getConnection(session.tenantId, session.apiKey);
      setConnection(info);
      onConnectionChange(info);
    } catch {
      setConnection(null);
      onConnectionChange(null);
    }
  };

  useEffect(() => {
    loadConnection();
  }, [session.tenantId]);

  const handleConnect = async (values: {
    db_name: string;
    db_type: "postgres" | "mongodb";
    conn_string: string;
    description: string;
  }) => {
    setLoading(true);
    try {
      await connectDatabase(session.tenantId, session.apiKey, values);
      message.success("Database connected");
      form.resetFields();
      await loadConnection();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setDisconnecting(true);
    try {
      await disconnectDatabase(session.tenantId, session.apiKey);
      message.success("Database disconnected");
      setConnection(null);
      onConnectionChange(null);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Disconnect failed");
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Connect database</h2>
        <p>Link one PostgreSQL or MongoDB database to this workspace.</p>
      </div>

      {connection ? (
        <Card
          className="surface-card"
          title="Connected database"
          extra={
            <Popconfirm
              title="Disconnect this database?"
              description="Schema index and connection will be removed."
              onConfirm={handleDisconnect}
              okText="Disconnect"
              cancelText="Cancel"
            >
              <Button danger icon={<DisconnectOutlined />} loading={disconnecting}>
                Disconnect
              </Button>
            </Popconfirm>
          }
        >
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="Name">{connection.db_name}</Descriptions.Item>
            <Descriptions.Item label="Type">{connection.db_type}</Descriptions.Item>
            <Descriptions.Item label="Description">
              {connection.description || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Status">{connection.status}</Descriptions.Item>
          </Descriptions>
        </Card>
      ) : (
        <Card title="New connection" className="surface-card">
          <Alert
            type="info"
            showIcon
            icon={<LinkOutlined />}
            message="One database per workspace"
            description="PostgreSQL: use a standard connection string. MongoDB: include the database name in the URI."
            style={{ marginBottom: 24 }}
          />
          <Form
            form={form}
            layout="vertical"
            onFinish={handleConnect}
            requiredMark={false}
            initialValues={{ db_type: "postgres" }}
          >
            <Form.Item
              label="Display name"
              name="db_name"
              rules={[{ required: true, message: "Required" }]}
            >
              <Input placeholder="Production DB" />
            </Form.Item>
            <Form.Item
              label="Database type"
              name="db_type"
              rules={[{ required: true }]}
            >
              <Select
                options={[
                  { value: "postgres", label: "PostgreSQL" },
                  { value: "mongodb", label: "MongoDB" },
                ]}
              />
            </Form.Item>
            <Form.Item
              label="Connection string"
              name="conn_string"
              rules={[{ required: true, message: "Required" }]}
            >
              <Input.Password
                placeholder="postgresql://user:pass@host:5432/mydb"
                visibilityToggle
              />
            </Form.Item>
            <Form.Item label="Description" name="description">
              <Input.TextArea rows={2} placeholder="Our main ecommerce database" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" loading={loading}>
                Test & connect
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}
    </div>
  );
}
