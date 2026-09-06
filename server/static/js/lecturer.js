/** Lecturer web dashboard UI */
const LecturerUI = {
    topics: [],
    questions: [],
    tests: [],
    allQuestions: [],
    groups: [],
    statsState: {
        view: 'overview',
        testId: null,
        studentId: null,
        focusTestId: null,
        compareTestId: null,
        groupFilter: '',
        testFilters: { q: '', mode: '', status: 'all', sort: 'date' },
        studentSearch: '',
    },
    _statsCharts: [],
    GROUP_CHART_COLORS: ['#667eea', '#764ba2', '#20c997', '#f0ad4e', '#dc3545', '#6c757d', '#0dcaf0', '#fd7e14'],

    async api(method, endpoint, data) {
        const opts = { method, credentials: 'include', headers: {} };
        if (data !== undefined) {
            if (data instanceof FormData) {
                opts.body = data;
            } else {
                opts.headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify(data);
            }
        }
        const res = await fetch(endpoint, opts);
        const json = hasJsonResponse(res) ? await res.json() : null;
        if (!res.ok) throw new Error(apiError(json, res.status));
        return json;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = coalesce(text, '');
        return div.innerHTML;
    },

    tableHtml(headers, rows) {
        if (!rows.length) return '<div class="alert alert-info">No items found.</div>';
        return `<div class="table-responsive"><table class="table table-hover">
            <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
            <tbody>${rows.join('')}</tbody></table></div>`;
    },

    isoToLocalDatetime(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        const pad = n => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    },

    localDatetimeToISO(localValue) {
        if (!localValue) return null;
        return new Date(localValue).toISOString();
    },

    formatDatetime(iso) {
        if (!iso) return '-';
        return new Date(iso).toLocaleString();
    },

    async init() {
        try {
            const me = await this.api('GET', '/api/v1/auth/me');
            if (me.role !== 'lecturer') { window.location.href = '/lecturer/login'; return; }
        } catch (e) {
            window.location.href = '/lecturer/login';
            return;
        }

        await this.loadTopics();
        await this.loadQuestions();
        document.getElementById('topicFilter').addEventListener('change', () => this.loadQuestions());

        var testsTab = document.querySelector('[data-bs-target="#testsTab"]');
        if (testsTab) testsTab.addEventListener('shown.bs.tab', () => {
            this.loadTests();
            if (this._testsPoll) clearInterval(this._testsPoll);
            this._testsPoll = setInterval(() => this.loadTests(), 5000);
        });
        var questionsTab = document.querySelector('[data-bs-target="#questionsTab"]');
        if (questionsTab) questionsTab.addEventListener('shown.bs.tab', () => {
            if (this._testsPoll) { clearInterval(this._testsPoll); this._testsPoll = null; }
        });
        var gradingTab = document.querySelector('[data-bs-target="#gradingTab"]');
        if (gradingTab) gradingTab.addEventListener('shown.bs.tab', () => this.loadGrading());
        var statisticsTab = document.querySelector('[data-bs-target="#statisticsTab"]');
        if (statisticsTab) statisticsTab.addEventListener('shown.bs.tab', () => this.loadStatistics());
        var groupsTab = document.querySelector('[data-bs-target="#groupsTab"]');
        if (groupsTab) groupsTab.addEventListener('shown.bs.tab', () => this.loadGroups());
        var studentsTab = document.querySelector('[data-bs-target="#studentsTab"]');
        if (studentsTab) studentsTab.addEventListener('shown.bs.tab', () => this.loadStudents());
        await this.loadGroups();
    },

    // --- Topics ---
    async loadTopics() {
        this.topics = await this.api('GET', '/api/v1/topics');
        const filter = document.getElementById('topicFilter');
        filter.innerHTML = '<option value="">All Topics</option>' +
            this.topics.map(t => `<option value="${t.id}">${this.escapeHtml(t.name)}</option>`).join('');
        const qTopic = document.getElementById('questionTopic');
        if (qTopic) qTopic.innerHTML = this.topics.map(t => `<option value="${t.id}">${this.escapeHtml(t.name)}</option>`).join('');
    },

    showTopicsModal() {
        this.renderTopicsList();
        new bootstrap.Modal(document.getElementById('topicsModal')).show();
    },

    renderTopicsList() {
        document.getElementById('topicsList').innerHTML = this.topics.length
            ? this.topics.map(t => `<div class="d-flex justify-content-between align-items-center border-bottom py-2">
                <span>${this.escapeHtml(t.name)}</span>
                <button class="btn btn-sm btn-outline-danger" onclick="LecturerUI.deleteTopic(${t.id})">Delete</button>
            </div>`).join('')
            : '<p class="text-muted">No topics yet.</p>';
    },

    async addTopic() {
        const name = document.getElementById('newTopicName').value.trim();
        if (!name) return alert('Enter a topic name');
        try {
            await this.api('POST', '/api/v1/topics', { name });
            document.getElementById('newTopicName').value = '';
            await this.loadTopics();
            this.renderTopicsList();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async deleteTopic(id) {
        if (!confirm('Delete this topic?')) return;
        try {
            await this.api('DELETE', `/api/v1/topics/${id}`);
            await this.loadTopics();
            await this.loadQuestions();
            this.renderTopicsList();
        } catch (e) { alert('Error: ' + e.message); }
    },

    // --- Questions ---
    async loadQuestions() {
        const topicId = document.getElementById('topicFilter').value;
        const url = topicId ? `/api/v1/questions?topic_id=${topicId}` : '/api/v1/questions';
        this.questions = await this.api('GET', url);
        this.renderQuestions();
    },

    renderQuestions() {
        const topicMap = Object.fromEntries(this.topics.map(t => [t.id, t.name]));
        const rows = this.questions.map(q => {
            const preview = q.content.length > 80 ? q.content.slice(0, 80) + '...' : q.content;
            const typeLabel = (q.answer_types && q.answer_types.length > 1)
                ? q.answer_types.map(t => t.replace('_', ' ')).join(' + ')
                : (q.type_label || q.type);
            return `<tr>
                <td>${q.id}</td>
                <td>${this.escapeHtml(topicMap[q.topic_id] || '?')}</td>
                <td><span class="badge bg-secondary">${this.escapeHtml(typeLabel)}</span></td>
                <td class="question-content-preview" title="${this.escapeHtml(q.content)}">${this.escapeHtml(preview)}</td>
                <td>${q.points}</td>
                <td class="table-actions">
                    <button class="btn btn-sm btn-outline-primary" onclick="LecturerUI.showQuestionModal(${q.id})">Edit</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="LecturerUI.deleteQuestion(${q.id})">Delete</button>
                </td>
            </tr>`;
        });
        document.getElementById('questionsTable').innerHTML = this.tableHtml(
            ['ID', 'Topic', 'Type', 'Content', 'Points', 'Actions'], rows
        );
    },

    getSelectedAnswerTypes() {
        return [...document.querySelectorAll('.answer-type-check:checked')].map(el => el.value);
    },

    setSelectedAnswerTypes(types) {
        document.querySelectorAll('.answer-type-check').forEach(el => {
            el.checked = types.includes(el.value);
        });
        this.onAnswerTypesChange();
    },

    onAnswerTypesChange() {
        const types = this.getSelectedAnswerTypes();
        const fields = document.getElementById('questionTypeFields');
        let html = '';
        if (types.includes('multiple_choice')) {
            html += `
                <div class="mb-3"><label class="form-label">Choices (one per line)</label>
                <textarea id="mcChoices" class="form-control" rows="4" placeholder="Option A\nOption B\nOption C"></textarea></div>
                <div class="mb-3"><label class="form-label">Correct Answer</label>
                <input type="text" id="mcCorrect" class="form-control"></div>`;
        }
        if (types.includes('code')) {
            html += `
                <div class="mb-3"><label class="form-label">Test Cases (JSON)</label>
                <textarea id="codeTestCases" class="form-control" rows="4" placeholder='[{"input":"5","output":"25"}]'></textarea></div>`;
        }
        fields.innerHTML = html;
    },

    onQuestionTypeChange() {
        this.onAnswerTypesChange();
    },

    async showQuestionModal(questionId) {
        document.getElementById('questionId').value = questionId || '';
        document.getElementById('questionModalTitle').textContent = questionId ? 'Edit Question' : 'Add Question';
        document.getElementById('questionContent').value = '';
        document.getElementById('questionPoints').value = '1';
        this.setSelectedAnswerTypes(['multiple_choice']);

        if (questionId) {
            const q = this.questions.find(x => x.id === questionId) ||
                await this.api('GET', `/api/v1/questions/${questionId}`);
            document.getElementById('questionTopic').value = q.topic_id;
            const types = q.answer_types && q.answer_types.length ? q.answer_types : [q.type];
            this.setSelectedAnswerTypes(types);
            document.getElementById('questionContent').value = q.content;
            document.getElementById('questionPoints').value = q.points;
            if (types.includes('multiple_choice') && q.correct_answer) {
                try {
                    const data = JSON.parse(q.correct_answer);
                    if (data.choices) document.getElementById('mcChoices').value = data.choices.join('\n');
                    if (data.correct) document.getElementById('mcCorrect').value = data.correct;
                } catch { document.getElementById('mcCorrect').value = q.correct_answer; }
            }
            if (types.includes('code') && q.test_cases) {
                document.getElementById('codeTestCases').value = JSON.stringify(q.test_cases, null, 2);
            }
        }
        new bootstrap.Modal(document.getElementById('questionModal')).show();
    },

    async saveQuestion() {
        const id = document.getElementById('questionId').value;
        const answerTypes = this.getSelectedAnswerTypes();
        if (!answerTypes.length) return alert('Select at least one answer type');

        const data = {
            topic_id: parseInt(document.getElementById('questionTopic').value),
            answer_types: answerTypes,
            content: document.getElementById('questionContent').value.trim(),
            points: parseFloat(document.getElementById('questionPoints').value)
        };
        if (!data.content) return alert('Content is required');

        if (answerTypes.includes('multiple_choice')) {
            const choices = document.getElementById('mcChoices').value.split('\n').map(c => c.trim()).filter(Boolean);
            const correct = document.getElementById('mcCorrect').value.trim();
            if (!choices.length || !correct) return alert('Choices and correct answer required for multiple choice');
            data.correct_answer = JSON.stringify({ choices, correct });
        }
        if (answerTypes.includes('code')) {
            const tcEl = document.getElementById('codeTestCases');
            const tc = tcEl ? tcEl.value.trim() : '';
            if (tc) {
                try { data.test_cases = JSON.parse(tc); }
                catch { return alert('Invalid test cases JSON'); }
            }
        }

        try {
            if (id) await this.api('PUT', `/api/v1/questions/${id}`, data);
            else await this.api('POST', '/api/v1/questions', data);
            bootstrap.Modal.getInstance(document.getElementById('questionModal')).hide();
            await this.loadQuestions();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async deleteQuestion(id) {
        if (!confirm('Delete this question?')) return;
        try {
            await this.api('DELETE', `/api/v1/questions/${id}`);
            await this.loadQuestions();
        } catch (e) { alert('Error: ' + e.message); }
    },

    // --- Tests ---
    onTestModeChange() {
        const mode = document.getElementById('testMode').value;
        document.getElementById('scheduledTestFields').style.display = mode === 'scheduled' ? 'block' : 'none';
        document.getElementById('liveTestFields').style.display = mode === 'live' ? 'block' : 'none';
    },

    liveStatusBadge(t) {
        if (t.test_mode !== 'live') return '<span class="badge bg-secondary">Scheduled</span>';
        const map = { waiting: 'secondary', live: 'success', ended: 'dark' };
        const labels = { waiting: 'Waiting', live: 'LIVE', ended: 'Ended' };
        const s = t.live_status || 'waiting';
        return `<span class="badge bg-${map[s] || 'secondary'}">${labels[s] || s}</span>`;
    },

    liveControlButtons(t) {
        if (t.test_mode !== 'live') return '-';
        const s = t.live_status || 'waiting';
        if (s === 'live') {
            const rem = t.live_seconds_remaining != null ? `${Math.floor(t.live_seconds_remaining / 60)}:${String(t.live_seconds_remaining % 60).padStart(2, '0')}` : '';
            return `<span class="text-danger fw-bold me-2">${rem}</span>
                <button class="btn btn-sm btn-warning" onclick="LecturerUI.extendLive(${t.id}, 5)">+5m</button>
                <button class="btn btn-sm btn-warning" onclick="LecturerUI.extendLive(${t.id}, 10)">+10m</button>
                <button class="btn btn-sm btn-danger" onclick="LecturerUI.endLive(${t.id})">End</button>`;
        }
        return `<button class="btn btn-sm btn-success" onclick="LecturerUI.showGoLiveModal(${t.id})">Go Live</button>`;
    },

    async loadTests() {
        this.tests = await this.api('GET', '/api/v1/tests');
        const rows = this.tests.map(t => `<tr>
            <td>${t.id}</td>
            <td>${this.escapeHtml(t.name)}</td>
            <td>${this.liveStatusBadge(t)}</td>
            <td>${t.test_mode === 'live' ? 'Live control' : (t.time_limit ? t.time_limit + ' min' : 'No limit')}</td>
            <td>${this.liveControlButtons(t)}</td>
            <td class="table-actions">
                <button class="btn btn-sm btn-outline-primary" onclick="LecturerUI.showTestModal(${t.id})">Edit</button>
                <button class="btn btn-sm btn-outline-danger" onclick="LecturerUI.deleteTest(${t.id})">Delete</button>
            </td>
        </tr>`);
        document.getElementById('testsTable').innerHTML = this.tableHtml(
            ['ID', 'Name', 'Status', 'Timing', 'Live Control', 'Actions'], rows
        );
    },

    showGoLiveModal(testId) {
        document.getElementById('goLiveTestId').value = testId;
        document.getElementById('goLiveDuration').value = '45';
        new bootstrap.Modal(document.getElementById('goLiveModal')).show();
    },

    async confirmGoLive() {
        const testId = document.getElementById('goLiveTestId').value;
        const duration = parseInt(document.getElementById('goLiveDuration').value);
        if (!duration || duration <= 0) return alert('Enter a valid duration');
        try {
            await this.api('POST', `/api/v1/tests/${testId}/live/start`, { duration_minutes: duration });
            bootstrap.Modal.getInstance(document.getElementById('goLiveModal')).hide();
            await this.loadTests();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async extendLive(testId, minutes) {
        try {
            await this.api('POST', `/api/v1/tests/${testId}/live/extend`, { minutes });
            await this.loadTests();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async endLive(testId) {
        if (!confirm('End the live session now? All in-progress tests will be auto-submitted.')) return;
        try {
            await this.api('POST', `/api/v1/tests/${testId}/live/end`);
            await this.loadTests();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async showTestModal(testId) {
        document.getElementById('testId').value = testId || '';
        document.getElementById('testModalTitle').textContent = testId ? 'Edit Test' : 'Create Test';
        document.getElementById('testName').value = '';
        document.getElementById('testDescription').value = '';
        document.getElementById('testTimeLimit').value = '0';
        document.getElementById('testAttempts').value = '1';
        document.getElementById('testAvailableFrom').value = '';
        document.getElementById('testAvailableUntil').value = '';
        document.getElementById('testMode').value = 'scheduled';
        this.onTestModeChange();

        this.allQuestions = await this.api('GET', '/api/v1/questions');
        let selectedIds = [];

        if (testId) {
            const test = await this.api('GET', `/api/v1/tests/${testId}`);
            document.getElementById('testName').value = test.name;
            document.getElementById('testDescription').value = test.description || '';
            document.getElementById('testMode').value = test.test_mode || 'scheduled';
            this.onTestModeChange();
            document.getElementById('testTimeLimit').value = test.time_limit || 0;
            document.getElementById('testAttempts').value = test.attempts_allowed || 1;
            document.getElementById('testAttemptsLive').value = test.attempts_allowed || 1;
            document.getElementById('testAvailableFrom').value = this.isoToLocalDatetime(test.available_from);
            document.getElementById('testAvailableUntil').value = this.isoToLocalDatetime(test.available_until);
            selectedIds = (test.questions || []).sort((a, b) => a.order - b.order).map(q => q.id);
        }

        const topicMap = Object.fromEntries(this.topics.map(t => [t.id, t.name]));
        document.getElementById('testQuestionsList').innerHTML = this.allQuestions.map(q => {
            const checked = selectedIds.includes(q.id) ? 'checked' : '';
            const order = selectedIds.indexOf(q.id);
            const orderLabel = order >= 0 ? ` (#${order + 1})` : '';
            const preview = q.content.length > 60 ? q.content.slice(0, 60) + '...' : q.content;
            return `<div class="form-check border-bottom py-1">
                <input class="form-check-input test-q-check" type="checkbox" value="${q.id}" id="tq-${q.id}" ${checked}
                    onchange="LecturerUI.updateTestQuestionOrder()">
                <label class="form-check-label" for="tq-${q.id}">
                    [${q.type}] ${this.escapeHtml(preview)} (${topicMap[q.topic_id] || '?'})${orderLabel}
                </label>
            </div>`;
        }).join('') || '<p class="text-muted">No questions in bank. Add questions first.</p>';

        new bootstrap.Modal(document.getElementById('testModal')).show();
    },

    updateTestQuestionOrder() {
        const checks = [...document.querySelectorAll('.test-q-check:checked')];
        checks.forEach((cb, i) => {
            const label = cb.nextElementSibling;
            const base = label.textContent.replace(/ \(#\d+\)$/, '');
            label.textContent = base + ` (#${i + 1})`;
        });
    },

    async saveTest() {
        const id = document.getElementById('testId').value;
        const name = document.getElementById('testName').value.trim();
        if (!name) return alert('Test name is required');

        const timeLimit = parseInt(document.getElementById('testTimeLimit').value);
        const testMode = document.getElementById('testMode').value;
        const attempts = testMode === 'live'
            ? parseInt(document.getElementById('testAttemptsLive').value)
            : parseInt(document.getElementById('testAttempts').value);
        const question_ids = [...document.querySelectorAll('.test-q-check:checked')].map((cb, i) => ({
            question_id: parseInt(cb.value), order: i + 1
        }));

        const data = {
            name,
            description: document.getElementById('testDescription').value.trim(),
            test_mode: testMode,
            attempts_allowed: attempts,
            question_ids
        };
        if (testMode === 'scheduled') {
            data.time_limit = timeLimit > 0 ? timeLimit : null;
            data.available_from = this.localDatetimeToISO(document.getElementById('testAvailableFrom').value);
            data.available_until = this.localDatetimeToISO(document.getElementById('testAvailableUntil').value);
        }

        try {
            if (id) await this.api('PUT', `/api/v1/tests/${id}`, data);
            else await this.api('POST', '/api/v1/tests', data);
            bootstrap.Modal.getInstance(document.getElementById('testModal')).hide();
            await this.loadTests();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async deleteTest(id) {
        if (!confirm('Delete this test?')) return;
        try {
            await this.api('DELETE', `/api/v1/tests/${id}`);
            await this.loadTests();
        } catch (e) { alert('Error: ' + e.message); }
    },

    // --- Grading ---
    async loadGrading() {
        let submissions = await this.api('GET', '/api/v1/submissions');
        submissions = submissions.filter(s => ['submitted', 'graded'].includes(s.status));
        const rows = submissions.map(s => `<tr>
            <td>${s.id}</td>
            <td>${this.escapeHtml(s.test_name || '?')}</td>
            <td>${this.escapeHtml(s.username || '?')}</td>
            <td><span class="badge bg-${s.status === 'graded' ? 'success' : 'warning'}">${s.status}</span></td>
            <td><a href="/lecturer/grading/${s.id}" class="btn btn-sm btn-primary">Grade</a></td>
        </tr>`);
        document.getElementById('gradingTable').innerHTML = this.tableHtml(
            ['ID', 'Test', 'Student', 'Status', 'Actions'], rows
        );
    },

    // --- Statistics ---
    destroyStatsCharts() {
        this._statsCharts.forEach(c => c.destroy());
        this._statsCharts = [];
    },

    statsNav(view, opts = {}) {
        this.statsState.view = view;
        if (opts.testId !== undefined) this.statsState.testId = opts.testId;
        if (opts.studentId !== undefined) this.statsState.studentId = opts.studentId;
        if (opts.focusTestId !== undefined) this.statsState.focusTestId = opts.focusTestId;
        if (opts.compareTestId !== undefined) this.statsState.compareTestId = opts.compareTestId;
        this.loadStatistics();
    },

    statsGroupQuery(extra = {}) {
        const params = new URLSearchParams();
        if (this.statsState.groupFilter !== '' && this.statsState.groupFilter != null) {
            params.set('group_id', this.statsState.groupFilter);
        }
        if (this.statsState.focusTestId && extra.includeFocusTest) {
            params.set('test_id', this.statsState.focusTestId);
        }
        if (this.statsState.compareTestId && extra.includeCompareTest) {
            params.set('test_id', this.statsState.compareTestId);
        }
        const qs = params.toString();
        return qs ? `?${qs}` : '';
    },

    renderGroupFilterSelect() {
        const sel = coalesce(this.statsState.groupFilter, '');
        return `<label class="form-label mb-0 small text-muted">Group</label>
            <select class="form-select form-select-sm" style="width:auto;min-width:150px;" onchange="LecturerUI.statsState.groupFilter=this.value; LecturerUI.loadStatistics();">
                <option value="" ${sel === '' ? 'selected' : ''}>All groups</option>
                ${(this.groups || []).map(g => `<option value="${g.id}" ${String(sel) === String(g.id) ? 'selected' : ''}>${this.escapeHtml(g.name)}</option>`).join('')}
            </select>`;
    },

    groupChartColor(index) {
        return this.GROUP_CHART_COLORS[index % this.GROUP_CHART_COLORS.length];
    },

    populateGroupSelects(selectedId = '') {
        const realGroups = (this.groups || []).filter(g => !g.is_virtual);
        const opts = `<option value="">Unassigned</option>` +
            realGroups.map(g => `<option value="${g.id}">${this.escapeHtml(g.name)}</option>`).join('');
        const studentSel = document.getElementById('studentGroupSelect');
        if (studentSel) {
            studentSel.innerHTML = opts;
            studentSel.value = selectedId == null ? '' : String(selectedId);
        }
        const filterSel = document.getElementById('studentGroupFilter');
        if (filterSel) {
            filterSel.innerHTML = `<option value="">All groups</option>` +
                (this.groups || []).map(g => `<option value="${g.id}">${this.escapeHtml(g.name)}</option>`).join('');
        }
    },

    renderStatsBreadcrumb(items) {
        const el = document.getElementById('statsBreadcrumb');
        if (!items.length) { el.innerHTML = ''; return; }
        el.innerHTML = items.map((item, i) => {
            if (i === items.length - 1) return `<span>${this.escapeHtml(item.label)}</span>`;
            return `<a href="#" onclick="LecturerUI.${item.action}; return false;">${this.escapeHtml(item.label)}</a> &rsaquo; `;
        }).join('');
    },

    renderStatsToolbar(html) {
        document.getElementById('statsToolbar').innerHTML = html || '';
    },

    scoreBarHtml(pct) {
        const p = coalesce(pct, 0);
        const color = p >= 70 ? '#667eea' : p >= 50 ? '#f0ad4e' : '#dc3545';
        return `<div class="stats-score-bar"><div class="stats-score-bar-fill" style="width:${Math.min(100, p)}%;background:${color}"></div></div>`;
    },

    pctBadge(pct) {
        if (pct == null) return '<span class="badge bg-secondary">—</span>';
        const cls = pct >= 70 ? 'bg-success' : pct >= 50 ? 'bg-warning text-dark' : 'bg-danger';
        return `<span class="badge ${cls}">${pct}%</span>`;
    },

    mountChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === 'undefined') return;
        const chart = new Chart(canvas, config);
        this._statsCharts.push(chart);
    },

    async loadStatistics() {
        const el = document.getElementById('statisticsContent');
        el.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';
        this.destroyStatsCharts();

        const { view } = this.statsState;
        try {
            if (view === 'overview') await this.renderStatsOverview();
            else if (view === 'tests') await this.renderStatsTestList();
            else if (view === 'testDetail') await this.renderStatsTestDetail(this.statsState.testId);
            else if (view === 'students') await this.renderStatsStudentList();
            else if (view === 'studentDetail') await this.renderStatsStudentDetail(this.statsState.studentId);
            else if (view === 'studentTestDetail') await this.renderStatsStudentTestDetail(this.statsState.studentId, this.statsState.testId);
            else if (view === 'compareGroups') await this.renderStatsCompareGroups();
            else await this.renderStatsOverview();
        } catch (e) {
            el.innerHTML = `<div class="alert alert-danger">${this.escapeHtml(e.message)}</div>`;
        }
    },

    async renderStatsOverview() {
        const data = await this.api('GET', `/api/v1/statistics/overview${this.statsGroupQuery({ includeFocusTest: true })}`);
        if (!this.statsState.focusTestId && data.focus_test_id) {
            this.statsState.focusTestId = data.focus_test_id;
        }

        this.renderStatsBreadcrumb([{ label: 'Class overview', action: "statsNav('overview')" }]);
        this.renderStatsToolbar(`
            ${this.renderGroupFilterSelect()}
            <label class="form-label mb-0 small text-muted">Focus test</label>
            <select class="form-select form-select-sm" style="width:auto;min-width:200px;" onchange="LecturerUI.statsState.focusTestId=parseInt(this.value)||null; LecturerUI.loadStatistics();">
                <option value="">Latest with grades</option>
                ${(data.tests_summary || []).map(t => `<option value="${t.test_id}" ${data.focus_test_id===t.test_id?'selected':''}>${this.escapeHtml(t.test_name)}</option>`).join('')}
            </select>
            <button class="btn btn-outline-primary btn-sm" onclick="LecturerUI.statsNav('compareGroups')"><i class="fas fa-layer-group me-1"></i>Compare groups</button>
            <button class="btn btn-outline-primary btn-sm" onclick="LecturerUI.statsNav('tests')"><i class="fas fa-list me-1"></i>Browse tests</button>
            <button class="btn btn-outline-primary btn-sm" onclick="LecturerUI.statsNav('students')"><i class="fas fa-users me-1"></i>Browse students</button>
        `);

        const el = document.getElementById('statisticsContent');
        const cards = [
            ['Students', data.total_students, 'fa-users'],
            ['Tests', data.total_tests, 'fa-file-alt'],
            ['Submissions', data.total_submissions, 'fa-paper-plane'],
            ['Graded', data.total_graded, 'fa-check-circle'],
        ];

        el.innerHTML = `
            <div class="row mb-4">${cards.map(([label, val, icon]) => `
                <div class="col-6 col-md-3 mb-3"><div class="card stat-card">
                    <div class="text-muted mb-1"><i class="fas ${icon}"></i></div>
                    <h3>${val}</h3><p class="text-muted mb-0 small">${label}</p>
                </div></div>`).join('')}</div>

            <div class="row mb-4">
                <div class="col-lg-7 mb-3">
                    <div class="card p-3 h-100">
                        <h6 class="mb-3">Average score by test</h6>
                        <div class="stats-chart-wrap"><canvas id="chartTestsAvg"></canvas></div>
                    </div>
                </div>
                <div class="col-lg-5 mb-3">
                    <div class="card p-3 h-100">
                        <h6 class="mb-1">Score distribution${data.focus_test_name ? `: ${this.escapeHtml(data.focus_test_name)}` : ''}</h6>
                        <p class="text-muted small mb-2">Graded submissions in selected test</p>
                        <div class="stats-chart-wrap"><canvas id="chartDistribution"></canvas></div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-lg-6 mb-3">
                    <div class="card p-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="mb-0">Tests</h6>
                            <button class="btn btn-link btn-sm p-0" onclick="LecturerUI.statsNav('tests')">View all</button>
                        </div>
                        ${this.tableHtml(['Test', 'Graded', 'Avg %', ''],
                            (data.tests_summary || []).slice(0, 8).map(t => `<tr class="stats-clickable-row" onclick="LecturerUI.statsNav('testDetail',{testId:${t.test_id}})">
                                <td><strong>${this.escapeHtml(t.test_name)}</strong><br><small class="text-muted">${t.test_mode} · ${t.question_count} Q</small></td>
                                <td>${t.graded_submissions}/${t.total_submissions}</td>
                                <td>${t.graded_submissions ? t.average_percentage + '%' : '—'}</td>
                                <td><i class="fas fa-chevron-right text-muted"></i></td>
                            </tr>`))}
                    </div>
                </div>
                <div class="col-lg-6 mb-3">
                    <div class="card p-3">
                        <h6 class="mb-3">Weak topics <small class="text-muted">(lowest avg %)</small></h6>
                        ${(data.weak_topics || []).length ? this.tableHtml(['Topic', 'Avg %', 'Answers'],
                            data.weak_topics.map(t => `<tr>
                                <td>${this.escapeHtml(t.topic_name)}</td>
                                <td>${this.pctBadge(t.average_percentage)}</td>
                                <td>${t.submission_count}</td>
                            </tr>`)) : '<div class="alert alert-info mb-0">No graded answers yet.</div>'}
                    </div>
                </div>
            </div>`;

        const gradedTests = (data.tests_summary || []).filter(t => t.graded_submissions > 0);
        if (gradedTests.length) {
            this.mountChart('chartTestsAvg', {
                type: 'bar',
                data: {
                    labels: gradedTests.map(t => t.test_name.length > 20 ? t.test_name.slice(0, 18) + '…' : t.test_name),
                    datasets: [{ label: 'Avg %', data: gradedTests.map(t => t.average_percentage), backgroundColor: '#667eea' }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    onClick: (_, elems) => { if (elems[0]) this.statsNav('testDetail', { testId: gradedTests[elems[0].index].test_id }); },
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: '%' } } },
                },
            });
        }

        const dist = data.focus_distribution || [];
        if (dist.some(d => d.count > 0)) {
            this.mountChart('chartDistribution', {
                type: 'bar',
                data: {
                    labels: dist.map(d => d.label),
                    datasets: [{ label: 'Students', data: dist.map(d => d.count), backgroundColor: '#764ba2' }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
                },
            });
        } else {
            var chartDistEl = document.querySelector('#chartDistribution');
            if (chartDistEl && chartDistEl.parentElement) {
                chartDistEl.parentElement.insertAdjacentHTML('beforeend',
                    '<p class="text-muted small text-center mb-0">No graded submissions for this test.</p>');
            }
        }
    },

    async renderStatsTestList() {
        const f = this.statsState.testFilters;
        const params = new URLSearchParams();
        if (f.q) params.set('q', f.q);
        if (f.mode) params.set('mode', f.mode);
        if (f.status && f.status !== 'all') params.set('status', f.status);
        if (f.sort) params.set('sort', f.sort);
        if (this.statsState.groupFilter !== '' && this.statsState.groupFilter != null) {
            params.set('group_id', this.statsState.groupFilter);
        }
        const data = await this.api('GET', `/api/v1/statistics/tests?${params}`);

        this.renderStatsBreadcrumb([
            { label: 'Class overview', action: "statsNav('overview')" },
            { label: 'Tests', action: "statsNav('tests')" },
        ]);
        this.renderStatsToolbar(`
            ${this.renderGroupFilterSelect()}
            <input type="search" class="form-control form-control-sm" style="width:200px;" placeholder="Search tests…"
                value="${this.escapeHtml(f.q)}" oninput="LecturerUI.statsState.testFilters.q=this.value; clearTimeout(LecturerUI._statsSearchTimer); LecturerUI._statsSearchTimer=setTimeout(()=>LecturerUI.loadStatistics(),300);">
            <select class="form-select form-select-sm" onchange="LecturerUI.statsState.testFilters.mode=this.value; LecturerUI.loadStatistics();">
                <option value="">All modes</option>
                <option value="scheduled" ${f.mode==='scheduled'?'selected':''}>Scheduled</option>
                <option value="live" ${f.mode==='live'?'selected':''}>Live</option>
            </select>
            <select class="form-select form-select-sm" onchange="LecturerUI.statsState.testFilters.status=this.value; LecturerUI.loadStatistics();">
                <option value="all" ${f.status==='all'?'selected':''}>All tests</option>
                <option value="has_submissions" ${f.status==='has_submissions'?'selected':''}>Has submissions</option>
                <option value="graded" ${f.status==='graded'?'selected':''}>Has grades</option>
                <option value="pending" ${f.status==='pending'?'selected':''}>Pending grading</option>
            </select>
            <select class="form-select form-select-sm" onchange="LecturerUI.statsState.testFilters.sort=this.value; LecturerUI.loadStatistics();">
                <option value="date" ${f.sort==='date'?'selected':''}>Sort: newest</option>
                <option value="name" ${f.sort==='name'?'selected':''}>Sort: name</option>
                <option value="avg_score" ${f.sort==='avg_score'?'selected':''}>Sort: avg score</option>
            </select>
        `);

        document.getElementById('statisticsContent').innerHTML = `
            <div class="card p-3">
                <h6 class="mb-3">${data.length} test${data.length !== 1 ? 's' : ''}</h6>
                ${this.tableHtml(['Test', 'Mode', 'Submissions', 'Graded', 'Pending', 'Avg %', ''],
                    data.map(t => `<tr class="stats-clickable-row" onclick="LecturerUI.statsNav('testDetail',{testId:${t.test_id}})">
                        <td><strong>${this.escapeHtml(t.test_name)}</strong><br><small class="text-muted">${t.question_count} questions</small></td>
                        <td><span class="badge bg-${t.test_mode==='live'?'danger':'secondary'}">${t.test_mode}</span></td>
                        <td>${t.total_submissions}</td>
                        <td>${t.graded_submissions}</td>
                        <td>${t.pending_grade || '—'}</td>
                        <td>${t.graded_submissions ? this.pctBadge(t.average_percentage) : '—'}</td>
                        <td><i class="fas fa-chevron-right text-muted"></i></td>
                    </tr>`))}
            </div>`;
    },

    async renderStatsTestDetail(testId) {
        if (!testId) { this.statsNav('tests'); return; }
        const data = await this.api('GET', `/api/v1/statistics/tests/${testId}${this.statsGroupQuery()}`);

        this.renderStatsBreadcrumb([
            { label: 'Class overview', action: "statsNav('overview')" },
            { label: 'Tests', action: "statsNav('tests')" },
            { label: data.test_name, action: `statsNav('testDetail',{testId:${testId}})` },
        ]);
        this.renderStatsToolbar(`
            ${this.renderGroupFilterSelect()}
            <button class="btn btn-outline-secondary btn-sm" onclick="LecturerUI.statsNav('tests')"><i class="fas fa-arrow-left me-1"></i>Back to tests</button>
        `);

        const el = document.getElementById('statisticsContent');
        el.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-3 mb-2"><div class="card stat-card p-3"><h3>${data.total_submissions}</h3><p class="text-muted mb-0 small">Submissions</p></div></div>
                <div class="col-md-3 mb-2"><div class="card stat-card p-3"><h3>${data.graded_submissions}</h3><p class="text-muted mb-0 small">Graded</p></div></div>
                <div class="col-md-3 mb-2"><div class="card stat-card p-3"><h3>${data.pending_grade || 0}</h3><p class="text-muted mb-0 small">Pending</p></div></div>
                <div class="col-md-3 mb-2"><div class="card stat-card p-3"><h3>${data.graded_submissions ? data.average_percentage + '%' : '—'}</h3><p class="text-muted mb-0 small">Class average</p></div></div>
            </div>
            <div class="row mb-4">
                <div class="col-lg-6 mb-3"><div class="card p-3"><h6 class="mb-3">Score distribution</h6><div class="stats-chart-wrap"><canvas id="chartTestDist"></canvas></div></div></div>
                <div class="col-lg-6 mb-3"><div class="card p-3"><h6 class="mb-3">Average score per question</h6><div class="stats-chart-wrap"><canvas id="chartQuestionAvg"></canvas></div></div></div>
            </div>
            <div class="card p-3 mb-4">
                <h6 class="mb-3">Question breakdown</h6>
                ${this.tableHtml(['#', 'Question', 'Avg score', 'Avg %', 'Answers'],
                    (data.question_statistics || []).map(q => `<tr>
                        <td>Q${q.order}</td>
                        <td class="question-content-preview" title="${this.escapeHtml(q.content)}">${this.escapeHtml(q.content)}</td>
                        <td>${q.average_score} / ${q.max_points}</td>
                        <td>${this.pctBadge(q.average_percentage)}</td>
                        <td>${q.answer_count}</td>
                    </tr>`))}
            </div>
            <div class="card p-3">
                <h6 class="mb-3">Students</h6>
                ${this.tableHtml(['Student', 'Status', 'Score', '%', 'Submitted', 'Actions'],
                    (data.student_results || []).map(s => `<tr>
                        <td><a href="#" onclick="LecturerUI.statsNav('studentDetail',{studentId:${s.student_id}}); return false;">${this.escapeHtml(s.username)}</a>
                            ${s.student_id_number ? `<br><small class="text-muted">${this.escapeHtml(s.student_id_number)}</small>` : ''}</td>
                        <td><span class="badge bg-${s.is_graded?'success':s.status==='submitted'?'warning text-dark':'secondary'}">${s.is_graded?'graded':s.status}</span></td>
                        <td>${s.total_score != null ? `${s.total_score} / ${s.max_score}` : '—'}</td>
                        <td>${this.pctBadge(s.percentage)}</td>
                        <td><small>${s.submitted_at ? this.formatDatetime(s.submitted_at) : '—'}</small></td>
                        <td>${s.submission_id ? `<a class="btn btn-sm btn-outline-primary" href="/lecturer/grading/${s.submission_id}">Grade</a>` : '—'}</td>
                    </tr>`))}
            </div>`;

        const dist = data.score_distribution || [];
        if (dist.some(d => d.count > 0)) {
            this.mountChart('chartTestDist', {
                type: 'bar',
                data: { labels: dist.map(d => d.label), datasets: [{ data: dist.map(d => d.count), backgroundColor: '#667eea' }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
            });
        }

        const qs = data.question_statistics || [];
        if (qs.length) {
            this.mountChart('chartQuestionAvg', {
                type: 'bar',
                data: {
                    labels: qs.map(q => `Q${q.order}`),
                    datasets: [{ label: 'Avg %', data: qs.map(q => q.average_percentage), backgroundColor: qs.map(q => q.average_percentage >= 70 ? '#667eea' : q.average_percentage >= 50 ? '#f0ad4e' : '#dc3545') }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } },
            });
        }
    },

    async renderStatsStudentList() {
        const q = this.statsState.studentSearch;
        const params = new URLSearchParams();
        if (q) params.set('q', q);
        if (this.statsState.groupFilter !== '' && this.statsState.groupFilter != null) {
            params.set('group_id', this.statsState.groupFilter);
        }
        const qs = params.toString();
        const data = await this.api('GET', `/api/v1/statistics/students${qs ? `?${qs}` : ''}`);

        this.renderStatsBreadcrumb([
            { label: 'Class overview', action: "statsNav('overview')" },
            { label: 'Students', action: "statsNav('students')" },
        ]);
        this.renderStatsToolbar(`
            ${this.renderGroupFilterSelect()}
            <input type="search" class="form-control form-control-sm" style="width:220px;" placeholder="Search name or ID…"
                value="${this.escapeHtml(q)}" oninput="LecturerUI.statsState.studentSearch=this.value; clearTimeout(LecturerUI._statsStudentTimer); LecturerUI._statsStudentTimer=setTimeout(()=>LecturerUI.loadStatistics(),300);">
        `);

        document.getElementById('statisticsContent').innerHTML = `
            <div class="card p-3">
                <h6 class="mb-3">${data.length} student${data.length !== 1 ? 's' : ''}</h6>
                ${this.tableHtml(['Student', 'Group', 'Submissions', 'Graded', 'Avg %', ''],
                    data.map(s => `<tr class="stats-clickable-row" onclick="LecturerUI.statsNav('studentDetail',{studentId:${s.student_id}})">
                        <td><strong>${this.escapeHtml(s.username)}</strong>${s.student_id_number ? `<br><small class="text-muted">${this.escapeHtml(s.student_id_number)}</small>` : ''}</td>
                        <td>${this.escapeHtml(s.group_name || 'Unassigned')}</td>
                        <td>${s.total_submissions}</td>
                        <td>${s.total_tests_graded}</td>
                        <td>${s.total_tests_graded ? this.pctBadge(s.average_percentage) : '—'}</td>
                        <td><i class="fas fa-chevron-right text-muted"></i></td>
                    </tr>`))}
            </div>`;
    },

    async renderStatsStudentDetail(studentId) {
        if (!studentId) { this.statsNav('students'); return; }
        const data = await this.api('GET', `/api/v1/statistics/students/${studentId}`);

        this.renderStatsBreadcrumb([
            { label: 'Class overview', action: "statsNav('overview')" },
            { label: 'Students', action: "statsNav('students')" },
            { label: data.username, action: `statsNav('studentDetail',{studentId:${studentId}})` },
        ]);
        this.renderStatsToolbar(`
            <button class="btn btn-outline-secondary btn-sm" onclick="LecturerUI.statsNav('students')"><i class="fas fa-arrow-left me-1"></i>Back to students</button>
        `);

        const el = document.getElementById('statisticsContent');
        el.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-4 mb-2"><div class="card stat-card p-3"><h3>${data.total_submissions}</h3><p class="text-muted mb-0 small">Submissions</p></div></div>
                <div class="col-md-4 mb-2"><div class="card stat-card p-3"><h3>${data.total_graded}</h3><p class="text-muted mb-0 small">Graded</p></div></div>
                <div class="col-md-4 mb-2"><div class="card stat-card p-3"><h3>${data.total_graded ? data.average_percentage + '%' : '—'}</h3><p class="text-muted mb-0 small">Average</p></div></div>
            </div>
            ${(data.test_chart || []).length ? `<div class="card p-3 mb-4"><h6 class="mb-3">Score trend across tests</h6><div class="stats-chart-wrap"><canvas id="chartStudentTrend"></canvas></div></div>` : ''}
            <div class="card p-3">
                <h6 class="mb-3">Tests</h6>
                ${this.tableHtml(['Test', 'Status', 'Score', '%', 'Submitted', 'Actions'],
                    (data.tests || []).map(t => `<tr class="stats-clickable-row" onclick="LecturerUI.statsNav('studentTestDetail',{studentId:${studentId},testId:${t.test_id}})">
                        <td><strong>${this.escapeHtml(t.test_name)}</strong></td>
                        <td><span class="badge bg-${t.is_graded?'success':t.status==='submitted'?'warning text-dark':'secondary'}">${t.is_graded?'graded':t.status}</span></td>
                        <td>${t.total_score != null ? `${t.total_score} / ${t.max_score}` : '—'}</td>
                        <td>${this.pctBadge(t.percentage)}</td>
                        <td><small>${t.submitted_at ? this.formatDatetime(t.submitted_at) : '—'}</small></td>
                        <td onclick="event.stopPropagation()">${t.submission_id ? `<a class="btn btn-sm btn-outline-primary" href="/lecturer/grading/${t.submission_id}">Grade</a>` : '—'}</td>
                    </tr>`))}
            </div>`;

        const chart = data.test_chart || [];
        if (chart.length) {
            this.mountChart('chartStudentTrend', {
                type: 'line',
                data: {
                    labels: chart.map(c => c.test_name.length > 18 ? c.test_name.slice(0, 16) + '…' : c.test_name),
                    datasets: [{ label: 'Score %', data: chart.map(c => c.percentage), borderColor: '#667eea', backgroundColor: 'rgba(102,126,234,0.15)', fill: true, tension: 0.3 }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    onClick: (_, elems) => {
                        if (elems[0]) {
                            const t = data.tests.filter(x => x.percentage != null)[elems[0].index];
                            if (t) this.statsNav('studentTestDetail', { studentId, testId: t.test_id });
                        }
                    },
                    scales: { y: { beginAtZero: true, max: 100 } },
                },
            });
        }
    },

    async renderStatsStudentTestDetail(studentId, testId) {
        if (!studentId || !testId) { this.statsNav('studentDetail', { studentId }); return; }
        const data = await this.api('GET', `/api/v1/statistics/students/${studentId}/tests/${testId}`);

        this.renderStatsBreadcrumb([
            { label: 'Class overview', action: "statsNav('overview')" },
            { label: 'Students', action: "statsNav('students')" },
            { label: data.username, action: `statsNav('studentDetail',{studentId:${studentId}})` },
            { label: data.test_name, action: `statsNav('studentTestDetail',{studentId:${studentId},testId:${testId}})` },
        ]);
        this.renderStatsToolbar(`
            <button class="btn btn-outline-secondary btn-sm" onclick="LecturerUI.statsNav('studentDetail',{studentId:${studentId}})"><i class="fas fa-arrow-left me-1"></i>Back to student</button>
            <a class="btn btn-primary btn-sm" href="/lecturer/grading/${data.submission_id}"><i class="fas fa-edit me-1"></i>Open grading</a>
            <button class="btn btn-outline-primary btn-sm" onclick="LecturerUI.statsNav('testDetail',{testId:${testId}})"><i class="fas fa-chart-bar me-1"></i>Test statistics</button>
        `);

        document.getElementById('statisticsContent').innerHTML = `
            <div class="card p-3 mb-4">
                <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
                    <div>
                        <h5 class="mb-1">${this.escapeHtml(data.username)} — ${this.escapeHtml(data.test_name)}</h5>
                        <span class="badge bg-${data.percentage != null ? 'success' : 'secondary'}">${data.status}</span>
                    </div>
                    <div class="text-end">
                        <div class="h4 mb-0">${data.total_score != null ? `${data.total_score} / ${data.max_score}` : 'Not graded'}</div>
                        ${data.percentage != null ? this.pctBadge(data.percentage) : ''}
                    </div>
                </div>
            </div>
            <div class="card p-3 mb-4"><h6 class="mb-3">Score by question</h6><div class="stats-chart-wrap"><canvas id="chartStudentQuestions"></canvas></div></div>
            <div class="card p-3">
                <h6 class="mb-3">Question breakdown</h6>
                ${this.tableHtml(['#', 'Question', 'Score', '%', 'Progress'],
                    (data.questions || []).map(q => `<tr>
                        <td>Q${q.order}</td>
                        <td class="question-content-preview" title="${this.escapeHtml(q.content)}">${this.escapeHtml(q.content)}</td>
                        <td>${q.score != null ? `${q.score} / ${q.max_points}` : '—'}</td>
                        <td>${this.pctBadge(q.percentage)}</td>
                        <td style="min-width:120px">${q.percentage != null ? this.scoreBarHtml(q.percentage) : '—'}</td>
                    </tr>`))}
            </div>`;

        const qs = (data.questions || []).filter(q => q.percentage != null);
        if (qs.length) {
            this.mountChart('chartStudentQuestions', {
                type: 'bar',
                data: {
                    labels: qs.map(q => `Q${q.order}`),
                    datasets: [{ label: '% of max', data: qs.map(q => q.percentage), backgroundColor: qs.map(q => q.percentage >= 70 ? '#667eea' : q.percentage >= 50 ? '#f0ad4e' : '#dc3545') }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } },
            });
        }
    },

    async renderStatsCompareGroups() {
        if (this.statsState.compareTestId == null) {
            this.statsState.compareTestId = this.statsState.focusTestId || '';
        }
        const data = await this.api('GET', `/api/v1/statistics/groups/compare${this.statsGroupQuery({ includeCompareTest: true })}`);

        this.renderStatsBreadcrumb([
            { label: 'Class overview', action: "statsNav('overview')" },
            { label: 'Compare groups', action: "statsNav('compareGroups')" },
        ]);
        this.renderStatsToolbar(`
            <label class="form-label mb-0 small text-muted">Distribution test</label>
            <select class="form-select form-select-sm" style="width:auto;min-width:200px;" onchange="LecturerUI.statsState.compareTestId=parseInt(this.value)||''; LecturerUI.loadStatistics();">
                <option value="">All tests (matrix only)</option>
                ${(data.tests || []).map(t => `<option value="${t.test_id}" ${String(this.statsState.compareTestId)===String(t.test_id)?'selected':''}>${this.escapeHtml(t.test_name)}</option>`).join('')}
            </select>
            <button class="btn btn-outline-secondary btn-sm" onclick="LecturerUI.statsNav('overview')"><i class="fas fa-arrow-left me-1"></i>Back to overview</button>
        `);

        const tests = data.tests || [];
        const matrix = data.matrix || [];
        const matrixHeaders = ['Group', 'Students', ...tests.map(t => this.escapeHtml(t.test_name)), 'Overall avg'];
        const matrixRows = matrix.map(row => `<tr>
            <td><strong>${this.escapeHtml(row.group_name)}</strong></td>
            <td>${row.student_count}</td>
            ${tests.map(t => {
                const cell = row.tests[String(t.test_id)] || {};
                const avg = cell.average_percentage;
                const n = cell.graded_count || 0;
                return `<td>${avg != null ? `${this.pctBadge(avg)}<br><small class="text-muted">n=${n}</small>` : '—'}</td>`;
            }).join('')}
            <td>${row.overall_average != null ? this.pctBadge(row.overall_average) : '—'}</td>
        </tr>`);

        const el = document.getElementById('statisticsContent');
        el.innerHTML = `
            <div class="row mb-4">
                <div class="col-12 mb-3">
                    <div class="card p-3">
                        <h6 class="mb-3">Average score by group (per test)</h6>
                        <div class="stats-chart-wrap" style="height:320px"><canvas id="chartGroupCompare"></canvas></div>
                    </div>
                </div>
            </div>
            ${(data.distributions || []).some(d => (d.distribution || []).some(x => x.count > 0)) ? `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card p-3">
                        <h6 class="mb-3">Score distribution by group${this.statsState.compareTestId ? '' : ' (select a test above)'}</h6>
                        <div class="stats-chart-wrap" style="height:300px"><canvas id="chartGroupDist"></canvas></div>
                    </div>
                </div>
            </div>` : ''}
            <div class="card p-3">
                <h6 class="mb-3">Summary matrix</h6>
                ${this.tableHtml(matrixHeaders, matrixRows)}
            </div>`;

        const chartTests = (data.chart_by_test || []).filter(ct =>
            ct.groups.some(g => g.average_percentage != null)
        );
        if (chartTests.length && matrix.length) {
            const labels = chartTests.map(ct => ct.test_name.length > 16 ? ct.test_name.slice(0, 14) + '…' : ct.test_name);
            const datasets = matrix.map((row, gi) => ({
                label: row.group_name,
                data: chartTests.map(ct => {
                    const g = ct.groups.find(x => x.group_id === row.group_id);
                    return g && g.average_percentage != null ? g.average_percentage : null;
                }),
                backgroundColor: this.groupChartColor(gi),
            }));
            this.mountChart('chartGroupCompare', {
                type: 'bar',
                data: { labels, datasets },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } },
                    scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: 'Avg %' } } },
                },
            });
        }

        const dist = data.distributions || [];
        if (dist.length && dist.some(d => d.distribution.some(x => x.count > 0))) {
            const bucketLabels = dist[0].distribution.map(d => d.label);
            this.mountChart('chartGroupDist', {
                type: 'bar',
                data: {
                    labels: bucketLabels,
                    datasets: dist.map((d, i) => ({
                        label: d.group_name,
                        data: d.distribution.map(x => x.count),
                        backgroundColor: this.groupChartColor(i),
                    })),
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } },
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
                },
            });
        }
    },

    // --- Groups ---
    async loadGroups() {
        this.groups = await this.api('GET', '/api/v1/groups');
        this.populateGroupSelects();
        const rows = (this.groups || []).map(g => `<tr class="${g.is_virtual ? '' : 'stats-clickable-row'}" ${g.is_virtual ? '' : `onclick="LecturerUI.viewGroupDetail(${g.id})"`}>
            <td><strong>${this.escapeHtml(g.name)}</strong>${g.is_virtual ? ' <span class="badge bg-secondary">virtual</span>' : ''}</td>
            <td>${coalesce(g.student_count, 0)}</td>
            <td>${g.average_percentage != null ? this.pctBadge(g.average_percentage) : '—'}</td>
            <td onclick="event.stopPropagation()">${g.is_virtual ? `<button class="btn btn-sm btn-outline-primary" onclick="LecturerUI.filterStudentsByGroup(0)">View students</button>` :
                `<button class="btn btn-sm btn-outline-primary me-1" onclick="LecturerUI.viewGroupDetail(${g.id})">View</button>
                 <button class="btn btn-sm btn-outline-secondary me-1" onclick="LecturerUI.showGroupModal(${g.id})">Edit</button>
                 <button class="btn btn-sm btn-outline-danger" onclick="LecturerUI.deleteGroup(${g.id})">Delete</button>`}
            </td>
        </tr>`);
        document.getElementById('groupsTable').innerHTML = this.tableHtml(
            ['Group', 'Students', 'Avg graded %', 'Actions'], rows
        );
    },

    async viewGroupDetail(groupId) {
        const data = await this.api('GET', `/api/v1/groups/${groupId}`);
        const rows = (data.students || []).map(s => `<tr>
            <td>${this.escapeHtml(s.username)}</td>
            <td>${this.escapeHtml(s.student_id || '—')}</td>
            <td><button class="btn btn-sm btn-outline-primary" onclick="LecturerUI.statsNav('studentDetail',{studentId:${s.id}}); document.querySelector('[data-bs-target=\\'#statisticsTab\\']').click();">Statistics</button></td>
        </tr>`);
        document.getElementById('groupsTable').innerHTML = `
            <div class="mb-3">
                <button class="btn btn-outline-secondary btn-sm" onclick="LecturerUI.loadGroups()"><i class="fas fa-arrow-left me-1"></i>Back to groups</button>
                <button class="btn btn-outline-primary btn-sm ms-2" onclick="LecturerUI.statsState.groupFilter='${groupId}'; LecturerUI.statsNav('overview'); document.querySelector('[data-bs-target=\\'#statisticsTab\\']').click();">Group statistics</button>
            </div>
            <div class="card p-3 mb-3">
                <h5 class="mb-1">${this.escapeHtml(data.name)}</h5>
                <p class="text-muted mb-0">${data.student_count} students · ${data.average_percentage != null ? `Avg ${data.average_percentage}%` : 'No grades yet'}</p>
            </div>
            ${this.tableHtml(['Username', 'Student ID', 'Actions'], rows)}`;
    },

    filterStudentsByGroup(groupId) {
        document.getElementById('studentGroupFilter').value = String(groupId);
        document.querySelector('[data-bs-target="#studentsTab"]').click();
        this.loadStudents();
    },

    showGroupModal(id) {
        document.getElementById('groupEditId').value = id || '';
        document.getElementById('groupModalTitle').textContent = id ? 'Edit Group' : 'Create Group';
        if (id) {
            const g = (this.groups || []).find(x => x.id === id);
            document.getElementById('groupName').value = (g && g.name) || '';
            document.getElementById('groupDescription').value = (g && g.description) || '';
        } else {
            document.getElementById('groupName').value = '';
            document.getElementById('groupDescription').value = '';
        }
        new bootstrap.Modal(document.getElementById('groupModal')).show();
    },

    async saveGroup() {
        const id = document.getElementById('groupEditId').value;
        const name = document.getElementById('groupName').value.trim();
        const description = document.getElementById('groupDescription').value.trim();
        if (!name) return alert('Group name required');
        try {
            if (id) {
                await this.api('PUT', `/api/v1/groups/${id}`, { name, description });
            } else {
                await this.api('POST', '/api/v1/groups', { name, description });
            }
            bootstrap.Modal.getInstance(document.getElementById('groupModal')).hide();
            await this.loadGroups();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async deleteGroup(id) {
        if (!confirm('Delete this group? Students will move to Unassigned.')) return;
        try {
            await this.api('DELETE', `/api/v1/groups/${id}`);
            await this.loadGroups();
        } catch (e) { alert('Error: ' + e.message); }
    },

    // --- Students ---
    async loadStudents() {
        var groupFilterEl = document.getElementById('studentGroupFilter');
        const groupFilter = groupFilterEl ? coalesce(groupFilterEl.value, '') : '';
        const params = groupFilter !== '' ? `?group_id=${encodeURIComponent(groupFilter)}` : '';
        const students = await this.api('GET', `/api/v1/students${params}`);
        const rows = students.map(s => `<tr>
            <td>${s.id}</td>
            <td>${this.escapeHtml(s.username)}</td>
            <td>${this.escapeHtml(s.student_id || '-')}</td>
            <td>${this.escapeHtml(s.group_name || 'Unassigned')}</td>
            <td>
                <button class="btn btn-sm btn-outline-secondary me-1" onclick="LecturerUI.showStudentModal(${s.id})">Edit</button>
                <button class="btn btn-sm btn-outline-danger" onclick="LecturerUI.deleteStudent(${s.id})">Delete</button>
            </td>
        </tr>`);
        document.getElementById('studentsTable').innerHTML = this.tableHtml(
            ['ID', 'Username', 'Student ID', 'Group', 'Actions'], rows
        );
    },

    async showStudentModal(id) {
        document.getElementById('studentEditId').value = id || '';
        document.getElementById('studentModalTitle').textContent = id ? 'Edit Student' : 'Add Student';
        document.getElementById('studentPasswordHint').textContent = id ? 'Leave blank to keep current password' : '';
        document.getElementById('studentPassword').required = !id;
        if (id) {
            const s = await this.api('GET', `/api/v1/students/${id}`);
            document.getElementById('studentUsername').value = s.username;
            document.getElementById('studentPassword').value = '';
            document.getElementById('studentIdField').value = s.student_id || '';
            this.populateGroupSelects(s.group_id != null ? s.group_id : '');
        } else {
            document.getElementById('studentUsername').value = '';
            document.getElementById('studentPassword').value = '';
            document.getElementById('studentIdField').value = '';
            this.populateGroupSelects('');
        }
        new bootstrap.Modal(document.getElementById('studentModal')).show();
    },

    async saveStudent() {
        const id = document.getElementById('studentEditId').value;
        const username = document.getElementById('studentUsername').value.trim();
        const password = document.getElementById('studentPassword').value;
        const student_id = document.getElementById('studentIdField').value.trim() || null;
        const groupRaw = document.getElementById('studentGroupSelect').value;
        const group_id = groupRaw === '' ? 0 : parseInt(groupRaw, 10);
        if (!username) return alert('Username required');
        if (!id && !password) return alert('Password required');
        try {
            const payload = { username, student_id, group_id };
            if (password) payload.password = password;
            if (id) {
                await this.api('PUT', `/api/v1/students/${id}`, payload);
            } else {
                payload.password = password;
                await this.api('POST', '/api/v1/students', payload);
            }
            bootstrap.Modal.getInstance(document.getElementById('studentModal')).hide();
            await this.loadStudents();
            await this.loadGroups();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async deleteStudent(id) {
        if (!confirm('Delete this student?')) return;
        try {
            await this.api('DELETE', `/api/v1/students/${id}`);
            await this.loadStudents();
        } catch (e) { alert('Error: ' + e.message); }
    },

    async importStudents(input) {
        if (!input.files.length) return;
        const formData = new FormData();
        formData.append('file', input.files[0]);
        try {
            const res = await fetch('/api/v1/students/import', { method: 'POST', credentials: 'include', body: formData });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);
            alert(`Imported ${data.imported} students.${data.errors ? ` ${data.errors} errors.` : ''}`);
            await this.loadStudents();
        } catch (e) { alert('Error: ' + e.message); }
        input.value = '';
    }
};
