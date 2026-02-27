// app/webapp/static/app.js
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const API_BASE = '';
const HEADERS = {
    'Content-Type': 'application/json',
    'X-Telegram-Init-Data': tg.initData,
};

// === TAB SWITCHING ===
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    });
});

// === LOAD DASHBOARD ===
async function loadDashboard() {
    try {
        const resp = await fetch(`${API_BASE}/api/dashboard`, { headers: HEADERS });
        if (!resp.ok) throw new Error('Auth failed');
        const data = await resp.json();

        // Plan badge
        const planBadge = document.getElementById('plan-badge');
        planBadge.textContent = data.subscription.plan.toUpperCase();

        // Subscription details
        document.getElementById('sub-details').innerHTML = `
            <p>📋 План: <strong>${data.subscription.plan}</strong></p>
            <p>📊 Статус: <strong>${data.subscription.status}</strong></p>
            <p>📅 До: <strong>${
                data.subscription.expires_at
                    ? new Date(data.subscription.expires_at).toLocaleDateString('ru')
                    : '∞'
            }</strong></p>
        `;

        // Limits
        const limitsGrid = document.getElementById('limits-grid');
        const limitNames = {
            channels: 'Каналы', tasks: 'Задачи',
            ai_requests_daily: 'AI запросов/день',
            autopost_daily: 'Автопостов/день',
        };
        limitsGrid.innerHTML = Object.entries(data.limits)
            .filter(([k]) => typeof data.limits[k] === 'number')
            .map(([key, val]) => `
                <div class="limit-item">
                    <div class="limit-name">${limitNames[key] || key}</div>
                    <div class="limit-value">${val === -1 ? '∞' : val}</div>
                </div>
            `).join('');

        // Posts
        const postsContainer = document.getElementById('recent-posts');
        postsContainer.innerHTML = data.recent_posts.map(p => `
            <div class="list-item">
                <div class="title">${p.content}</div>
                <div class="meta">${p.status} ${
                    p.scheduled_at ? '• ' + new Date(p.scheduled_at).toLocaleString('ru') : ''
                }</div>
            </div>
        `).join('') || '<p style="color:var(--text-hint)">Нет постов</p>';

        // Tasks
        const tasksContainer = document.getElementById('recent-tasks');
        tasksContainer.innerHTML = data.recent_tasks.map(t => `
            <div class="list-item">
                <div class="title">${t.title}</div>
                <div class="meta">${t.type} • ${t.status}</div>
            </div>
        `).join('') || '<p style="color:var(--text-hint)">Нет задач</p>';

        // Load analytics
        loadAnalytics();

    } catch (err) {
        console.error('Dashboard load error:', err);
        tg.showAlert('Ошибка загрузки данных');
    }
}

async function loadAnalytics() {
    try {
        const resp = await fetch(`${API_BASE}/api/analytics`, { headers: HEADERS });
        const data = await resp.json();

        document.getElementById('stat-posts').textContent = data.total_posts || 0;
        document.getElementById('stat-published').textContent = data.published_posts || 0;
        document.getElementById('stat-tasks').textContent = data.total_tasks || 0;
    } catch (err) {
        console.error('Analytics error:', err);
    }
}

// === CREATE POST ===
document.getElementById('post-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const content = document.getElementById('post-content').value;
    const schedule = document.getElementById('post-schedule').value;
    const platforms = [...document.querySelectorAll('.checkbox-group input:checked')]
        .map(cb => cb.value);

    if (!content.trim()) {
        tg.showAlert('Введите текст поста');
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/posts`, {
            method: 'POST',
            headers: HEADERS,
            body: JSON.stringify({
                content,
                scheduled_at: schedule || null,
                platforms,
            }),
        });

        if (resp.ok) {
            tg.showAlert('✅ Пост создан!');
            document.getElementById('post-content').value = '';
            document.getElementById('post-schedule').value = '';
            loadDashboard();
        } else {
            const err = await resp.json();
            tg.showAlert(`Ошибка: ${err.error}`);
        }
    } catch (err) {
        tg.showAlert('Ошибка сети');
    }
});

// === THEME ===
tg.onEvent('themeChanged', () => {
    document.documentElement.style.setProperty('--bg-primary', tg.themeParams.bg_color);
    document.documentElement.style.setProperty('--text-primary', tg.themeParams.text_color);
});

// === INIT ===
loadDashboard();