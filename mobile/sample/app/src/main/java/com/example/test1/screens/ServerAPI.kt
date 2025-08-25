// package com.example.test1.network
package com.example.test1.network

import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

// Simple data class to hold initial sync response (adjust to your API shape)
data class RoomSyncResponse(
    val groupName: String,
    val nowPlaying: String,
    val participants: List<String>,
    val queue: List<String>,
    val currentPage: Int,
    val totalPages: Int
)

class ServerApi {

    companion object {
        private const val BASE_URL = "http://34.125.143.141:8000"
        private val JSON = "application/json; charset=utf-8".toMediaTypeOrNull()
    }

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS) // for websockets
        .build()

    // Utility to convert map to json string
    fun toJson(map: Any): String = when (map) {
        is Map<*, *> -> JSONObject(map as Map<*, *>).toString()
        is String -> map
        else -> JSONObject(map as Map<String, Any>).toString()
    }

    fun parseRoomId(body: String?): String? {
        // adjust depending on server json
        body ?: return null
        return try {
            val jo = JSONObject(body)
            jo.optString("room_id", jo.optString("roomId", null))
        } catch (e: Exception) { null }
    }

    // REST: create room
    fun createRoom(token: String): Response = runBlockingRequest {
        val url = "$BASE_URL/rooms/"
        val req = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $token")
            .post("{}".toRequestBody(JSON))
            .build()
        client.newCall(req).execute()
    }

    // REST: join room
    fun joinRoom(roomId: String, token: String): Response = runBlockingRequest {
        val url = "$BASE_URL/rooms/$roomId/join"
        val req = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $token")
            .post("{}".toRequestBody(JSON))
            .build()
        client.newCall(req).execute()
    }

    // Get room sync (GET /rooms/{room_id}/sync)
    fun getRoomSync(roomId: String, token: String): RoomSyncResponse? {
        val url = "$BASE_URL/rooms/$roomId/sync"
        val req = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $token")
            .get()
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return null
            val body = resp.body?.string() ?: return null
            val jo = JSONObject(body)
            val group = jo.optString("groupName", "Group")
            val now = jo.optString("nowPlaying", "")
            val participants = jo.optJSONArray("participants")?.let { arr ->
                (0 until arr.length()).map { arr.getString(it) }
            } ?: emptyList()
            val queue = jo.optJSONArray("queue")?.let { arr ->
                (0 until arr.length()).map { arr.getString(it) }
            } ?: emptyList()
            val currPage = jo.optInt("currentPage", 0)
            val total = jo.optInt("totalPages", 1)
            return RoomSyncResponse(group, now, participants, queue, currPage, total)
        }
    }

    // POST song to room
    fun postRoomSong(roomId: String, token: String, songId: String): Response = runBlockingRequest {
        val url = "$BASE_URL/rooms/$roomId/song"
        val body = JSONObject().put("song_id", songId).toString().toRequestBody(JSON)
        val req = Request.Builder().url(url).addHeader("Authorization", "Bearer $token").post(body).build()
        client.newCall(req).execute()
    }

    // POST page update
    fun postRoomPage(roomId: String, token: String, pageIndex: Int): Response = runBlockingRequest {
        val url = "$BASE_URL/rooms/$roomId/page"
        val body = JSONObject().put("page", pageIndex).toString().toRequestBody(JSON)
        val req = Request.Builder().url(url).addHeader("Authorization", "Bearer $token").post(body).build()
        client.newCall(req).execute()
    }

    // Open websocket to /ws/{room_id}
    fun openRoomWebSocket(roomId: String, listener: RoomWsListener): okhttp3.WebSocket {
        val wsUrl = "ws://34.125.143.141:8000/ws/$roomId"
        val req = Request.Builder().url(wsUrl).build()
        return client.newWebSocket(req, listener)
    }

    private fun runBlockingRequest(block: () -> Response): Response {
        // note: executed on background coroutine so this is fine in ViewModel
        return block()
    }
}
