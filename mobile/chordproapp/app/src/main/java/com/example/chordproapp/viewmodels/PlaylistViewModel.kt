package com.example.chordproapp.viewmodels

import androidx.compose.runtime.mutableStateMapOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.chordproapp.data.model.Playlist
import com.example.chordproapp.data.model.Song
import com.example.chordproapp.data.repository.PlaylistRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class PlaylistViewModel(
    val repository: PlaylistRepository,
    private val userId: String // Add userId to ensure user-specific operations
) : ViewModel() {

    var newlyCreatedPlaylists = mutableStateMapOf<String, Boolean>()
        private set

    private val _playlists = MutableStateFlow<List<Playlist>>(emptyList())
    val playlists: StateFlow<List<Playlist>> = _playlists

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage

    init {
        // Automatically load playlists for this user when ViewModel is created
        loadAllPlaylists()
    }

    fun markAsNew(playlistName: String) {
        newlyCreatedPlaylists[playlistName] = true
    }

    fun clearNewFlag(playlistName: String) {
        newlyCreatedPlaylists[playlistName] = false
    }

    fun isNewPlaylist(playlistName: String): Boolean {
        return newlyCreatedPlaylists[playlistName] ?: false
    }

    fun loadAllPlaylists() {
        viewModelScope.launch {
            try {
                val result = repository.listAllPlaylists()
                _playlists.value = result
                _errorMessage.value = null
            } catch (e: Exception) {
                _errorMessage.value = "Failed to load playlists: ${e.message}"
            }
        }
    }

    fun createPlaylist(name: String, onResult: (Playlist?) -> Unit) {
        viewModelScope.launch {
            try {
                val newPlaylist = repository.createPlaylist(name)
                if (newPlaylist != null) {
                    loadAllPlaylists() // Reload to get fresh data
                    markAsNew(newPlaylist.name)
                    _errorMessage.value = null
                } else {
                    _errorMessage.value = "Failed to create playlist"
                }
                onResult(newPlaylist)
            } catch (e: Exception) {
                _errorMessage.value = "Error creating playlist: ${e.message}"
                onResult(null)
            }
        }
    }

    fun addSongToPlaylist(playlistId: String, song: Song, onResult: (Boolean) -> Unit) {
        viewModelScope.launch {
            try {
                val success = repository.addSongsToPlaylist(playlistId, song.id.toString())
                if (success) {
                    // Immediately update local state
                    _playlists.value = _playlists.value.map { pl ->
                        if (pl.id == playlistId && !pl.songs.contains(song)) {
                            pl.copy(songs = pl.songs + song)
                        } else pl
                    }
                    _errorMessage.value = null
                } else {
                    _errorMessage.value = "Failed to add song to playlist"
                }
                onResult(success)
            } catch (e: Exception) {
                _errorMessage.value = "Error adding song: ${e.message}"
                onResult(false)
            }
        }
    }

    fun deletePlaylist(playlistId: String) {
        viewModelScope.launch {
            try {
                val success = repository.deletePlaylist(playlistId)
                if (success) {
                    loadAllPlaylists() // Reload to get fresh data
                    _errorMessage.value = null
                } else {
                    _errorMessage.value = "Failed to delete playlist"
                }
            } catch (e: Exception) {
                _errorMessage.value = "Error deleting playlist: ${e.message}"
            }
        }
    }

    fun removeSongFromPlaylist(playlistId: String, songId: Int) {
        viewModelScope.launch {
            try {
                val success = repository.removeSong(playlistId, songId)
                if (success) {
                    loadAllPlaylists() // Reload to get fresh data
                    _errorMessage.value = null
                } else {
                    _errorMessage.value = "Failed to remove song from playlist"
                }
            } catch (e: Exception) {
                _errorMessage.value = "Error removing song: ${e.message}"
            }
        }
    }

    fun clearUserData() {
        _playlists.value = emptyList()
        _errorMessage.value = null
        newlyCreatedPlaylists.clear()
    }

    fun getCurrentUserId(): String = userId
}
