import android.content.Context
import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.chordproapp.data.repository.SongRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

class ViewerViewModel(
    private val repository: SongRepository,
    private val appContext: Context
) : ViewModel() {

    private val _pdfPages = MutableStateFlow<List<Bitmap>>(emptyList())
    val pdfPages: StateFlow<List<Bitmap>> = _pdfPages.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    private val _currentPage = MutableStateFlow(0)
    val currentPage: StateFlow<Int> = _currentPage.asStateFlow()

    private var pdfRenderer: PdfRenderer? = null
    private var parcelFileDescriptor: ParcelFileDescriptor? = null

    fun loadPdf(songId: Int) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            try {
                val pdfBytes = repository.getSongPdf(songId)
                if (pdfBytes != null) {
                    val pages = convertPdfToImages(appContext, pdfBytes)
                    _pdfPages.value = pages
                } else {
                    _error.value = "Failed to load PDF"
                }
            } catch (e: Exception) {
                _error.value = "Error loading PDF: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun updateCurrentPage(page: Int) {
        _currentPage.value = page
    }

    private suspend fun convertPdfToImages(context: Context, pdfBytes: ByteArray): List<Bitmap> {
        return withContext(Dispatchers.IO) {
            val pages = mutableListOf<Bitmap>()

            try {
                val tempFile = File.createTempFile("temp_pdf", ".pdf", context.cacheDir)
                FileOutputStream(tempFile).use { fos ->
                    fos.write(pdfBytes)
                }

                parcelFileDescriptor = ParcelFileDescriptor.open(tempFile, ParcelFileDescriptor.MODE_READ_ONLY)
                pdfRenderer = PdfRenderer(parcelFileDescriptor!!)

                for (i in 0 until pdfRenderer!!.pageCount) {
                    val page = pdfRenderer!!.openPage(i)
                    val bitmap = Bitmap.createBitmap(
                        page.width * 2,
                        page.height * 2,
                        Bitmap.Config.ARGB_8888
                    )
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    pages.add(bitmap)
                    page.close()
                }

                tempFile.delete()
            } catch (e: IOException) {
                throw Exception("Failed to render PDF: ${e.message}")
            }

            pages
        }
    }

    override fun onCleared() {
        super.onCleared()
        try {
            pdfRenderer?.close()
            parcelFileDescriptor?.close()
        } catch (e: IOException) {
            // ignore
        }
    }
}
