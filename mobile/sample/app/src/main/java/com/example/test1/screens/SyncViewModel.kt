package com.example.musicsync.viewmodel

import android.net.Uri
import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

data class SyncUiState(
    val isFullscreen: Boolean = false,
    val currentPage: Int = 1,
    val totalPages: Int = 5,
    val currentPdfUri: Uri? = null,
    val songQueue: List<String> = listOf("Song A", "Song B"),
    val participants: List<String> = listOf("Alice", "Bob")
)

class SyncViewModel : ViewModel() {

    private val _uiState = MutableStateFlow(SyncUiState())
    val uiState: StateFlow<SyncUiState> = _uiState

    fun toggleFullscreen() {
        _uiState.value = _uiState.value.copy(isFullscreen = !_uiState.value.isFullscreen)
    }

    fun nextPage() {
        val current = _uiState.value.currentPage
        if (current < _uiState.value.totalPages) {
            _uiState.value = _uiState.value.copy(currentPage = current + 1)
        }
    }

    fun previousPage() {
        val current = _uiState.value.currentPage
        if (current > 1) {
            _uiState.value = _uiState.value.copy(currentPage = current - 1)
        }
    }

    fun removeParticipant(name: String) {
        _uiState.value = _uiState.value.copy(
            participants = _uiState.value.participants.filterNot { it == name }
        )
    }

    fun leaveRoom() {
        // Handle leaving logic here (navigation back, clearing state, etc.)
    }
}
