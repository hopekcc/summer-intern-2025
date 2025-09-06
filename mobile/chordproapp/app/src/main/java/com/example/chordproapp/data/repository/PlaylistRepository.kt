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

    suspend fun addSongsToPlaylist(playlistId: String, songId: String): Boolean {
        return try {
            println("[DEBUG] Adding song $songId to playlist $playlistId")
            val response = api.addSongs(playlistId, PlaylistApiService.AddSongRequest(songId))
            println("[DEBUG] API Response: ${response.code()}, Success: ${response.isSuccessful}")

            if (response.isSuccessful) {
                val body = response.body()
                println("[DEBUG] Response body: $body")
                val success = body?.success == true
                println("[DEBUG] Final success result: $success")
                success
            } else {
                println("[DEBUG] API call failed with code: ${response.code()}")
                println("[DEBUG] Error body: ${response.errorBody()?.string()}")
                false
            }
        } catch (e: Exception) {
            println("[DEBUG] Exception in addSongsToPlaylist: ${e.message}")
            e.printStackTrace()
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

    suspend fun removeSong(playlistId: String, songId: String): Boolean {
        return try {
            println("[DEBUG] Removing song $songId from playlist $playlistId")
            val response = api.removeSong(playlistId, songId)
            println("[DEBUG] API response code: ${response.code()}")
            response.isSuccessful
        } catch (e: Exception) {
            println("[DEBUG] Exception: ${e.message}")
            false
        }
    }

}
