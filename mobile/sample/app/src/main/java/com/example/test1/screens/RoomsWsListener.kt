package com.example.test1.network

import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject

class RoomWsListener(
    val onOpenSendToken: (WebSocket) -> Unit = {},
    val onSongUpdate: (String) -> Unit = {},
    val onPageUpdate: (Int) -> Unit = {},
    val onRoomState: ((RoomSyncResponse) -> Unit) = {},
    val onError: (String) -> Unit = {},
    val onClose: () -> Unit = {}
) : WebSocketListener() {

    override fun onOpen(webSocket: WebSocket, response: Response) {
        onOpenSendToken(webSocket)
    }

    override fun onMessage(webSocket: WebSocket, text: String) {
        try {
            val jo = JSONObject(text)
            val type = jo.optString("type")
            val data = jo.optJSONObject("data")
            when (type) {
                "song_update" -> {
                    val title = data?.optString("title") ?: ""
                    onSongUpdate(title)
                }
                "page_update" -> {
                    val page = jo.optInt("page", data?.optInt("page") ?: -1)
                    onPageUpdate(page)
                }
                "room_state" -> {
                    // parse full state
                    val participants = data?.optJSONArray("participants")?.let { arr ->
                        (0 until arr.length()).map { arr.getString(it) }
                    } ?: emptyList()
                    val queue = data?.optJSONArray("queue")?.let { arr ->
                        (0 until arr.length()).map { arr.getString(it) }
                    } ?: emptyList()
                    val now = data?.optString("nowPlaying", "") ?: ""
                    val group = data?.optString("groupName", "") ?: ""
                    val curr = data?.optInt("currentPage", 0) ?: 0
                    val total = data?.optInt("totalPages", 1) ?: 1
                    val r = RoomSyncResponse(group, now, participants, queue, curr, total)
                    onRoomState(r)
                }
                else -> {
                    // ignore unknown
                }
            }
        } catch (e: Exception) {
            onError(e.message ?: "parse error")
        }
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        onError(t.message ?: "ws failure")
    }

    override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
        webSocket.close(1000, null)
        onClose()
    }

    override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
        onClose()
    }
}
