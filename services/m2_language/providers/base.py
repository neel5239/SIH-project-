from abc import ABC, abstractmethod
from typing import Any


class LanguageProvider(ABC):
    """
    Abstract provider interface for M2 language services.

    M2 can use different providers for online and offline processing.
    """

    @abstractmethod
    def speech_to_text(
        self,
        audio_path: str,
        source_language: str | None = None,
    ) -> dict[str, Any]:
        """
        Convert speech audio into text.
        """
        raise NotImplementedError

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> dict[str, Any]:
        """
        Translate text from source language to target language.
        """
        raise NotImplementedError

    @abstractmethod
    def text_to_speech(
        self,
        text: str,
        language: str,
    ) -> bytes:
        """
        Convert text into speech audio.
        """
        raise NotImplementedError