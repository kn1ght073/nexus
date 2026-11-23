/**
 * NEXUS Client Console Frontend Logic
 * Strictly connects to user-scoped /api/account/* endpoints with verified ownership.
 */
(() => {
  'use strict';

  let token = localStorage.getItem('nexus.token');
  const API_BASE = window.location.origin;

  async function api(path, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.status === 401) {
      localStorage.removeItem('nexus.token');
      localStorage.removeItem('nexus.refresh');
      window.location.href = '/admin';
      throw new Error('Unauthorized');
    }
    if (res.status === 204) return null;
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }

  function formatDate(isoStr) {
    if (!isoStr) return 'Never';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  }

  // --- View Switcher ---
  const navLinks = document.querySelectorAll('.sidebar-nav .nav-link');
  const viewPanels = document.querySelectorAll('.view-panel');
  const bcTitle = document.getElementById('c-bc-title');

  function switchView(viewId) {
    navLinks.forEach((link) => {
      if (link.getAttribute('data-view') === viewId) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    viewPanels.forEach((panel) => {
      if (panel.id === `view-${viewId}`) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    });

    const activeLink = document.querySelector(`.sidebar-nav .nav-link[data-view="${viewId}"]`);
    if (activeLink && bcTitle) {
      bcTitle.textContent = activeLink.querySelector('span')?.textContent || 'Client Console';
    }
  }

  navLinks.forEach((link) => {
    link.addEventListener('click', (e) => {
      const v = link.getAttribute('data-view');
      if (v) {
        e.preventDefault();
        switchView(v);
      }
    });
  });

  // --- 1. Load Account Overview ---
  async function loadOverview() {
    try {
      const ov = await api('/api/account/overview');
      const google = ov.google_identity;

      // Sidebar Profile
      const userName = google?.name || ov.display_name || ov.email.split('@')[0];
      const nameEl = document.getElementById('c-user-name');
      const idEl = document.getElementById('c-user-id');
      if (nameEl) nameEl.textContent = userName;
      if (idEl) idEl.textContent = `ID #NX-${String(ov.id).padStart(6, '0')}`;

      const avatarCont = document.getElementById('c-avatar-container');
      if (avatarCont && google?.picture_url) {
        avatarCont.innerHTML = `<img src="${google.picture_url}" alt="${userName}" class="client-avatar-img" style="width:32px;height:32px;">`;
      }

      // Hero Profile Card
      const heroName = document.getElementById('c-hero-name');
      const heroEmail = document.getElementById('c-hero-email');
      const heroId = document.getElementById('c-hero-id');
      const heroCreated = document.getElementById('c-hero-created');
      const heroProvider = document.getElementById('c-hero-provider');
      const heroLinked = document.getElementById('c-hero-linked');
      const heroAvatarBox = document.getElementById('c-hero-avatar-box');

      if (heroName) heroName.textContent = userName;
      if (heroEmail) heroEmail.textContent = ov.email;
      if (heroId) heroId.textContent = `Account ID: #NX-${String(ov.id).padStart(6, '0')}`;
      if (heroCreated) heroCreated.textContent = `Member since: ${formatDate(ov.created_at)}`;

      if (heroProvider) {
        heroProvider.textContent = google?.linked ? 'Google OIDC' : 'Master Passphrase';
      }
      if (heroLinked) {
        heroLinked.textContent = google?.linked_at ? `Linked ${formatDate(google.linked_at)}` : 'Sovereign Account';
      }

      if (heroAvatarBox && google?.picture_url) {
        heroAvatarBox.innerHTML = `<img src="${google.picture_url}" alt="${userName}" class="client-avatar-img" style="width:64px;height:64px;">`;
      }

      // Metrics
      const mDev = document.getElementById('c-metric-devices');
      const mDevSub = document.getElementById('c-metric-devices-sub');
      const mSess = document.getElementById('c-metric-sessions');
      const mSessSub = document.getElementById('c-metric-sessions-sub');

      if (mDev) mDev.textContent = ov.device_stats.total;
      if (mDevSub) mDevSub.textContent = `${ov.device_stats.active} online`;
      if (mSess) mSess.textContent = ov.session_stats.active;
      if (mSessSub) mSessSub.textContent = `${ov.session_stats.total} total sessions`;

      // Show Operator Console link if role allows
      if (ov.role === 'operator' || ov.role === 'owner') {
        const opLink = document.getElementById('link-operator-console');
        if (opLink) opLink.classList.remove('hidden');
      }
    } catch (err) {
      console.error('Error loading account overview', err);
    }
  }

  // --- 2. Load Devices & Sessions ---
  async function loadDevices() {
    const tbody = document.getElementById('c-devices-tbody');
    if (!tbody) return;
    try {
      const devices = await api('/api/account/devices');
      if (devices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 24px; color: #64748b;">No registered hardware devices found.</td></tr>';
        return;
      }
      tbody.innerHTML = devices
        .map(
          (d) => `
        <tr>
          <td style="font-weight: 600; color: #fff;">${d.name}</td>
          <td style="text-transform: uppercase; font-family: monospace; font-size: 11px; color: #94a3b8;">${d.platform}</td>
          <td>
            ${
              d.is_online
                ? '<span style="color: #34d399; font-family: monospace; font-size: 11px;">● ONLINE</span>'
                : '<span style="color: #64748b; font-family: monospace; font-size: 11px;">○ OFFLINE</span>'
            }
          </td>
          <td style="color: #94a3b8; font-size: 11px;">${formatDate(d.registered_at)}</td>
          <td style="color: #94a3b8; font-size: 11px;">${formatDate(d.last_seen)}</td>
          <td style="text-align: right;">
            <button class="btn btn-sm btn-danger btn-revoke-dev" data-id="${d.id}" data-name="${d.name}" style="padding: 4px 10px; font-size: 11px;">
              Revoke
            </button>
          </td>
        </tr>
      `
        )
        .join('');

      tbody.querySelectorAll('.btn-revoke-dev').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-id');
          const name = btn.getAttribute('data-name');
          if (confirm(`Revoke and unbind hardware device "${name}"?`)) {
            try {
              await api(`/api/account/devices/${id}`, { method: 'DELETE' });
              loadDevices();
              loadOverview();
            } catch (e) {
              alert(e.message);
            }
          }
        });
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color: #f43f5e;">${err.message}</td></tr>`;
    }
  }

  async function loadSessions() {
    const tbody = document.getElementById('c-sessions-tbody');
    if (!tbody) return;
    try {
      const sessions = await api('/api/account/sessions');
      if (sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 24px; color: #64748b;">No active sessions found.</td></tr>';
        return;
      }
      tbody.innerHTML = sessions
        .map((s) => {
          const isRevoked = Boolean(s.revoked_at);
          const isExpired = new Date(s.expires_at) < new Date();
          const isActive = !isRevoked && !isExpired;
          return `
          <tr>
            <td style="font-weight: 600; color: #fff;">
              ${s.user_agent ? s.user_agent.slice(0, 32) : 'Nexus Sovereign Client'}
              <div style="font-size: 10px; font-family: monospace; color: #64748b;">Session #${s.id}</div>
            </td>
            <td style="text-transform: uppercase; font-family: monospace; font-size: 10px; color: #38bdf8;">${s.created_via}</td>
            <td style="font-family: monospace; font-size: 11px; color: #94a3b8;">${s.last_used_ip || 'Internal'}</td>
            <td>
              ${
                isActive
                  ? '<span style="color: #34d399; font-family: monospace; font-size: 11px;">● ACTIVE</span>'
                  : isRevoked
                  ? '<span style="color: #f43f5e; font-family: monospace; font-size: 11px;">✕ REVOKED</span>'
                  : '<span style="color: #64748b; font-family: monospace; font-size: 11px;">○ EXPIRED</span>'
              }
            </td>
            <td style="color: #94a3b8; font-size: 11px;">${formatDate(s.issued_at)}</td>
            <td style="color: #94a3b8; font-size: 11px;">${formatDate(s.expires_at)}</td>
            <td style="text-align: right;">
              ${
                isActive
                  ? `<button class="btn btn-sm btn-danger btn-revoke-sess" data-id="${s.id}" style="padding: 4px 10px; font-size: 11px;">Revoke</button>`
                  : '<span style="font-size: 10px; color: #475569; font-family: monospace;">Inactivated</span>'
              }
            </td>
          </tr>
        `;
        })
        .join('');

      tbody.querySelectorAll('.btn-revoke-sess').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-id');
          if (confirm(`Revoke session #${id}? This will invalidate its entire token lineage.`)) {
            try {
              await api(`/api/account/sessions/${id}`, { method: 'DELETE' });
              loadSessions();
              loadOverview();
            } catch (e) {
              alert(e.message);
            }
          }
        });
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: #f43f5e;">${err.message}</td></tr>`;
    }
  }

  // --- 3. Load Activity ---
  let activeCat = 'all';
  async function loadActivity(category = 'all') {
    const stream = document.getElementById('c-activity-stream');
    const countEl = document.getElementById('c-activity-count');
    if (!stream) return;
    try {
      const q = category !== 'all' ? `?category=${category}&limit=50` : '?limit=50';
      const data = await api(`/api/account/activity${q}`);
      if (countEl) countEl.textContent = `Displaying ${data.items.length} of ${data.total} recorded events.`;

      if (data.items.length === 0) {
        stream.innerHTML = '<div style="text-align:center; padding: 24px; color: #64748b;">No activity recorded for this category.</div>';
        return;
      }

      stream.innerHTML = data.items
        .map(
          (item) => `
        <div style="padding: 12px 16px; background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-family: monospace; font-size: 12px; font-weight: 600; color: #38bdf8;">${item.action}</span>
              <span style="font-size: 10px; color: #64748b; font-family: monospace;">#${item.id}</span>
            </div>
            <span style="font-size: 11px; color: #64748b; font-family: monospace;">${formatDate(item.created_at)}</span>
          </div>
          <p style="font-size: 12px; color: #cbd5e1; margin-top: 6px; font-family: monospace; word-break: break-all;">
            ${item.detail || 'Executed successfully.'}
          </p>
        </div>
      `
        )
        .join('');
    } catch (err) {
      stream.innerHTML = `<div style="text-align:center; padding: 24px; color: #f43f5e;">${err.message}</div>`;
    }
  }

  document.querySelectorAll('.filter-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      activeCat = btn.getAttribute('data-cat') || 'all';
      loadActivity(activeCat);
    });
  });

  // --- 4. Load Server Status ---
  async function loadServerStatus() {
    const t0 = performance.now();
    try {
      const srv = await api('/api/account/server-status');
      const ping = Math.round(performance.now() - t0);

      const pingEl = document.getElementById('c-live-ping');
      if (pingEl) pingEl.textContent = `${ping} ms`;

      const cpEl = document.getElementById('c-srv-cp');
      const dbEl = document.getElementById('c-srv-db');
      const relayEl = document.getElementById('c-srv-relay');
      const verEl = document.getElementById('c-srv-ver');

      if (cpEl) cpEl.textContent = (srv.control_plane || 'OPERATIONAL').toUpperCase();
      if (dbEl) dbEl.textContent = (srv.database || 'HEALTHY').toUpperCase();
      if (relayEl) relayEl.textContent = (srv.relay_mesh || 'ACTIVE').toUpperCase();
      if (verEl) verEl.textContent = srv.api_version || 'v0.3.0';
    } catch (err) {
      console.error('Server status probe failed', err);
    }
  }

  // --- 5. Load Account Data Summary ---
  async function loadDataSummary() {
    try {
      const summary = await api('/api/account/data-summary');
      const pEl = document.getElementById('c-dt-projects');
      const nEl = document.getElementById('c-dt-notes');
      const tEl = document.getElementById('c-dt-tasks');
      const iEl = document.getElementById('c-dt-inbox');

      if (pEl) pEl.textContent = summary.stats.projects || 0;
      if (nEl) nEl.textContent = summary.stats.notes || 0;
      if (tEl) tEl.textContent = summary.stats.tasks || 0;
      if (iEl) iEl.textContent = summary.stats.inbox_items || 0;
    } catch (err) {
      console.error('Data summary load failed', err);
    }
  }

  // --- Logout ---
  const logoutBtn = document.getElementById('client-logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      try {
        await api('/api/auth/logout', { method: 'POST' });
      } catch (_) {}
      localStorage.removeItem('nexus.token');
      localStorage.removeItem('nexus.refresh');
      window.location.href = '/';
    });
  }

  // Initialize all sections
  loadOverview();
  loadDevices();
  loadSessions();
  loadActivity();
  loadServerStatus();
  loadDataSummary();
  setInterval(loadServerStatus, 15000);
})();
