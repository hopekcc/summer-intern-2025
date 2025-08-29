import { auth } from "./firebaseConfig.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js";

console.log("✅ playlist.js loaded");

// Wait for DOM before querying elements
window.addEventListener('DOMContentLoaded', () => {
  let idToken = null;
  let playlist = [];

  // DOM refs
  const searchInput       = document.getElementById('searchInput');
  const searchButton      = document.getElementById('searchButton');
  const searchResults     = document.getElementById('searchResults');
  const tracksList        = document.getElementById('tracksList');
  const tabButtons        = document.querySelectorAll('.tab-btn');
  const playlistNameInput = document.getElementById('playlistName');
  const trackCount        = document.getElementById('trackCount');
  const playlistContent   = document.getElementById('playlistContent');
  const playlistActions   = document.getElementById('playlistActions');
  const saveBtn           = document.querySelector('.save-btn');

  console.log('🔍 searchResults element found:', searchResults); // Should not be null
  console.log('🔍 searchResults id:', searchResults?.id); // Should be "searchResults"
  // Firebase auth init
  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      console.log("❌ No user authenticated");
      return;
    }
    console.log("✅ User authenticated:", user.email);
    idToken = await user.getIdToken(true);
    console.log("✅ Got ID token");
    bindUI();
    loadBrowseSongs();
    updatePlaylistDisplay();
  });

  function bindUI() {
    let currentType = 'title';

    // Tab switching
    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        tabButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentType = btn.dataset.type;
        console.log("🔄 Search type changed to:", currentType);
        searchInput.placeholder = {
          title:  'Search by title…',
          artist: 'Search by artist…',
          id:     'Search by ID…'
        }[currentType];
      });
    });

    // Search button click
    searchButton.addEventListener('click', () => {
      const q = searchInput.value.trim();
      console.log('🔍 Search clicked, query=', q, 'type=', currentType);
      if (q.length < 2) {
        alert('Please enter at least 2 characters to search');
        return;
      }
      performSearch(q, currentType);
    });

    // Enter key
    searchInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        searchButton.click();
      }
    });

    // Save playlist
    saveBtn.addEventListener('click', savePlaylist);
  }

  async function performSearch(query, type) {
    console.log('🔍 Starting search for:', query, 'type:', type);
    console.log('📦 searchResults element:', searchResults);
    console.log('📦 searchResults classes before show:', searchResults.className);
    searchResults.classList.remove('hidden');
    searchResults.style.display = 'block';
    console.log('🔍 Forced show - classes now:', searchResults.className);
    console.log('🔍 Forced show - display now:', searchResults.style.display);
    console.log('📦 searchResults classes after show:', searchResults.className);
    console.log('📦 searchResults display style:', window.getComputedStyle(searchResults).display);
    
    // Show loading state
    searchResults.innerHTML = '<p style="color:#64748b; padding:1rem;">Searching...</p>';
    
    try {
      if (!idToken) {
        throw new Error('Not authenticated - please sign in');
      }

      const url = `http://34.125.143.141:8000/songs/list?search=${encodeURIComponent(query)}&limit=50`;
      console.log('🌐 Making request to:', url);
      
      const res = await fetch(url, {
        headers: { 
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log('📡 Response status:', res.status);
      console.log('📡 Response headers:', Object.fromEntries(res.headers.entries()));
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('❌ API Error:', res.status, errorText);
        throw new Error(`API returned ${res.status}: ${errorText}`);
      }
      
        const data = await res.json();
        console.log('✅ Raw API response:', data); // Log the actual structure first

        // Extract the songs array from the response object
        // The actual property name might be 'songs', 'results', 'items', or 'data'
        const songs = data.songs || data.results || data.items || data.data || data;

        // Ensure it's an array
        if (!Array.isArray(songs)) {
        console.error('❌ Expected array but got:', typeof songs, songs);
        throw new Error('Invalid response format - not an array');
        }

        console.log('✅ Search results:', songs.length, 'songs found');
        console.log('📄 First few results:', songs.slice(0, 3));

        renderTrackCards(songs, searchResults);
      
    } catch (err) {
      console.error('❌ Search error:', err);
      searchResults.innerHTML = `
        <div style="color:#ef4444; padding:1rem; border:1px solid #fecaca; border-radius:0.5rem; background:#fef2f2;">
          <strong>Search failed:</strong> ${err.message}
          <br><small>Check the console for more details</small>
        </div>
      `;
    }
  }

  async function loadBrowseSongs() {
    console.log('📚 Loading browse songs...');
    try {
      if (!idToken) {
        console.log('❌ No token for browse songs');
        return;
      }

      // Fixed endpoint
        const res = await fetch('http://34.125.143.141:8000/songs/list?limit=10', {
        headers: { 
            'Authorization': `Bearer ${idToken}`,
            'Content-Type': 'application/json'
        }
      });
      
      console.log('📡 Browse response status:', res.status);
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('❌ Browse API Error:', res.status, errorText);
        return;
      }
      
        const data = await res.json();
        console.log('✅ Raw browse response:', data); // Log the actual structure

        // Extract the songs array from the response object
        const songs = data.songs || data.results || data.items || data.data || data;

        // Ensure it's an array
        if (!Array.isArray(songs)) {
        console.error('❌ Expected array but got:', typeof songs, data);
        return;
        }

        console.log('✅ Browse songs loaded:', songs.length);
        renderTrackCards(songs, tracksList);
      
    } catch (e) {
      console.error('❌ Browse load error:', e);
    }
  }

  function renderTrackCards(songs, container) {
    if (!songs || songs.length === 0) {
      container.innerHTML = '<p style="color:#64748b; padding:1rem;">No songs found.</p>';
      return;
    }

    console.log('🎨 Rendering', songs.length, 'track cards');
    
    container.innerHTML = songs.map(song => {
      // Escape HTML to prevent XSS
      const safeTitle = escapeHtml(song.title || 'Unknown Title');
      const safeArtist = escapeHtml(song.artist || 'Unknown Artist');
      const safeId = escapeHtml(song.id || 'unknown');
      
      return `
        <div class="card track-card" data-track-id="${safeId}">
          <div class="track-content">
            <div class="track-info">
              <h4 class="track-title">${safeTitle}</h4>
              <p class="track-artist">${safeArtist}</p>
              <span class="badge">${safeId}</span>
            </div>
            <div class="track-actions">
              <button class="btn-primary" onclick="addToPlaylist('${safeId}','${safeTitle}','${safeArtist}')">
                Add
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // Helper function to escape HTML
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  window.addToPlaylist = (id, title, artist) => {
    console.log('➕ Adding to playlist:', { id, title, artist });
    if (playlist.some(t => t.id === id)) {
      alert('This song is already in your playlist!');
      return;
    }
    playlist.push({ id, title, artist });
    updatePlaylistDisplay();
  };

  window.removeFromPlaylist = id => {
    console.log('➖ Removing from playlist:', id);
    playlist = playlist.filter(t => t.id !== id);
    updatePlaylistDisplay();
  };

  function updatePlaylistDisplay() {
    trackCount.textContent = `${playlist.length} track${playlist.length !== 1 ? 's':''}`;
    if (!playlist.length) {
      hide(playlistActions);
      playlistContent.innerHTML = `
        <div class="empty-playlist">
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
          </svg>
          <p>No tracks added yet</p>
          <p class="empty-subtitle">Search and add tracks to get started</p>
        </div>
      `;
      return;
    }
    show(playlistActions);
    playlistContent.innerHTML = playlist.map(t => `
      <div class="card track-card" style="margin-bottom:0.5rem;">
        <div class="track-content">
          <div class="track-info">
            <p><strong>${escapeHtml(t.title)}</strong> — ${escapeHtml(t.artist)}</p>
          </div>
          <button onclick="removeFromPlaylist('${escapeHtml(t.id)}')" 
                  style="background:none;border:none;color:#ef4444;cursor:pointer;padding:0.5rem;">
            ✕
          </button>
        </div>
      </div>
    `).join('');
  }

async function savePlaylist() {
  const name = playlistNameInput.value.trim();
  console.log('💾 Saving playlist:', name, playlist.length, 'tracks');
  
  if (!name) {
    alert('Please enter a playlist name');
    return;
  }
  if (!playlist.length) {
    alert('Please add some tracks first');
    return;
  }
  
  try {
    // Try without trailing slash first
    const createUrl = `/playlists?name=${encodeURIComponent(name)}`;
    console.log('📝 Creating playlist at:', createUrl);
    
    const createRes = await fetch(createUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${idToken}`
      }
    });
    
    console.log('📡 Response status:', createRes.status);
    
    if (createRes.status === 404) {
      // If 404, try with trailing slash
      console.log('❌ Got 404, trying with trailing slash...');
      const altUrl = `/playlists/?name=${encodeURIComponent(name)}`;
      const altRes = await fetch(altUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`
        }
      });
      
      if (altRes.ok) {
        const playlistData = await altRes.json();
        console.log('✅ Playlist created:', playlistData);
        // Continue with adding songs...
        alert('Playlist saved successfully!');
        playlist = [];
        playlistNameInput.value = 'My New Playlist';
        updatePlaylistDisplay();
        return;
      }
    }
    
    if (!createRes.ok) {
      const errorText = await createRes.text();
      console.error('❌ Create playlist error:', createRes.status, errorText);
      throw new Error(`Failed to create playlist: ${createRes.status}`);
    }
    
    const playlistData = await createRes.json();
    console.log('✅ Playlist created:', playlistData);
    
    alert('Playlist saved successfully!');
    playlist = [];
    playlistNameInput.value = 'My New Playlist';
    updatePlaylistDisplay();
    
  } catch (e) {
    console.error('❌ Save error:', e);
    alert(`Save failed: ${e.message}`);
  }
}

  function show(el) { el.classList.remove('hidden'); }
  function hide(el) { el.classList.add('hidden'); }
});