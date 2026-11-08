import pytest

from apps.documents.models import Document
from apps.retrieval.services import search

pytestmark = pytest.mark.django_db

QUESTION = "How many days per week can I work from home once probation is over?"


def test_best_hit_is_the_right_passage_with_its_page(indexed):
    hits = search(user=indexed, query=QUESTION, top_k=3)

    assert hits[0].chunk.document.title == "nordlicht_handbook"
    assert hits[0].chunk.page == 1
    assert "three days per week" in hits[0].chunk.text
    assert hits[0].score >= hits[1].score >= hits[2].score
    assert 0 < hits[0].score <= 1.0001


def test_other_documents_answer_other_questions(indexed):
    hits = search(user=indexed, query="What does a blinking orange light mean?", top_k=1)
    assert hits[0].chunk.document.title == "aurora7_manual"
    assert hits[0].chunk.page == 3


def test_search_can_be_limited_to_some_documents(indexed):
    manual = Document.objects.get(title="aurora7_manual")
    hits = search(user=indexed, query=QUESTION, top_k=5, document_ids=[manual.id])
    assert hits
    assert {hit.chunk.document_id for hit in hits} == {manual.id}


def test_users_never_search_each_others_documents(indexed, other_user):
    assert search(user=other_user, query=QUESTION) == []


def test_results_below_the_score_threshold_are_dropped(indexed, settings):
    settings.RETRIEVAL_MIN_SCORE = 0.999
    assert search(user=indexed, query=QUESTION) == []


def test_top_k_limits_the_number_of_hits(indexed):
    assert len(search(user=indexed, query=QUESTION, top_k=2)) == 2
