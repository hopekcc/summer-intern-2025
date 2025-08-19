package com.example.chordproapp.data

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import okhttp3.logging.HttpLoggingInterceptor
import okhttp3.OkHttpClient
import com.example.chordproapp.data.Song
import com.example.chordproapp.data.SongDetail
import com.example.chordproapp.data.ApiService

class SongRepository(private val tokenProvider: () -> String?) {
    private val api: ApiService

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
            .create(ApiService::class.java)
    }

    suspend fun searchSongs(query: String): List<Song> {
        return try {
            val response = api.searchSongs(query)
            if (response.isSuccessful) response.body() ?: emptyList() else emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun getAllSongs(): List<Song> {
        return try {
            val response = api.getAllSongs()
            if (response.isSuccessful) response.body() ?: emptyList() else emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun getSongDetails(songId: Int): SongDetail? {
        return try {
            val response = api.getSongDetails(songId)
            if (response.isSuccessful) response.body() else null
        } catch (e: Exception) {
            null
        }
    }

    suspend fun getSongPdf(songId: Int): ByteArray? {
        return try {
            val response = api.getSongPdf(songId)
            if (response.isSuccessful && response.body() != null) {
                response.body()!!.bytes()
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

}
