const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');
const tasksList = document.getElementById('tasksList');
const toast = document.getElementById('toast');

let debounceTimer;

// Handle Search Input
searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const query = e.target.value.trim();
    
    if (query.length < 3) {
        searchResults.classList.add('hidden');
        return;
    }

    debounceTimer = setTimeout(async () => {
        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            renderResults(data);
        } catch (err) {
            console.error('Search error:', err);
        }
    }, 500);
});

// Render TMDB Results
function renderResults(results) {
    searchResults.innerHTML = '';
    
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="result-item"><p>No results found.</p></div>';
        searchResults.classList.remove('hidden');
        return;
    }

    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'result-item';
        
        const posterUrl = item.poster_path ? `https://image.tmdb.org/t/p/w92${item.poster_path}` : 'https://via.placeholder.com/50x75?text=No+Image';
        
        div.innerHTML = `
            <img src="${posterUrl}" class="result-poster" alt="${item.title}">
            <div class="result-info">
                <h4>${item.title}</h4>
                <p>${item.year} • ${item.media_type ? item.media_type.toUpperCase() : 'Unknown'}</p>
            </div>
        `;
        
        div.addEventListener('click', () => fetchTorrent(item.title, item.year));
        searchResults.appendChild(div);
    });
    
    searchResults.classList.remove('hidden');
}

// Fetch Torrent
async function fetchTorrent(title, year) {
    searchInput.value = '';
    searchResults.classList.add('hidden');
    showToast(`Searching for torrents: ${title}...`);
    
    try {
        const res = await fetch('/api/fetch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: title, year: year })
        });
        
        const data = await res.json();
        if (res.ok) {
            showToast(`Started downloading: ${data.torrent.title}`);
            pollStatus();
        } else {
            showToast(`Error: ${data.detail}`, true);
        }
    } catch (err) {
        console.error('Fetch error:', err);
        showToast('Failed to start fetch.', true);
    }
}

// Dashboard Polling
async function pollStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        renderTasks(data.tasks || []);
    } catch (err) {
        console.error('Status error:', err);
    }
}

function renderTasks(tasks) {
    if (tasks.length === 0) {
        tasksList.innerHTML = `
            <tr id="emptyStateRow">
                <td colspan="4" class="empty-state">No transfers found. Search for something to get started!</td>
            </tr>`;
        return;
    }

    let html = '';
    tasks.forEach(task => {
        let statusDisplay = task.status;
        if (statusDisplay === 'upload_failed') statusDisplay = 'upload failed';

        html += `
            <tr>
                <td class="task-title" title="${task.title}">${task.title}</td>
                <td><span class="task-status status-${task.status}">${statusDisplay}</span></td>
                <td class="progress-cell">
                    <div style="width: 100%; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden; margin-bottom: 4px;">
                        <div style="width: ${task.progress_string || '0%'}; background: linear-gradient(90deg, #6366f1, #a855f7); height: 100%; transition: width 0.3s ease;"></div>
                    </div>
                    <span style="font-size: 0.8rem; color: var(--text-secondary);">${task.progress_string || '0%'}</span>
                </td>
                <td class="task-speed">${task.download_speed || '-'}</td>
            </tr>
        `;
    });

    tasksList.innerHTML = html;
}

// Toast Notification
function showToast(message, isError = false) {
    toast.textContent = message;
    toast.style.background = isError ? '#ef4444' : '#10b981';
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Hide dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.classList.add('hidden');
    }
});

// Initial poll and interval
pollStatus();
setInterval(pollStatus, 3000);
