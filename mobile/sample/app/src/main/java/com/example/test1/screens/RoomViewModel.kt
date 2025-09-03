package com.yourapp.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class RoomViewModel @Inject constructor(
    private val serverApi: ServerApi, // Retrofit/FastAPI client
    private val roomWsListener: RoomWsListener // WebSocket for real-time page sync
) : ViewModel() {

    // Room State
    private val _roomCode = MutableStateFlow<String?>(null)
    val roomCode = _roomCode.asStateFlow()

    private val _groupName = MutableStateFlow<String?>(null)
    val groupName = _groupName.asStateFlow()

    private val _participants = MutableStateFlow<List<String>>(emptyList())
    val participants = _participants.asStateFlow()

    private val _nowPlaying = MutableStateFlow<String?>(null)
    val nowPlaying = _nowPlaying.asStateFlow()

    private val _currentPage = MutableStateFlow(1)
    val currentPage = _currentPage.asStateFlow()

    private val _pdfUri = MutableStateFlow<String?>(null)
    val pdfUri = _pdfUri.asStateFlow()

    private val _imageUri = MutableStateFlow<String?>(null)
    val imageUri = _imageUri.asStateFlow()

    private val _isHost = MutableStateFlow(false)
    val isHost = _isHost.asStateFlow()

    private val _loading = MutableStateFlow(false)
    val loading = _loading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage = _errorMessage.asStateFlow()

    init {
        // Start listening for real-time page updates via WebSocket
        viewModelScope.launch {
            roomWsListener.pageFlow.collect { page ->
                _currentPage.value = page
            }
        }
    }

    // API Functions

    fun createRoom(token: String, groupName: String) = viewModelScope.launch {
        _loading.value = true
        try {
            val response = serverApi.createRoom("Bearer $token")
            _roomCode.value = response.roomId
            _groupName.value = groupName
            _isHost.value = true
            fetchRoomDetails(token)
        } catch (e: Exception) {
            _errorMessage.value = e.localizedMessage
        } finally {
            _loading.value = false
        }
    }

    fun joinRoom(roomId: String, userName: String, token: String) = viewModelScope.launch {
        _loading.value = true
        try {
            serverApi.joinRoom(roomId, "Bearer $token")
            _roomCode.value = roomId
            _isHost.value = false
            fetchRoomDetails(token)
        } catch (e: Exception) {
            _errorMessage.value = e.localizedMessage
        } finally {
            _loading.value = false
        }
    }

    fun leaveRoom(token: String) = viewModelScope.launch {
        _loading.value = true
        try {
            _roomCode.value?.let { serverApi.leaveRoom(it, "Bearer $token") }
            resetState()
        } catch (e: Exception) {
            _errorMessage.value = e.localizedMessage
        } finally {
            _loading.value = false
        }
    }

    fun selectSong(songId: String, token: String) = viewModelScope.launch {
        _loading.value = true
        try {
            _roomCode.value?.let {
                serverApi.selectSongForRoom(it, songId, "Bearer $token")
                fetchRoomDetails(token)
            }
        } catch (e: Exception) {
            _errorMessage.value = e.localizedMessage
        } finally {
            _loading.value = false
        }
    }

    fun updatePage(page: Int, token: String) = viewModelScope.launch {
        try {
            _roomCode.value?.let {
                serverApi.updateRoomPage(it, page, "Bearer $token")
                _currentPage.value = page
            }
        } catch (e: Exception) {
            _errorMessage.value = e.localizedMessage
        }
    }

    fun fetchRoomDetails(token: String) = viewModelScope.launch {
        try {
            _roomCode.value?.let {
                val details = serverApi.getRoomDetails(it, "Bearer $token")
                _participants.value = details.participants
                _nowPlaying.value = details.songId
                fetchRoomPdf(it, token)
                fetchRoomImage(it, token)
            }
        } catch (e: Exception) {
            _errorMessage.value = e.localizedMessage
        }
    }

    private fun fetchRoomPdf(roomId: String, token: String) = viewModelScope.launch {
        try {
            val pdfUrl = serverApi.getRoomPdf(roomId, "Bearer $token")
            _pdfUri.value = pdfUrl
        } catch (e: Exception) {
            _errorMessage.value = e.localizedMessage
        }
    }

    private fun fetchRoomImage(roomId: String, token: String) = viewModelScope.launch {
        try {
            val imageUrl = serverApi.getRoomImage(roomId, "Bearer $token")
            _imageUri.value = imageUrl
        } catch (e: Exception) {
            _errorMessage.value = e.localizedMessage
        }
    }

    private fun resetState() {
        _roomCode.value = null
        _groupName.value = null
        _participants.value = emptyList()
        _nowPlaying.value = null
        _currentPage.value = 1
        _pdfUri.value = null
        _imageUri.value = null
        _isHost.value = false
        _errorMessage.value = null
    }
}
