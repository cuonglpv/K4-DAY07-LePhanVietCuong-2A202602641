"""Run a reproducible retrieval benchmark over the Georgetown Library corpus.

Each member changes only ``STRATEGY`` so comparisons use the same corpus,
embedding backend, chunk size, and benchmark queries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable, Protocol

from dotenv import load_dotenv
from src import (
    Document,
    EmbeddingStore,
    FixedSizeChunker,
    GeminiEmbedder,
    RecursiveChunker,
    SentenceChunker,
    _mock_embed,
)

CORPUS_DIR = Path("data/library-policy")
CACHE_PATH = Path(".embedding_cache.json")
CHUNK_SIZE = 500
# Cường's assigned strategy. Other members should change only this line.
STRATEGY = "recursive"

BENCHMARKS = [
    {
        "query": "How long can I borrow books?",
        "gold_answer": "Georgetown undergraduate students may borrow an unlimited number of books for 6 weeks.",
        "gold_doc_id": "borrowing-books-undergraduate",
        "required_markers": ["unlimited", "6 weeks"],
        "metadata_filter": {"audience": "student"},
    },
    {
        "query": "How many reserve items may a student borrow at one time?",
        "gold_answer": "Students may borrow up to three reserve items at one time.",
        "gold_doc_id": "course-reserves-student",
        "required_markers": ["borrow up to three reserve items"],
        "metadata_filter": {"audience": "student"},
    },
    {
        "query": "How do I request library equipment, and how far in advance must I reserve it?",
        "gold_answer": "Select Reserve this item from an equipment page, open HoyaSearch, and log in to make a request. Reservations must be made at least 1 day in advance.",
        "gold_doc_id": "equipment-loans",
        "required_markers": ["Reserve this item", "at least 1 day in advance"],
        "metadata_filter": None,
    },
    {
        "query": "How long do Interlibrary Loan requests usually take to arrive?",
        "gold_answer": "Items designated Interlibrary Loan Request average 7–14 business days to arrive.",
        "gold_doc_id": "interlibrary-consortium-loans",
        "required_markers": ["7-14 business days"],
        "metadata_filter": None,
    },
    {
        "query": "Where is food allowed in Lauinger Library, and what kinds of food are prohibited?",
        "gold_answer": "Food is allowed only on Lauinger Library's second floor. Pizza, hamburgers, fries, ice cream, hot subs, and other smelly, greasy, or messy foods are prohibited.",
        "gold_doc_id": "library-use-policy",
        "required_markers": ["second floor", "pizza", "hamburgers"],
        "metadata_filter": None,
    },
]


class Chunker(Protocol):
    def chunk(self, text: str) -> list[str]: ...


class CachedEmbedder:
    """Cache embeddings by content hash so repeated benchmark runs save quota."""

    def __init__(self, embedder: Callable[[str], list[float]], cache_path: Path) -> None:
        self.embedder = embedder
        self.cache_path = cache_path
        self._backend_name = getattr(embedder, "_backend_name", "custom")
        try:
            loaded: dict[str, list[float]] = json.loads(cache_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            loaded = {}
        # Migrate cache entries written before backend namespacing. They were
        # produced by the current backend in this run, then become isolated
        # from a later switch to mock/local/OpenAI embeddings.
        self.cache = {
            (key if ":" in key else f"{self._backend_name}:{key}"): value
            for key, value in loaded.items()
        }

    def __call__(self, text: str) -> list[float]:
        key = f"{self._backend_name}:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
        if key not in self.cache:
            self.cache[key] = [float(value) for value in self.embedder(text)]
            self.cache_path.write_text(json.dumps(self.cache), encoding="utf-8")
        return self.cache[key]


class HeadingChunker:
    """Split Markdown by heading, preserving each heading on child chunks."""

    def __init__(self, chunk_size: int = CHUNK_SIZE) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        sections = [section.strip() for section in re.split(r"(?=^#{1,6}\s+)", text, flags=re.M) if section.strip()]
        chunks: list[str] = []
        for section in sections:
            heading_match = re.match(r"^(#{1,6}\s+[^\n]+)", section)
            heading = heading_match.group(1) if heading_match else ""
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue
            for child in self._fallback.chunk(section):
                if heading and not child.startswith(heading):
                    child = f"{heading}\n{child}"
                chunks.append(child)
        return chunks


def parse_markdown(path: Path) -> tuple[dict[str, str], str]:
    """Return simple YAML front matter and the cleaned Markdown body."""
    raw = path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError(f"Expected YAML front matter in {path}")
    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, parts[2].strip()


def make_chunker(strategy: str) -> Chunker:
    chunkers: dict[str, Chunker] = {
        "fixed": FixedSizeChunker(chunk_size=CHUNK_SIZE, overlap=50),
        "sentence": SentenceChunker(max_sentences_per_chunk=3),
        "recursive": RecursiveChunker(chunk_size=CHUNK_SIZE),
        "heading": HeadingChunker(chunk_size=CHUNK_SIZE),
    }
    try:
        return chunkers[strategy]
    except KeyError as error:
        raise ValueError(f"Unknown STRATEGY={strategy!r}; choose one of {sorted(chunkers)}") from error


def make_embedder() -> CachedEmbedder:
    load_dotenv(override=False)
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    if provider == "gemini":
        return CachedEmbedder(GeminiEmbedder(), CACHE_PATH)
    if provider != "mock":
        raise ValueError("bench.py supports EMBEDDING_PROVIDER=mock or gemini")
    return CachedEmbedder(_mock_embed, CACHE_PATH)


def build_store(corpus_dir: Path, chunker: Chunker, embedding_fn: Callable[[str], list[float]]) -> tuple[EmbeddingStore, int]:
    store = EmbeddingStore(collection_name="georgetown-library-benchmark", embedding_fn=embedding_fn)
    documents: list[Document] = []
    for path in sorted(corpus_dir.glob("*.md")):
        metadata, content = parse_markdown(path)
        for index, chunk in enumerate(chunker.chunk(content)):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata={**metadata, "doc_id": path.stem, "chunk_index": index},
                )
            )
    store.add_documents(documents)
    return store, len(documents)


def score_results(benchmark: dict, results: list[dict]) -> tuple[int, int | None, bool]:
    """Return rubric score, gold-document rank, and answer-content availability."""
    gold_rank = next(
        (
            rank
            for rank, result in enumerate(results, start=1)
            if result["metadata"].get("doc_id") == benchmark["gold_doc_id"]
        ),
        None,
    )
    marker_present = any(
        all(marker.lower() in result["content"].lower() for marker in benchmark["required_markers"])
        for result in results
    )
    if not marker_present or gold_rank is None:
        return 0, gold_rank, marker_present
    return (2 if gold_rank == 1 else 1), gold_rank, marker_present


def render_query(number: int, benchmark: dict, results: list[dict], label: str = "") -> list[str]:
    score, gold_rank, marker_present = score_results(benchmark, results)
    lines = [f"\n[{number}{label}] {benchmark['query']}"]
    lines.append(f"  filter={benchmark['metadata_filter'] or 'none'}")
    lines.append(f"  gold={benchmark['gold_doc_id']}: {benchmark['gold_answer']}")
    lines.append(
        f"  rubric_score={score}/2; gold_doc_rank={gold_rank or 'absent'}; "
        f"answer_marker_in_top3={marker_present}"
    )
    for rank, result in enumerate(results, start=1):
        preview = " ".join(result["content"].split())[:180]
        lines.append(
            f"  {rank}. score={result['score']:.4f} "
            f"doc_id={result['metadata'].get('doc_id')} | {preview}"
        )
    return lines


def run_strategy(strategy: str, include_ab: bool, embedding_fn: CachedEmbedder) -> str:
    store, count = build_store(CORPUS_DIR, make_chunker(strategy), embedding_fn)
    lines = [
        f"Strategy: {strategy}",
        f"Embedding backend: {embedding_fn._backend_name}",
        f"Loaded {count} chunks from {CORPUS_DIR}",
    ]
    total = 0
    for number, benchmark in enumerate(BENCHMARKS, start=1):
        results = store.search_with_filter(
            benchmark["query"], top_k=3, metadata_filter=benchmark["metadata_filter"]
        )
        score, _, _ = score_results(benchmark, results)
        total += score
        lines.extend(render_query(number, benchmark, results))

        # Q1 is deliberately ambiguous by audience; run the required A/B test.
        if include_ab and number == 1:
            unfiltered = store.search(benchmark["query"], top_k=3)
            ab_benchmark = {**benchmark, "metadata_filter": None}
            lines.extend(render_query(number, ab_benchmark, unfiltered, label="A/B unfiltered"))
    lines.append(f"\nTotal rubric proxy: {total}/10")
    lines.append(
        "Interpretation: the proxy requires both the gold document and answer markers; "
        "a gold doc_id alone is not treated as a correct retrieval."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Georgetown Library retrieval benchmark.")
    parser.add_argument(
        "--all-strategies",
        action="store_true",
        help="run fixed, sentence, and recursive for the required Q1 A/B comparison",
    )
    parser.add_argument("--output", type=Path, default=Path("ket_qua_benchmark.txt"))
    args = parser.parse_args()
    if not CORPUS_DIR.is_dir():
        raise SystemExit(f"Corpus directory not found: {CORPUS_DIR}")

    embedding_fn = make_embedder()
    strategies = ["fixed", "sentence", "recursive"] if args.all_strategies else [STRATEGY]
    output = "\n".join(run_strategy(strategy, include_ab=True, embedding_fn=embedding_fn) for strategy in strategies)
    args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    print(f"Saved benchmark evidence to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
