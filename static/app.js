let sessionId = localStorage.getItem('nischay_session_id');
const API_BASE = resolveApiBase();
let currentTab = 'reasoning';

function resolveApiBase() {
  const params = new URLSearchParams(window.location.search);
  const override = params.get('apiBase');
  if (override) {
    localStorage.setItem('nischay_api_base', override);
    return override.replace(/\/$/, '');
  }

  const saved = localStorage.getItem('nischay_api_base');
  if (saved) {
    if (!window.location.origin.includes('localhost') && saved.includes('localhost')) {
      localStorage.removeItem('nischay_api_base');
    } else {
      return saved.replace(/\/$/, '');
    }
  }

  if (window.location.protocol === 'file:') {
    return 'http://localhost:8000/api/v1';
  }

  return '/api/v1';
}

async function checkApiHealth() {
  const statusEl = document.getElementById('api-status');
  if (!statusEl) return true;
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) throw new Error('Health check failed');
    statusEl.textContent = '';
    return true;
  } catch (err) {
    statusEl.textContent = 'Backend not reachable. Start the API server and refresh.';
    return false;
  }
}

async function apiCall(path, options = {}) {
  const token = localStorage.getItem('nischay_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers
  };

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    if (!path.startsWith('/auth/')) {
      localStorage.removeItem('nischay_token');
      localStorage.removeItem('nischay_student_id');
      localStorage.removeItem('nischay_session_id');
      showAuth();
    }
    const err = await response.json().catch(() => ({ detail: 'Unauthorized' }));
    throw new Error(err.detail || 'Session expired. Please sign in again.');
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'API request failed' }));
    throw new Error(err.detail || 'API request failed');
  }
  return response.json();
}

/* ── NAVIGATION SYSTEM ── */
const tabLabels = {
  reasoning: 'Chat', dashboard: 'Dashboard', trajectory: 'Trajectory',
  memory: 'Memory Log', resume: 'Resume Analysis'
};

function navTo(name, el, e) {
  if (e) e.preventDefault();
  if (name === currentTab) return;

  const overlay = document.getElementById('page-transition');
  overlay.classList.add('active');

  setTimeout(() => {
    switchTab(name, el);
    currentTab = name;

    if (name === 'trajectory') updateTraj();
    if (name === 'dashboard') loadDashboard();

    document.getElementById('breadcrumb-current').textContent = tabLabels[name] || name;

    document.querySelectorAll('#nav-links a').forEach(a => a.classList.remove('active'));
    if (el) el.classList.add('active');

    const mobileLinks = document.getElementById('nav-links');
    if (mobileLinks.classList.contains('open')) mobileLinks.classList.remove('open');

    setTimeout(() => overlay.classList.remove('active'), 250);
  }, 200);
}

async function loadDashboard() {
  console.log('Dashboard update triggered');
  // Future: Fetch career rankings and student cluster from backend
}

function toggleMobileMenu() {
  document.getElementById('nav-links').classList.toggle('open');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
  }
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!sidebar || !overlay) return;
  
  sidebar.classList.toggle('open');
  overlay.classList.toggle('active');
  
  const mobileLinks = document.getElementById('nav-links');
  if (mobileLinks && mobileLinks.classList.contains('open')) {
    mobileLinks.classList.remove('open');
  }
}

// Global reference for auth dialog visibility
window.showAuth = function() {
  document.getElementById('auth-overlay').style.display = 'flex';
}

function toggleAuth(isReg) {
  document.getElementById('login-view').style.display = isReg ? 'none' : 'block';
  document.getElementById('register-view').style.display = isReg ? 'block' : 'none';
  document.getElementById('auth-error').textContent = '';
}

function logout() {
  localStorage.removeItem('nischay_token');
  localStorage.removeItem('nischay_student_id');
  localStorage.removeItem('nischay_session_id');
  sessionId = null;
  showAuth();
}

