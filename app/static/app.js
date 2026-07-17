const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');
const tasksList = document.getElementById('tasksList');
const toast = document.getElementById('toast');

// Modal Elements
const torrentModal = document.getElementById('torrentModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const torrentLoader = document.getElementById('torrentLoader');
const torrentList = document.getElementById('torrentList');

// TV Modal Elements
const tvModal = document.getElementById('tvModal');
const closeTvModalBtn = document.getElementById('closeTvModalBtn');
const tvLoader = document.getElementById('tvLoader');
const tvContent = document.getElementById('tvContent');
const seasonGrid = document.getElementById('seasonGrid');
const episodeList = document.getElementById('episodeList');
const episodesTitle = document.getElementById('episodesTitle');
const tvModalTitle = document.getElementById('tvModalTitle');

let debounceTimer;
let currentFilter = 'all';
let currentTvShow = null;
let globalTasks = [];

const fallbackPoster = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="92" height="138" viewBox="0 0 92 138"%3E%3Crect width="92" height="138" fill="%23222222"/%3E%3Cpath d="M28 42h36v54H28zM28 56h36M38 42v14M54 42v14" fill="none" stroke="%23888888" stroke-width="4"/%3E%3C/svg%3E';

function getPosterUrl(posterPath, size = 'w92') {
    return posterPath && /^\/[A-Za-z0-9._/-]+$/.test(posterPath)
        ? `https://image.tmdb.org/t/p/${size}${posterPath}`
        : fallbackPoster;
}

function escapeHtml(value) {
    const element = document.createElement('div');
    element.textContent = value ?? '';
    return element.innerHTML;
}

// Modal Logic
function openModal() {
    torrentModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    torrentModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
}

function openTvModalHandler() {
    tvModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeTvModal() {
    tvModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
}

if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
if (torrentModal) torrentModal.addEventListener('click', (e) => {
    if (e.target === torrentModal) closeModal();
});

if (closeTvModalBtn) closeTvModalBtn.addEventListener('click', closeTvModal);
if (tvModal) tvModal.addEventListener('click', (e) => {
    if (e.target === tvModal) closeTvModal();
});

// Dashboard Filtering
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentFilter = e.target.getAttribute('data-filter');
        pollStatus(); // re-render
    });
});

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
        
        const posterUrl = getPosterUrl(item.poster_path);
        
        div.innerHTML = `
            <img src="${posterUrl}" class="result-poster" alt="${item.title}">
            <div class="result-info">
                <h4>${item.title}</h4>
                <p>${item.year} • ${item.media_type ? item.media_type.toUpperCase() : 'Unknown'}</p>
            </div>
        `;
        
        div.addEventListener('click', () => {
            if (item.media_type === 'tv') {
                openTvModal(item.id, item.title, item.year, item.poster_path);
            } else {
                fetchTorrent(item.title, item.year, 'movie', null, null, item.poster_path);
            }
        });
        searchResults.appendChild(div);
    });
    
    searchResults.classList.remove('hidden');
}

// TV Modal Flow
async function openTvModal(tv_id, title, year, poster_path) {
    searchInput.value = '';
    searchResults.classList.add('hidden');
    
    currentTvShow = { title, year, poster_path };
    tvModalTitle.textContent = title;
    
    seasonGrid.innerHTML = '';
    episodeList.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.9rem;">Select a season to view episodes.</p>';
    episodesTitle.textContent = 'Episodes';
    
    tvLoader.classList.remove('hidden');
    tvContent.classList.add('hidden');
    openTvModalHandler();
    
    try {
        const res = await fetch(`/api/tv/${tv_id}`);
        const data = await res.json();
        
        tvLoader.classList.add('hidden');
        tvContent.classList.remove('hidden');
        
        renderSeasons(tv_id, data.seasons || []);
    } catch (err) {
        tvLoader.classList.add('hidden');
        seasonGrid.innerHTML = `<p style="color: #ff4757;">Failed to load seasons.</p>`;
        tvContent.classList.remove('hidden');
    }
}

