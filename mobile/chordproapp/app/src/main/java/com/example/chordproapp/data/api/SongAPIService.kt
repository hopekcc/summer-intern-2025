package com.example.chordproapp.data.api

import com.example.chordproapp.data.model.Song
import com.example.chordproapp.data.model.SongDetail
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Path

interface ApiService {
    @GET("songs/list")
    suspend fun getAllSongs(): Response<List<Song>>

    @GET("songs/search/{query}")
    suspend fun searchSongs(@Path("query") query: String): Response<List<Song>>

    @GET("songs/{song_id}")
    suspend fun getSongDetails(@Path("song_id") songId: Int): Response<SongDetail>

    @GET("songs/{song_id}/pdf")
    suspend fun getSongPdf(@Path("song_id") songId: Int): Response<ResponseBody>
}