async function handleAuth(type) {
  const errorEl = document.getElementById('auth-error');
  errorEl.textContent = '';
  const ok = await checkApiHealth();
  if (!ok) return;
  try {
    let data;
    if (type === 'login') {
      const email = document.getElementById('login-email').value.trim();
      const password = document.getElementById('login-pass').value;
      if (!email || !password) {
        throw new Error('Email and password are required.');
      }
      data = await apiCall('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
    } else {
      const name = document.getElementById('reg-name').value.trim();
      const email = document.getElementById('reg-email').value.trim();
      const password = document.getElementById('reg-pass').value;
      if (!name || !email || !password) {
        throw new Error('Name, email, and password are required.');
      }
      if (password.length < 6) {
        throw new Error('Password must be at least 6 characters.');
      }
      data = await apiCall('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, email, password })
      });
    }

    localStorage.setItem('nischay_token', data.access_token);
    localStorage.setItem('nischay_student_id', data.student_id);
    document.getElementById('auth-overlay').style.display = 'none';
    initApp();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

/* ── APP INITIALIZATION ── */
async function initApp() {
  const overlay = document.getElementById('page-transition');
  overlay.classList.add('active');
  document.querySelector('.transition-text').textContent = 'Initializing reasoning system...';

  await checkApiHealth();
  if (!localStorage.getItem('nischay_token')) {
    overlay.classList.remove('active');
    showAuth();
    return;
  }

  try {
    await loadProfile();
    if (!sessionId) {
      await resetChat();
    }
    await loadMemoryCount();
    document.querySelector('.transition-text').textContent = 'Ready';
    setTimeout(() => overlay.classList.remove('active'), 300);
  } catch (err) {
    console.error('Init failed:', err);
    overlay.classList.remove('active');
    showAuth();
  }
}

async function loadProfile() {
  try {
    const profile = await apiCall('/profile/');

    const nameEl = document.getElementById('nav-user-name');
    if (nameEl && profile.name) nameEl.textContent = profile.name;

    const pct = profile.completeness || 0;
    document.querySelector('.completeness-pct').textContent = pct + '%';
    document.querySelector('.completeness-bar').style.width = pct + '%';

    if (profile.personality_signals) {
      const sigs = profile.personality_signals;
      updateTraitBar('Risk tolerance', sigs.risk_tolerance);
      updateTraitBar('Intrinsic motivation', sigs.intrinsic_motivation);
      updateTraitBar('Analytical style', sigs.analytical_style);
      updateTraitBar('Conscientiousness', sigs.conscientiousness);
    }

    const scoreEl = document.getElementById('sidebar-contra-score');
    if (scoreEl && profile.contradiction_score !== undefined) {
      scoreEl.textContent = profile.contradiction_score;
      const bar = document.getElementById('sidebar-contra-bar');
      if (bar) bar.style.width = profile.contradiction_score + '%';
      scoreEl.style.color = profile.contradiction_score > 60 ? '#E05C4B' : profile.contradiction_score > 30 ? '#D4954A' : '#2EBF8E';
    }

    const stageEl = document.getElementById('sidebar-stage');
    if (stageEl && profile.conversation_stage) {
      stageEl.innerHTML = `<div class="stage-dot"></div>${profile.conversation_stage}`;
    }
  } catch (err) {
    console.error('Failed to load profile', err);
  }
}

let allMemories = [];

async function loadMemoryCount() {
  try {
    const data = await apiCall('/memory/');
    allMemories = data.memories || [];
    const countEl = document.getElementById('sidebar-memory-count');
    if (countEl && data.total !== undefined) {
      countEl.textContent = data.total + ' insights stored';
    }
    renderMemories('all');
    renderDriftLog(data.memories); // Use memories to find drift patterns

    // COMPLETENESS & CONTRADICTION SCORE CALCULATION
    const completenessPct = Math.min(100, Math.round((allMemories.length / 21) * 100));
    const pctEl = document.querySelector('.completeness-pct');
    if (pctEl) pctEl.textContent = completenessPct + '%';
    const barEl = document.querySelector('.completeness-bar');
    if (barEl) barEl.style.width = completenessPct + '%';
    const subEl = document.querySelector('.completeness-sub');
    if (subEl) subEl.textContent = `${allMemories.length} fields captured · ${Math.max(0, 21 - allMemories.length)} remaining`;

    const contradictions = allMemories.filter(m => m.type && m.type.toLowerCase() === 'contradiction');
    const contradictionScore = Math.min(100, contradictions.length * 20); // Each contradiction adds 20%
    const scoreEl = document.getElementById('sidebar-contra-score');
    if (scoreEl) {
      scoreEl.textContent = contradictionScore;
      const cBar = document.getElementById('sidebar-contra-bar');
      if (cBar) cBar.style.width = contradictionScore + '%';
      scoreEl.style.color = contradictionScore > 60 ? '#E05C4B' : contradictionScore > 30 ? '#D4954A' : '#2EBF8E';
    }

    // Update behavioral drift status
    const driftPill = document.getElementById('sidebar-drift-pill');
    const driftText = document.getElementById('sidebar-drift-text');
    if (driftPill && driftText) {
      if (contradictionScore >= 40) {
        driftPill.className = 'status-pill status-drift';
        driftPill.style.borderColor = 'rgba(224,92,75,0.3)';
        driftPill.style.background = 'rgba(224,92,75,0.1)';
        driftPill.style.color = '#E05C4B';
        driftPill.textContent = '⚠ Drift Detected';
        driftText.textContent = 'Significant anomalies identified between stated priorities and long-term trajectory.';
      } else if (contradictionScore > 0) {
        driftPill.className = 'status-pill';
        driftPill.style.borderColor = 'rgba(212,149,74,0.3)';
        driftPill.style.background = 'rgba(212,149,74,0.1)';
        driftPill.style.color = '#D4954A';
        driftPill.textContent = '⚡ Low Drift';
        driftText.textContent = 'Minor cognitive inconsistencies identified. System is closely monitoring alignment.';
      } else {
        driftPill.className = 'status-pill status-stable';
        driftPill.style.borderColor = '';
        driftPill.style.background = '';
        driftPill.style.color = '';
        driftPill.textContent = '✔ Stable';
        driftText.textContent = 'No anomalies detected in reasoning path.';
      }
    }

    if (currentTab === 'dashboard') loadDashboard();
  } catch (err) {
    console.error('Failed to load memory count', err);
  }
}

function renderMemories(type = 'all') {
  const container = document.getElementById('memory-items');
  if (!container) return;

  const filtered = type === 'all' 
    ? allMemories 
    : allMemories.filter(m => m.type.toLowerCase() === type.toLowerCase());

  if (filtered.length === 0) {
    container.innerHTML = `<div style="color:var(--text-dim);font-size:0.85rem;text-align:center;padding:3rem">
      No memories of type "${type}" found.
    </div>`;
    return;
  }

  container.innerHTML = '';
  filtered.forEach(m => {
    const row = document.createElement('div');
    row.className = `memory-row type-${m.type || 'preference'}`;
    const color = m.type === 'fear' ? '#E05C4B' : m.type === 'goal' ? '#2EBF8E' : m.type === 'contradiction' ? '#D4954A' : '#C8933C';
    row.innerHTML = `
      <div class="memory-type-dot" style="background:${color}"></div>
      <div class="memory-row-content">${m.content}</div>
      <div class="memory-row-meta">${new Date(m.created_at).toLocaleDateString()} · Confidence ${Math.round((m.confidence||0)*100)}%</div>
    `;
    container.appendChild(row);
  });
}

function renderDriftLog(memories) {
  const container = document.getElementById('drift-log-container');
  const rows = document.getElementById('drift-log-rows');
  if (!container || !rows) return;

  const drifts = memories.filter(m => m.type === 'contradiction' || m.confidence > 0.85);
  if (drifts.length > 0) {
    container.style.display = 'block';
    rows.innerHTML = drifts.slice(0, 3).map(d => `
      <div class="drift-row">
        <div class="drift-meta">${new Date(d.created_at).toLocaleTimeString()}</div>
        <div class="drift-content">${d.content}</div>
      </div>
    `).join('');
  } else {
    container.style.display = 'none';
  }
}

// Add filter pill listeners
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      renderMemories(pill.textContent.toLowerCase());
    });
  });
});

