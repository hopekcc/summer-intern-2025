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

data class PlaylistApiResponse(
    val success: Boolean,
    val data: List<Playlist>,
    val message: String,
    val meta: PlaylistMeta
)

data class PlaylistMeta(
    val user_id: String,
    val count: Int
)

data class SinglePlaylistResponse(
    val success: Boolean,
    val data: Playlist,
    val message: String
)

interface PlaylistApiService {
    @POST("playlists/")
    suspend fun createPlaylist(@Body request: CreatePlaylistRequest): Response<SinglePlaylistResponse>

    data class AddSongRequest(
        val song_id: String
    )

    @POST("playlists/{id}/songs")
    suspend fun addSongs(
        @Path("id") playlistId: String,
        @Body body: AddSongRequest
    ): Response<SinglePlaylistResponse>

    @GET("playlists/")
    suspend fun listAllPlaylists(): Response<PlaylistApiResponse>

    @DELETE("playlists/{id}")
    suspend fun deletePlaylist(@Path("id") playlistId: String): Response<ResponseBody>

    @DELETE("playlists/{id}/songs/{song_id}")
    suspend fun removeSong(
        @Path("id") playlistId: String,
        @Path("song_id") songId: String
    ): Response<ResponseBody>
}
