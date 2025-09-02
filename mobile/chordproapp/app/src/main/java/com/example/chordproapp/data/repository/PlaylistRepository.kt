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
        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BODY }
        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .addInterceptor(AuthInterceptor(tokenProvider))
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
            if (response.isSuccessful) {
                response.body()?.data
            } else null
        } catch (e: Exception) {
            null
        }
    }

    suspend fun addSongsToPlaylist(playlistId: String, songId: Int): Boolean {
        return try {
            val response = api.addSongs(playlistId, songId)
            val body = response.body()
            println("Add song response: $body") // debug
            response.isSuccessful && (body?.success == true)
        } catch (e: Exception) {
            println("Add song exception: ${e.message}") // debug
            false
        }
    }



    suspend fun listAllPlaylists(): List<Playlist> {
        return try {
            val response = api.listAllPlaylists()
            if (response.isSuccessful) {
                response.body()?.data ?: emptyList()
            } else {
                emptyList()
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun deletePlaylist(id: String): Boolean {
        return try {
            val response = api.deletePlaylist(id)
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }

    suspend fun removeSong(playlistId: String, songId: Int): Boolean {
        return try {
            val response = api.removeSong(playlistId, songId)
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }
}
