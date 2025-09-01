package com.example.chordproapp.data.api

import com.example.chordproapp.data.model.Playlist
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

data class CreatePlaylistRequest(val name: String)

interface PlaylistApiService {
    @POST("playlists/")
    suspend fun createPlaylist(@Body request: CreatePlaylistRequest): Response<Playlist>

    @POST("playlists/{id}/songs")
    suspend fun addSongs(@Path("id") id: Int): Response<Playlist>

    @GET("playlists/")
    suspend fun listAllPlaylists(): Response<List<Playlist>>

    @DELETE("playlists/{id}")
    suspend fun deletePlaylist(@Path("id") id: Int): Response<ResponseBody>

    @DELETE("playlists/{id}/songs/{song_id}")
    suspend fun removeSong(
        @Path("id") id: Int,
        @Path("song_id") songId: Int
    ): Response<ResponseBody>
}
