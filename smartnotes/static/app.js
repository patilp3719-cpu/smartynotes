document.addEventListener('DOMContentLoaded', () => {
    // State
    let notes = [];
    let currentNoteId = null;
    let saveTimeout = null;
    let aiPollingInterval = null;
    let askPanelOpen = false;

    // DOM Elements
    const themeToggle = document.getElementById('theme-toggle');
    const noteList = document.getElementById('note-list');
    const newNoteBtn = document.getElementById('new-note-btn');
    const searchInput = document.getElementById('search-input');
    
    const editorContainer = document.getElementById('editor-container');
    const emptyState = document.getElementById('empty-state');
    
    const noteTitle = document.getElementById('note-title');
    const noteContent = document.getElementById('note-content');
    const noteDueDate = document.getElementById('note-due-date');
    const addTagInput = document.getElementById('add-tag-input');
    const noteTags = document.getElementById('note-tags');
    const saveStatus = document.getElementById('save-status');
    const deleteBtn = document.getElementById('delete-btn');
    
    const aiInsightsCard = document.getElementById('ai-insights-card');
    const aiSummary = document.getElementById('ai-summary');
    const aiPriority = document.getElementById('ai-priority');
    const aiTags = document.getElementById('ai-tags');
    
    const askHeader = document.getElementById('ask-header');
    const askBody = document.getElementById('ask-body');
    const askToggle = document.getElementById('ask-toggle');
    const askInput = document.getElementById('ask-input');
    const askBtn = document.getElementById('ask-btn');
    const askHistory = document.getElementById('ask-history');
    const toastContainer = document.getElementById('toast-container');

    // Initialization
    initTheme();
    loadNotes();
    startReminderPolling();
    requestNotificationPermission();

    // Event Listeners
    themeToggle.addEventListener('click', toggleTheme);
    newNoteBtn.addEventListener('click', createNote);
    searchInput.addEventListener('input', debounce(() => loadNotes(searchInput.value), 300));
    
    noteTitle.addEventListener('input', scheduleSave);
    noteContent.addEventListener('input', scheduleSave);
    noteDueDate.addEventListener('change', scheduleSave);
    addTagInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && addTagInput.value.trim()) {
            addManualTag(addTagInput.value.trim());
            addTagInput.value = '';
        }
    });
    document.querySelectorAll('.quick-tag').forEach(tagEl => {
        tagEl.addEventListener('click', () => {
            addManualTag(tagEl.dataset.tag);
        });
    });
    deleteBtn.addEventListener('click', deleteCurrentNote);
    
    const reEnrichBtn = document.getElementById('re-enrich-btn');
    reEnrichBtn.addEventListener('click', forceReEnrich);
    
    askHeader.addEventListener('click', toggleAskPanel);
    askBtn.addEventListener('click', sendAskQuestion);
    askInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendAskQuestion();
    });

    // Theme
    function initTheme() {
        const isDark = localStorage.getItem('theme') === 'dark';
        if (isDark) document.documentElement.setAttribute('data-theme', 'dark');
    }

    function toggleTheme() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDark) {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
    }

    // API Calls
    async function apiRequest(endpoint, options = {}) {
        try {
            const res = await fetch(`/api${endpoint}`, {
                ...options,
                headers: { 'Content-Type': 'application/json', ...options.headers }
            });
            if (!res.ok) throw new Error(`API Error: ${res.status}`);
            return await res.json();
        } catch (err) {
            console.error(err);
            showToast(err.message, 'error');
            throw err;
        }
    }

    async function loadNotes(query = '') {
        const url = query ? `/notes?q=${encodeURIComponent(query)}` : '/notes';
        notes = await apiRequest(url);
        renderNoteList();
    }

    // Rendering
    function renderNoteList() {
        noteList.innerHTML = '';
        notes.forEach(note => {
            const li = document.createElement('li');
            li.className = `note-item ${currentNoteId === note.id ? 'active' : ''}`;
            li.onclick = () => selectNote(note.id);
            
            const title = note.title || 'Untitled';
            const contentPreview = note.content ? note.content.substring(0, 50) + '...' : 'No content';
            const isDue = note.due_date && new Date(note.due_date) < new Date();
            
            li.innerHTML = `
                <h4>${escapeHTML(title)} ${isDue ? '<span class="due-badge">Due</span>' : ''}</h4>
                <p>${escapeHTML(contentPreview)}</p>
            `;
            noteList.appendChild(li);
        });
    }

    async function selectNote(id) {
        if (currentNoteId === id) return;
        currentNoteId = id;
        renderNoteList(); // Update active state
        
        try {
            const note = await apiRequest(`/notes/${id}`);
            
            editorContainer.classList.remove('hidden');
            emptyState.classList.add('hidden');
            
            noteTitle.value = note.title || '';
            noteContent.value = note.content || '';
            if (note.due_date) {
                // Ensure correct format for datetime-local
                const d = new Date(note.due_date);
                noteDueDate.value = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
            } else {
                noteDueDate.value = '';
            }
            
            renderTags(note.tags || []);
            renderAiInsights(note);
            
            // Poll for AI updates if recently updated
            startAiPolling(id);
            saveStatus.textContent = 'Saved';
        } catch (err) {
            currentNoteId = null;
            editorContainer.classList.add('hidden');
            emptyState.classList.remove('hidden');
        }
    }

    async function createNote() {
        const note = await apiRequest('/notes', {
            method: 'POST',
            body: JSON.stringify({ title: 'New Note', content: '' })
        });
        await loadNotes(searchInput.value);
        selectNote(note.id);
    }

    async function deleteCurrentNote() {
        if (!currentNoteId) return;
        if (!confirm('Send this note to the shadow realm? 🌌')) return;
        
        // Stop AI polling immediately so it doesn't try to fetch a deleted note
        if (aiPollingInterval) {
            clearInterval(aiPollingInterval);
            aiPollingInterval = null;
        }
        
        const idToDelete = currentNoteId;
        currentNoteId = null;
        editorContainer.classList.add('hidden');
        emptyState.classList.remove('hidden');
        
        try {
            await apiRequest(`/notes/${idToDelete}`, { method: 'DELETE' });
        } catch (err) {
            // Note might already be gone, that's fine
            console.warn('Delete request error (may be already deleted):', err);
        }
        
        await loadNotes(searchInput.value);
    }

    // Saving
    function scheduleSave() {
        saveStatus.textContent = 'Scribbling furiously... ✍️';
        if (saveTimeout) clearTimeout(saveTimeout);
        saveTimeout = setTimeout(saveNote, 1000);
    }

    async function saveNote() {
        if (!currentNoteId) return;
        
        let due_date = null;
        if (noteDueDate.value) {
            due_date = new Date(noteDueDate.value).toISOString();
        }
        
        const updateData = {
            title: noteTitle.value,
            content: noteContent.value,
            due_date: due_date
            // Tags are handled separately
        };
        
        try {
            const updated = await apiRequest(`/notes/${currentNoteId}`, {
                method: 'PUT',
                body: JSON.stringify(updateData)
            });
            saveStatus.textContent = 'Safe & Sound 🛡️';
            
            // Update local notes array and re-render list
            const index = notes.findIndex(n => n.id === currentNoteId);
            if (index !== -1) {
                notes[index] = updated;
                renderNoteList();
            }
            startAiPolling(currentNoteId);
        } catch {
            saveStatus.textContent = 'Error saving';
        }
    }

    // Tags
    function renderTags(tags) {
        noteTags.innerHTML = '';
        tags.forEach(tag => {
            const el = document.createElement('div');
            el.className = 'tag';
            el.innerHTML = `<span>${escapeHTML(tag)}</span><span class="remove-tag" data-tag="${escapeHTML(tag)}">&times;</span>`;
            el.querySelector('.remove-tag').onclick = () => removeTag(tag);
            noteTags.appendChild(el);
        });
    }

    async function addManualTag(tag) {
        if (!currentNoteId) return;
        const note = notes.find(n => n.id === currentNoteId);
        let tags = note.tags || [];
        if (!tags.includes(tag)) {
            tags.push(tag);
            await apiRequest(`/notes/${currentNoteId}`, {
                method: 'PUT',
                body: JSON.stringify({ tags })
            });
            note.tags = tags;
            renderTags(tags);
        }
    }

    async function removeTag(tag) {
        if (!currentNoteId) return;
        const note = notes.find(n => n.id === currentNoteId);
        let tags = note.tags || [];
        tags = tags.filter(t => t !== tag);
        await apiRequest(`/notes/${currentNoteId}`, {
            method: 'PUT',
            body: JSON.stringify({ tags })
        });
        note.tags = tags;
        renderTags(tags);
    }

    // AI Insights
    function renderAiInsights(note) {
        if (note.ai_summary || note.ai_priority || (note.ai_tags && note.ai_tags.length)) {
            aiInsightsCard.classList.remove('hidden');
            aiSummary.textContent = note.ai_summary || 'N/A';
            aiPriority.textContent = note.ai_priority || 'N/A';
            
            aiTags.innerHTML = '';
            if (note.ai_tags) {
                note.ai_tags.forEach(tag => {
                    const el = document.createElement('div');
                    el.className = 'tag suggested';
                    el.title = "Click to add";
                    el.innerHTML = `<span>${escapeHTML(tag)}</span> <span style="font-size: 10px;">+</span>`;
                    el.onclick = () => { addManualTag(tag); el.remove(); };
                    aiTags.appendChild(el);
                });
            }
        } else {
            aiInsightsCard.classList.add('hidden');
        }
    }

    async function forceReEnrich() {
        if (!currentNoteId) return;
        
        // Show loading state
        aiSummary.textContent = 'Re-analyzing with AI... 🤖';
        aiPriority.textContent = '...';
        aiTags.innerHTML = '';
        
        try {
            await apiRequest(`/notes/${currentNoteId}/enrich`, { method: 'POST' });
            // Start polling for the updated AI data
            startAiPolling(currentNoteId);
        } catch (err) {
            aiSummary.textContent = 'Re-analysis failed. Check your API key.';
        }
    }
    
    function startAiPolling(noteId) {
        if (aiPollingInterval) clearInterval(aiPollingInterval);
        
        let attempts = 0;
        aiPollingInterval = setInterval(async () => {
            if (currentNoteId !== noteId || attempts > 10) {
                clearInterval(aiPollingInterval);
                return;
            }
            try {
                const note = await apiRequest(`/notes/${noteId}`);
                renderAiInsights(note);
                if (note.ai_summary) {
                    clearInterval(aiPollingInterval);
                }
            } catch (e) {
                clearInterval(aiPollingInterval);
            }
            attempts++;
        }, 2000);
    }

    // Ask Notes
    function toggleAskPanel() {
        askPanelOpen = !askPanelOpen;
        if (askPanelOpen) {
            askBody.classList.remove('hidden');
            askToggle.textContent = '▼';
        } else {
            askBody.classList.add('hidden');
            askToggle.textContent = '▲';
        }
    }

    async function sendAskQuestion() {
        const q = askInput.value.trim();
        if (!q) return;
        
        appendAskMessage(q, 'user');
        askInput.value = '';
        
        try {
            const res = await apiRequest('/ask', {
                method: 'POST',
                body: JSON.stringify({ question: q })
            });
            let answerHtml = escapeHTML(res.answer);
            if (res.source_note_ids && res.source_note_ids.length) {
                answerHtml += `<span class="chat-sources">Sources: ${res.source_note_ids.join(', ')}</span>`;
            }
            appendAskMessage(answerHtml, 'ai', true);
        } catch {
            appendAskMessage('Error getting answer.', 'ai');
        }
    }

    function appendAskMessage(text, role, isHtml = false) {
        const div = document.createElement('div');
        div.className = `chat-msg chat-${role}`;
        if (isHtml) {
            div.innerHTML = text;
        } else {
            div.textContent = text;
        }
        askHistory.appendChild(div);
        askHistory.scrollTop = askHistory.scrollHeight;
    }

    // Reminders
    function startReminderPolling() {
        setInterval(async () => {
            try {
                const res = await apiRequest('/reminders/due');
                if (res.reminders && res.reminders.length) {
                    res.reminders.forEach(r => {
                        const msg = `Reminder: ${r.title}`;
                        showToast(msg, 'info');
                        if (Notification.permission === 'granted') {
                            new Notification('SmartNotes Reminder', { body: msg });
                        }
                    });
                    loadNotes(searchInput.value); // Reload to update badges
                }
            } catch (e) { }
        }, 30000); // Poll every 30s
    }
    
    function requestNotificationPermission() {
        if ('Notification' in window && Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }

    // Utilities
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => { clearTimeout(timeout); func(...args); };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function escapeHTML(str) {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }
});
