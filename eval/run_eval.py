"""Measure retrieval quality on the sample documents.

For every question in eval/questions.json the ground truth is a document, a page
and a short answer phrase. A retrieved chunk is "correct" only if it comes from
that page AND contains the phrase. A question counts as a hit at rank k if any of
the top-k chunks is correct.

The "random" row is the expected score of a ranking that ignores the question
completely; it shows how much of the result is just a small corpus.

    python eval/run_eval.py                               # default hash embedder
    EMBEDDING_BACKEND=sentence-transformers python eval/run_eval.py
    python eval/run_eval.py --chunk-size 400 --overlap 80

The evaluation uses the same extract, chunk and embed code as the web app and
an in-memory cosine search. pgvector computes the same cosine similarity, so
the numbers carry over to the API.
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.chunk import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP_CHARS, chunk_pages  # noqa: E402
from pipeline.embed import get_embedder  # noqa: E402
from pipeline.extract import extract_pages  # noqa: E402
from pipeline.index import InMemoryIndex  # noqa: E402

DOCS_DIR = Path(__file__).parent / "docs"
QUESTIONS_FILE = Path(__file__).parent / "questions.json"
KS = (1, 3, 5)
MAX_RANK = 10


def build_index(embedder, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP_CHARS):
    index = InMemoryIndex()
    for path in sorted(DOCS_DIR.glob("*.pdf")):
        chunks = chunk_pages(extract_pages(path.read_bytes(), path.name), max_chars, overlap)
        vectors = embedder.embed_documents([c.text for c in chunks])
        for chunk, vector in zip(chunks, vectors, strict=True):
            index.add(path.name, chunk.page, chunk.index, chunk.text, vector)
    return index


def is_correct(chunk, item: dict) -> bool:
    return (
        chunk.document == item["doc"]
        and chunk.page == item["page"]
        and item["answer"].lower() in chunk.text.lower()
    )


def evaluate(index: InMemoryIndex, embedder, questions: list[dict]) -> dict:
    hits = {k: 0 for k in KS}
    random_hits = {k: 0.0 for k in KS}
    reciprocal_ranks = []
    misses = []
    total_chunks = len(index.items)
    for item in questions:
        gold = sum(1 for chunk in index.items if is_correct(chunk, item))
        if gold == 0:
            raise ValueError(
                f"No chunk contains the answer phrase {item['answer']!r}; the phrase is "
                "split by a chunk boundary or misspelled. Fix questions.json or the chunk size."
            )
        for k in KS:
            random_hits[k] += 1 - math.comb(total_chunks - gold, k) / math.comb(total_chunks, k)

        results = index.search(embedder.embed_query(item["question"]), k=MAX_RANK)
        rank = next(
            (
                position
                for position, (_, chunk) in enumerate(results, start=1)
                if is_correct(chunk, item)
            ),
            None,
        )
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        for k in KS:
            if rank is not None and rank <= k:
                hits[k] += 1
        if rank is None or rank > 1:
            top = results[0][1]
            misses.append(
                {
                    "question": item["question"],
                    "expected": f"{item['doc']} p.{item['page']}",
                    "rank": rank,
                    "top_result": f"{top.document} p.{top.page}",
                }
            )
    total = len(questions)
    return {
        "questions": total,
        "chunks": len(index.items),
        **{f"hit@{k}": hits[k] / total for k in KS},
        **{f"random_hit@{k}": random_hits[k] / total for k in KS},
        "mrr": sum(reciprocal_ranks) / total,
        "not_ranked_first": misses,
    }


def run(backend: str | None = None, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP_CHARS) -> dict:
    embedder = get_embedder(backend)
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    return evaluate(build_index(embedder, max_chars, overlap), embedder, questions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--backend", help="hash or sentence-transformers (default: env or hash)")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP_CHARS)
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args()

    result = run(args.backend, args.chunk_size, args.overlap)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"questions: {result['questions']}   chunks indexed: {result['chunks']}")
    print("| Metric | Value | Random ranking |\n|---|---|---|")
    for k in KS:
        print(f"| Hit@{k} | {result[f'hit@{k}']:.2f} | {result[f'random_hit@{k}']:.2f} |")
    print(f"| MRR | {result['mrr']:.2f} | |")
    if result["not_ranked_first"]:
        print("\nNot ranked first:")
        for miss in result["not_ranked_first"]:
            print(f"- {miss['question']}  expected {miss['expected']}, rank {miss['rank']}, top: {miss['top_result']}")


if __name__ == "__main__":
    main()
