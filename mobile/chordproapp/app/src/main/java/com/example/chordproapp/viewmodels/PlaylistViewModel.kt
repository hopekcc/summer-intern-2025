package com.example.chordproapp.viewmodels

import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.ViewModel

class PlaylistViewModel : ViewModel() {
    private val _playlists = mutableStateListOf(
        "Playlist 1",
        "Playlist 2",
        "Playlist 3",
        "Playlist 4",
        "Playlist 5"
    )
    val playlists: List<String> get() = _playlists
    private var deletedPlaylist: String? = null

    fun addPlaylist(name: String) {
        if (name.isNotBlank() && !playlists.contains(name)) {
            _playlists.add(name)
        }
    }

    fun deletePlaylist(name: String) {
        if (playlists.contains(name)) {
            deletedPlaylist = name
            _playlists.remove(name)
        }
    }

    fun undoDelete() {
        deletedPlaylist?.let {
            if (!_playlists.contains(it)) {
                _playlists.add(it)
            }
            deletedPlaylist = null
        }
    }
}