import math
from importlib.util import find_spec

import pytest

from pipeline.embed import EMBEDDING_DIM, HashingEmbedder, get_embedder
from pipeline.index import dot


@pytest.fixture
def embedder():
    return HashingEmbedder()


def test_vectors_have_the_right_size_and_unit_length(embedder):
    (vector,) = embedder.embed_documents(["Remote work is allowed three days per week."])
    assert len(vector) == EMBEDDING_DIM
    assert math.isclose(math.sqrt(dot(vector, vector)), 1.0, rel_tol=1e-9)


def test_embedding_is_deterministic(embedder):
    text = "The router restarts twice during the firmware update."
    assert embedder.embed_query(text) == HashingEmbedder().embed_query(text)


def test_documents_and_queries_use_the_same_space(embedder):
    text = "factory reset button"
    assert embedder.embed_documents([text])[0] == embedder.embed_query(text)


def test_related_text_scores_higher_than_unrelated(embedder):
    query = embedder.embed_query("How many days can I work remotely?")
    related = embedder.embed_documents(["Employees may work remotely up to three days per week."])[0]
    unrelated = embedder.embed_documents(["Hold the reset button for ten seconds."])[0]
    assert dot(query, related) > dot(query, unrelated) + 0.1


def test_simple_plurals_share_features(embedder):
    assert dot(embedder.embed_query("device"), embedder.embed_query("devices")) > 0.99


def test_text_without_content_words_gives_a_zero_vector_not_an_error(embedder):
    assert embedder.embed_query("the of and") == [0.0] * EMBEDDING_DIM
    assert embedder.embed_query("") == [0.0] * EMBEDDING_DIM


def test_non_latin_text_is_supported(embedder):
    vector = embedder.embed_query("مرخصی سالانه چند روز است")
    assert math.isclose(dot(vector, vector), 1.0, rel_tol=1e-9)


def test_default_backend_is_the_hashing_embedder(monkeypatch):
    monkeypatch.delenv("EMBEDDING_BACKEND", raising=False)
    assert isinstance(get_embedder(), HashingEmbedder)


def test_unknown_backend():
    with pytest.raises(ValueError, match="Unknown EMBEDDING_BACKEND"):
        get_embedder("does-not-exist")


@pytest.mark.skipif(find_spec("sentence_transformers") is not None, reason="library is installed")
def test_missing_optional_dependency_gives_a_helpful_error():
    with pytest.raises(RuntimeError, match="requirements-ml.txt"):
        get_embedder("sentence-transformers")
