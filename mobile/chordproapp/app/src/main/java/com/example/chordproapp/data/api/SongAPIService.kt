package com.example.chordproapp.data.api

import com.example.chordproapp.data.model.Song
import com.example.chordproapp.data.model.SongDetail
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @GET("songs/list")
    suspend fun getAllSongs(): Response<List<Song>>

    @GET("songs/search/{query}")
    suspend fun searchSongs(@Path("query") query: String): Response<List<Song>>

    @GET("songs/{song_id}")
    suspend fun getSongDetails(@Path("song_id") songId: Int): Response<SongDetail>

    @GET("songs/{song_id}/pdf")
    suspend fun getSongPdf(@Path("song_id") songId: Int): Response<ResponseBody>

    @GET("songs/")
    suspend fun basicSearch(
        @Query("search") query: String,
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0
    ): Response<List<Song>>

    @GET("songs/search/substring")
    suspend fun substringSearch(
        @Query("q") query: String,
        @Query("limit") limit: Int = 10
    ): Response<List<Song>>

    @GET("songs/search/similarity")
    suspend fun similaritySearch(
        @Query("q") query: String,
        @Query("limit") limit: Int = 10
    ): Response<List<Song>>

    @GET("songs/search/text")
    suspend fun fullTextSearch(
        @Query("q") query: String,
        @Query("limit") limit: Int = 10
    ): Response<List<Song>>

}
