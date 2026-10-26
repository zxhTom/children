const $ = (id) => document.getElementById(id);
const state = { children: [], entries: [], checkups: [], jaundice: [], growth: [], suggestions: [], visits: {}, childId: null, handbookMonth: null, story: null };
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const safeMedia = (url) => /^\/static_uploads\/[a-f0-9]{32}\.(jpg|jpeg|png|gif|webp|mp3|wav|m4a|ogg)$/i.test(url || '') ? url : '';
const today = () => { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`; };
const dateOnly = (value) => String(value || '').slice(0, 10);
const prettyDate = (value) => dateOnly(value).replace(/-/g, '.');
const asDateTime = (value) => value ? `${value}T12:00:00` : null;
const numberOrNull = (id) => $(id).value === '' ? null : Number($(id).value);
const childById = (id) => state.children.find((child) => child.id === Number(id));
const childName = (id) => { const child = childById(id); return child ? (child.nickname || child.name) : '待归档'; };
const selectedChild = () => childById(state.childId);
let toastTimer;

function toast(message, error = false) {
    const node = $('toast');
    node.textContent = message;
    node.classList.toggle('error', error);
    node.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.remove('show'), 3400);
}

async function api(url, options = {}) {
    const response = await fetch(url, options);
    if (response.status === 401 && url !== '/api/login') { location.replace('/login'); throw new Error('登录已过期'); }
    if (!response.ok) {
        let detail = '请求失败，请稍后重试';
        try { const data = await response.json(); if (typeof data.detail === 'string') detail = data.detail; } catch (_) { /* response has no JSON body */ }
        throw new Error(detail);
    }
    return response.json();
}

const jsonOptions = (method, data) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
const queryChild = (item) => state.childId === null || (Array.isArray(item.child_ids) ? item.child_ids.includes(state.childId) : item.child_id === state.childId);

async function allEntries() {
    const entries = [];
    while (true) {
        const page = await api(`/api/entries?skip=${entries.length}&limit=500`);
        entries.push(...page);
        if (page.length < 500) return entries;
    }
}

async function refresh() {
    const children = await api('/api/children');
    state.children = children;
    if (state.childId !== null && !childById(state.childId)) state.childId = null;
    const [entries, checkups, jaundice, growth, suggestions, plans] = await Promise.all([
        allEntries(), api('/api/checkups'), api('/api/jaundice'), api('/api/growth'), api('/api/moments/suggestions'),
        Promise.all(children.map((child) => api(`/api/children/${child.id}/visits`))),
    ]);
    Object.assign(state, { entries, checkups, jaundice, growth, suggestions });
    state.visits = Object.fromEntries(plans.map((plan) => [plan.child_id, plan.visits]));
    render();
}

function optionList() { return state.children.map((child) => `<option value="${child.id}">${esc(child.nickname || child.name)}</option>`).join(''); }
function selectOptions(id) {
    const previous = $(id).value;
    $(id).innerHTML = optionList();
    const editField = { checkupChild: 'checkupEditId', jaundiceChild: 'jaundiceEditId', growthChild: 'growthEditId' }[id];
    if (editField && $(editField).value && previous && childById(previous)) $(id).value = previous;
    else if (state.childId !== null) $(id).value = String(state.childId);
    else if (previous && childById(previous)) $(id).value = previous;
}
function childChecks(id, checkedIds) {
    $(id).innerHTML = state.children.map((child) => `<label class="child-check"><input type="checkbox" value="${child.id}" ${checkedIds.includes(child.id) ? 'checked' : ''}><span>${esc(child.nickname || child.name)}</span></label>`).join('');
}
function checkedChildren(id) { return [...$(id).querySelectorAll('input:checked')].map((input) => Number(input.value)); }
function ageText(birth) {
    const start = new Date(`${birth}T12:00:00`);
    const now = new Date();
    let months = (now.getFullYear() - start.getFullYear()) * 12 + now.getMonth() - start.getMonth();
    if (now.getDate() < start.getDate()) months--;
    if (months < 1) return `出生 ${Math.max(1, Math.floor((now - start) / 86400000) + 1)} 天`;
    if (months < 12) return `${months} 个月`;
    return `${Math.floor(months / 12)} 岁${months % 12 ? ` ${months % 12} 个月` : ''}`;
}
function renderHeader() {
    $('childFilter').innerHTML = `<option value="all">全部宝宝 · 家庭视角</option>${optionList()}`;
    $('childFilter').value = state.childId === null ? 'all' : String(state.childId);
    const child = selectedChild();
    $('heroTitle').textContent = child ? `${child.nickname || child.name}的每一步，都值得珍藏。` : '把每一步成长，留给未来的我们。';
    $('heroSubtitle').textContent = child ? `${child.name} · ${ageText(child.birth_date)} · 出生于 ${prettyDate(child.birth_date)}` : '从第一声笑，到一起长大的每一天，都有地方安放。';
    $('editChildButton').hidden = !child;
    document.documentElement.style.setProperty('--accent', child?.color || '#d97757');
    const entries = state.entries.filter(queryChild);
    $('statEntries').textContent = entries.length;
    $('statMilestones').textContent = entries.filter((entry) => entry.kind === 'milestone').length;
    $('statCheckups').textContent = state.checkups.filter(queryChild).length;
    $('statGrowth').textContent = state.growth.filter(queryChild).length;
}
function empty(icon, message) { return `<div class="empty"><span class="empty-icon">${icon}</span>${esc(message)}</div>`; }
function chips(ids) {
    return ids.length ? ids.map((id) => `<span class="chip">${esc(childName(id))}</span>`).join('') : '<span class="chip">待归档</span>';
}
function editButton(type, id) { return `<button class="minor-button edit-record" type="button" data-edit-record="${type}" data-record-id="${id}">编辑记录 ↗</button>`; }
function renderOverview() {
    const unassigned = state.entries.filter((entry) => !entry.child_ids.length).length + state.checkups.filter((item) => item.child_id === null).length + state.jaundice.filter((item) => item.child_id === null).length;
    $('unassignedBanner').hidden = !unassigned;
    $('unassignedBanner').textContent = unassigned ? `有 ${unassigned} 条旧记录尚未确定归属。请在成长时间轴或健康手册中把它们关联到宝宝。` : '';
    const recent = state.entries.filter(queryChild).slice(0, 3);
    $('overviewMoments').innerHTML = recent.length ? recent.map((entry) => `<article class="moment-card ${entry.kind === 'milestone' ? 'milestone' : ''}"><span class="moment-type">${entry.kind === 'milestone' ? '✦ 关键时刻' : '✎ 成长日记'}</span><h3>${esc(entry.title || (entry.kind === 'milestone' ? '值得纪念的一天' : '今天的故事'))}</h3><p>${esc(entry.content || '一张照片，一段回忆。')}</p><div class="moment-meta"><span>${prettyDate(entry.occurred_at || entry.created_at)}</span><span>${esc(entry.child_ids.map(childName).join(' · ') || '待归档')}</span></div></article>`).join('') : empty('✧', '成长故事从第一条记录开始。');
    $('familyCards').innerHTML = state.children.map((child) => `<button class="family-person" type="button" data-select-child="${child.id}"><span class="avatar" style="background:${child.color}">${esc((child.nickname || child.name).slice(0, 1))}</span><span><strong>${esc(child.nickname || child.name)}</strong><small>${esc(child.name)} · ${ageText(child.birth_date)}</small></span></button>`).join('');
    const planCards = (state.childId === null ? state.children : [selectedChild()]).filter(Boolean).map((child) => {
        const visits = state.visits[child.id] || [];
        const next = visits.find((visit) => visit.status !== 'recorded' && visit.due_date >= today());
        return next ? `<div class="visit-row ${next.status}"><span class="visit-dot"></span><span class="visit-name">${esc(child.nickname || child.name)}</span><span>${esc(next.label)}随访</span><strong>${prettyDate(next.due_date)}</strong></div>` : '';
    }).filter(Boolean);
    $('visitPreview').innerHTML = planCards.length ? planCards.join('') : '<p class="muted">当前没有后续随访时间点，可继续记录医生安排。</p>';
}
function mediaHtml(item) {
    const url = safeMedia(item.media_url);
    if (!url) return '';
    return item.media_type === 'audio' ? `<audio class="timeline-media audio" controls src="${url}"></audio>` : `<img class="timeline-media" src="${url}" alt="成长记录照片" loading="lazy">`;
}

function addBirthMonths(birth, months) {
    const [year, month, day] = birth.split('-').map(Number);
    const target = new Date(year, month - 1 + months, 1, 12);
    target.setDate(Math.min(day, new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate()));
    return `${target.getFullYear()}-${String(target.getMonth() + 1).padStart(2, '0')}-${String(target.getDate()).padStart(2, '0')}`;
}
function ageMonth(birth, day) {
    if (day < birth) return -1;
    const [by, bm] = birth.split('-').map(Number);
    const [dy, dm] = day.split('-').map(Number);
    let months = (dy - by) * 12 + dm - bm;
    if (day < addBirthMonths(birth, months)) months--;
    return months;
}
function chapterLabel(month) {
    if (month < 0) return '出生前';
    if (month < 12) return `出生第 ${month + 1} 个月`;
    return `${Math.floor(month / 12)} 岁${month % 12 ? ` ${month % 12} 个月` : ''}起`;
}
function chapterEvents(child) {
    const items = [];
    state.entries.filter((item) => item.child_ids.includes(child.id)).forEach((item) => items.push({ type: 'entry', date: dateOnly(item.occurred_at || item.created_at), item }));
    state.checkups.filter((item) => item.child_id === child.id).forEach((item) => items.push({ type: 'checkup', date: dateOnly(item.checkup_date), item }));
    state.growth.filter((item) => item.child_id === child.id && !item.checkup_id).forEach((item) => items.push({ type: 'growth', date: dateOnly(item.measured_at), item }));
    state.jaundice.filter((item) => item.child_id === child.id).forEach((item) => items.push({ type: 'jaundice', date: dateOnly(item.record_date), item }));
    return items.map((event) => ({ ...event, month: ageMonth(child.birth_date, event.date) })).sort((a, b) => b.date.localeCompare(a.date) || b.item.id - a.item.id);
}
function handbookEventHtml(event) {
    const item = event.item;
    if (event.type === 'entry') return `<article class="chapter-event"><span class="chapter-event-kind">${item.kind === 'milestone' ? '✦ 关键时刻' : '✎ 成长日记'} · ${prettyDate(event.date)}</span><h3>${esc(item.title || (item.kind === 'milestone' ? '值得纪念的一天' : '这一天的故事'))}</h3>${item.content ? `<p>${esc(item.content)}</p>` : ''}${mediaHtml(item)}${item.child_ids.length > 1 ? '<small>家人共同的记忆</small>' : ''}${editButton('entry', item.id)}</article>`;
    if (event.type === 'checkup') return `<article class="chapter-event"><span class="chapter-event-kind">♡ 体检记录 · ${prettyDate(event.date)}</span><h3>${esc(item.hospital || '一次健康随访')}</h3>${item.report_text ? `<p>${esc(item.report_text)}</p>` : ''}${safeMedia(item.media_url) ? `<img class="timeline-media" src="${safeMedia(item.media_url)}" alt="体检单照片" loading="lazy">` : ''}<div class="record-metrics">${metricPills(item)}</div>${item.next_checkup_date ? `<small>医生建议复查：${prettyDate(item.next_checkup_date)}</small>` : ''}${editButton('checkup', item.id)}</article>`;
    if (event.type === 'jaundice') return `<article class="chapter-event"><span class="chapter-event-kind">♡ 黄疸观察 · ${prettyDate(event.date)}</span><h3>记录数值 ${esc(item.value)}</h3>${item.note ? `<p>${esc(item.note)}</p>` : ''}${editButton('jaundice', item.id)}</article>`;
    return `<article class="chapter-event"><span class="chapter-event-kind">↗ 生长测量 · ${prettyDate(event.date)}</span><h3>一次成长刻度</h3><div class="record-metrics">${metricPills(item)}</div>${item.note ? `<p>${esc(item.note)}</p>` : ''}${editButton('growth', item.id)}</article>`;
}
function renderHandbook() {
    const root = $('handbookContent');
    const child = selectedChild();
    if (!child) {
        root.innerHTML = state.children.length ? `<div class="handbook-pick surface"><h3>先翻开一本宝宝的手册</h3><p class="muted">选择宝宝后，就能按月龄回看那些被记录下来的日子。</p><div class="handbook-pick-list">${state.children.map((item) => `<button class="button soft" type="button" data-handbook-child="${item.id}">${esc(item.nickname || item.name)}的手册 →</button>`).join('')}</div></div>` : empty('✧', '先添加宝宝档案，再开始一本成长手册。');
        return;
    }
    const events = chapterEvents(child);
    const chapterSizes = new Map();
    events.forEach((event) => chapterSizes.set(event.month, (chapterSizes.get(event.month) || 0) + 1));
    const currentMonth = Math.max(0, ageMonth(child.birth_date, today()));
    const months = [...new Set([...events.map((event) => event.month), currentMonth])].sort((a, b) => b - a);
    if (!months.includes(state.handbookMonth)) state.handbookMonth = currentMonth;
    const month = state.handbookMonth;
    const chapter = events.filter((event) => event.month === month);
    const start = month < 0 ? null : addBirthMonths(child.birth_date, month);
    const end = month < 0 ? child.birth_date : addBirthMonths(child.birth_date, month + 1);
    const counts = { entry: chapter.filter((event) => event.type === 'entry').length, checkup: chapter.filter((event) => event.type === 'checkup').length, growth: chapter.filter((event) => event.type === 'growth').length, jaundice: chapter.filter((event) => event.type === 'jaundice').length };
    root.innerHTML = `<div class="handbook-layout"><aside class="surface handbook-index"><span class="kicker">CHAPTER INDEX</span><h3>${esc(child.nickname || child.name)}的章节</h3><p class="muted">显示有记录的月份和当前月龄。</p><div class="chapter-index-list">${months.map((value) => `<button class="chapter-index-item ${value === month ? 'active' : ''}" type="button" data-chapter-month="${value}" aria-current="${value === month ? 'page' : 'false'}"><span>${esc(chapterLabel(value))}</span><small>${chapterSizes.has(value) ? `${chapterSizes.get(value)} 条` : '待记录'}</small></button>`).join('')}</div></aside><div class="handbook-page"><div class="chapter-cover"><span class="kicker">${esc(child.nickname || child.name)} · GROWING DAYS</span><h2>${esc(chapterLabel(month))}</h2><p>${month < 0 ? `出生于 ${prettyDate(child.birth_date)} 之前` : `${prettyDate(start)} — ${prettyDate(end)} 前`}</p><div class="chapter-counts"><span>${counts.entry} 段回忆</span><span>${counts.checkup} 次体检</span><span>${counts.growth} 次家庭测量</span>${counts.jaundice ? `<span>${counts.jaundice} 条黄疸观察</span>` : ''}</div></div><div class="chapter-actions"><button class="button soft" type="button" data-chapter-write>写一段回忆</button><button class="button ghost" type="button" data-chapter-story>用本章生成故事 ↗</button></div><div class="chapter-event-list">${chapter.length ? chapter.map(handbookEventHtml).join('') : empty('✎', '这一章还没有记录。写下一个真实的瞬间，手册就会多一页。')}</div></div></div>`;
}
function renderTimeline(preserveSelection = false) {
    const chosen = preserveSelection || $('entryEditId').value ? checkedChildren('entryChildren') : state.childId === null ? [] : [state.childId];
    childChecks('entryChildren', chosen);
    renderPrompts();
    const filter = $('entryKindFilter').value;
    const entries = state.entries.filter(queryChild).filter((entry) => filter === 'all' || entry.kind === filter);
    $('timelineList').innerHTML = entries.length ? entries.map((entry) => `<article class="timeline-item ${entry.kind === 'milestone' ? 'milestone' : ''}"><div class="timeline-card ${entry.kind === 'milestone' ? 'milestone' : ''}"><div class="timeline-head"><div><span class="kicker">${entry.kind === 'milestone' ? '✦ KEY MOMENT' : 'DAILY NOTE'} · ${prettyDate(entry.occurred_at || entry.created_at)}</span><h3>${esc(entry.title || (entry.kind === 'milestone' ? '关键时刻' : '成长日记'))}</h3></div><span class="small-meta">${esc(entry.author || '家人')} 记录</span></div><p>${esc(entry.content || '')}</p>${mediaHtml(entry)}<div class="tagline">${chips(entry.child_ids)}${entry.child_ids.length > 1 ? '<span class="chip shared">共同的记忆</span>' : ''}<button class="minor-button" type="button" data-assign-entry="${entry.id}">关联宝宝 ↗</button>${editButton('entry', entry.id)}</div></div></article>`).join('') : empty('✎', '这里还没有记录。写下今天，故事就开始了。');
}
function renderPrompts() {
    const child = childById(checkedChildren('entryChildren')[0]);
    let prompts = ['今天谁陪着宝宝？', '有什么想对未来说的话？'];
    if (child) {
        const years = (new Date() - new Date(`${child.birth_date}T12:00:00`)) / (365.25 * 86400000);
        prompts = years < 1 ? ['今天的新表情或声音？', '第一次一起做了什么？'] : years < 3 ? ['最近学会了什么新词或动作？', '和家人一起的趣事？'] : ['今天最自豪的一件事？', '新朋友、新爱好或新尝试？'];
    }
    $('recordPrompts').innerHTML = `<strong>记录灵感</strong>${prompts.map((prompt) => `<span>${esc(prompt)}</span>`).join('')}`;
}
function assignHealthHtml(type, item) {
    if (item.child_id !== null) return `<span class="chip">${esc(childName(item.child_id))}</span>`;
    return `<select class="small-select assign-health-select" aria-label="选择归档宝宝">${optionList()}</select><button class="minor-button" type="button" data-assign-health="${type}" data-record-id="${item.id}">归档</button>`;
}
function metricPills(item) {
    return [['weight_kg', '体重', 'kg'], ['height_cm', '身高', 'cm'], ['head_cm', '头围', 'cm']].filter(([key]) => item[key] !== null && item[key] !== undefined).map(([key, label, unit]) => `<span class="metric-pill">${label} <strong>${esc(item[key])}</strong> ${unit}</span>`).join('');
}
function renderHealth() {
    ['checkupChild', 'jaundiceChild'].forEach(selectOptions);
    const checkups = state.checkups.filter(queryChild);
    $('checkupList').innerHTML = checkups.length ? checkups.map((item) => `<article class="record"><div class="record-head"><div><span class="kicker">${prettyDate(item.checkup_date)}</span><h3>${esc(item.hospital || '体检记录')}</h3></div><div class="tagline">${assignHealthHtml('checkups', item)}</div></div>${item.report_text ? `<p>${esc(item.report_text)}</p>` : ''}${item.abnormal_indicators ? `<p class="followup">旧版自动分析记录：${esc(item.abnormal_indicators)}</p>` : ''}${safeMedia(item.media_url) ? `<img class="timeline-media" src="${safeMedia(item.media_url)}" alt="体检单照片" loading="lazy">` : ''}<div class="record-metrics">${metricPills(item)}</div>${item.next_checkup_date ? `<p class="followup">医生建议复查：${prettyDate(item.next_checkup_date)} ${esc(item.next_checkup_notes || '')}</p>` : ''}${editButton('checkup', item.id)}</article>`).join('') : empty('♡', '还没有体检记录。');
    const child = selectedChild();
    $('visitPlan').innerHTML = child ? (state.visits[child.id] || []).map((visit) => `<div class="plan-item ${visit.status}"><span class="plan-marker"></span><span><strong>${esc(visit.label)}</strong><small>${prettyDate(visit.due_date)}</small></span><em>${visit.status === 'recorded' ? '已记录' : visit.status === 'pending' ? '待核对' : '将到来'}</em></div>`).join('') : '<p class="muted">选择一个宝宝，查看按出生日期排列的随访节点。</p>';
    const jaundice = state.jaundice.filter(queryChild);
    $('jaundiceList').innerHTML = jaundice.slice(-6).reverse().map((item) => `<div class="compact-record"><span>${prettyDate(item.record_date)} · ${esc(childName(item.child_id))} ${esc(item.note || '')}</span><strong>${esc(item.value)}</strong>${item.child_id === null ? assignHealthHtml('jaundice', item) : ''}${editButton('jaundice', item.id)}</div>`).join('');
    $('jaundiceChart').innerHTML = child ? lineChart(jaundice, 'record_date', 'value', '#d0a054', '') : '<div class="chart-empty">选择宝宝后查看黄疸记录趋势</div>';
}
function lineChart(items, dateKey, valueKey, color, unit) {
    const values = items.filter((item) => item[valueKey] !== null && item[valueKey] !== undefined).sort((a, b) => String(a[dateKey]).localeCompare(String(b[dateKey])));
    if (!values.length) return '<div class="chart-empty">暂无测量数据</div>';
    const width = 640, height = 225, left = 52, right = 18, top = 18, bottom = 38;
    const numbers = values.map((item) => Number(item[valueKey]));
    const min = Math.min(...numbers), max = Math.max(...numbers);
    const padding = Math.max((max - min) * .18, max < 20 ? .4 : 1);
    const low = Math.max(0, min - padding), high = max + padding;
    const x = (index) => left + (values.length === 1 ? (width - left - right) / 2 : index * (width - left - right) / (values.length - 1));
    const y = (value) => top + (high - value) * (height - top - bottom) / (high - low);
    const points = values.map((item, index) => `${x(index).toFixed(1)},${y(Number(item[valueKey])).toFixed(1)}`).join(' ');
    const grid = [0, 1, 2, 3].map((step) => { const yy = top + step * (height - top - bottom) / 3; const label = (high - step * (high - low) / 3).toFixed(1); return `<line x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}" stroke="#e9ebe7"/><text x="${left - 8}" y="${yy + 4}" text-anchor="end" fill="#99a4a5" font-size="11">${label}</text>`; }).join('');
    const circles = values.map((item, index) => `<circle cx="${x(index).toFixed(1)}" cy="${y(Number(item[valueKey])).toFixed(1)}" r="5" fill="${color}" stroke="#fff" stroke-width="2"><title>${esc(prettyDate(item[dateKey]))}: ${esc(item[valueKey])}${esc(unit)}</title></circle>`).join('');
    const labels = `<text x="${x(0)}" y="${height - 9}" text-anchor="middle" fill="#99a4a5" font-size="11">${esc(prettyDate(values[0][dateKey]))}</text>${values.length > 1 ? `<text x="${x(values.length - 1)}" y="${height - 9}" text-anchor="middle" fill="#99a4a5" font-size="11">${esc(prettyDate(values.at(-1)[dateKey]))}</text>` : ''}`;
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(unit || '数值')}趋势，共${values.length}个数据点">${grid}<polyline points="${points}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${circles}${labels}</svg>`;
}
function renderGrowth() {
    selectOptions('growthChild');
    const rows = state.growth.filter(queryChild);
    $('growthList').innerHTML = rows.length ? [...rows].reverse().map((item) => `<article class="record"><div class="record-head"><div><span class="kicker">${prettyDate(item.measured_at)}</span><h3>${esc(childName(item.child_id))}的生长记录</h3></div><span class="chip">${item.checkup_id ? '来自体检' : '家人测量'}</span></div><div class="record-metrics">${metricPills(item)}</div>${item.note ? `<p>${esc(item.note)}</p>` : ''}${editButton(item.checkup_id ? 'checkup' : 'growth', item.checkup_id || item.id)}</article>`).join('') : empty('↗', '还没有测量记录。');
    $('growthChart').innerHTML = selectedChild() ? lineChart(rows, 'measured_at', $('growthMetric').value, '#c9785d', $('growthMetric').selectedOptions[0].textContent.split('·').at(-1).trim()) : '<div class="chart-empty">请在页面上方选择一个宝宝，查看专属生长曲线</div>';
}
function renderStoryForm() { childChecks('storyChildren', state.story ? state.story.children.map((child) => child.id) : state.childId === null ? state.children.map((child) => child.id) : [state.childId]); }
function renderSuggestions() {
    const suggestions = state.suggestions.filter(queryChild).slice(0, 5);
    $('suggestionsBlock').hidden = !suggestions.length;
    $('suggestionList').innerHTML = suggestions.map((item) => `<div class="suggestion-row"><div><strong>${esc(item.title)}</strong><small>${prettyDate(item.occurred_at)} · ${esc(item.reason)} · ${esc(item.child_ids.map(childName).join('、'))}</small></div><button class="minor-button" type="button" data-promote-entry="${item.id}">标记为关键时刻 →</button></div>`).join('');
}
function storyHealthHtml(story) {
    if (!story.health_notes?.length) return '';
    const notes = story.health_notes.map((item) => {
        const values = item.latest ? [
            item.latest.weight_kg == null ? '' : `体重 ${item.latest.weight_kg} kg`,
            item.latest.height_cm == null ? '' : `身高 ${item.latest.height_cm} cm`,
            item.latest.head_cm == null ? '' : `头围 ${item.latest.head_cm} cm`,
        ].filter(Boolean).join(' · ') : '';
        return `<div class="story-health-card"><strong>${esc(item.name)}</strong><span>${item.checkups} 次体检 · ${item.measurements} 次测量</span>${values ? `<small>${prettyDate(item.latest.date)} · ${esc(values)}</small>` : ''}</div>`;
    }).join('');
    return `<section class="story-health"><h3>手册里的成长刻度</h3><p>以下数据来自所选时间内的体检与测量记录。</p><div class="story-health-grid">${notes}</div></section>`;
}
function storyHtml(story) {
    const subtitle = story.children.map((child) => child.nickname || child.name).join(' · ');
    return `<article class="story-preview"><div class="story-cover"><div class="ornament">✳</div><span class="kicker">OUR GROWING DAYS</span><h2>${esc(story.title)}</h2><p>${esc(subtitle)} · ${story.from_date ? prettyDate(story.from_date) : '从最初'} — ${story.to_date ? prettyDate(story.to_date) : '到今天'}</p><div class="story-stats"><span>${story.stats.records} 段记录</span><span>${story.stats.milestones} 个关键时刻</span><span>${story.stats.shared} 段共同回忆</span></div></div><p class="story-summary">${esc(story.summary)}</p>${storyHealthHtml(story)}${story.sections.map((section) => `<section class="story-section"><h3>${esc(section.period)}</h3>${section.moments.map((moment) => `<div class="story-moment"><span class="date">${prettyDate(moment.date)} · ${moment.kind === 'milestone' ? '✦ 关键时刻' : '成长日记'}</span><h4>${esc(moment.title)}</h4><p>${esc(moment.content)}</p>${mediaHtml(moment)}<small>${esc(moment.children.map((child) => `${child.name} · ${child.age}`).join(' / '))} · ${esc(moment.author)}记录</small></div>`).join('')}</section>`).join('')}<div class="story-end">✦ · ✦ · ✦</div></article>`;
}
function renderStory() {
    renderStoryForm();
    renderSuggestions();
    $('storyEmpty').hidden = Boolean(state.story);
    $('storyResult').hidden = !state.story;
    $('storyPreview').innerHTML = state.story ? storyHtml(state.story) : '';
    $('printRoot').innerHTML = $('storyPreview').innerHTML;
}
function render() { renderHeader(); renderOverview(); renderHandbook(); renderTimeline(); renderHealth(); renderGrowth(); renderStory(); }
function switchTab(name) {
    document.querySelectorAll('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === name));
    document.querySelectorAll('.panel').forEach((panel) => panel.classList.toggle('active', panel.id === `panel-${name}`));
    document.querySelector('.tabs').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
async function upload(file) {
    if (!file) return null;
    const form = new FormData();
    form.append('file', file);
    return api('/api/upload', { method: 'POST', body: form });
}
async function submitForm(event, work) {
    event.preventDefault();
    const button = event.submitter || event.target.querySelector('button[type=submit]');
    if (button) button.disabled = true;
    try { await work(); } catch (error) { toast(error.message || '操作失败', true); } finally { if (button) button.disabled = false; }
}
function resetFile(inputId, labelId) { $(inputId).value = ''; $(labelId).textContent = ''; }
const editForms = {
    entry: { form: 'entryForm', edit: 'entryEditId', date: 'entryDate', notice: 'entryEditNotice', save: 'entrySaveButton', create: '保存这段记忆', update: '保存修改', tab: 'timeline' },
    checkup: { form: 'checkupForm', edit: 'checkupEditId', date: 'checkupDate', notice: 'checkupEditNotice', save: 'checkupSaveButton', title: 'checkupFormTitle', create: '保存体检', update: '保存修改', tab: 'health' },
    jaundice: { form: 'jaundiceForm', edit: 'jaundiceEditId', date: 'jaundiceDate', notice: 'jaundiceEditNotice', save: 'jaundiceSaveButton', create: '＋ 添加观察', update: '保存修改', tab: 'health' },
    growth: { form: 'growthForm', edit: 'growthEditId', date: 'growthDate', notice: 'growthEditNotice', save: 'growthSaveButton', title: 'growthFormTitle', create: '保存测量', update: '保存修改', tab: 'growth' },
};
function cancelEdit(type) {
    const config = editForms[type];
    $(config.form).reset();
    $(config.edit).value = '';
    $(config.date).value = today();
    $(config.notice).hidden = true;
    $(config.save).textContent = config.create;
    if (config.title) $(config.title).textContent = type === 'checkup' ? '新增体检记录' : '添加一次测量';
    document.querySelector(`[data-cancel-edit="${type}"]`).hidden = true;
    if (type === 'entry') { resetFile('entryMedia', 'entryFileName'); $('entryRemoveMediaWrap').hidden = true; childChecks('entryChildren', state.childId === null ? [] : [state.childId]); renderPrompts(); }
    if (type === 'checkup') { resetFile('checkupMedia', 'checkupFileName'); $('checkupRemoveMediaWrap').hidden = true; }
}
function openRecordEdit(type, id) {
    const records = { entry: state.entries, checkup: state.checkups, jaundice: state.jaundice, growth: state.growth }[type];
    const item = records?.find((record) => record.id === id);
    if (!item) return toast('这条记录未找到，请刷新后重试', true);
    if (type === 'growth' && item.checkup_id) return openRecordEdit('checkup', item.checkup_id);
    cancelEdit(type);
    const config = editForms[type];
    $(config.edit).value = String(id);
    $(config.notice).hidden = false;
    $(config.save).textContent = config.update;
    if (config.title) $(config.title).textContent = type === 'checkup' ? '修改体检记录' : '修改家庭测量';
    document.querySelector(`[data-cancel-edit="${type}"]`).hidden = false;
    if (type === 'entry') {
        $('entryKind').value = item.kind;
        $('entryDate').value = dateOnly(item.occurred_at || item.created_at);
        $('entryAuthor').value = item.author || '家人';
        $('entryTitle').value = item.title || '';
        $('entryContent').value = item.content || '';
        $('entryRemoveMediaWrap').hidden = !item.media_url;
        childChecks('entryChildren', item.child_ids);
        renderPrompts();
    } else if (type === 'checkup') {
        $('checkupChild').value = item.child_id == null ? $('checkupChild').value : String(item.child_id);
        $('checkupDate').value = dateOnly(item.checkup_date);
        $('checkupHospital').value = item.hospital || '';
        $('checkupWeight').value = item.weight_kg ?? '';
        $('checkupHeight').value = item.height_cm ?? '';
        $('checkupHead').value = item.head_cm ?? '';
        $('checkupNotes').value = item.report_text || '';
        $('checkupNext').value = dateOnly(item.next_checkup_date);
        $('checkupNextNotes').value = item.next_checkup_notes || '';
        $('checkupRemoveMediaWrap').hidden = !item.media_url;
    } else if (type === 'jaundice') {
        $('jaundiceChild').value = item.child_id == null ? $('jaundiceChild').value : String(item.child_id);
        $('jaundiceDate').value = dateOnly(item.record_date);
        $('jaundiceValue').value = item.value;
        $('jaundiceNote').value = item.note || '';
    } else {
        $('growthChild').value = String(item.child_id);
        $('growthDate').value = dateOnly(item.measured_at);
        $('growthWeight').value = item.weight_kg ?? '';
        $('growthHeight').value = item.height_cm ?? '';
        $('growthHead').value = item.head_cm ?? '';
        $('growthNote').value = item.note || '';
    }
    switchTab(config.tab);
    $(config.form).scrollIntoView({ behavior: 'smooth', block: 'start' });
    $(config.date).focus({ preventScroll: true });
}
function bindEvents() {
    document.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => switchTab(tab.dataset.tab)));
    document.querySelectorAll('[data-go]').forEach((button) => button.addEventListener('click', () => switchTab(button.dataset.go)));
    $('childFilter').addEventListener('change', (event) => { state.childId = event.target.value === 'all' ? null : Number(event.target.value); state.handbookMonth = null; state.story = null; render(); });
    $('heroAddMoment').addEventListener('click', () => { switchTab('timeline'); $('entryTitle').focus(); });
    $('heroMakeStory').addEventListener('click', () => switchTab('story'));
    $('addChildButton').addEventListener('click', () => openChildDialog());
    $('familyAddChild').addEventListener('click', () => openChildDialog());
    $('editChildButton').addEventListener('click', () => openChildDialog(selectedChild()));
    $('logoutButton').addEventListener('click', async () => { try { await api('/api/logout', { method: 'POST' }); } finally { location.replace('/login'); } });
    document.querySelectorAll('[data-close]').forEach((button) => button.addEventListener('click', () => $(button.dataset.close).close()));
    document.querySelectorAll('[data-cancel-edit]').forEach((button) => button.addEventListener('click', () => cancelEdit(button.dataset.cancelEdit)));
    $('entryKindFilter').addEventListener('change', () => renderTimeline(true));
    $('entryChildren').addEventListener('change', renderPrompts);
    $('growthMetric').addEventListener('change', renderGrowth);
    ['entryMedia', 'checkupMedia'].forEach((id) => $(id).addEventListener('change', () => $(`${id === 'entryMedia' ? 'entry' : 'checkup'}FileName`).textContent = $(id).files[0]?.name || ''));
    $('entryForm').addEventListener('submit', (event) => submitForm(event, saveEntry));
    $('checkupForm').addEventListener('submit', (event) => submitForm(event, saveCheckup));
    $('jaundiceForm').addEventListener('submit', (event) => submitForm(event, saveJaundice));
    $('growthForm').addEventListener('submit', (event) => submitForm(event, saveGrowth));
    $('storyForm').addEventListener('submit', (event) => submitForm(event, generateStory));
    $('childForm').addEventListener('submit', (event) => submitForm(event, saveChild));
    $('assignForm').addEventListener('submit', (event) => submitForm(event, saveAssignment));
    $('printStory').addEventListener('click', () => window.print());
    document.body.addEventListener('click', async (event) => {
        const editor = event.target.closest('[data-edit-record]');
        if (editor) { openRecordEdit(editor.dataset.editRecord, Number(editor.dataset.recordId)); return; }
        const childButton = event.target.closest('[data-select-child]');
        if (childButton) { state.childId = Number(childButton.dataset.selectChild); state.handbookMonth = null; state.story = null; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); }
        const handbookChild = event.target.closest('[data-handbook-child]');
        if (handbookChild) { state.childId = Number(handbookChild.dataset.handbookChild); state.handbookMonth = null; state.story = null; render(); }
        const chapterButton = event.target.closest('[data-chapter-month]');
        if (chapterButton) { state.handbookMonth = Number(chapterButton.dataset.chapterMonth); renderHandbook(); }
        if (event.target.closest('[data-chapter-write]')) { switchTab('timeline'); $('entryTitle').focus(); }
        if (event.target.closest('[data-chapter-story]')) {
            const child = selectedChild();
            const month = state.handbookMonth;
            if (child && month !== null) {
                $('storyFrom').value = month < 0 ? '' : addBirthMonths(child.birth_date, month);
                const end = month < 0 ? child.birth_date : addBirthMonths(child.birth_date, month + 1);
                const lastDay = new Date(`${end}T12:00:00`); lastDay.setDate(lastDay.getDate() - 1);
                $('storyTo').value = `${lastDay.getFullYear()}-${String(lastDay.getMonth() + 1).padStart(2, '0')}-${String(lastDay.getDate()).padStart(2, '0')}`;
                $('storyTitle').value = '';
                state.story = null; switchTab('story'); renderStoryForm();
                try { await generateStory(); } catch (error) { toast(error.message || '故事生成失败', true); }
            }
        }
        const assignment = event.target.closest('[data-assign-entry]');
        if (assignment) openAssignDialog(Number(assignment.dataset.assignEntry));
        const promote = event.target.closest('[data-promote-entry]');
        if (promote) {
            try { await api(`/api/entries/${promote.dataset.promoteEntry}`, jsonOptions('PATCH', { kind: 'milestone' })); state.story = null; await refresh(); toast('已加入关键时刻'); } catch (error) { toast(error.message, true); }
        }
        const health = event.target.closest('[data-assign-health]');
        if (health) {
            const select = health.parentElement.querySelector('select');
            try { await api(`/api/${health.dataset.assignHealth}/${health.dataset.recordId}`, jsonOptions('PATCH', { child_id: Number(select.value) })); await refresh(); toast('已归档到宝宝'); } catch (error) { toast(error.message, true); }
        }
    });
}
async function saveEntry() {
    const id = $('entryEditId').value;
    const childIds = checkedChildren('entryChildren');
    if (!childIds.length) throw new Error('请至少选择一个宝宝');
    const media = await upload($('entryMedia').files[0]);
    const payload = { child_ids: childIds, kind: $('entryKind').value, title: $('entryTitle').value.trim() || null, author: $('entryAuthor').value.trim() || '家人', content: $('entryContent').value.trim(), occurred_at: asDateTime($('entryDate').value) };
    if (media) { payload.media_url = media.media_url; payload.media_type = media.media_type; }
    else if (!id || $('entryRemoveMedia').checked) { payload.media_url = null; payload.media_type = null; }
    await api(id ? `/api/entries/${id}` : '/api/entries', jsonOptions(id ? 'PATCH' : 'POST', payload));
    cancelEdit('entry'); state.story = null;
    await refresh(); toast(id ? '成长记录已修改' : '这段成长记忆已保存');
}
async function saveCheckup() {
    const id = $('checkupEditId').value;
    const media = await upload($('checkupMedia').files[0]);
    const payload = { child_id: Number($('checkupChild').value), checkup_date: asDateTime($('checkupDate').value), hospital: $('checkupHospital').value.trim() || null, report_text: $('checkupNotes').value.trim() || null, next_checkup_date: asDateTime($('checkupNext').value), next_checkup_notes: $('checkupNextNotes').value.trim() || null, weight_kg: numberOrNull('checkupWeight'), height_cm: numberOrNull('checkupHeight'), head_cm: numberOrNull('checkupHead') };
    if (media) payload.media_url = media.media_url;
    else if (!id || $('checkupRemoveMedia').checked) payload.media_url = null;
    await api(id ? `/api/checkups/${id}` : '/api/checkups', jsonOptions(id ? 'PATCH' : 'POST', payload));
    cancelEdit('checkup'); state.story = null; await refresh(); toast(id ? '体检与曲线已更新' : '体检与测量已保存');
}
async function saveJaundice() {
    const id = $('jaundiceEditId').value;
    await api(id ? `/api/jaundice/${id}` : '/api/jaundice', jsonOptions(id ? 'PATCH' : 'POST', { child_id: Number($('jaundiceChild').value), record_date: asDateTime($('jaundiceDate').value), value: Number($('jaundiceValue').value), note: $('jaundiceNote').value.trim() || null }));
    cancelEdit('jaundice'); await refresh(); toast(id ? '黄疸观察已修改' : '黄疸观察已保存');
}
async function saveGrowth() {
    const id = $('growthEditId').value;
    const payload = { child_id: Number($('growthChild').value), measured_at: asDateTime($('growthDate').value), weight_kg: numberOrNull('growthWeight'), height_cm: numberOrNull('growthHeight'), head_cm: numberOrNull('growthHead'), note: $('growthNote').value.trim() || null };
    if ([payload.weight_kg, payload.height_cm, payload.head_cm].every((value) => value === null)) throw new Error('至少填写一项测量值');
    await api(id ? `/api/growth/${id}` : '/api/growth', jsonOptions(id ? 'PATCH' : 'POST', payload));
    cancelEdit('growth'); state.story = null; await refresh(); toast(id ? '测量记录已修改' : '测量记录已保存');
}
async function generateStory() {
    const ids = checkedChildren('storyChildren');
    if (!ids.length) throw new Error('请选择故事里的宝宝');
    state.story = await api('/api/stories/generate', jsonOptions('POST', { child_ids: ids, from_date: $('storyFrom').value || null, to_date: $('storyTo').value || null, title: $('storyTitle').value.trim() || null }));
    renderStory(); toast('成长故事已生成');
    $('storyResult').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function openChildDialog(child = null) {
    $('childForm').reset(); $('childEditId').value = child?.id || '';
    $('childDialogTitle').textContent = child ? '编辑宝宝档案' : '添加宝宝档案';
    $('childName').value = child?.name || '';
    $('childNickname').value = child?.nickname || '';
    $('childBirthDate').value = child?.birth_date || '';
    $('childColor').value = child?.color || '#d97757';
    $('childDialog').showModal();
}
async function saveChild() {
    const id = $('childEditId').value;
    const payload = { name: $('childName').value.trim(), nickname: $('childNickname').value.trim() || null, birth_date: $('childBirthDate').value, color: $('childColor').value };
    const child = await api(id ? `/api/children/${id}` : '/api/children', jsonOptions(id ? 'PATCH' : 'POST', payload));
    state.childId = child.id;
    state.handbookMonth = null;
    $('childDialog').close(); await refresh(); toast(id ? '宝宝档案已更新' : '宝宝档案已创建');
}
function openAssignDialog(entryId) {
    const entry = state.entries.find((item) => item.id === entryId);
    if (!entry) return;
    $('assignEntryId').value = entryId;
    $('assignDescription').textContent = entry.title || entry.content.slice(0, 55) || '这段成长记忆';
    childChecks('assignChildren', entry.child_ids);
    $('assignDialog').showModal();
}
async function saveAssignment() {
    const childIds = checkedChildren('assignChildren');
    if (!childIds.length) throw new Error('请至少选择一个宝宝');
    await api(`/api/entries/${$('assignEntryId').value}`, jsonOptions('PATCH', { child_ids: childIds }));
    $('assignDialog').close(); state.story = null; await refresh(); toast('宝宝关联已更新');
}

document.addEventListener('DOMContentLoaded', async () => {
    ['entryDate', 'checkupDate', 'jaundiceDate', 'growthDate'].forEach((id) => $(id).value = today());
    bindEvents();
    try { await refresh(); } catch (error) { toast(error.message || '加载失败', true); }
});
