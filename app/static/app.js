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
        renderTasks(data);
    } catch (err) {
        console.error('Status error:', err);
    }
}

function renderTasks(tasksObj) {
    const tasks = Object.values(tasksObj);
    
    if (tasks.length === 0) {
        tasksList.innerHTML = '<div class="empty-state">No active downloads. Search for something to get started!</div>';
        return;
    }

    tasksList.innerHTML = '';
    
    tasks.forEach(task => {
        const div = document.createElement('div');
        div.className = 'task-card';
        
        let progressNum = parseFloat(task.progress) || 0;
        if (task.status === 'completed') progressNum = 100;
        
        div.innerHTML = `
            <div class="task-header">
                <div class="task-title">${task.title}</div>
                <div class="task-status">${task.status}</div>
            </div>
            <div class="progress-track">
                <div class="progress-fill" style="width: ${progressNum}%"></div>
            </div>
            <div class="task-meta">
                <span>${task.progress}</span>
                <span>${task.speed || ''}</span>
            </div>
        `;
        tasksList.appendChild(div);
    });
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