function updateTraitBar(label, value) {
  const rows = document.querySelectorAll('.trait-row');
  rows.forEach(row => {
    if (row.querySelector('span').textContent === label) {
      const bar = row.querySelector('.trait-bar');
      if (bar && value !== undefined) {
        bar.style.width = value + '%';
        bar.style.transition = 'width 0.8s cubic-bezier(0.34, 1.2, 0.64, 1)';
      }
    }
  });
}

function switchTab(name, el) {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
  }
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  if (el && el.closest('.tabs')) el.classList.add('active');

  const tabEl = document.querySelector(`.tab[onclick*="'${name}'"]`);
  if (tabEl) tabEl.classList.add('active');

  document.getElementById('panel-' + name).classList.add('active');
  currentTab = name;

  if (name === 'dashboard') loadDashboard();
  if (name === 'memory') loadMemoryCount();
  if (name === 'trajectory') updateTraj();
}

async function loadDashboard() {
  try {
    const profile = await apiCall('/profile/');
    const careersResponse = await apiCall('/careers/').catch(() => ({ careers: [] }));
    const trajectoryResponse = await apiCall('/trajectory/').catch(() => ({ trajectory: [] }));
    
    const careersData = careersResponse.careers || [];
    const trajectoryData = trajectoryResponse.trajectory || [];

    // REQUIRE AT LEAST 1 INSIGHT OR DYNAMIC BACKEND DATA
    if (allMemories.length === 0 && careersData.length === 0 && trajectoryData.length === 0) {
      const placeholder = '<div style="color:var(--text-dim);font-size:0.8rem;text-align:center;padding:1rem">Gathering data...</div>';
      
      const clusterEl = document.getElementById('dash-cluster');
      if (clusterEl) clusterEl.innerHTML = placeholder;
      
      const riskVal = document.getElementById('dash-risk-val');
      const riskText = document.getElementById('dash-risk-text');
      if (riskVal && riskText) {
        riskVal.textContent = '—';
        riskVal.style.color = 'var(--text-dim)';
        riskText.textContent = 'Gathering data...';
      }

      const rankingsEl = document.getElementById('dash-rankings');
      if (rankingsEl) rankingsEl.innerHTML = '<div style="color:var(--text-dim);font-size:0.8rem;text-align:center;padding:2rem">Gathering data...</div>';
      
      return;
    }

    // 1. Cluster Analysis
    const clusterEl = document.getElementById('dash-cluster');
    if (clusterEl) {
      const completenessPct = Math.min(100, Math.round((allMemories.length / 21) * 100));
      if (completenessPct > 20 || trajectoryData.length > 0) {
        clusterEl.innerHTML = `
          <div style="font-family:var(--font-display);font-weight:700;font-size:1.1rem;color:var(--text-primary);margin-bottom:0.5rem">Analytically capable, Tier-2</div>
          <div style="font-size:0.75rem;color:var(--text-muted)">Similar students: <span style="color:var(--accent-success)">1,248 in database</span></div>
        `;
      } else {
        clusterEl.textContent = 'Undetermined cluster. Keep chatting to refine.';
      }
    }

    // 2. Risk Calculation
    const riskVal = document.getElementById('dash-risk-val');
    const riskText = document.getElementById('dash-risk-text');
    if (riskVal && riskText) {
      const contradictions = allMemories.filter(m => m.type && m.type.toLowerCase() === 'contradiction');
      const score = Math.min(100, contradictions.length * 20);
      riskVal.textContent = score + '%';
      riskVal.style.color = score > 60 ? 'var(--accent-danger)' : score > 30 ? 'var(--accent-warn)' : 'var(--accent-success)';
      
      if (score > 60) riskText.textContent = 'High risk detected. Internal values contradict stated goal.';
      else if (score > 30) riskText.textContent = 'Moderate risk. Some misalignment in risk tolerance.';
      else riskText.textContent = 'Stable. Profile alignment is high.';
    }

    // 3. Career Rankings
    const rankingsEl = document.getElementById('dash-rankings');
    if (rankingsEl) {
      let careers = careersData;
      // Fallback to mock logic if the API returns empty but we bypassed the guard (e.g. 5+ memories)
      if (careers.length === 0) {
        const sigs = profile.personality_signals || {};
        careers = [
          { name: 'B.Tech CSE', fit: (sigs.analytical_style || 50) + 10 },
          { name: 'B.Des', fit: (sigs.intrinsic_motivation || 50) - 5 },
          { name: 'B.Com + CA', fit: (sigs.conscientiousness || 50) + 5 }
        ];
      }
      
      const sortedCareers = careers.sort((a,b) => b.fit - a.fit);
      rankingsEl.innerHTML = sortedCareers.map((c, i) => `
        <div style="display:flex;justify-content:space-between;padding:0.65rem 0;border-bottom:1px solid rgba(255,255,255,0.05)">
          <div style="font-size:0.85rem"><span>${i+1}.</span> ${c.name}</div>
          <div style="font-family:var(--font-mono);font-size:0.8rem;color:var(--accent-cyan)">${Math.min(98, Math.max(12, c.fit))}% fit</div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Dashboard load failed:', err);
  }
}

/* ── STREAMING CHAT ── */
async function sendMessage() {
  const input = document.getElementById('chat-input');
  const area = document.getElementById('chat-area');
  const text = input.value.trim();
  if (!text || !sessionId) return;

  input.value = '';
  input.style.height = 'auto';

  const ub = document.createElement('div');
  ub.className = 'bubble-user';
  ub.textContent = text;
  area.appendChild(ub);

  const typing = document.createElement('div');
  typing.className = 'typing-indicator';
  typing.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  area.appendChild(typing);
  area.scrollTop = area.scrollHeight;

  try {
    const token = localStorage.getItem('nischay_token');
    const response = await fetch(`${API_BASE}/chat/${sessionId}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ message: text })
    });

    if (response.status === 401) {
      if (typing.parentNode) area.removeChild(typing);
      logout();
      return;
    }

    if (!response.ok) {
      throw new Error('Stream request failed');
    }

    if (typing.parentNode) area.removeChild(typing);

    const ab = document.createElement('div');
    ab.className = 'bubble-ai';
    const metaDiv = document.createElement('div');
    metaDiv.className = 'response-meta';
    metaDiv.innerHTML = `
      <span class="agent-label">Processing...</span>
      <span class="confidence-label">Confidence: —</span>
    `;
    ab.appendChild(metaDiv);
    const contentDiv = document.createElement('div');
    contentDiv.className = 'streaming-cursor';
    ab.appendChild(contentDiv);
    area.appendChild(ab);
    area.scrollTop = area.scrollHeight;

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));

          if (data.type === 'meta') {
            metaDiv.innerHTML = `
              <span class="agent-label">${data.agent || 'AI'}</span>
              <span class="confidence-label">Confidence: ${data.confidence || '—'}</span>
            `;
            const sidebarAgent = document.querySelector('.agent-active');
            if (sidebarAgent) {
              sidebarAgent.innerHTML = `<div class="agent-active-label">// currently running</div>${data.agent}`;
            }
          } else if (data.type === 'token') {
            fullText += data.token;
            contentDiv.textContent = fullText;
            area.scrollTop = area.scrollHeight;
          } else if (data.type === 'done') {
            contentDiv.classList.remove('streaming-cursor');
          }
        } catch (e) {
          /* skip malformed SSE lines */
        }
      }
    }

    contentDiv.classList.remove('streaming-cursor');
    contentDiv.innerHTML = fullText.replace(/\n/g, '<br>');
    area.scrollTop = area.scrollHeight;

    // Refresh Sidebar Stats
    await loadProfile();
    await loadMemoryCount();

  } catch (err) {
    if (typing.parentNode) area.removeChild(typing);
    console.error('Chat error:', err);
    const errBubble = document.createElement('div');
    errBubble.className = 'bubble-ai';
    errBubble.innerHTML = `<div style="color:var(--accent-danger);font-size:0.82rem;">Connection error. Please try again.</div>`;
    area.appendChild(errBubble);
  }
}