function renderSeasons(tv_id, seasons) {
    seasonGrid.innerHTML = '';
    seasons.forEach(s => {
        const btn = document.createElement('button');
        btn.className = 'season-btn';
        btn.textContent = `Season ${s.season_number}`;
        
        btn.addEventListener('click', () => {
            document.querySelectorAll('.season-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadEpisodes(tv_id, s.season_number);
        });
        
        seasonGrid.appendChild(btn);
    });
}

async function loadEpisodes(tv_id, season_number) {
    episodesTitle.textContent = `Season ${season_number} Episodes`;
    episodeList.innerHTML = '';
    const loader = document.getElementById('episodeLoader');
    loader.classList.remove('hidden');
    
    try {
        const res = await fetch(`/api/tv/${tv_id}/season/${season_number}`);
        const episodes = await res.json();
        loader.classList.add('hidden');
        
        const showTitleLower = currentTvShow.title.toLowerCase();
        const showTitleParts = showTitleLower.replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(w => w.length > 0);
        const seasonPadded = String(season_number).padStart(2, '0');
        const seasonMatchers = [`s${seasonPadded}`, `season ${season_number}`, `season ${seasonPadded}`];
        
        const hasFullSeason = globalTasks.some(t => {
            if (t.media_type !== 'tv') return false;
            const tTitleLower = t.title.toLowerCase().replace(/[^a-z0-9\s]/g, '');
            const containsShow = showTitleParts.every(w => tTitleLower.includes(w));
            if (!containsShow) return false;
            // Matches season but does not match an episode pattern
            return seasonMatchers.some(m => tTitleLower.includes(m.replace(/\s/g, ''))) && !tTitleLower.match(/e\d{1,2}/);
        });

        const fullSeasonBadge = hasFullSeason ? `<span style="background: rgba(255,255,255,0.1); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: 8px; border: 1px solid rgba(255,255,255,0.2);">✓ Added</span>` : '';
        
        // Add "Full Season" button
        const fullSeasonItem = document.createElement('div');
        fullSeasonItem.className = 'episode-item';
        fullSeasonItem.style.flexDirection = 'column';
        fullSeasonItem.style.alignItems = 'stretch';
        fullSeasonItem.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                <div class="episode-info">
                    <h4>Full Season ${season_number} Pack ${fullSeasonBadge}</h4>
                    <p>Download the entire season</p>
                </div>
                <button class="find-torrents-btn">Find Torrents</button>
            </div>
            <div class="inline-torrent-container"></div>
        `;
        fullSeasonItem.querySelector('button').addEventListener('click', () => {
            fetchTorrentInline(currentTvShow.title, currentTvShow.year, 'tv', season_number, null, currentTvShow.poster_path, fullSeasonItem.querySelector('.inline-torrent-container'));
        });
        episodeList.appendChild(fullSeasonItem);
        
        // Add individual episodes
        episodes.forEach(ep => {
            const epPadded = String(ep.episode_number).padStart(2, '0');
            const epMatchers = [`s${seasonPadded}e${epPadded}`, `${season_number}x${epPadded}`];
            
            const hasEpisode = hasFullSeason || globalTasks.some(t => {
                if (t.media_type !== 'tv') return false;
                const tTitleLower = t.title.toLowerCase().replace(/[^a-z0-9\s]/g, '');
                const containsShow = showTitleParts.every(w => tTitleLower.includes(w));
                if (!containsShow) return false;
                return epMatchers.some(m => tTitleLower.includes(m.replace(/[^a-z0-9]/g, '')));
            });

            const episodeBadge = hasEpisode ? `<span style="background: rgba(255,255,255,0.1); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: 8px; border: 1px solid rgba(255,255,255,0.2);">✓ Added</span>` : '';

            const item = document.createElement('div');
            item.className = 'episode-item';
            item.style.flexDirection = 'column';
            item.style.alignItems = 'stretch';
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <div class="episode-info">
                        <h4>${ep.episode_number}. ${ep.name} ${episodeBadge}</h4>
                    </div>
                    <button class="find-torrents-btn">Find Torrents</button>
                </div>
                <div class="inline-torrent-container"></div>
            `;
            item.querySelector('button').addEventListener('click', () => {
                fetchTorrentInline(currentTvShow.title, currentTvShow.year, 'tv', season_number, ep.episode_number, currentTvShow.poster_path, item.querySelector('.inline-torrent-container'));
            });
            episodeList.appendChild(item);
        });
        
    } catch (err) {
        loader.classList.add('hidden');
        episodeList.innerHTML = `<p style="color: #ff4757;">Failed to load episodes.</p>`;
    }
}


