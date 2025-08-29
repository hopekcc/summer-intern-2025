import { auth } from "./firebaseConfig.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js";

let idToken = null;
let playlist = [];

// Elements
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');
const tracksList = document.getElementById('tracksList');
const tabButtons = document.querySelectorAll('.tab-btn');
const playlistNameInput = document.getElementById('playlistName');
const trackCount = document.getElementById('trackCount');
const playlistContent = document.getElementById('playlistContent');
const playlistActions = document.getElementById('playlistActions');
const saveBtn = document.querySelector('.save-btn');

// Auth and initialization
onAuthStateChanged(auth, async (user) => {
  if (user) {
    idToken = await user.getIdToken(true);
    bindUI();
    loadBrowseSongs();
    updatePlaylistDisplay();
  }
});

function bindUI() {
  let currentSearchType = 'title';

  // Tab switching
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentSearchType = btn.dataset.type;
      const placeholders = { title: 'Search by title...', artist: 'Search by artist...', id: 'Search by ID...' };
      searchInput.placeholder = placeholders[currentSearchType];
    });
  });

  // Search input
  let debounce;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounce);
    const q = searchInput.value.trim();
    if (q.length < 2) return hide(searchResults);
    debounce = setTimeout(() => performSearch(q, currentSearchType), 300);
  });

  // Save playlist
  saveBtn.addEventListener('click', savePlaylist);
}

async function performSearch(query, type) {
  show(searchResults);
  try {
    const res = await fetch(`/songs/list?search=${encodeURIComponent(query)}&limit=50`, {
      headers: { 'Authorization': `Bearer ${idToken}` }
    });
    if (!res.ok) throw new Error(res.status);
    const songs = await res.json();
    renderTrackCards(songs, searchResults);
  } catch (e) {
    searchResults.innerHTML = `<p style=\"color:#ef4444;\">Search failed (${e.message})</p>`;
  }
}

async function loadBrowseSongs() {
  try {
    const res = await fetch('/songs/list?limit=10', { headers: { 'Authorization': `Bearer ${idToken}` } });
    if (!res.ok) return;
    const songs = await res.json();
    renderTrackCards(songs, tracksList);
  } catch {}
}

function renderTrackCards(songs, container) {
  container.innerHTML = songs.map(song => `
    <div class=\"card track-card\" data-track-id=\"${song.id}\">  
      <div class=\"track-content\">
        <div class=\"track-info\">
          <h4 class=\"track-title\">${song.title}</h4>
          <p class=\"track-artist\">${song.artist}</p>
        </div>
        <div class=\"track-actions\">
          <button class=\"btn-primary\" onclick=\"addToPlaylist('${song.id}','${song.title}','${song.artist}')\">Add</button>
        </div>
      </div>
    </div>
  `).join('');
}

window.addToPlaylist = (id, title, artist) => {
  if (playlist.find(t => t.id === id)) return alert('Already added');
  playlist.push({ id, title, artist });
  updatePlaylistDisplay();
};

window.removeFromPlaylist = id => {
  playlist = playlist.filter(t => t.id !== id);
  updatePlaylistDisplay();
};

function updatePlaylistDisplay() {
  trackCount.textContent = `${playlist.length} track${playlist.length!==1?'s':''}`;
  if (!playlist.length) {
    hide(playlistActions);
    playlistContent.innerHTML = `<div class=\"empty-playlist\">No tracks added yet</div>`;
    return;
  }
  show(playlistActions);
  playlistContent.innerHTML = playlist.map(t => `
    <div class=\"card track-card\">
      <div class=\"track-content\">
        <p>${t.title} — ${t.artist}</p>
        <button onclick=\"removeFromPlaylist('${t.id}')\">✕</button>
      </div>
    </div>
  `).join('');
}

async function savePlaylist() {
  const name = playlistNameInput.value.trim();
  if (!name) return alert('Enter a name');
  if (!playlist.length) return alert('Add tracks first');
  try {
    const res = await fetch('/playlists/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name, tracks: playlist })
    });
    if (!res.ok) throw new Error(res.status);
    alert('Saved!');
    playlist = []; updatePlaylistDisplay();
  } catch (e) { alert('Save failed'); }
}

function show(el){ el.classList.remove('hidden'); }
function hide(el){ el.classList.add('hidden'); }
