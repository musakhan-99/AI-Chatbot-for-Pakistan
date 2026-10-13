const els = {
  form: document.getElementById('chatForm'),
  input: document.getElementById('messageInput'),
  send: document.getElementById('sendBtn'),
  messages: document.getElementById('messages'),
  welcome: document.getElementById('welcome'),
  suggestions: document.getElementById('suggestions'),
  language: document.getElementById('languageSelect'),
  modeButtons: [...document.querySelectorAll('.mode-btn')],
  modePill: document.getElementById('modePill'),
  welcomeCopy: document.getElementById('welcomeCopy'),
  newChat: document.getElementById('newChatBtn'),
  sidebar: document.getElementById('sidebar'),
  menuBtn: document.getElementById('menuBtn'),
  overlay: document.getElementById('mobileOverlay'),
};

const STORAGE_KEY = 'pakistan-ai-history-v1';
const SETTINGS_KEY = 'pakistan-ai-settings-v1';

let state = {
  mode: 'local',
  language: 'auto',
  history: [],
  busy: false,
};

const prompts = {
  local: [
    ['Government services', 'How can I apply for a Pakistani passport?'],
    ['Tax & business', 'Explain NTN and filer status in simple Roman Urdu.'],
    ['Education', 'Explain the higher education system in Pakistan.'],
    ['Explore Pakistan', 'Tell me about the history and culture of Swat.'],
  ],
  visitor: [
    ['Plan a trip', 'Plan a first-time 10-day trip to Pakistan.'],
    ['Culture & etiquette', 'What should a foreign visitor know about Pakistani culture?'],
    ['Visa guidance', 'Where should I verify Pakistan tourist visa requirements?'],
    ['Destinations', 'Compare Hunza, Skardu and Swat for a first-time visitor.'],
  ],
};

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    const settings = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
    if (Array.isArray(saved)) state.history = saved.slice(-20);
    if (settings.mode === 'visitor' || settings.mode === 'local') state.mode = settings.mode;
    if (['auto', 'en', 'ur', 'roman-ur', 'ps'].includes(settings.language)) state.language = settings.language;
  } catch (_) {}
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.history.slice(-20)));
  localStorage.setItem(SETTINGS_KEY, JSON.stringify({ mode: state.mode, language: state.language }));
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function renderText(value) {
  const safe = escapeHtml(value);
  const lines = safe.split(/\r?\n/);
  let html = '';
  let inList = false;

  for (const raw of lines) {
    const line = raw.trim();
    if (/^[-*]\s+/.test(line)) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${inlineFormat(line.replace(/^[-*]\s+/, ''))}</li>`;
      continue;
    }
    if (inList) { html += '</ul>'; inList = false; }
    if (!line) { html += '<p></p>'; continue; }
    if (/^###\s+/.test(line)) {
      html += `<h3>${inlineFormat(line.replace(/^###\s+/, ''))}</h3>`;
    } else if (/^#{1,2}\s+/.test(line)) {
      html += `<h3>${inlineFormat(line.replace(/^#{1,2}\s+/, ''))}</h3>`;
    } else {
      html += `<p>${inlineFormat(line)}</p>`;
    }
  }
  if (inList) html += '</ul>';
  return html;
}

function inlineFormat(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function isRtl() {
  return state.language === 'ur' || state.language === 'ps';
}

function setMode(mode) {
  state.mode = mode;
  els.modeButtons.forEach(btn => btn.classList.toggle('active', btn.dataset.mode === mode));
  els.modePill.textContent = mode === 'local' ? 'Pakistani mode' : 'Visitor mode';
  els.welcomeCopy.textContent = mode === 'local'
    ? 'Get practical answers about Pakistan, from culture and cities to education, government services, tourism and business.'
    : 'Explore Pakistan with context for international visitors: destinations, etiquette, visas, culture, transport and practical local guidance.';
  renderSuggestions();
  saveState();
}

function renderSuggestions() {
  els.suggestions.innerHTML = '';
  prompts[state.mode].forEach(([title, prompt]) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'suggestion';
    btn.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(prompt)}</span>`;
    btn.addEventListener('click', () => {
      els.input.value = prompt;
      autoResize();
      els.input.focus();
    });
    els.suggestions.appendChild(btn);
  });
}

function renderHistory() {
  els.messages.innerHTML = '';
  if (!state.history.length) {
    els.welcome.style.display = '';
    return;
  }
  els.welcome.style.display = 'none';
  for (const item of state.history) addMessageToDom(item);
  scrollBottom(false);
}

function addMessageToDom(item) {
  const row = document.createElement('div');
  row.className = `message ${item.role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = item.role === 'assistant' ? 'PK' : 'YOU';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if (item.rtl) bubble.classList.add('rtl');

  if (item.role === 'assistant') {
    const content = document.createElement('div');
    content.className = 'answer-content';
    content.innerHTML = renderText(item.content);
    bubble.appendChild(content);

    if ((item.sources && item.sources.length) || (item.warnings && item.warnings.length)) {
      const sourceArea = document.createElement('div');
      sourceArea.className = 'source-area';

      if (item.sources && item.sources.length) {
        const title = document.createElement('div');
        title.className = 'source-title';
        title.textContent = 'Sources & authorities';
        sourceArea.appendChild(title);

        const grid = document.createElement('div');
        grid.className = 'source-grid';
        item.sources.slice(0, 6).forEach(source => {
          const link = document.createElement('a');
          link.className = 'source-card';
          link.href = source.url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          const typeLabel = source.source_type === 'official' ? 'Official' : 'Wikipedia';
          link.innerHTML = `
            <div class="source-name">${escapeHtml(source.title)}</div>
            <div class="source-meta">
              <span class="badge ${source.source_type === 'official' ? 'official' : ''}">${typeLabel}</span>
              <span>${escapeHtml(source.authority || source.language || '')}</span>
            </div>`;
          grid.appendChild(link);
        });
        sourceArea.appendChild(grid);
      }

      if (item.warnings && item.warnings.length) {
        const warning = document.createElement('div');
        warning.className = 'warning-box';
        warning.textContent = item.warnings.join(' ');
        sourceArea.appendChild(warning);
      }

      bubble.appendChild(sourceArea);
    }
  } else {
    bubble.textContent = item.content;
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  els.messages.appendChild(row);
}

function addTyping() {
  const row = document.createElement('div');
  row.className = 'message assistant';
  row.id = 'typingRow';
  row.innerHTML = '<div class="avatar">PK</div><div class="bubble"><div class="typing"><i></i><i></i><i></i></div></div>';
  els.messages.appendChild(row);
  scrollBottom();
}

function removeTyping() {
  document.getElementById('typingRow')?.remove();
}

function setBusy(value) {
  state.busy = value;
  els.send.disabled = value;
  els.input.disabled = value;
}

function scrollBottom(smooth = true) {
  window.scrollTo({ top: document.body.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
}

function autoResize() {
  els.input.style.height = 'auto';
  els.input.style.height = `${Math.min(els.input.scrollHeight, 170)}px`;
}

async function sendMessage(message) {
  if (!message.trim() || state.busy) return;

  const priorHistory = state.history
    .filter(x => x.role === 'user' || x.role === 'assistant')
    .slice(-8)
    .map(x => ({ role: x.role, content: x.content }));

  const userItem = { role: 'user', content: message.trim(), rtl: isRtl() };
  state.history.push(userItem);
  saveState();
  els.welcome.style.display = 'none';
  addMessageToDom(userItem);
  els.input.value = '';
  autoResize();
  setBusy(true);
  addTyping();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message.trim(),
        mode: state.mode,
        language: state.language,
        history: priorHistory,
      }),
    });

    let data = {};
    try { data = await response.json(); } catch (_) {}

    if (!response.ok) {
      const detail = data.detail || `Request failed (${response.status}).`;
      throw new Error(detail);
    }

    const assistantItem = {
      role: 'assistant',
      content: data.answer,
      sources: data.sources || [],
      warnings: data.warnings || [],
      rtl: isRtl(),
    };
    state.history.push(assistantItem);
    saveState();
    removeTyping();
    addMessageToDom(assistantItem);
  } catch (error) {
    removeTyping();
    const assistantItem = {
      role: 'assistant',
      content: `I couldn't complete that request. ${error.message}`,
      sources: [],
      warnings: [],
      rtl: false,
    };
    state.history.push(assistantItem);
    saveState();
    addMessageToDom(assistantItem);
  } finally {
    setBusy(false);
    els.input.focus();
    scrollBottom();
  }
}

els.form.addEventListener('submit', e => {
  e.preventDefault();
  sendMessage(els.input.value);
});

els.input.addEventListener('input', autoResize);
els.input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    els.form.requestSubmit();
  }
});

els.modeButtons.forEach(btn => btn.addEventListener('click', () => setMode(btn.dataset.mode)));
els.language.addEventListener('change', () => {
  state.language = els.language.value;
  saveState();
  els.input.dir = isRtl() ? 'rtl' : 'auto';
});

els.newChat.addEventListener('click', () => {
  state.history = [];
  saveState();
  renderHistory();
  els.sidebar.classList.remove('open');
  els.overlay.classList.remove('show');
  els.input.focus();
});

els.menuBtn.addEventListener('click', () => {
  els.sidebar.classList.add('open');
  els.overlay.classList.add('show');
});
els.overlay.addEventListener('click', () => {
  els.sidebar.classList.remove('open');
  els.overlay.classList.remove('show');
});

loadState();
els.language.value = state.language;
setMode(state.mode);
els.input.dir = isRtl() ? 'rtl' : 'auto';
renderHistory();
autoResize();