async function resetChat() {
  try {
    const data = await apiCall('/chat/new', { method: 'POST' });
    sessionId = data.session_id;
    localStorage.setItem('nischay_session_id', sessionId);

    const area = document.getElementById('chat-area');
    area.innerHTML = `<div class="bubble-ai">
      <div class="response-meta">
        <span class="agent-label">Profile Agent</span>
        <span class="confidence-label">Confidence: —</span>
      </div>
      I'm Nischay — your AI career and life coach. Tell me about your situation, and I'll help you see the probability distribution of your future before you commit years to it.<br><br>
      What's on your mind?
    </div>`;
  } catch (err) {
    console.error('Failed to reset chat', err);
  }
}

let selectedPaths = [];
const careerData = {
  'MBBS': { color: '#E05C4B', income: [0, 0, 0, 5, 12, 18, 22, 28, 35, 45], satisfaction: [80, 75, 70, 65, 60, 58, 55, 52, 50, 48], burnout: [10, 15, 25, 40, 55, 60, 65, 70, 72, 75], autonomy: [2, 2, 3, 3, 4, 5, 6, 7, 8, 9], regretBase: 42 },
  'CSE': { color: '#C8933C', income: [8, 12, 18, 25, 32, 40, 50, 65, 80, 100], satisfaction: [85, 88, 85, 82, 80, 78, 75, 72, 70, 68], burnout: [5, 10, 15, 20, 25, 30, 35, 40, 45, 50], autonomy: [7, 7, 8, 8, 8, 8, 9, 9, 9, 10], regretBase: 24 },
  'CA': { color: '#2EBF8E', income: [6, 9, 13, 18, 24, 30, 38, 48, 60, 75], satisfaction: [75, 78, 80, 82, 80, 78, 76, 74, 72, 70], burnout: [20, 30, 35, 40, 35, 30, 30, 30, 30, 30], autonomy: [4, 5, 6, 7, 7, 7, 8, 8, 8, 9], regretBase: 31 },
  'DES': { color: '#6B5DB0', income: [5, 8, 12, 15, 20, 26, 34, 42, 52, 65], satisfaction: [90, 92, 88, 85, 82, 80, 78, 76, 74, 72], burnout: [10, 15, 20, 25, 30, 35, 40, 45, 48, 50], autonomy: [8, 9, 9, 10, 10, 10, 10, 10, 10, 10], regretBase: 18 },
  'MBA': { color: '#5878C8', income: [10, 15, 22, 35, 50, 70, 90, 120, 150, 200], satisfaction: [70, 72, 68, 65, 62, 60, 58, 56, 54, 52], burnout: [30, 40, 50, 60, 65, 70, 75, 80, 85, 90], autonomy: [5, 6, 6, 7, 7, 8, 8, 9, 9, 9], regretBase: 38 }
};

