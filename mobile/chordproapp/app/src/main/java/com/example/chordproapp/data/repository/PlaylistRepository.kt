package com.example.chordproapp.data.repository

import com.example.chordproapp.data.AuthInterceptor
import com.example.chordproapp.data.api.CreatePlaylistRequest
import com.example.chordproapp.data.api.PlaylistApiService
import com.example.chordproapp.data.model.Playlist
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class PlaylistRepository(tokenProvider: () -> String?) {
    private val api: PlaylistApiService

    init {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .addInterceptor(AuthInterceptor(tokenProvider)) // <-- inject token automatically
            .build()

        api = Retrofit.Builder()
            .baseUrl("http://34.125.143.141:8000/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(PlaylistApiService::class.java)
    }

    suspend fun createPlaylist(name: String): Playlist? {
        return try {
            val response = api.createPlaylist(CreatePlaylistRequest(name))
            if (response.isSuccessful)
                response.body()
                else null
        } catch (e: Exception) {
            null
        }
    }

    suspend fun addSongsToPlaylist(playlistId: Int, songId: Int): Boolean {
        return try {
            val response = api.addSongs(playlistId)
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }

    suspend fun listAllPlaylists(): List<Playlist> {
        return try {
            val response = api.listAllPlaylists()
            if (response.isSuccessful) {
                response.body() ?: emptyList()
            } else {
                emptyList()
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun deletePlaylist(id: Int): Boolean {
        return try {
            val response = api.deletePlaylist(id)
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }

    suspend fun removeSong(playlistId: Int, songId: Int): Boolean {
        return try {
            val response = api.removeSong(playlistId, songId)
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }
}
