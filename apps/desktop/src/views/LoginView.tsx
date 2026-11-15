import { useEffect, useState } from "react";
import { api } from "../api";

export function LoginView({ onLogin }: { onLogin: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") {
        const tokens = await api.login(email, password);
        api.setToken(tokens.access_token);
        localStorage.setItem("nexus.refresh", tokens.refresh_token);
      } else {
        await api.register(email, password);
        const tokens = await api.login(email, password);
        api.setToken(tokens.access_token);
      }
      onLogin();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>NEXUS</h1>
        <p className="subtitle">Personal Digital Infrastructure — local only</p>

        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            minLength={8}
            required
          />
        </label>

        {error && <div className="error">{error}</div>}

        <button type="submit" disabled={busy}>
          {busy ? "…" : mode === "login" ? "Log in" : "Create account"}
        </button>

        <button
          type="button"
          className="linklike"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "No account? Register" : "Have an account? Log in"}
        </button>
      </form>
    </div>
  );
}

export function CoreStatus() {
  const [health, setHealth] = useState<string>("checking…");
  useEffect(() => {
    api
      .health()
      .then((h) => setHealth(`${h.service} v${h.version} — ${h.status}`))
      .catch((e) => setHealth(`Core unreachable at ${api.baseUrl} (${String(e)})`));
  }, []);
  return <div className="core-status">Core: {health}</div>;
}