function toggleTraj(path, el) {
  const idx = selectedPaths.indexOf(path);
  if (idx > -1) {
    selectedPaths.splice(idx, 1);
    el.classList.remove('active');
  } else {
    if (selectedPaths.length >= 2) {
      // Remove first one if already 2 selected
      const first = selectedPaths.shift();
      const btns = document.querySelectorAll('.traj-btn');
      btns.forEach(b => { if(b.textContent.includes(first)) b.classList.remove('active'); });
    }
    selectedPaths.push(path);
    el.classList.add('active');
  }
  updateTraj();
}

function updateTraj() {
  const motivation = document.getElementById('slider-motivation').value / 100;
  const pressure = document.getElementById('slider-pressure').value / 100;

  renderCharts(motivation, pressure);
  updateRegretScores(motivation, pressure);
}

function renderCharts(mot, pre) {
  const charts = ['income', 'satisfaction', 'burnout', 'autonomy'];
  charts.forEach(type => {
    const svg = document.getElementById(`svg-${type}`);
    if (!svg) return;

    // Clear existing lines
    const oldLines = svg.querySelectorAll('.traj-line');
    oldLines.forEach(l => l.remove());

    selectedPaths.forEach(path => {
      const data = careerData[path];
      let points = [];
      const values = data[type];

      values.forEach((v, i) => {
        let adjusted = v;
        // Simple logic to adjust based on sliders
        if (type === 'satisfaction') adjusted = v * (0.5 + mot) * (1.2 - pre);
        if (type === 'burnout') adjusted = v * (1.5 - mot) * (0.8 + pre);
        if (type === 'income') adjusted = v * (0.8 + (mot * 0.4)) * (1.0 - (pre * 0.2));
        if (type === 'autonomy') adjusted = v * (0.5 + (mot * 0.8)) * (1.1 - (pre * 0.3));
        
        const x = 10 + (i * 37);
        let y = 105 - (adjusted);
        if (type === 'income') y = 105 - (adjusted * 0.5); // scale income
        if (type === 'autonomy') y = 105 - (adjusted * 9); // scale 1-10
        
        points.push(`${x},${Math.max(10, Math.min(105, y))}`);
      });

      const poly = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      poly.setAttribute("points", points.join(" "));
      poly.setAttribute("fill", "none");
      poly.setAttribute("stroke", data.color);
      poly.setAttribute("stroke-width", "2");
      poly.setAttribute("class", "traj-line");
      poly.setAttribute("stroke-linecap", "round");
      svg.appendChild(poly);
    });
  });
}

