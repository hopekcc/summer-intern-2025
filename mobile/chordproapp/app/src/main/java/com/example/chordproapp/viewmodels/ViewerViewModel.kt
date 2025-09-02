package com.example.chordproapp.viewmodels

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.chordproapp.data.repository.SongRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class ViewerViewModel(
    private val repository: SongRepository,
    private val appContext: Context
) : ViewModel() {

    private val _pageImages = MutableStateFlow<List<Bitmap>>(emptyList())
    val pageImages: StateFlow<List<Bitmap>> get() = _pageImages

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> get() = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> get() = _error

    private val _currentPage = MutableStateFlow(0)
    val currentPage: StateFlow<Int> get() = _currentPage

    fun loadPages(songId: Int, totalPages: Int) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            val pages = mutableListOf<Bitmap>()
            try {
                for (i in 1..totalPages) {
                    val bytes = repository.getSongPageImage(songId, i)
                    Log.d("ViewerViewModel", "Page $i bytes size: ${bytes?.size ?: 0}")
                    if (bytes != null) {
                        val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        if (bmp != null) {
                            pages.add(bmp)
                        } else {
                            Log.e("ViewerViewModel", "Failed to decode page $i")
                        }
                    } else {
                        Log.e("ViewerViewModel", "No bytes returned for page $i")
                    }
                }

                if (pages.isEmpty()) {
                    _error.value = "No pages available"
                }
                _pageImages.value = pages

            } catch (e: Exception) {
                _error.value = "Error loading pages: ${e.message}"
                Log.e("ViewerViewModel", "Error loading pages", e)
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun setCurrentPage(page: Int) {
        _currentPage.value = page
    }
}
