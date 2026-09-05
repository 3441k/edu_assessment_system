/** Lecturer web dashboard UI */
const LecturerUI = {
    topics: [],
    questions: [],
    tests: [],
    allQuestions: [],

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
        const json = res.headers.get('content-type')?.includes('json') ? await res.json() : null;
        if (!res.ok) throw new Error(json?.error || `Request failed (${res.status})`);
        return json;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text ?? '';
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
        } catch {
            window.location.href = '/lecturer/login';
            return;
        }

        await this.loadTopics();
        await this.loadQuestions();
        document.getElementById('topicFilter').addEventListener('change', () => this.loadQuestions());

        document.querySelector('[data-bs-target="#testsTab"]')?.addEventListener('shown.bs.tab', () => {
            this.loadTests();
            if (this._testsPoll) clearInterval(this._testsPoll);
            this._testsPoll = setInterval(() => this.loadTests(), 5000);
        });
        document.querySelector('[data-bs-target="#questionsTab"]')?.addEventListener('shown.bs.tab', () => {
            if (this._testsPoll) { clearInterval(this._testsPoll); this._testsPoll = null; }
        });
        document.querySelector('[data-bs-target="#gradingTab"]')?.addEventListener('shown.bs.tab', () => this.loadGrading());
        document.querySelector('[data-bs-target="#statisticsTab"]')?.addEventListener('shown.bs.tab', () => this.loadStatistics());
        document.querySelector('[data-bs-target="#studentsTab"]')?.addEventListener('shown.bs.tab', () => this.loadStudents());
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
            const tc = document.getElementById('codeTestCases')?.value.trim();
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
    async loadStatistics() {
        const view = document.getElementById('statsView').value;
        const el = document.getElementById('statisticsContent');
        el.innerHTML = '<div class="text-center"><div class="spinner-border"></div></div>';

        try {
            if (view === 'overview') {
                const s = await this.api('GET', '/api/v1/statistics/overview');
                el.innerHTML = `<div class="row">${[
                    ['Students', s.total_students], ['Tests', s.total_tests],
                    ['Questions', s.total_questions], ['Submissions', s.total_submissions],
                    ['Graded', s.total_graded]
                ].map(([label, val]) => `<div class="col-md-4 mb-3"><div class="card stat-card"><h3>${val}</h3><p class="text-muted mb-0">${label}</p></div></div>`).join('')}</div>`;
            } else if (view === 'topics') {
                const data = await this.api('GET', '/api/v1/statistics/topics');
                el.innerHTML = this.tableHtml(['Topic', 'Questions', 'Avg Score', 'Submissions'],
                    data.map(t => `<tr><td>${this.escapeHtml(t.topic_name)}</td><td>${t.question_count}</td><td>${t.average_score}</td><td>${t.submission_count}</td></tr>`));
            } else if (view === 'students') {
                const data = await this.api('GET', '/api/v1/statistics/students');
                el.innerHTML = this.tableHtml(['Student', 'Tests Graded', 'Avg Percentage'],
                    data.map(s => `<tr><td>${this.escapeHtml(s.username)}</td><td>${s.total_tests}</td><td>${s.average_percentage}%</td></tr>`));
            } else if (view === 'tests') {
                const tests = await this.api('GET', '/api/v1/tests');
                if (!tests.length) { el.innerHTML = '<div class="alert alert-info">No tests.</div>'; return; }
                let html = '<div class="list-group">';
                for (const t of tests) {
                    const stats = await this.api('GET', `/api/v1/statistics/tests/${t.id}`);
                    html += `<div class="list-group-item"><strong>${this.escapeHtml(t.name)}</strong>
                        &mdash; Submissions: ${stats.total_submissions ?? stats.submission_count ?? '-'}, Avg: ${stats.average_percentage ?? '-'}%</div>`;
                }
                html += '</div>';
                el.innerHTML = html;
            }
        } catch (e) {
            el.innerHTML = `<div class="alert alert-danger">${this.escapeHtml(e.message)}</div>`;
        }
    },

    // --- Students ---
    async loadStudents() {
        const students = await this.api('GET', '/api/v1/students');
        const rows = students.map(s => `<tr>
            <td>${s.id}</td>
            <td>${this.escapeHtml(s.username)}</td>
            <td>${this.escapeHtml(s.student_id || '-')}</td>
            <td><button class="btn btn-sm btn-outline-danger" onclick="LecturerUI.deleteStudent(${s.id})">Delete</button></td>
        </tr>`);
        document.getElementById('studentsTable').innerHTML = this.tableHtml(
            ['ID', 'Username', 'Student ID', 'Actions'], rows
        );
    },

    showStudentModal() {
        document.getElementById('studentUsername').value = '';
        document.getElementById('studentPassword').value = '';
        document.getElementById('studentIdField').value = '';
        new bootstrap.Modal(document.getElementById('studentModal')).show();
    },

    async saveStudent() {
        const username = document.getElementById('studentUsername').value.trim();
        const password = document.getElementById('studentPassword').value;
        const student_id = document.getElementById('studentIdField').value.trim() || null;
        if (!username || !password) return alert('Username and password required');
        try {
            await this.api('POST', '/api/v1/students', { username, password, student_id });
            bootstrap.Modal.getInstance(document.getElementById('studentModal')).hide();
            await this.loadStudents();
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
