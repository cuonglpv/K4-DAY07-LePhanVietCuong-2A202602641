from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # Keep the sentence-ending punctuation with its sentence.  The final
        # alternative also accepts a sentence that has no trailing whitespace.
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])(?:\s+|$)", text.strip())
            if sentence.strip()
        ]
        return [
            " ".join(sentences[index : index + self.max_sentences_per_chunk])
            for index in range(0, len(sentences), self.max_sentences_per_chunk)
        ]


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        # A positive limit is necessary to guarantee progress in the final
        # character-level fallback.
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text.strip()] if current_text.strip() else []

        if not remaining_separators:
            return [
                current_text[index : index + self.chunk_size].strip()
                for index in range(0, len(current_text), self.chunk_size)
                if current_text[index : index + self.chunk_size].strip()
            ]

        separator = remaining_separators[0]
        later_separators = remaining_separators[1:]
        if not separator:
            return self._split(current_text, [])

        # If this separator is absent, try the next, lower-priority one.
        if separator not in current_text:
            return self._split(current_text, later_separators)

        # Retain separators so that sentences/paragraphs do not run together
        # when adjacent pieces are packed into a chunk.
        pieces = current_text.split(separator)
        units: list[str] = []
        for index, piece in enumerate(pieces):
            if not piece and index == len(pieces) - 1:
                continue
            unit = piece + (separator if index < len(pieces) - 1 else "")
            if len(unit) > self.chunk_size:
                units.extend(self._split(unit, later_separators))
            elif unit:
                units.append(unit)

        chunks: list[str] = []
        buffer = ""
        for unit in units:
            if buffer and len(buffer) + len(unit) > self.chunk_size:
                if buffer.strip():
                    chunks.append(buffer.strip())
                buffer = unit
            else:
                buffer += unit
        if buffer.strip():
            chunks.append(buffer.strip())
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    magnitude_a = math.sqrt(sum(value * value for value in vec_a))
    magnitude_b = math.sqrt(sum(value * value for value in vec_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return _dot(vec_a, vec_b) / (magnitude_a * magnitude_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=0),
            "by_sentences": SentenceChunker(),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }
        comparison: dict[str, dict] = {}
        for name, strategy in strategies.items():
            chunks = strategy.chunk(text)
            comparison[name] = {
                "count": len(chunks),
                "avg_length": (sum(map(len, chunks)) / len(chunks)) if chunks else 0.0,
                "chunks": chunks,
            }
        return comparison