function updateRegretScores(mot, pre) {
  [1, 2].forEach(i => {
    const probEl = document.getElementById(`traj-prob-${i}`);
    const labelEl = document.getElementById(`traj-label-${i}`);
    const path = selectedPaths[i - 1];

    if (path) {
      const data = careerData[path];
      const prob = Math.round(data.regretBase * (1.5 - mot) * (0.7 + pre));
      probEl.textContent = Math.min(95, Math.max(5, prob)) + '%';
      probEl.style.color = prob > 50 ? '#E05C4B' : prob > 30 ? '#D4954A' : '#2EBF8E';
      labelEl.textContent = path;
    } else {
      probEl.textContent = '—';
      probEl.style.color = '#4A4438';
      labelEl.textContent = i === 1 ? 'Select a career path' : 'Select 2nd path to compare';
    }
  });
}

async function handleFileUpload(input) {
  if (!input.files.length) return;
  const zone = document.getElementById('upload-zone');
  const feedbackList = document.getElementById('resume-feedback-list');
  const feedbackLabel = document.getElementById('resume-feedback-label');
  
  zone.innerHTML = `
    <div style="font-size:1.5rem;margin-bottom:0.5rem">⌛</div>
    <div style="font-family:var(--font-display);font-weight:600;">Analyzing...</div>`;

  try {
    const token = localStorage.getItem('nischay_token');
    if (!token) throw new Error('Please sign in first.');
    const formData = new FormData();
    formData.append('file', input.files[0]);

    const response = await fetch(`${API_BASE}/resume/analyze`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    const data = await response.json();

    zone.innerHTML = `
      <div style="font-size:1.5rem;margin-bottom:0.5rem">✓</div>
      <div style="font-family:var(--font-display);font-weight:600;color:var(--accent-success)">Analysis complete</div>
      <div style="font-size:0.8rem;color:var(--text-dim);margin-top:0.3rem">${input.files[0].name}</div>`;

    if (data.feedback && data.feedback.length > 0) {
      feedbackLabel.textContent = 'Intelligent Feedback — AI Analysis';
      feedbackList.innerHTML = '';
      data.feedback.forEach(item => {
        const div = document.createElement('div');
        div.className = `feedback-item ${item.priority || 'medium'}`;
        div.innerHTML = `
          <div class="feedback-priority">${item.priority || 'medium'} priority</div>
          <div class="feedback-before">Before: ${item.before}</div>
          <div class="feedback-after">After: ${item.after}</div>
          <div class="feedback-why">Why: ${item.why}</div>
        `;
        feedbackList.appendChild(div);
      });
    }
  } catch (err) {
    zone.innerHTML = `<div style="color:var(--accent-danger)">Error: ${err.message}</div>`;
  }
}

// Auto-resize textarea
const inputEl = document.getElementById('chat-input');
if (inputEl) {
  inputEl.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
  });
}

