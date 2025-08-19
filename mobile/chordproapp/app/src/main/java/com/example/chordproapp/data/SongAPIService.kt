package com.example.chordproapp.data

import okhttp3.Interceptor
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

class AuthInterceptor(private val tokenProvider: () -> String?) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): okhttp3.Response {
        val requestBuilder = chain.request().newBuilder()
        tokenProvider()?.let { token ->
            requestBuilder.addHeader("Authorization", "Bearer $token")
        }
        return chain.proceed(requestBuilder.build())
    }
}
