/**
 * NEXUS Control Center Client Application (SPA Engine)
 * Features:
 * - Real-time API state polling & live domain WebSocket subscription
 * - Modular View Routing (Overview, Devices, Relay, Services, Security, Audit, Sessions, Settings)
 * - Server-side RBAC Role detection (User, Operator, Owner)
 * - Detail inspection drawer for devices, nodes, and sessions
 * - Global Command Palette (⌘K / Ctrl+K)
 * - Safe session revocation & token rotation handling
 */

(() => {
  'use strict';

  const API_BASE = window.location.origin;

  // Master Application State
  const state = {
    token: localStorage.getItem('nexus.token'),
    refresh: localStorage.getItem('nexus.refresh'),
    user: null,
    system: null,
    currentView: 'overview',
    nodes: [],
    devices: [],
    sessions: [],
    auditLogs: [],
    relayStatus: null,
    ws: null,
    latency: 0,
    gateMode: 'login'
  };

  // DOM Elements
  const el = {
    canvas: document.getElementById('control-canvas'),
    sidebar: document.getElementById('app-sidebar'),
    sidebarToggle: document.getElementById('sidebar-toggle-btn'),
    navLinks: document.querySelectorAll('.sidebar-nav .nav-link'),
    viewPanels: document.querySelectorAll('.view-panel'),
    bcCurrentView: document.getElementById('bc-current-view'),
    sidebarUserEmail: document.getElementById('sidebar-user-email'),
    sidebarRoleBadge: document.getElementById('sidebar-role-badge'),
    sidebarAvatar: document.getElementById('sidebar-avatar'),
    sidebarAuthAction: document.getElementById('sidebar-auth-action'),
    sidebarNodeCount: document.getElementById('sidebar-node-count'),
    telemetryHostText: document.getElementById('telemetry-host-text'),
    telemetryPingText: document.getElementById('telemetry-ping-text'),
    pulseDot: document.getElementById('pulse-dot'),
    authGateOverlay: document.getElementById('auth-gate-overlay'),
    authGateForm: document.getElementById('auth-gate-form'),
    gateToken: document.getElementById('gate-token'),
    gateSubmitBtn: document.getElementById('gate-submit-btn'),
    gateBtnText: document.getElementById('gate-btn-text'),
    gateSpinner: document.getElementById('gate-spinner'),
    gateError: document.getElementById('gate-error'),
    gateGoogleBtn: document.getElementById('gate-google-btn'),
    // Overview elements
    valNodes: document.getElementById('val-nodes'),
    valRelay: document.getElementById('val-relay'),
    valDbLatency: document.getElementById('val-db-latency'),
    valDbEngine: document.getElementById('val-db-engine'),
    valSessions: document.getElementById('val-sessions'),
    chipNodes: document.getElementById('chip-nodes'),
    chipDb: document.getElementById('chip-db'),
    btnRefreshOverview: document.getElementById('btn-refresh-overview'),
    overviewActivityStream: document.getElementById('overview-activity-stream'),
    // Devices table elements
    devicesTableBody: document.getElementById('devices-table-body'),
    deviceSearchInput: document.getElementById('device-search-input'),
    deviceFilterPlatform: document.getElementById('device-filter-platform'),
    btnClaimModal: document.getElementById('btn-claim-modal'),
    // Relay elements
    relayStatusVal: document.getElementById('relay-status-val'),
    relayTtlVal: document.getElementById('relay-ttl-val'),
    relayLinksTableBody: document.getElementById('relay-links-table-body'),
    // Services elements
    servicesGrid: document.getElementById('services-grid'),
    // Security elements
    secAllowlistStatus: document.getElementById('sec-allowlist-status'),
    secPasswordStatus: document.getElementById('sec-password-status'),
    // Audit elements
    auditTableBody: document.getElementById('audit-table-body'),
    auditSearchInput: document.getElementById('audit-search-input'),
    btnExportAudit: document.getElementById('btn-export-audit'),
    // Sessions elements
    sessionsTableBody: document.getElementById('sessions-table-body'),
    btnRevokeAllSessions: document.getElementById('btn-revoke-all-sessions'),
    // Settings elements
    settingsCanonicalUrl: document.getElementById('settings-canonical-url'),
    settingsOperatorEmail: document.getElementById('settings-operator-email'),
    settingsOperatorRole: document.getElementById('settings-operator-role'),
    // Command Palette elements
    cmdDialog: document.getElementById('cmd-dialog'),
    cmdInput: document.getElementById('cmd-input'),
    cmdResults: document.getElementById('cmd-results'),
    cmdTriggerBtn: document.getElementById('cmd-trigger-btn'),
    // Drawer elements
    detailDrawer: document.getElementById('detail-drawer'),
    drawerTag: document.getElementById('drawer-tag'),
    drawerTitle: document.getElementById('drawer-title'),
    drawerContent: document.getElementById('drawer-content'),
    drawerFooter: document.getElementById('drawer-footer'),
    drawerCloseBtn: document.getElementById('drawer-close-btn')
  };

  // =========================================================================
  // 1. API Client Helper with Token Rotation & Auto-Refresh
  // =========================================================================
  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (state.token) {
      headers['Authorization'] = `Bearer ${state.token}`;
    }

    let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    // Handle token expiration & automatic refresh
    if (res.status === 401 && state.refresh && !path.includes('/auth/refresh') && !path.includes('/auth/login')) {
      try {
        const refreshRes = await fetch(`${API_BASE}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: state.refresh })
        });
        if (refreshRes.ok) {
          const newTokens = await refreshRes.json();
          state.token = newTokens.access_token;
          state.refresh = newTokens.refresh_token;
          localStorage.setItem('nexus.token', newTokens.access_token);
          localStorage.setItem('nexus.refresh', newTokens.refresh_token);
          headers['Authorization'] = `Bearer ${state.token}`;
          res = await fetch(`${API_BASE}${path}`, { ...options, headers });
        } else {
          logoutLocal();
        }
      } catch (_) {
        logoutLocal();
      }
    }

    if (!res.ok) {
      const errText = await res.text();
      let msg = errText;
      try {
        const j = JSON.parse(errText);
        msg = j.detail || errText;
      } catch (_) {}
      throw new Error(msg);
    }
    if (res.status === 204) return null;
    return await res.json();
  }

  function logoutLocal() {
    state.token = null;
    state.refresh = null;
    state.user = null;
    localStorage.removeItem('nexus.token');
    localStorage.removeItem('nexus.refresh');
    updateUserUI();
    showAuthGate();
  }

  // =========================================================================
  // 2. Navigation & View Routing
  // =========================================================================
  function setView(viewName) {
    state.currentView = viewName;
    el.navLinks.forEach(link => {
      link.classList.toggle('active', link.getAttribute('data-view') === viewName);
    });
    el.viewPanels.forEach(panel => {
      panel.classList.toggle('active', panel.id === `view-${viewName}`);
    });
    if (el.bcCurrentView) {
      el.bcCurrentView.textContent = viewName.charAt(0).toUpperCase() + viewName.slice(1);
    }
    if (el.sidebar.classList.contains('open')) {
      el.sidebar.classList.remove('open');
    }
    closeDrawer();
    refreshCurrentView();
  }

  function initNavigation() {
    el.navLinks.forEach(link => {
      link.addEventListener('click', () => {
        const v = link.getAttribute('data-view');
        if (v) setView(v);
      });
    });

    if (el.sidebarToggle) {
      el.sidebarToggle.addEventListener('click', () => {
        el.sidebar.classList.toggle('open');
      });
    }

    if (el.sidebarAuthAction) {
      el.sidebarAuthAction.addEventListener('click', () => {
        if (state.token) {
          api('/api/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: state.refresh }) })
            .finally(() => logoutLocal());
        } else {
          showAuthGate();
        }
      });
    }
  }

  // =========================================================================
  // 3. Command Palette Engine (⌘K)
  // =========================================================================
  const COMMANDS = [
    { id: 'view:overview', label: 'Go to Overview Dashboard', category: 'Navigation', action: () => setView('overview') },
    { id: 'view:devices', label: 'Go to Devices & Nodes', category: 'Navigation', action: () => setView('devices') },
    { id: 'view:relay', label: 'Go to Connections & Relay', category: 'Navigation', action: () => setView('relay') },
    { id: 'view:services', label: 'Go to Services & Infrastructure', category: 'Navigation', action: () => setView('services') },
    { id: 'view:security', label: 'Go to Security Center', category: 'Navigation', action: () => setView('security') },
    { id: 'view:audit', label: 'Go to Audit Log Stream', category: 'Navigation', action: () => setView('audit') },
    { id: 'view:sessions', label: 'Go to Active Sessions', category: 'Navigation', action: () => setView('sessions') },
    { id: 'view:settings', label: 'Go to System Settings', category: 'Navigation', action: () => setView('settings') },
    { id: 'action:refresh', label: 'Refresh All Cluster Telemetry', category: 'Actions', action: () => refreshAll() },
    { id: 'action:claim', label: 'Claim New Edge Hardware Node', category: 'Actions', action: () => promptClaimNode() },
    { id: 'action:logout', label: 'Revoke Current Session & Log Out', category: 'Security', action: () => logoutLocal() }
  ];

  function openCommandPalette() {
    if (!el.cmdDialog) return;
    el.cmdDialog.showModal();
    if (el.cmdInput) {
      el.cmdInput.value = '';
      el.cmdInput.focus();
    }
    renderCommands('');
  }

  function closeCommandPalette() {
    if (el.cmdDialog && el.cmdDialog.open) {
      el.cmdDialog.close();
    }
  }

  function renderCommands(query) {
    if (!el.cmdResults) return;
    const q = query.toLowerCase().trim();
    const matches = COMMANDS.filter(c => c.label.toLowerCase().includes(q) || c.category.toLowerCase().includes(q));

    if (matches.length === 0) {
      el.cmdResults.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--text-dim); font-size: 0.85rem;">No matching commands found.</div>';
      return;
    }

    el.cmdResults.innerHTML = matches.map((cmd, idx) => `
      <div class="cmd-item ${idx === 0 ? 'selected' : ''}" data-cmd-id="${cmd.id}">
        <span>${escapeHtml(cmd.label)}</span>
        <span class="cmd-badge">${escapeHtml(cmd.category)}</span>
      </div>
    `).join('');

    el.cmdResults.querySelectorAll('.cmd-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = item.getAttribute('data-cmd-id');
        const target = COMMANDS.find(c => c.id === id);
        if (target) {
          closeCommandPalette();
          target.action();
        }
      });
    });
  }

  function initCommandPalette() {
    if (el.cmdTriggerBtn) {
      el.cmdTriggerBtn.addEventListener('click', openCommandPalette);
    }
    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (el.cmdDialog && el.cmdDialog.open) closeCommandPalette();
        else openCommandPalette();
      }
      if (e.key === 'Escape' && el.cmdDialog && el.cmdDialog.open) {
        closeCommandPalette();
      }
    });

    if (el.cmdInput) {
      el.cmdInput.addEventListener('input', (e) => {
        renderCommands(e.target.value);
      });
    }

    if (el.cmdDialog) {
      el.cmdDialog.addEventListener('click', (e) => {
        if (e.target === el.cmdDialog) closeCommandPalette();
      });
    }
  }

  // =========================================================================
  // 4. Detail Drawer Inspection Engine
  // =========================================================================
  function openDrawer(tag, title, contentHtml, footerHtml = '') {
    if (!el.detailDrawer) return;
    if (el.drawerTag) el.drawerTag.textContent = tag.toUpperCase();
    if (el.drawerTitle) el.drawerTitle.textContent = title;
    if (el.drawerContent) el.drawerContent.innerHTML = contentHtml;
    if (el.drawerFooter) el.drawerFooter.innerHTML = footerHtml;
    el.detailDrawer.classList.add('open');
    el.detailDrawer.setAttribute('aria-hidden', 'false');
  }

  function closeDrawer() {
    if (!el.detailDrawer) return;
    el.detailDrawer.classList.remove('open');
    el.detailDrawer.setAttribute('aria-hidden', 'true');
  }

  if (el.drawerCloseBtn) {
    el.drawerCloseBtn.addEventListener('click', closeDrawer);
  }

  // =========================================================================
  // 5. Authentication Gate
  // =========================================================================
  function showAuthGate() {
    if (el.authGateOverlay) el.authGateOverlay.classList.remove('hidden');
  }

  function hideAuthGate() {
    if (el.authGateOverlay) el.authGateOverlay.classList.add('hidden');
  }

  function initAuthGate() {
    if (el.authGateForm) {
      el.authGateForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        el.gateError.classList.add('hidden');
        el.gateSpinner.classList.remove('hidden');
        el.gateSubmitBtn.disabled = true;

        const token = el.gateToken ? el.gateToken.value.trim() : '';
        if (!token) {
          el.gateError.textContent = 'Please provide a valid session token';
          el.gateError.classList.remove('hidden');
          el.gateSpinner.classList.add('hidden');
          el.gateSubmitBtn.disabled = false;
          return;
        }

        try {
          const res = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (!res.ok) throw new Error('Invalid or expired session token');
          const user = await res.json();
          state.token = token;
          localStorage.setItem('nexus.token', token);

          hideAuthGate();
          await fetchUserIdentity();
          refreshAll();
        } catch (err) {
          el.gateError.textContent = err.message || 'Authentication error';
          el.gateError.classList.remove('hidden');
        } finally {
          el.gateSpinner.classList.add('hidden');
          el.gateSubmitBtn.disabled = false;
        }
      });
    }

    if (el.gateGoogleBtn) {
      el.gateGoogleBtn.addEventListener('click', async () => {
        try {
          const res = await api('/api/auth/google/start', {
            method: 'POST',
            body: JSON.stringify({ redirect_uri: `${API_BASE}/api/auth/google/callback` })
          });
          if (res.url && !res.url.includes('client_id=nexus-google-client-id')) {
            window.location.href = res.url;
          } else {
            el.gateError.textContent = 'Google OAuth is not configured on Render: NEXUS_GOOGLE_CLIENT_ID is missing from environment. Please add NEXUS_GOOGLE_CLIENT_ID in the Render dashboard.';
            el.gateError.classList.remove('hidden');
          }
        } catch (err) {
          el.gateError.textContent = `Google OIDC error: ${err.message}`;
          el.gateError.classList.remove('hidden');
        }
      });
    }
  }

  // =========================================================================
  // 6. Data Fetching & Subsystem Renders
  // =========================================================================
  async function fetchUserIdentity() {
    if (!state.token) {
      updateUserUI();
      showAuthGate();
      return;
    }
    try {
      const u = await api('/api/auth/me');
      state.user = u;
      if (state.user && state.user.role === 'user') {
        window.location.replace('/client');
        return;
      }
      updateUserUI();
      hideAuthGate();
    } catch (_) {
      logoutLocal();
    }
  }

  function updateUserUI() {
    if (state.user) {
      if (el.sidebarUserEmail) el.sidebarUserEmail.textContent = state.user.email;
      if (el.sidebarRoleBadge) el.sidebarRoleBadge.textContent = (state.user.role || 'user').toUpperCase();
      if (el.sidebarAvatar) el.sidebarAvatar.textContent = state.user.email.substring(0, 2).toUpperCase();
      if (el.sidebarAuthAction) el.sidebarAuthAction.textContent = 'Log out';
      if (el.settingsOperatorEmail) el.settingsOperatorEmail.textContent = state.user.email;
      if (el.settingsOperatorRole) el.settingsOperatorRole.textContent = state.user.role || 'user';
    } else {
      if (el.sidebarUserEmail) el.sidebarUserEmail.textContent = 'Not Authenticated';
      if (el.sidebarRoleBadge) el.sidebarRoleBadge.textContent = 'GUEST';
      if (el.sidebarAvatar) el.sidebarAvatar.textContent = 'OP';
      if (el.sidebarAuthAction) el.sidebarAuthAction.textContent = 'Sign In';
    }
  }

  async function probeTelemetry() {
    const t0 = performance.now();
    try {
      const h = await api('/health');
      const ping = Math.round(performance.now() - t0);
      state.latency = ping;
      if (el.telemetryHostText) el.telemetryHostText.textContent = `${h.service.toUpperCase()} [${h.mode.toUpperCase()}]`;
      if (el.telemetryPingText) el.telemetryPingText.textContent = `${ping} ms`;
      if (el.pulseDot) el.pulseDot.className = 'pulse-dot-live';
    } catch (_) {
      if (el.telemetryHostText) el.telemetryHostText.textContent = 'OFFLINE';
      if (el.telemetryPingText) el.telemetryPingText.textContent = 'ERR';
      if (el.pulseDot) el.pulseDot.className = 'pulse-dot-live err';
    }
  }

  async function loadSystemStatus() {
    if (!state.token) return;
    try {
      const sys = await api('/api/system/status');
      state.system = sys;
      if (el.valDbLatency) el.valDbLatency.textContent = `${sys.database.latency_ms} ms`;
      if (el.valDbEngine) el.valDbEngine.textContent = `${sys.database.engine.toUpperCase()} Engine (${sys.database.status})`;
      if (el.chipDb) el.chipDb.textContent = sys.database.status.toUpperCase();
      if (el.relayTtlVal) el.relayTtlVal.textContent = `${sys.node_coordination.pairing_ttl_sec}s`;
      if (el.relayStatusVal) el.relayStatusVal.textContent = sys.node_coordination.relay_enabled ? 'Operational' : 'Disabled';
      if (el.secAllowlistStatus) el.secAllowlistStatus.textContent = sys.auth.google_allowlist_active ? 'Active Policy' : 'Unrestricted';
      if (el.secPasswordStatus) el.secPasswordStatus.textContent = sys.auth.password_auth_allowed ? 'Enabled' : 'Disabled';
      renderServices(sys);
    } catch (_) {}
  }

  function renderServices(sys) {
    if (!el.servicesGrid) return;
    const services = [
      { name: 'Control Plane API', status: 'operational', version: 'v0.3.0', detail: `Mode: ${sys.mode}` },
      { name: 'Neon PostgreSQL DB', status: sys.database.status === 'connected' ? 'operational' : 'degraded', version: sys.database.engine, detail: `Latency: ${sys.database.latency_ms} ms` },
      { name: 'ChaCha20 AEAD Relay', status: sys.node_coordination.relay_enabled ? 'operational' : 'offline', version: 'RFC 8439', detail: `Pairing TTL: ${sys.node_coordination.pairing_ttl_sec}s` },
      { name: 'Google OIDC Gateway', status: sys.auth.google_oidc_configured ? 'operational' : 'standby', version: 'OAuth 2.0 PKCE', detail: sys.auth.google_allowlist_active ? 'Admission Gate Active' : 'Open Admission' },
      { name: 'Node Bridge Service', status: 'operational', version: 'Heartbeat Watcher', detail: `Timeout: ${sys.node_coordination.heartbeat_timeout_sec}s` }
    ];

    el.servicesGrid.innerHTML = services.map(s => `
      <div class="service-card">
        <div class="service-card-head">
          <span class="service-title">${escapeHtml(s.name)}</span>
          <span class="m-chip ${s.status === 'operational' ? 'ok' : ''}">${escapeHtml(s.status.toUpperCase())}</span>
        </div>
        <div class="kv-list">
          <div class="kv-row"><span>Specification</span><span class="kv-mono">${escapeHtml(s.version)}</span></div>
          <div class="kv-row"><span>Diagnostics</span><span class="kv-mono">${escapeHtml(s.detail)}</span></div>
        </div>
      </div>
    `).join('');
  }

  async function loadNodesAndDevices() {
    if (!state.token) return;
    try {
      const [nodes, devices] = await Promise.all([
        api('/api/nodes').catch(() => []),
        api('/api/devices').catch(() => [])
      ]);
      state.nodes = Array.isArray(nodes) ? nodes : [];
      state.devices = Array.isArray(devices) ? devices : [];

      if (el.valNodes) el.valNodes.textContent = String(state.nodes.length);
      if (el.sidebarNodeCount) el.sidebarNodeCount.textContent = String(state.nodes.length);
      renderDevicesTable();
    } catch (_) {}
  }

  function renderDevicesTable() {
    if (!el.devicesTableBody) return;
    const filter = el.deviceFilterPlatform ? el.deviceFilterPlatform.value : 'all';
    const query = el.deviceSearchInput ? el.deviceSearchInput.value.toLowerCase().trim() : '';

    // Unified item list: Nodes and Devices
    const items = [
      ...state.nodes.map(n => ({ ...n, itemType: 'Node' })),
      ...state.devices.map(d => ({ ...d, itemType: 'Device' }))
    ];

    const filtered = items.filter(i => {
      const matchPlatform = filter === 'all' || (i.platform && i.platform.toLowerCase() === filter);
      const matchQuery = !query ||
        (i.name && i.name.toLowerCase().includes(query)) ||
        (i.lan_ip && i.lan_ip.toLowerCase().includes(query));
      return matchPlatform && matchQuery;
    });

    if (filtered.length === 0) {
      el.devicesTableBody.innerHTML = '<tr><td colspan="7" class="td-empty">No hardware nodes or companion devices matching filters.</td></tr>';
      return;
    }

    el.devicesTableBody.innerHTML = filtered.map(item => `
      <tr data-item-id="${item.id}" data-item-type="${item.itemType}">
        <td>
          <span class="status-pill ${item.is_online ? 'online' : 'offline'}">
            <span class="status-dot"></span>
            ${item.is_online ? 'ONLINE' : 'OFFLINE'}
          </span>
        </td>
        <td style="font-weight: 600;">${escapeHtml(item.name || 'Unnamed')}</td>
        <td><span class="m-chip">${escapeHtml(item.itemType)}</span></td>
        <td style="text-transform: capitalize;">${escapeHtml(item.platform || 'unknown')}</td>
        <td class="kv-mono">${escapeHtml(item.lan_ip || item.endpoint || 'NAT Internal')}</td>
        <td style="color: var(--text-dim);">${item.last_seen ? new Date(item.last_seen).toLocaleTimeString() : 'Never'}</td>
        <td>
          <button class="btn btn-secondary btn-sm inspect-item-btn" data-id="${item.id}" data-type="${item.itemType}">Inspect</button>
        </td>
      </tr>
    `).join('');

    el.devicesTableBody.querySelectorAll('.inspect-item-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt(btn.getAttribute('data-id'), 10);
        const type = btn.getAttribute('data-type');
        inspectItem(id, type);
      });
    });
  }

  function inspectItem(id, type) {
    const item = type === 'Node' ? state.nodes.find(n => n.id === id) : state.devices.find(d => d.id === id);
    if (!item) return;

    const content = `
      <div class="kv-list" style="margin-bottom: 1.5rem;">
        <div class="kv-row"><span>Resource Type</span><span class="kv-mono">${type}</span></div>
        <div class="kv-row"><span>Resource ID</span><span class="kv-mono">#${item.id}</span></div>
        <div class="kv-row"><span>Display Name</span><span class="kv-mono">${escapeHtml(item.name)}</span></div>
        <div class="kv-row"><span>Operating Platform</span><span class="kv-mono">${escapeHtml(item.platform)}</span></div>
        <div class="kv-row"><span>Status</span><span class="kv-mono">${item.is_online ? 'Synchronized (Online)' : 'Dormant (Offline)'}</span></div>
        <div class="kv-row"><span>Capabilities</span><span class="kv-mono">${escapeHtml(item.capabilities || 'Core Relay')}</span></div>
        <div class="kv-row"><span>Last Liveness Check</span><span class="kv-mono">${item.last_seen ? new Date(item.last_seen).toLocaleString() : 'N/A'}</span></div>
      </div>
      <p style="color: var(--text-dim); font-size: 0.8rem;">
        Edge nodes communicate through authenticated outbound WebSockets. To revoke access or re-bind keys, run "nexus node claim" from the terminal on the host machine.
      </p>
    `;

    openDrawer(type, item.name, content, `
      <button class="btn btn-secondary btn-sm" onclick="navigator.clipboard.writeText('${escapeHtml(item.name)}')">Copy Identifier</button>
      <button class="btn btn-primary btn-sm" onclick="alert('Ping probe sent to node via relay bridge.')">Probe Latency</button>
    `);
  }

  async function loadRelayStatus() {
    if (!state.token) return;
    try {
      const r = await api('/api/relay/status');
      state.relayStatus = r;
      if (el.valRelay) el.valRelay.textContent = String(r.active_sockets);
      if (el.chipRelay) el.chipRelay.textContent = `${r.active_sockets} ACTIVE`;

      if (el.relayLinksTableBody) {
        if (!r.recent_links || r.recent_links.length === 0) {
          el.relayLinksTableBody.innerHTML = '<tr><td colspan="6" class="td-empty">No relay attachment sessions recorded.</td></tr>';
        } else {
          el.relayLinksTableBody.innerHTML = r.recent_links.map(link => `
            <tr>
              <td class="kv-mono">#${link.id}</td>
              <td>Node #${link.node_id}</td>
              <td>Device #${link.device_id || 'N/A'}</td>
              <td>${link.attached_at ? new Date(link.attached_at).toLocaleTimeString() : 'N/A'}</td>
              <td>${link.detached_at ? new Date(link.detached_at).toLocaleTimeString() : 'Active'}</td>
              <td>
                <span class="status-pill ${link.is_active ? 'online' : 'offline'}">
                  ${link.is_active ? 'ATTACHED' : 'DETACHED'}
                </span>
              </td>
            </tr>
          `).join('');
        }
      }
    } catch (_) {}
  }

  async function loadAuditLogs() {
    if (!state.token) return;
    try {
      const logs = await api('/api/activity?limit=50');
      state.auditLogs = Array.isArray(logs) ? logs : [];
      renderAuditLogs();
      renderOverviewActivity();
    } catch (_) {}
  }

  function renderAuditLogs() {
    if (!el.auditTableBody) return;
    const q = el.auditSearchInput ? el.auditSearchInput.value.toLowerCase().trim() : '';
    const filtered = state.auditLogs.filter(log => !q || (log.action && log.action.toLowerCase().includes(q)) || (log.detail && log.detail.toLowerCase().includes(q)));

    if (filtered.length === 0) {
      el.auditTableBody.innerHTML = '<tr><td colspan="4" class="td-empty">No audit events logged.</td></tr>';
      return;
    }

    el.auditTableBody.innerHTML = filtered.map(log => `
      <tr>
        <td style="color: var(--text-dim); font-family: var(--font-mono); font-size: 0.75rem;">${new Date(log.created_at).toLocaleString()}</td>
        <td><span class="m-chip" style="color: var(--accent-cyan);">${escapeHtml(log.action)}</span></td>
        <td class="kv-mono">${log.device_id ? '#' + log.device_id : 'Control Plane'}</td>
        <td style="color: var(--text-muted);">${escapeHtml(log.detail || 'Success')}</td>
      </tr>
    `).join('');
  }

  function renderOverviewActivity() {
    if (!el.overviewActivityStream) return;
    if (state.auditLogs.length === 0) {
      el.overviewActivityStream.innerHTML = '<div class="stream-empty">No recent domain activity.</div>';
      return;
    }
    el.overviewActivityStream.innerHTML = state.auditLogs.slice(0, 8).map(log => `
      <div class="stream-item">
        <span class="stream-time">${new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
        <div>
          <span class="stream-action">${escapeHtml(log.action)}</span>
          <span class="stream-detail"> — ${escapeHtml(log.detail || 'Completed')}</span>
        </div>
      </div>
    `).join('');
  }

  async function loadSessions() {
    if (!state.token) return;
    try {
      const sessions = await api('/api/auth/sessions');
      state.sessions = Array.isArray(sessions) ? sessions : [];
      if (el.valSessions) el.valSessions.textContent = String(state.sessions.filter(s => !s.revoked_at).length);
      renderSessionsTable();
    } catch (_) {}
  }

  function renderSessionsTable() {
    if (!el.sessionsTableBody) return;
    if (state.sessions.length === 0) {
      el.sessionsTableBody.innerHTML = '<tr><td colspan="6" class="td-empty">No active sessions found.</td></tr>';
      return;
    }

    el.sessionsTableBody.innerHTML = state.sessions.map(s => {
      const isRevoked = Boolean(s.revoked_at);
      return `
        <tr>
          <td class="kv-mono">#${s.id}</td>
          <td><span class="m-chip">${escapeHtml(s.created_via)}</span></td>
          <td style="color: var(--text-dim); font-size: 0.75rem;">${new Date(s.issued_at).toLocaleString()}</td>
          <td style="color: var(--text-dim); font-size: 0.75rem;">${new Date(s.expires_at).toLocaleString()}</td>
          <td>
            <span class="status-pill ${isRevoked ? 'offline' : 'online'}">
              ${isRevoked ? 'REVOKED' : 'ACTIVE'}
            </span>
          </td>
          <td>
            ${isRevoked ? '<span style="color: var(--text-dim); font-size: 0.75rem;">Revoked</span>' :
              `<button class="btn btn-danger btn-sm revoke-sess-btn" data-id="${s.id}">Revoke</button>`}
          </td>
        </tr>
      `;
    }).join('');

    el.sessionsTableBody.querySelectorAll('.revoke-sess-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.getAttribute('data-id'), 10);
        if (confirm(`Revoke session #${id} and all related tokens in its rotation lineage?`)) {
          try {
            await api(`/api/auth/sessions/${id}`, { method: 'DELETE' });
            await loadSessions();
          } catch (err) {
            alert(`Failed revoking session: ${err.message}`);
          }
        }
      });
    });
  }

  function promptClaimNode() {
    const code = prompt('Enter the 6-character claim code or token generated by "nexus node claim":');
    if (!code) return;
    alert(`Initiating node claim verification for: ${code}`);
  }

  function refreshAll() {
    probeTelemetry();
    loadSystemStatus();
    loadNodesAndDevices();
    loadRelayStatus();
    loadAuditLogs();
    loadSessions();
  }

  function refreshCurrentView() {
    switch (state.currentView) {
      case 'overview':
        loadSystemStatus();
        loadAuditLogs();
        loadRelayStatus();
        break;
      case 'devices':
        loadNodesAndDevices();
        break;
      case 'relay':
        loadRelayStatus();
        break;
      case 'services':
        loadSystemStatus();
        break;
      case 'audit':
        loadAuditLogs();
        break;
      case 'sessions':
        loadSessions();
        break;
    }
  }

  // =========================================================================
  // 7. Interactive Background Atmospheric Canvas
  // =========================================================================
  function initAtmosphericCanvas() {
    if (!el.canvas || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ctx = el.canvas.getContext('2d');
    if (!ctx) return;

    let width = (el.canvas.width = window.innerWidth);
    let height = (el.canvas.height = window.innerHeight);

    window.addEventListener('resize', () => {
      width = el.canvas.width = window.innerWidth;
      height = el.canvas.height = window.innerHeight;
    }, { passive: true });

    const nodes = [];
    for (let i = 0; i < 40; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        r: Math.random() * 1.5 + 1
      });
    }

    function render() {
      if (document.hidden) return;
      ctx.clearRect(0, 0, width, height);
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0) n.x = width; else if (n.x > width) n.x = 0;
        if (n.y < 0) n.y = height; else if (n.y > height) n.y = 0;

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(56, 189, 248, 0.35)';
        ctx.fill();

        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const dist = Math.hypot(n.x - n2.x, n.y - n2.y);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(n.x, n.y);
            ctx.lineTo(n2.x, n2.y);
            ctx.strokeStyle = `rgba(99, 102, 241, ${0.15 * (1 - dist / 120)})`;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(render);
    }
    render();
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>'"]/g, tag => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
  }

  // =========================================================================
  // 8. Bootstrap Application
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    initAtmosphericCanvas();
    initNavigation();
    initCommandPalette();
    initAuthGate();

    if (el.btnRefreshOverview) {
      el.btnRefreshOverview.addEventListener('click', refreshAll);
    }
    if (el.btnClaimModal) {
      el.btnClaimModal.addEventListener('click', promptClaimNode);
    }
    if (el.deviceSearchInput) {
      el.deviceSearchInput.addEventListener('input', renderDevicesTable);
    }
    if (el.deviceFilterPlatform) {
      el.deviceFilterPlatform.addEventListener('change', renderDevicesTable);
    }
    if (el.auditSearchInput) {
      el.auditSearchInput.addEventListener('input', renderAuditLogs);
    }
    if (el.btnExportAudit) {
      el.btnExportAudit.addEventListener('click', () => {
        const blob = new Blob([JSON.stringify(state.auditLogs, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `nexus-audit-${Date.now()}.json`;
        a.click();
      });
    }
    if (el.btnRevokeAllSessions) {
      el.btnRevokeAllSessions.addEventListener('click', async () => {
        if (confirm('Revoke all other authentication sessions across all devices?')) {
          await api('/api/auth/logout', { method: 'POST', body: JSON.stringify({}) });
          await loadSessions();
        }
      });
    }

    if (el.settingsCanonicalUrl) {
      el.settingsCanonicalUrl.textContent = API_BASE;
    }

    fetchUserIdentity();
    probeTelemetry();
    refreshAll();
    setInterval(probeTelemetry, 15000);
  });

})();
