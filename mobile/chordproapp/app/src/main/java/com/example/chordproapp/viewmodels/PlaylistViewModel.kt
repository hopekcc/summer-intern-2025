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
                markAsNew(newPlaylist.name)
            } else {
                _errorMessage.value = "Failed to create playlist"
            }
            onResult(newPlaylist)
        }
    }

    fun addSongToPlaylist(playlistId: String, song: Song, onResult: (Boolean) -> Unit) {
        viewModelScope.launch {
            val success = repository.addSongsToPlaylist(playlistId, song.id.toString())
            if (success) {
                // Immediately update local state
                _playlists.value = _playlists.value.map { pl ->
                    if (pl.id == playlistId) {
                        val updatedSongs = if (pl.songs.any { it.id == song.id }) {
                            pl.songs
                        } else {
                            pl.songs + song
                        }
                        pl.copy(songs = updatedSongs)
                    } else pl
                }
            } else {
                _errorMessage.value = "Failed to add song"
            }
            onResult(success)
        }
    }


    fun deletePlaylist(playlistId: String) {
        viewModelScope.launch {
            val success = repository.deletePlaylist(playlistId)
            if (success) loadAllPlaylists()
            else _errorMessage.value = "Failed to delete playlist"
        }
    }

    fun removeSongFromPlaylist(playlistId: String, songId: String) {
        viewModelScope.launch {
            val success = repository.removeSong(playlistId, songId)
            if (success) {
                // Update UI immediately
                _playlists.value = _playlists.value.map { playlist ->
                    if (playlist.id == playlistId) {
                        playlist.copy(songs = playlist.songs.filterNot { it.id.toString() == songId }) // compare with String
                    } else playlist
                }
            } else {
                _errorMessage.value = "Failed to remove song"
            }
        }
    }
}