// ── CURSOR ──
const cur = document.getElementById('cursor');
const ring = document.getElementById('cursor-ring');
let mx = 0, my = 0, rx = 0, ry = 0;
let cursorInitialized = false;

document.addEventListener('mousemove', e => {
  mx = e.clientX;
  my = e.clientY;
  if (!cursorInitialized) {
    cursorInitialized = true;
    if (cur) cur.style.opacity = '1';
    if (ring) ring.style.opacity = '1';
  }
});

function animateCursor() {
  if (cur) { cur.style.left = mx + 'px'; cur.style.top = my + 'px'; }
  rx += (mx - rx) * 0.12; ry += (my - ry) * 0.12;
  if (ring) { ring.style.left = rx + 'px'; ring.style.top = ry + 'px'; }
  requestAnimationFrame(animateCursor);
}
animateCursor();

function bindCursorEvents() {
  document.querySelectorAll('a, button, input[type=range], textarea, .tab, .filter-pill, .traj-btn, .chat-send-btn, .theme-toggle').forEach(el => {
    el.addEventListener('mouseenter', () => {
      if (cur) { cur.style.width = '20px'; cur.style.height = '20px'; }
      if (ring) { ring.style.width = '50px'; ring.style.height = '50px'; }
    });
    el.addEventListener('mouseleave', () => {
      if (cur) { cur.style.width = '12px'; cur.style.height = '12px'; }
      if (ring) { ring.style.width = '36px'; ring.style.height = '36px'; }
    });
  });
}
bindCursorEvents();
// Re-bind cursor events whenever content changes dynamically
const observer = new MutationObserver(bindCursorEvents);
observer.observe(document.body, { childList: true, subtree: true });

