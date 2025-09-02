package com.example.chordproapp.data.model

import com.google.gson.annotations.SerializedName

data class Song(
    @SerializedName("song_id") val id: Int,
    val title: String,
    val artist: String,
    @SerializedName("page_count") val pageCount: Int
)

data class SongDetail(
    @SerializedName("song_id") val id: Int,
    val title: String,
    val artist: String,
    @SerializedName("page_count") val pageCount: Int
)
