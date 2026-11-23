/**
 * NEXUS Interactive Client Engine & Real-Time Orchestrator
 * Supports:
 * - Particle neural mesh background with cursor interactivity & FPS-aware throttling
 * - IntersectionObserver scroll-driven reveals & counter animations
 * - Live Control-Plane API connectivity (status, nodes, auth login/register, OIDC)
 * - In-browser diagnostic terminal simulator with live command evaluation
 * - Dynamic single-variable environment awareness
 */

(() => {
  'use strict';

  // --- Dynamic Single Variable API Root ---
  const API_BASE = window.location.origin;

  // State Management
  const state = {
    token: localStorage.getItem('nexus.token'),
    refresh: localStorage.getItem('nexus.refresh'),
    user: null,
    nodes: [],
    mode: 'login',
    clusterOnline: false,
    latency: 0
  };

  // DOM Elements
  const el = {
    canvas: document.getElementById('neural-canvas'),
    cursorGlow: document.getElementById('cursor-glow'),
    statusPulse: document.getElementById('status-pulse'),
    statusText: document.getElementById('status-text'),
    statusLatency: document.getElementById('status-latency'),
    authPanel: document.getElementById('auth-panel'),
    loggedOutState: document.getElementById('logged-out-state'),
    loggedInState: document.getElementById('logged-in-state'),
    tabLogin: document.getElementById('tab-login'),
    tabRegister: document.getElementById('tab-register'),
    authForm: document.getElementById('auth-form'),
    authEmail: document.getElementById('auth-email'),
    authPassword: document.getElementById('auth-password'),
    authSubmitBtn: document.getElementById('auth-submit-btn'),
    authBtnText: document.getElementById('auth-btn-text'),
    authSpinner: document.getElementById('auth-spinner'),
    authErrorBanner: document.getElementById('auth-error-banner'),
    sessionEmail: document.getElementById('session-email'),
    sessionAvatar: document.getElementById('session-avatar'),
    sessionLogoutBtn: document.getElementById('session-logout-btn'),
    cpModeBadge: document.getElementById('cp-mode-badge'),
    cpUrlDisplay: document.getElementById('cp-url-display'),
    quickCmdCode: document.getElementById('quick-cmd-code'),
    copyCmdBtn: document.getElementById('copy-cmd-btn'),
    googleAuthBtn: document.getElementById('google-auth-btn'),
    termBody: document.getElementById('term-body'),
    termDynamicOutput: document.getElementById('term-dynamic-output'),
    termInput: document.getElementById('term-input'),
    termInputRow: document.getElementById('term-input-row'),
    clearTermBtn: document.getElementById('clear-term-btn'),
    termCanonicalUrl: document.getElementById('term-canonical-url'),
    meshNodesContainer: document.getElementById('mesh-nodes-container'),
    metricNodes: document.getElementById('metric-nodes'),
    metricLatency: document.getElementById('metric-latency'),
    navItems: document.querySelectorAll('.nav-item'),
    mobileToggle: document.getElementById('mobile-toggle'),
    navMenu: document.querySelector('.nav-menu')
  };

  // =========================================================================
  // 1. Interactive Particle Neural Mesh Engine
  // =========================================================================
  function initNeuralCanvas() {
    if (!el.canvas || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ctx = el.canvas.getContext('2d');
    if (!ctx) return;

    let width = (el.canvas.width = window.innerWidth);
    let height = (el.canvas.height = window.innerHeight);

    window.addEventListener('resize', () => {
      width = el.canvas.width = window.innerWidth;
      height = el.canvas.height = window.innerHeight;
    }, { passive: true });

    const mouse = { x: width / 2, y: height / 2, active: false };
    window.addEventListener('mousemove', (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
      if (el.cursorGlow) {
        el.cursorGlow.style.transform = `translate(${mouse.x}px, ${mouse.y}px)`;
        el.cursorGlow.style.opacity = '1';
      }
    }, { passive: true });

    document.addEventListener('mouseleave', () => {
      mouse.active = false;
      if (el.cursorGlow) el.cursorGlow.style.opacity = '0';
    });

    const PARTICLE_COUNT = Math.min(Math.floor((width * height) / 14000), 75);
    const particles = [];

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.65,
        vy: (Math.random() - 0.5) * 0.65,
        radius: Math.random() * 1.5 + 1
      });
    }

    let animationFrameId;
    let isSkipped = false;

    // Modern Web Guidance: Efficient Background Processing
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        cancelAnimationFrame(animationFrameId);
      } else {
        render();
      }
    });

    function render() {
      if (document.hidden) return;
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        else if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        else if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(56, 189, 248, 0.4)';
        ctx.fill();

        // Connect particles near mouse
        if (mouse.active) {
          const dx = mouse.x - p.x;
          const dy = mouse.y - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 140) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.strokeStyle = `rgba(56, 189, 248, ${0.35 * (1 - dist / 140)})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }

        // Connect neighbor particles
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 110) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(99, 102, 241, ${0.18 * (1 - dist / 110)})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    }

    render();
  }

  // =========================================================================
  // 2. Scroll Reveals & Navigation Interactivity
  // =========================================================================
  function initScrollObservables() {
    const revealItems = document.querySelectorAll('.scroll-reveal');
    if (!('IntersectionObserver' in window)) {
      revealItems.forEach(item => item.classList.add('revealed'));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    revealItems.forEach(el => observer.observe(el));

    // Nav active tab highlight on scroll
    const sections = document.querySelectorAll('main > section[id]');
    window.addEventListener('scroll', () => {
      let current = '';
      const scrollY = window.pageYOffset;
      sections.forEach(section => {
        const top = section.offsetTop - 140;
        const height = section.offsetHeight;
        if (scrollY >= top && scrollY < top + height) {
          current = section.getAttribute('id');
        }
      });
      el.navItems.forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-nav') === current);
      });
    }, { passive: true });

    // Mobile nav toggle
    if (el.mobileToggle && el.navMenu) {
      el.mobileToggle.addEventListener('click', () => {
        const isOpen = el.navMenu.classList.toggle('open');
        el.mobileToggle.setAttribute('aria-expanded', String(isOpen));
      });
    }
  }

  // =========================================================================
  // 3. API Communication & Live Health Telemetry
  // =========================================================================
  async function apiRequest(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (state.token) {
      headers['Authorization'] = `Bearer ${state.token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
      const errText = await res.text();
      let errDetail = errText;
      try {
        const json = JSON.parse(errText);
        errDetail = json.detail || errText;
      } catch (_) {}
      throw new Error(errDetail);
    }
    if (res.status === 204) return null;
    return await res.json();
  }

  async function probeClusterHealth() {
    const start = performance.now();
    try {
      const health = await apiRequest('/health');
      const rtt = Math.round(performance.now() - start);
      state.clusterOnline = true;
      state.latency = rtt;

      if (el.statusPulse) {
        el.statusPulse.className = 'pulse-indicator status-online';
      }
      if (el.statusText) el.statusText.textContent = `${health.service.toUpperCase()} [${health.mode.toUpperCase()}]`;
      if (el.statusLatency) el.statusLatency.textContent = `${rtt} ms`;
      if (el.metricLatency) el.metricLatency.textContent = `${rtt}ms`;
      if (el.cpModeBadge) el.cpModeBadge.textContent = health.mode === 'control-plane' ? 'Control Plane (Coordination)' : 'Full Local Node';
      if (el.cpUrlDisplay) el.cpUrlDisplay.textContent = API_BASE;
      if (el.termCanonicalUrl) el.termCanonicalUrl.textContent = API_BASE;
      if (el.quickCmdCode) el.quickCmdCode.textContent = `nexus cp login --email ${state.user ? state.user.email : 'you@domain.com'}`;
    } catch (err) {
      state.clusterOnline = false;
      if (el.statusPulse) {
        el.statusPulse.className = 'pulse-indicator status-error';
      }
      if (el.statusText) el.statusText.textContent = 'GATEWAY UNREACHABLE';
      if (el.statusLatency) el.statusLatency.textContent = 'ERR';
    }
  }

  async function fetchSessionUser() {
    if (!state.token) {
      renderAuthState(false);
      return;
    }
    try {
      const user = await apiRequest('/api/auth/me');
      state.user = user;
      renderAuthState(true);
      loadNodes();
    } catch (_) {
      // Token expired or invalid
      state.token = null;
      localStorage.removeItem('nexus.token');
      renderAuthState(false);
    }
  }

  async function loadNodes() {
    try {
      const nodes = await apiRequest('/api/nodes');
      state.nodes = Array.isArray(nodes) ? nodes : [];
      renderNodes(state.nodes);
    } catch (_) {
      // In control plane mode without node registrations yet
      renderNodes([]);
    }
  }

  function renderNodes(nodes) {
    if (el.metricNodes) el.metricNodes.textContent = String(nodes.length || 0);
    if (!el.meshNodesContainer) return;

    if (nodes.length === 0) {
      el.meshNodesContainer.innerHTML = `
        <div class="node-skeleton-card" style="grid-column: 1 / -1; text-align: center; padding: 3rem 1.5rem;">
          <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">📡</div>
          <h3 style="font-size: 1.25rem; font-family: var(--font-display); margin-bottom: 0.5rem;">No Mesh Nodes Currently Claimed</h3>
          <p style="color: var(--text-dim); max-width: 500px; margin: 0 auto 1.5rem auto; font-size: 0.9rem;">
            Install the NEXUS CLI on your workstation or server, then register it using the command below to establish an end-to-end encrypted relay bridge.
          </p>
          <div style="display: inline-flex; align-items: center; gap: 0.75rem; background: #000; border: 1px solid var(--border-subtle); padding: 0.65rem 1rem; border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 0.85rem; color: var(--accent-cyan);">
            <code>nexus cp claim &lt;code&gt;</code>
          </div>
        </div>
      `;
      return;
    }

    el.meshNodesContainer.innerHTML = nodes.map(n => `
      <div class="node-skeleton-card">
        <div class="node-header">
          <span class="node-icon">🖥️</span>
          <div class="node-title-box">
            <span class="node-name">${escapeHtml(n.name || 'Nexus Node')}</span>
            <span class="node-status-badge ${n.is_online ? 'status-active' : 'status-offline'}">
              ${n.is_online ? 'SYNCHRONIZED' : 'OFFLINE'}
            </span>
          </div>
        </div>
        <div class="node-stats">
          <div><span class="stat-l">Node ID</span><span class="stat-v">#${n.id}</span></div>
          <div><span class="stat-l">Role</span><span class="stat-v">${escapeHtml(n.role || 'primary')}</span></div>
          <div><span class="stat-l">IP Address</span><span class="stat-v">${escapeHtml(n.lan_ip || '127.0.0.1')}</span></div>
          <div><span class="stat-l">Heartbeat</span><span class="stat-v">${n.heartbeat_at ? new Date(n.heartbeat_at).toLocaleTimeString() : 'Never'}</span></div>
        </div>
      </div>
    `).join('');
  }

  function renderAuthState(loggedIn) {
    if (loggedIn && state.user) {
      if (el.loggedOutState) el.loggedOutState.classList.remove('active');
      if (el.loggedInState) el.loggedInState.classList.add('active');
      if (el.sessionEmail) el.sessionEmail.textContent = state.user.email;
      if (el.sessionAvatar) el.sessionAvatar.textContent = state.user.email.substring(0, 2).toUpperCase();
      const navAuth = document.getElementById('nav-auth-btn');
      if (navAuth) navAuth.textContent = 'Vault Active';
    } else {
      if (el.loggedInState) el.loggedInState.classList.remove('active');
      if (el.loggedOutState) el.loggedOutState.classList.add('active');
      const navAuth = document.getElementById('nav-auth-btn');
      if (navAuth) navAuth.textContent = 'Operator Login';
    }
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>'"]/g, tag => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
  }

  // =========================================================================
  // 4. Authentication Interaction Flow
  // =========================================================================
  function initAuth() {
    if (el.tabLogin && el.tabRegister) {
      el.tabLogin.addEventListener('click', () => {
        state.mode = 'login';
        el.tabLogin.classList.add('active');
        el.tabRegister.classList.remove('active');
        el.authBtnText.textContent = 'Authenticate Session';
        el.authErrorBanner.classList.add('hidden');
      });
      el.tabRegister.addEventListener('click', () => {
        state.mode = 'register';
        el.tabRegister.classList.add('active');
        el.tabLogin.classList.remove('active');
        el.authBtnText.textContent = 'Register New Identity';
        el.authErrorBanner.classList.add('hidden');
      });
    }

    if (el.authForm) {
      el.authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        el.authErrorBanner.classList.add('hidden');
        el.authSpinner.classList.remove('hidden');
        el.authSubmitBtn.disabled = true;

        const email = el.authEmail.value.trim();
        const password = el.authPassword.value;

        try {
          if (state.mode === 'register') {
            await apiRequest('/api/auth/register', {
              method: 'POST',
              body: JSON.stringify({ email, password })
            });
            termLog(`[AUTH] Successfully registered new identity: ${email}`, 'green');
          }

          const tokens = await apiRequest('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
          });

          state.token = tokens.access_token;
          state.refresh = tokens.refresh_token;
          localStorage.setItem('nexus.token', tokens.access_token);
          if (tokens.refresh_token) localStorage.setItem('nexus.refresh', tokens.refresh_token);

          termLog(`[AUTH] Operator authenticated. Token stored in vault.`, 'green');
          await fetchSessionUser();
        } catch (err) {
          el.authErrorBanner.textContent = err.message || 'Authentication failed.';
          el.authErrorBanner.classList.remove('hidden');
          termLog(`[ERR] Authentication error: ${err.message}`, 'amber');
        } finally {
          el.authSpinner.classList.add('hidden');
          el.authSubmitBtn.disabled = false;
        }
      });
    }

    if (el.sessionLogoutBtn) {
      el.sessionLogoutBtn.addEventListener('click', () => {
        state.token = null;
        state.refresh = null;
        state.user = null;
        localStorage.removeItem('nexus.token');
        localStorage.removeItem('nexus.refresh');
        renderAuthState(false);
        renderNodes([]);
        termLog(`[AUTH] Session terminated by operator.`, 'dim');
      });
    }

    if (el.copyCmdBtn && el.quickCmdCode) {
      el.copyCmdBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(el.quickCmdCode.textContent);
        el.copyCmdBtn.textContent = 'Copied!';
        setTimeout(() => { el.copyCmdBtn.textContent = 'Copy'; }, 2000);
      });
    }

    if (el.googleAuthBtn) {
      el.googleAuthBtn.addEventListener('click', async () => {
        try {
          const res = await apiRequest('/api/auth/google/start', {
            method: 'POST',
            body: JSON.stringify({ redirect_uri: `${API_BASE}/api/auth/google/callback` })
          });
          if (res.url) {
            window.location.href = res.url;
          }
        } catch (err) {
          el.authErrorBanner.textContent = `Google OIDC error: ${err.message}`;
          el.authErrorBanner.classList.remove('hidden');
        }
      });
    }
  }

  // =========================================================================
  // 5. In-Browser Diagnostic Terminal Simulator
  // =========================================================================
  function termLog(msg, colorClass = '') {
    if (!el.termDynamicOutput) return;
    const line = document.createElement('div');
    line.className = `term-line ${colorClass ? 'c-' + colorClass : ''}`;
    line.textContent = msg;
    el.termDynamicOutput.appendChild(line);
    el.termBody.scrollTop = el.termBody.scrollHeight;
  }

  function initTerminal() {
    if (!el.termInputRow || !el.termInput) return;

    if (el.clearTermBtn) {
      el.clearTermBtn.addEventListener('click', () => {
        if (el.termDynamicOutput) el.termDynamicOutput.innerHTML = '';
      });
    }

    el.termInputRow.addEventListener('submit', async (e) => {
      e.preventDefault();
      const raw = el.termInput.value.trim();
      if (!raw) return;
      el.termInput.value = '';

      termLog(`operator@nexus:~$ ${raw}`, 'white');
      const parts = raw.split(/\s+/);
      const cmd = parts[0].toLowerCase();
      const arg = parts.slice(1).join(' ');

      switch (cmd) {
        case 'help':
          termLog('Available commands:');
          termLog('  status    - Probe live health of the control plane API');
          termLog('  nodes     - Query all registered edge hardware nodes');
          termLog('  whoami    - Show current authenticated operator credentials');
          termLog('  ping      - Measure round-trip time (RTT) to the cluster gateway');
          termLog('  url       - Display the canonical master public endpoint');
          termLog('  clear     - Clear terminal buffer');
          break;

        case 'status':
          termLog('Probing cluster health at ' + API_BASE + '...', 'dim');
          try {
            const h = await apiRequest('/health');
            termLog(`Cluster OK: service=${h.service}, mode=${h.mode}`, 'green');
          } catch (err) {
            termLog(`Status check failed: ${err.message}`, 'amber');
          }
          break;

        case 'nodes':
          termLog('Querying mesh node registry...', 'dim');
          try {
            const nodes = await apiRequest('/api/nodes');
            if (!nodes.length) {
              termLog('No nodes claimed yet. Run "nexus cp claim" to bind hardware.', 'dim');
            } else {
              nodes.forEach(n => termLog(`[Node #${n.id}] ${n.name} (${n.role}) — ${n.lan_ip} [${n.is_online ? 'ONLINE' : 'OFFLINE'}]`, 'cyan'));
            }
          } catch (err) {
            termLog(`Failed to query nodes (requires login): ${err.message}`, 'amber');
          }
          break;

        case 'whoami':
          if (state.user) {
            termLog(`Authenticated as: ${state.user.email} (ID: ${state.user.id})`, 'green');
          } else {
            termLog('Not authenticated. Please log in via the Control Interface.', 'amber');
          }
          break;

        case 'ping':
          const t0 = performance.now();
          await apiRequest('/health').catch(() => {});
          termLog(`PONG from ${API_BASE} in ${(performance.now() - t0).toFixed(2)} ms`, 'cyan');
          break;

        case 'url':
          termLog(`Unified Public URL: ${API_BASE}`, 'cyan');
          termLog('Submodules & CLI read NEXUS_PUBLIC_URL automatically.', 'dim');
          break;

        case 'clear':
          if (el.termDynamicOutput) el.termDynamicOutput.innerHTML = '';
          break;

        default:
          termLog(`nexus: command not found: ${cmd}. Type 'help' for available commands.`, 'amber');
          break;
      }
    });
  }

  // =========================================================================
  // 6. Bootstrap Everything
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    initNeuralCanvas();
    initScrollObservables();
    initAuth();
    initTerminal();
    probeClusterHealth();
    fetchSessionUser();
    setInterval(probeClusterHealth, 15000);
  });

})();
