package com.example.chordproapp.data.model

data class Playlist(
    val id: String,
    val name: String,
    val description: String?,
    val user_id: String,
    val song_count: Int,
    val songs: List<Song> = emptyList()
)
