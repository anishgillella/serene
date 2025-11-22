"""
Simple transcription endpoint using Deepgram REST API
"""
import logging
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcription", tags=["transcription"])

@router.post("/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribe audio file using Deepgram REST API
    
    Accepts: audio file (wav, mp3, m4a, etc.)
    Returns: transcript text
    
    This uses Deepgram REST API for prerecorded transcription (not real-time).
    For real-time transcription during LiveKit sessions, use the agent.
    """
    try:
        # Read audio file
        audio_data = await audio_file.read()
        logger.info(f"Received audio file: {audio_file.filename}, size: {len(audio_data)} bytes")
        
        # Call Deepgram REST API with Nova-3 and utterances for best diarization
        url = "https://api.deepgram.com/v1/listen"
        params = {
            "model": "nova-3",  # Best diarization accuracy
            "language": "en",
            "punctuate": "true",
            "diarize": "true",  # Speaker diarization
            "utterances": "true",  # Returns segment-wise utterances with speaker labels
            "smart_format": "true",
        }
        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}"
        }
        
        logger.info("Sending to Deepgram REST API...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                files={"audio": (audio_file.filename, audio_data)}
            )
            response.raise_for_status()
            result = response.json()
        
        # Extract transcript with speaker diarization
        transcript_text = ""
        utterances = []  # List of utterances with speaker info
        
        if result.get("results") and result["results"].get("channels"):
            channel = result["results"]["channels"][0]
            
            if channel.get("alternatives"):
                alternative = channel["alternatives"][0]
                
                # Get full transcript
                transcript_text = alternative.get("transcript", "")
                
                # Extract utterances with speaker info (if utterances=true was used)
                if "utterances" in alternative:
                    for utterance in alternative["utterances"]:
                        utterances.append({
                            "speaker": utterance.get("speaker", 0),
                            "transcript": utterance.get("transcript", ""),
                            "start": utterance.get("start", 0),
                            "end": utterance.get("end", 0),
                        })
                else:
                    # Fallback: extract from words array
                    words = alternative.get("words", [])
                    current_speaker = None
                    current_text = []
                    
                    for word in words:
                        word_speaker = word.get("speaker")
                        if word_speaker is not None:
                            if current_speaker != word_speaker and current_text:
                                # Save previous utterance
                                utterances.append({
                                    "speaker": current_speaker,
                                    "transcript": " ".join(current_text),
                                    "start": words[0].get("start", 0) if words else 0,
                                    "end": word.get("start", 0),
                                })
                                current_text = []
                            current_speaker = word_speaker
                        
                        if current_speaker is not None:
                            current_text.append(word.get("word", ""))
                    
                    # Add last utterance
                    if current_text and current_speaker is not None:
                        utterances.append({
                            "speaker": current_speaker,
                            "transcript": " ".join(current_text),
                            "start": words[-len(current_text)].get("start", 0) if words else 0,
                            "end": words[-1].get("end", 0) if words else 0,
                        })
        
        logger.info(f"Transcript received: {len(utterances)} utterances, {transcript_text[:100]}...")
        
        return {
            "success": True,
            "transcript": transcript_text,
            "utterances": utterances,  # Speaker-segmented utterances
            "metadata": {
                "filename": audio_file.filename,
                "utterance_count": len(utterances),
            }
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/transcribe-base64")
async def transcribe_base64_audio(audio_base64: str, filename: str = "audio.wav"):
    """
    Transcribe base64-encoded audio
    
    Accepts: base64 string of audio data
    Returns: transcript text
    """
    try:
        import base64
        
        # Decode base64
        audio_data = base64.b64decode(audio_base64)
        logger.info(f"Received base64 audio, decoded size: {len(audio_data)} bytes")
        
        # Initialize Deepgram client
        deepgram = DeepgramClient(settings.DEEPGRAM_API_KEY)
        
        # Create file source
        payload: FileSource = {
            "buffer": audio_data,
        }
        
        # Configure options
        options = PrerecordedOptions(
            model="nova-2",
            language="en",
            punctuate=True,
            diarize=True,
        )
        
        # Transcribe
        logger.info("Sending to Deepgram...")
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        # Extract transcript
        transcript_text = ""
        if response.results and response.results.channels:
            channel = response.results.channels[0]
            if channel.alternatives:
                transcript_text = channel.alternatives[0].transcript
        
        logger.info(f"Transcript received: {transcript_text[:100]}...")
        
        return {
            "success": True,
            "transcript": transcript_text,
            "metadata": {
                "filename": filename,
                "duration": response.metadata.duration if response.metadata else None,
            }
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

