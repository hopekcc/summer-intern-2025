import os
import subprocess
import tempfile
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Import the unlimited scraper modules
import sys
unlimited_path = os.path.join(os.path.dirname(__file__), '..', 'unlimited')
sys.path.insert(0, unlimited_path)
from scraper import song_scraper, chordpro_utils

from scripts.runtime.logger import logger as _app_logger

logger = _app_logger.getChild("api.unlimited")

router = APIRouter(prefix="/unlimited", tags=["Song Scraping"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ScrapeRequest(BaseModel):
    title: str = Field(..., description="Song title to search for", example="Wonderwall")
    artist: Optional[str] = Field(None, description="Artist name (optional)", example="Oasis")
    debug: bool = Field(False, description="Enable debug output")

class ScrapeResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    pdf_path: Optional[str] = Field(None, description="Path to generated PDF file")
    chordpro_path: Optional[str] = Field(None, description="Path to generated ChordPro file")

# ============================================================================
# UNLIMITED SONG SCRAPING ENDPOINTS
# ============================================================================

@router.post("/scrape", response_model=ScrapeResponse, summary="Scrape Song", description="Scrape a song from online sources and generate PDF/ChordPro files.")
async def scrape_song(request: ScrapeRequest):
    """
    Scrape a song using the unlimited CLI logic and return PDF if successful.
    
    This endpoint replicates the functionality of the unlimited CLI:
    1. Scrapes raw chord text from online sources
    2. Processes and validates the ChordPro format
    3. Saves as .pro file
    4. Converts to PDF using chordpro binary
    5. Returns success/error status
    """
    title = request.title.strip()
    artist = request.artist.strip() if request.artist else None
    
    if not title:
        raise HTTPException(status_code=400, detail="Song title is required")
    
    logger.info(f"Scraping song: '{title}'" + (f" by {artist}" if artist else ""))
    
    try:
        # Step 1: Scrape raw text (same as CLI)
        logger.info("Step 1: Scraping raw chord text...")
        raw_text = song_scraper.scrape_song_raw(title, artist)
        if not raw_text:
            logger.warning("Could not retrieve any chords")
            return ScrapeResponse(
                success=False,
                message="❌ Could not retrieve any chords for this song."
            )
        
        # Step 2: Validate + convert (same as CLI)
        logger.info("Step 2: Processing and validating ChordPro format...")
        chordpro_text = chordpro_utils.process_raw_chords(raw_text)
        
        # Step 3: Only proceed if valid (same as CLI)
        if not chordpro_utils.is_chordpro(chordpro_text):
            logger.warning("ChordPro validation failed after cleanup")
            return ScrapeResponse(
                success=False,
                message="⚠️ Could not generate valid ChordPro format for this song."
            )
        
        # Step 4: Save as .pro file (same as CLI)
        logger.info("Step 3: Saving ChordPro file...")
        save_path = song_scraper.save_to_file(title, artist, chordpro_text)
        logger.info(f"Saved ChordPro to: {save_path}")
        
        # Step 5: Render to PDF using chordpro binary (same as CLI)
        logger.info("Step 4: Converting to PDF...")
        pdf_path = save_path.replace(".pro", ".pdf")
        
        try:
            subprocess.run(
                ["chordpro", save_path, "--output", pdf_path],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Successfully generated PDF: {pdf_path}")
            
            return ScrapeResponse(
                success=True,
                message=f"✅ Successfully scraped and converted '{title}'" + (f" by {artist}" if artist else "") + " to PDF.",
                pdf_path=pdf_path,
                chordpro_path=save_path
            )
            
        except FileNotFoundError:
            logger.error("chordpro binary not found")
            return ScrapeResponse(
                success=False,
                message="⚠️ chordpro binary not found. Install it and ensure it's on your PATH.",
                chordpro_path=save_path
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"chordpro failed with exit code {e.returncode}")
            return ScrapeResponse(
                success=False,
                message=f"⚠️ chordpro failed with exit code {e.returncode}. ChordPro file saved but PDF conversion failed.",
                chordpro_path=save_path
            )
            
    except Exception as e:
        logger.error(f"Unexpected error during scraping: {e}", exc_info=True)
        return ScrapeResponse(
            success=False,
            message=f"❌ Unexpected error: {str(e)}"
        )

@router.get("/download-pdf")
async def download_pdf(file_path: str = Query(..., description="Full path to the PDF file")):
    """
    Download a generated PDF file.
    
    Args:
        file_path: Full path to the PDF file to download
        
    Returns:
        FileResponse with the PDF file or error if file not found
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    if not file_path.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File is not a PDF")
    
    # Extract filename for download
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        media_type='application/pdf',
        filename=filename
    )

@router.get("/download-chordpro")
async def download_chordpro(file_path: str = Query(..., description="Full path to the ChordPro file")):
    """
    Download a generated ChordPro (.pro) file.
    
    Args:
        file_path: Full path to the ChordPro file to download
        
    Returns:
        FileResponse with the ChordPro file or error if file not found
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ChordPro file not found")
    
    if not file_path.endswith('.pro'):
        raise HTTPException(status_code=400, detail="File is not a ChordPro file")
    
    # Extract filename for download
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        media_type='text/plain',
        filename=filename
    )

@router.get("/health")
async def health_check():
    """
    Health check endpoint for the unlimited scraper service.
    
    Returns:
        Status of the scraper dependencies
    """
    status = {
        "service": "unlimited-scraper",
        "status": "healthy",
        "dependencies": {}
    }
    
    # Check if chordpro binary is available
    try:
        result = subprocess.run(
            ["chordpro", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        status["dependencies"]["chordpro"] = {
            "available": True,
            "version": result.stdout.strip() if result.returncode == 0 else "unknown"
        }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        status["dependencies"]["chordpro"] = {
            "available": False,
            "error": "Binary not found or timeout"
        }
    
    # Check if songs directory exists
    songs_dir = song_scraper.SONGS_DIR
    status["dependencies"]["songs_directory"] = {
        "path": songs_dir,
        "exists": os.path.exists(songs_dir),
        "writable": os.access(songs_dir, os.W_OK) if os.path.exists(songs_dir) else False
    }
    
    return status
