import { useCallback, useEffect, useState } from "react";
import { ConnectionInfo, TenantSession, getConnection } from "./api/client";
import { AppLayout, AppStep } from "./components/AppLayout";
import { ChatPanel } from "./components/ChatPanel";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { OnboardPanel } from "./components/OnboardPanel";
import { SetupPanel } from "./components/SetupPanel";
import { clearSession, loadSession, saveSession } from "./session";

function App() {
  const [session, setSession] = useState<TenantSession | null>(() => loadSession());
  const [step, setStep] = useState<AppStep>("connect");
  const [connection, setConnection] = useState<ConnectionInfo | null>(null);
  const [dbStatus, setDbStatus] = useState<string | undefined>();

  const refreshConnection = useCallback(async () => {
    if (!session) return;
    try {
      const info = await getConnection(session.tenantId, session.apiKey);
      setConnection(info);
      setDbStatus(info.status);
    } catch {
      setConnection(null);
      setDbStatus(undefined);
    }
  }, [session]);

  useEffect(() => {
    refreshConnection();
  }, [refreshConnection]);

  useEffect(() => {
    if (connection) {
      setDbStatus(connection.status);
    }
  }, [connection]);

  const handleSetup = (newSession: TenantSession) => {
    saveSession(newSession);
    setSession(newSession);
  };

  const handleLogout = () => {
    clearSession();
    setSession(null);
    setConnection(null);
    setDbStatus(undefined);
    setStep("connect");
  };

  if (!session) {
    return <SetupPanel onComplete={handleSetup} />;
  }

  return (
    <AppLayout
      session={session}
      step={step}
      onStepChange={setStep}
      onLogout={handleLogout}
      connectionStatus={dbStatus}
    >
      {step === "connect" && (
        <ConnectionPanel
          session={session}
          onConnectionChange={(info) => {
            setConnection(info);
            setDbStatus(info?.status);
          }}
        />
      )}
      {step === "onboard" && (
        <OnboardPanel
          session={session}
          hasConnection={!!connection}
          onStatusChange={setDbStatus}
          onRefreshConnection={refreshConnection}
        />
      )}
      {step === "chat" && <ChatPanel session={session} dbStatus={dbStatus} />}
    </AppLayout>
  );
}

export default App;