// ── PARTICLES ──
(function initParticles() {
  const canvas = document.getElementById('particles-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, nodes, edges;

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', () => { resize(); build(); });

  function build() {
    const count = Math.floor((W * H) / 22000);
    nodes = Array.from({length: count}, () => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5, pulse: Math.random() * Math.PI * 2
    }));
    edges = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i+1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        if (Math.sqrt(dx*dx+dy*dy) < 130) edges.push([i,j]);
      }
    }
  }
  build();

  let t = 0;
  function draw() {
    ctx.clearRect(0, 0, W, H);
    t += 0.008;
    if (Math.round(t*100) % 40 === 0) {
      edges = [];
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i+1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          if (Math.sqrt(dx*dx+dy*dy) < 130) edges.push([i,j]);
        }
      }
    }
    edges.forEach(([a,b]) => {
      const na = nodes[a], nb = nodes[b];
      const dx = na.x-nb.x, dy = na.y-nb.y;
      const d = Math.sqrt(dx*dx+dy*dy);
      const alpha = (1 - d/130) * 0.09;
      ctx.beginPath();
      ctx.moveTo(na.x, na.y);
      ctx.lineTo(nb.x, nb.y);
      ctx.strokeStyle = `rgba(200,147,60,${alpha})`;
      ctx.lineWidth = 0.6;
      ctx.stroke();
    });
    nodes.forEach(n => {
      n.x += n.vx; n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
      n.pulse += 0.02;
      const glow = Math.sin(n.pulse) * 0.3 + 0.7;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI*2);
      ctx.fillStyle = `rgba(200,147,60,${0.22 * glow})`;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }
  draw();
})();

// Start
initApp();
