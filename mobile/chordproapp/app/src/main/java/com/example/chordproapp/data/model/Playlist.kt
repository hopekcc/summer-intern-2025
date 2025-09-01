package com.example.chordproapp.data.model

data class Playlist(
    val id: Int,
    val name: String,
    val songs: List<Song> = emptyList()
)