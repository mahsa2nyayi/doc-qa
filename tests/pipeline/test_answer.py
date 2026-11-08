from pipeline.answer import best_sentences
from pipeline.embed import HashingEmbedder
from pipeline.extract import extract_pages
from tests.helpers import HANDBOOK, MANUAL, sample_bytes

embedder = HashingEmbedder()


def test_picks_the_sentence_that_answers_the_question():
    page = extract_pages(sample_bytes(HANDBOOK), HANDBOOK)[0].text
    answer = best_sentences(embedder, "How many days per week can I work from home?", page, n=1)
    assert "three days per week" in answer


def test_returns_sentences_in_their_original_order():
    page = extract_pages(sample_bytes(MANUAL), MANUAL)[1].text
    answer = best_sentences(embedder, "How do I reset the router to factory settings?", page, n=2)
    assert answer.index("A factory reset is performed") < answer.index("A factory reset erases")


def test_short_text_is_returned_whole():
    assert best_sentences(embedder, "anything", "One sentence only.", n=2) == "One sentence only."
