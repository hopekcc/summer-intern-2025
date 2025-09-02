package com.example.chordproapp.viewmodels

import androidx.compose.runtime.mutableStateMapOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.chordproapp.data.model.Playlist
import com.example.chordproapp.data.repository.PlaylistRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class PlaylistViewModel(
    val repository: PlaylistRepository
) : ViewModel() {

    var newlyCreatedPlaylists = mutableStateMapOf<String, Boolean>()
        private set

    fun markAsNew(playlistName: String) {
        newlyCreatedPlaylists[playlistName] = true
    }

    fun clearNewFlag(playlistName: String) {
        newlyCreatedPlaylists[playlistName] = false
    }

    fun isNewPlaylist(playlistName: String): Boolean {
        return newlyCreatedPlaylists[playlistName] ?: false
    }

    private val _playlists = MutableStateFlow<List<Playlist>>(emptyList())
    val playlists: StateFlow<List<Playlist>> = _playlists

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage

    fun loadAllPlaylists() {
        viewModelScope.launch {
            val result = repository.listAllPlaylists()
            _playlists.value = result
        }
    }

    fun createPlaylist(name: String, onResult: (Playlist?) -> Unit) {
        viewModelScope.launch {
            val newPlaylist = repository.createPlaylist(name)
            if (newPlaylist != null) {
                loadAllPlaylists()
                markAsNew(newPlaylist.name) // Use playlist name instead of ID for marking as new
            } else {
                _errorMessage.value = "Failed to create playlist"
            }
            onResult(newPlaylist)
        }
    }

    fun addSongToPlaylist(playlistId: String, songId: Int) {
        viewModelScope.launch {
            val success = repository.addSongsToPlaylist(playlistId, songId)
            if (success) loadAllPlaylists()
            else _errorMessage.value = "Failed to add song"
        }
    }

    fun deletePlaylist(playlistId: String) {
        viewModelScope.launch {
            val success = repository.deletePlaylist(playlistId)
            if (success) loadAllPlaylists()
            else _errorMessage.value = "Failed to delete playlist"
        }
    }

    fun removeSongFromPlaylist(playlistId: String, songId: Int) {
        viewModelScope.launch {
            val success = repository.removeSong(playlistId, songId)
            if (success) loadAllPlaylists()
            else _errorMessage.value = "Failed to remove song"
        }
    }
}
