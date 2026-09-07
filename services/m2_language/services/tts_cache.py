import hashlib
from pathlib import Path


class TTSCache:
    """
    File-based cache for generated TTS audio.

    The cache prevents repeated TTS generation for the same
    text + language combination.
    """

    def __init__(self, cache_dir: str = "services/m2_language/tests/audio/tts_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str, language: str) -> Path:
        cache_key = f"{language}:{text}".encode("utf-8")
        filename = hashlib.sha256(cache_key).hexdigest() + ".wav"
        return self.cache_dir / filename

    def get(self, text: str, language: str) -> bytes | None:
        """
        Return cached audio if available.
        """
        path = self._cache_path(text, language)

        if not path.exists():
            return None

        return path.read_bytes()

    def put(self, text: str, language: str, audio: bytes) -> Path:
        """
        Store generated audio in the cache.
        """
        if not audio:
            raise ValueError("Cannot cache empty audio.")

        path = self._cache_path(text, language)
        path.write_bytes(audio)

        return path

    def get_or_create(
        self,
        text: str,
        language: str,
        generator,
    ) -> bytes:
        """
        Return cached audio or generate and cache it.
        """
        cached = self.get(text, language)

        if cached is not None:
            return cached

        audio = generator(text, language)

        if not audio:
            raise RuntimeError("TTS generator returned empty audio.")

        self.put(text, language, audio)

        return audio