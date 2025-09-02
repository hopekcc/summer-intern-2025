package com.example.chordproapp.data.repository

import android.content.Context
import com.example.chordproapp.data.AuthInterceptor
import com.example.chordproapp.data.api.ApiService
import com.example.chordproapp.data.model.Song
import com.example.chordproapp.data.model.SongDetail
import okhttp3.OkHttpClient
import okhttp3.ResponseBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.File

class SongRepository(
    private val tokenProvider: () -> String?,
    private val appContext: Context
) {
    private val api: ApiService

    init {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .addInterceptor(AuthInterceptor(tokenProvider))
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
            val response = api.similaritySearch(query)
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

    suspend fun getSongPdf(songId: Int): File? {
        return try {
            val response = api.getSongPdf(songId)
            if (response.isSuccessful && response.body() != null) {
                val pdfFile = File(appContext.cacheDir, "song_${songId}.pdf")
                response.body()!!.byteStream().use { input ->
                    pdfFile.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }
                pdfFile
            } else null
        } catch (e: Exception) {
            null
        }
    }

    suspend fun getSongPageImage(songId: Int, pageNumber: Int): ByteArray? {
        return try {
            val response = api.getSongPage(songId, pageNumber)
            if (response.isSuccessful && response.body() != null) {
                response.body()!!.bytes()
            } else null
        } catch (e: Exception) {
            null
        }
    }
}