// Fetch Torrent list inline
async function fetchTorrentInline(title, year, media_type, season, episode, poster_path, container) {
    if (container.innerHTML !== '') {
        // Toggle visibility if already loaded
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = '<div class="inline-loader">Searching torrents...</div>';
    
    try {
        const payload = { query: title, year: year, season: season };
        if (episode !== null) payload.episode = episode;

        const res = await fetch('/api/search_torrents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const torrents = await res.json();
        
        if (res.ok && torrents.length > 0) {
            renderInlineTorrents(torrents, media_type, poster_path, container);
        } else {
            container.innerHTML = `<div class="inline-torrent-dropdown"><p style="text-align:center; color: var(--text-secondary);">No torrents found.</p></div>`;
        }
    } catch (err) {
        console.error('Fetch error:', err);
        container.innerHTML = `<div class="inline-torrent-dropdown"><p style="text-align:center; color: #ff4757;">Failed to fetch torrents.</p></div>`;
    }
}

function renderInlineTorrents(torrents, media_type, poster_path, container) {
    container.innerHTML = '<div class="inline-torrent-dropdown"></div>';
    const dropdown = container.querySelector('.inline-torrent-dropdown');
    
    torrents.forEach((t, index) => {
        const item = document.createElement('div');
        item.className = 'inline-torrent-item';
        
        const sizeMb = (t.size_bytes / (1024 * 1024)).toFixed(2);
        const sizeGb = (t.size_bytes / (1024 * 1024 * 1024)).toFixed(2);
        const sizeStr = sizeGb >= 1 ? `${sizeGb} GB` : `${sizeMb} MB`;
        
        item.innerHTML = `
            <div class="torrent-title" style="font-size: 0.95rem;">${t.title}</div>
            <div class="torrent-meta" style="font-size: 0.8rem;">
                <div class="torrent-badge">${t.resolution || t.source}</div>
                <div class="seeders">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    ${t.seeders}
                </div>
                <div class="size">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    ${sizeStr}
                </div>
            </div>
        `;
        
        const remainingFallbacks = torrents.filter((_, i) => i !== index).map(tor => tor.magnet);
        
        item.addEventListener('click', () => {
            startDownload({
                title: t.title,
                magnet: t.magnet,
                fallback_magnets: remainingFallbacks,
                media_type: media_type,
                poster_path: poster_path
            });
        });
        
        dropdown.appendChild(item);
    });
}

// Fetch Torrent list and show modal
async function fetchTorrent(title, year, media_type = 'movie', season = null, episode = null, poster_path = null) {
    searchInput.value = '';
    searchResults.classList.add('hidden');
    
    torrentList.innerHTML = '';
    torrentLoader.classList.remove('hidden');
    openModal();
    
    try {
        const payload = { query: title, year: year };
        if (season !== null) payload.season = season;
        if (episode !== null) payload.episode = episode;

        const res = await fetch('/api/search_torrents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const torrents = await res.json();
        torrentLoader.classList.add('hidden');
        
        if (res.ok && torrents.length > 0) {
            renderTorrents(torrents, media_type, poster_path);
        } else {
            torrentList.innerHTML = `<p style="text-align:center; color: var(--text-secondary); padding: 2rem;">No torrents found.</p>`;
        }
    } catch (err) {
        console.error('Fetch error:', err);
        torrentLoader.classList.add('hidden');
        torrentList.innerHTML = `<p style="text-align:center; color: #ef4444; padding: 2rem;">Failed to fetch torrents.</p>`;
    }
}

function renderTorrents(torrents, media_type, poster_path) {
    torrentList.innerHTML = '';
    
    torrents.forEach((t, index) => {
        const item = document.createElement('div');
        item.className = 'torrent-list-item';
        
        const sizeMb = (t.size_bytes / (1024 * 1024)).toFixed(2);
        const sizeGb = (t.size_bytes / (1024 * 1024 * 1024)).toFixed(2);
        const sizeStr = sizeGb >= 1 ? `${sizeGb} GB` : `${sizeMb} MB`;
        
        item.innerHTML = `
            <div class="torrent-title">${t.title}</div>
            <div class="torrent-meta">
                <div class="torrent-badge">${t.resolution || t.source}</div>
                <div class="seeders">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    ${t.seeders}
                </div>
                <div class="leechers">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l3-9 5 18 3-9h5"/></svg>
                    ${t.leechers}
                </div>
                <div class="size">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    ${sizeStr}
                </div>
            </div>
        `;
        
        const remainingFallbacks = torrents.filter((_, i) => i !== index).map(tor => tor.magnet);
        
        item.addEventListener('click', () => {
            startDownload({
                title: t.title,
                magnet: t.magnet,
                fallback_magnets: remainingFallbacks,
                media_type: media_type,
                poster_path: poster_path
            });
        });
        
        torrentList.appendChild(item);
    });
}

async function startDownload(payload) {
    showToast(`Started downloading: ${payload.title}`);
    
    try {
        const res = await fetch('/api/fetch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        if (res.ok) {
            pollStatus();
        } else {
            showToast(`Error: ${data.detail}`, true);
        }
    } catch (err) {
        console.error('Download error:', err);
        showToast('Failed to start download.', true);
    }
}

// Dashboard Polling
async function pollStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        globalTasks = data.tasks || [];
        renderTasks(globalTasks);
    } catch (err) {
        console.error('Status error:', err);
    }
}

function renderTasks(tasks) {
    const filteredTasks = tasks.filter(t => currentFilter === 'all' || t.media_type === currentFilter);

    if (filteredTasks.length === 0) {
        tasksList.innerHTML = `
            <tr id="emptyStateRow">
                <td colspan="5" class="empty-state">No transfers found. Search for something to get started!</td>
            </tr>`;
        return;
    }

    let html = '';
    filteredTasks.forEach(task => {
        let statusDisplay = task.status;
        if (statusDisplay === 'upload_failed') statusDisplay = 'upload failed';

        const badge = task.media_type === 'tv' ? '<span class="media-badge">TV</span>' : '<span class="media-badge">MOVIE</span>';
        const posterUrl = getPosterUrl(task.poster_path);
        const safeTitle = escapeHtml(task.title);

        html += `
            <tr>
                <td class="task-title" title="${safeTitle}" data-label="Title">
                    <div class="task-title-content">
                        <img src="${posterUrl}" class="task-poster" alt="" loading="lazy">
                        <div class="task-title-details">
                            ${badge}
                            <span>${safeTitle}</span>
                        </div>
                    </div>
                </td>
                <td data-label="Status"><span class="task-status status-${task.status}">${statusDisplay}</span></td>
                <td class="progress-cell" data-label="Progress">
                    <div style="width: 100%; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden; margin-bottom: 4px;">
                        <div style="width: ${task.progress_string || '0%'}; background: var(--text-primary); height: 100%; transition: width 0.3s ease;"></div>
                    </div>
                    <span style="font-size: 0.8rem; color: var(--text-secondary);">${task.progress_string || '0%'}</span>
                </td>
                <td class="task-speed" data-label="Speed">${task.download_speed || '-'}</td>
                <td class="task-action" data-label="Action">
                    ${(task.status === 'upload_failed' || task.status === 'failed') ? `
                    <button class="retry-btn" onclick="retryTask('${task.id}')" title="Retry Upload">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
                    </button>
                    ` : ''}
                    <button class="delete-btn" onclick="deleteTask('${task.id}')" title="Delete Task">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
                    </button>
                </td>
            </tr>
        `;
    });

    tasksList.innerHTML = html;
}

// Toast Notification
function showToast(message, isError = false) {
    toast.textContent = message;
    toast.style.background = isError ? '#ffffff' : '#ffffff';
    toast.style.color = '#000000';
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Delete Task
async function deleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) return;
    
    try {
        const res = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            showToast('Task deleted successfully');
            pollStatus();
        } else {
            const data = await res.json();
            showToast(`Error: ${data.detail || 'Failed to delete task'}`, true);
        }
    } catch (err) {
        console.error('Delete error:', err);
        showToast('Failed to delete task.', true);
    }
}

// Retry Task
async function retryTask(taskId) {
    try {
        const res = await fetch(`/api/tasks/${taskId}/retry`, {
            method: 'POST'
        });
        
        if (res.ok) {
            showToast('Retry started successfully');
            pollStatus();
        } else {
            const data = await res.json();
            showToast(`Error: ${data.detail || 'Failed to retry task'}`, true);
        }
    } catch (err) {
        console.error('Retry error:', err);
        showToast('Failed to retry task.', true);
    }
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
