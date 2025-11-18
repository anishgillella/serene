"""AssemblyAI streaming STT integration (Universal Streaming v3)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Iterable, List, Optional

import websockets
from websockets.http import Headers

logger = logging.getLogger(__name__)

ASSEMBLY_REALTIME_URL = "wss://streaming.assemblyai.com/v3/ws"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_MODEL = "universal-streaming-english"


class AssemblyAIStreamingClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> None:
        self.api_key = api_key or os.environ.get("ASSEMBLY_API_KEY")
        if not self.api_key:
            raise RuntimeError("ASSEMBLY_API_KEY missing. Set it in .env")
        self.sample_rate = sample_rate

    @property
    def url(self) -> str:
        """Build WebSocket URL"""
        return (
            f"{ASSEMBLY_REALTIME_URL}?sample_rate={self.sample_rate}"
            f"&speech_model={DEFAULT_MODEL}"
        )

    async def stream_segments(self, segments: Iterable[bytes]) -> List[str]:
        transcripts: List[str] = []
        turn_buffer: dict = {}  # Buffer to track latest transcript per turn
        
        # Add Authorization header for v3 API
        headers = Headers({"Authorization": self.api_key})
        async with websockets.connect(
            self.url,
            additional_headers=headers,
            ping_interval=5,
            ping_timeout=20,
        ) as ws:

            async def sender() -> None:
                # AssemblyAI requires chunks between 50-1000ms
                # At 16kHz 16-bit PCM: 50ms = 1600 bytes, 1000ms = 32000 bytes
                CHUNK_SIZE_BYTES = 3200  # ~100ms at 16kHz 16-bit PCM
                
                for segment in segments:
                    if not segment:
                        continue
                    # Split large segments into smaller chunks
                    for i in range(0, len(segment), CHUNK_SIZE_BYTES):
                        chunk = segment[i : i + CHUNK_SIZE_BYTES]
                        if len(chunk) >= 1600:  # Ensure at least 50ms
                            # v3 API accepts binary audio data directly
                            await ws.send(chunk)
                            await asyncio.sleep(0.05)
                
                # Wait a bit for final transcripts to arrive
                await asyncio.sleep(1.0)
                # Close the connection
                await ws.close()

            send_task = asyncio.create_task(sender())
            
            try:
                async for message in ws:
                    # Handle both binary and text messages
                    if isinstance(message, bytes):
                        try:
                            data = json.loads(message.decode('utf-8'))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                    else:
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError:
                            continue
                    
                    # Extract transcript from response
                    msg_type = data.get("type") or data.get("message_type")
                    
                    if msg_type == "Begin":
                        continue
                    elif msg_type == "Turn":
                        # v3 API uses "Turn" for transcripts
                        turn_order = data.get("turn_order", 0)
                        is_final = data.get("end_of_turn", False)
                        text = data.get("transcript", "").strip()
                        
                        if text:
                            # Store in buffer with turn_order as key
                            turn_buffer[turn_order] = text
                            logger.debug(f"Turn {turn_order} (final={is_final}): {text}")
                            
                            # If end of turn, add to final transcripts
                            if is_final and turn_order in turn_buffer:
                                final_text = turn_buffer.pop(turn_order)
                                logger.info(f"Final transcript for turn {turn_order}: {final_text}")
                                transcripts.append(final_text)
                    elif msg_type == "End":
                        break
            except Exception as e:
                # Connection closed, which is expected after all segments
                logger.debug(f"Connection closed: {e}")
            finally:
                try:
                    await send_task
                except Exception:
                    pass
        
        # Add any remaining buffered transcripts
        for text in turn_buffer.values():
            if text:
                transcripts.append(text)
        
        return transcripts

    def transcribe(self, segments: Iterable[bytes]) -> List[str]:
        return asyncio.run(self.stream_segments(segments))
