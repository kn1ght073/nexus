document.addEventListener('DOMContentLoaded', () => {
  // 1. Live Telemetry Health Probe
  const statusBadge = document.getElementById('live-status-badge');
  const statusDot = statusBadge ? statusBadge.querySelector('.status-dot') : null;
  const statusText = document.getElementById('status-text');
  const statusPing = document.getElementById('status-ping');

  async function probeHealth() {
    const t0 = performance.now();
    try {
      const res = await fetch('/health', { cache: 'no-store' });
      const t1 = performance.now();
      const latency = Math.round(t1 - t0);
      if (res.ok) {
        if (statusDot) statusDot.classList.add('online');
        if (statusText) statusText.textContent = 'ONLINE';
        if (statusPing) statusPing.textContent = `${latency} ms`;
      } else {
        throw new Error('Non-200');
      }
    } catch {
      if (statusDot) statusDot.classList.remove('online');
      if (statusText) statusText.textContent = 'STANDBY';
      if (statusPing) statusPing.textContent = '-- ms';
    }
  }

  probeHealth();
  setInterval(probeHealth, 12000);

  // 2. Checksum and Command Copy Handlers
  document.querySelectorAll('.btn-copy-hash').forEach(btn => {
    btn.addEventListener('click', async () => {
      const hash = btn.getAttribute('data-hash');
      if (!hash) return;
      try {
        await navigator.clipboard.writeText(hash);
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span>Copied!</span>';
        btn.style.color = '#34d399';
        setTimeout(() => {
          btn.innerHTML = originalText;
          btn.style.color = '';
        }, 2000);
      } catch (err) {
        console.error('Clipboard copy failed', err);
      }
    });
  });

  document.querySelectorAll('.btn-copy-cmd').forEach(btn => {
    btn.addEventListener('click', async () => {
      const cmd = btn.getAttribute('data-cmd');
      if (!cmd) return;
      try {
        await navigator.clipboard.writeText(cmd);
        const span = btn.querySelector('span');
        if (span) span.textContent = 'Copied!';
        setTimeout(() => {
          if (span) span.textContent = 'Copy';
        }, 2000);
      } catch (err) {
        console.error('Clipboard copy failed', err);
      }
    });
  });

  // 3. Interactive Terminal Tabs
  const terminalSnippets = {
    login: `<span class="cmd-prompt">$</span> nexus cp login --email operator@nexus.internal
<span class="dim">Connecting to control plane: https://nexus-control-plane-uvi8.onrender.com</span>
<span class="success">✓ Authenticated successfully. Session key locked in system keychain.</span>

<span class="cmd-prompt">$</span> nexus whoami
<span class="info">User:</span> operator@nexus.internal   <span class="info">Role:</span> owner   <span class="info">Status:</span> active`,

    status: `<span class="cmd-prompt">$</span> nexus node status
<span class="dim">ID         NAME            HOST / IP       ROLE       STATUS    LAST SEEN</span>
-------------------------------------------------------------------------
node_win   workstation-01  192.168.1.120   primary    <span class="success">ONLINE</span>    1s ago
node_mac   macbook-pro-m3  192.168.1.144   worker     <span class="success">ONLINE</span>    3s ago
node_mob   galaxy-s24      cellular        satellite  <span class="dim">STANDBY</span>   42s ago`,

    tunnel: `<span class="cmd-prompt">$</span> nexus relay tunnel node_win --port 8000
<span class="dim">ℹ Initiating Ephemeral Diffie-Hellman handshake...</span>
<span class="success">✓ Directional ChaCha20-Poly1305 symmetric keys established.</span>
<span class="success">✓ Nonce tracking active (monotonic replay guard).</span>
<span class="info">✓ Tunnel open: localhost:8000 &lt;==&gt; node_win:8000 (0.8ms local)</span>`,

    ai: `<span class="cmd-prompt">$</span> nexus pipeline run voice_to_task --input audio_note.opus
<span class="dim">ℹ Transcribing locally via faster-whisper (tiny.en on Metal/DirectML)...</span>
<span class="success">✓ Transcript: "Audit production sessions and check relay peer connections"</span>
<span class="dim">ℹ Routing intent to local Ollama (qwen2.5:1.5b)...</span>
<span class="info">✓ Task created in local inbox: ID task_91a0c (Zero cloud transmission)</span>`
  };

  const codeEl = document.getElementById('terminal-code');
  const tabs = document.querySelectorAll('.terminal-tab');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const key = tab.getAttribute('data-tab');
      if (codeEl && terminalSnippets[key]) {
        codeEl.innerHTML = terminalSnippets[key];
      }
    });
  });

  // Terminal Snippet Copy
  const termCopyBtn = document.getElementById('terminal-copy-btn');
  if (termCopyBtn && codeEl) {
    termCopyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(codeEl.innerText);
        termCopyBtn.textContent = 'Copied!';
        setTimeout(() => {
          termCopyBtn.textContent = 'Copy Snippet';
        }, 2000);
      } catch (err) {
        console.error('Clipboard copy failed', err);
      }
    });
  }
});
