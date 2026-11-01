"""Unit tests for curated question bank service."""

from app.schemas import QuestionCategory
from app.services.question_bank import (
    get_all_questions,
    get_question_by_id,
    get_questions_by_category,
)


def test_question_bank_counts():
    questions = get_all_questions()
    assert len(questions) == 15

    sql_q = get_questions_by_category(QuestionCategory.SQL)
    py_q = get_questions_by_category(QuestionCategory.PYTHON)
    sys_q = get_questions_by_category(QuestionCategory.ML_SYSTEM_DESIGN)

    assert len(sql_q) == 5
    assert len(py_q) == 5
    assert len(sys_q) == 5


def test_sql_questions_have_duckdb_seeds():
    sql_questions = get_questions_by_category(QuestionCategory.SQL)
    for q in sql_questions:
        assert q.seed_sql is not None and len(q.seed_sql.strip()) > 0
        assert "CREATE TABLE" in q.seed_sql
        assert len(q.rubric_criteria) >= 3


def test_python_questions_have_unit_tests():
    python_questions = get_questions_by_category(QuestionCategory.PYTHON)
    for q in python_questions:
        assert q.unit_tests is not None and len(q.unit_tests.strip()) > 0
        assert q.starter_code is not None and len(q.starter_code.strip()) > 0
        assert "def " in q.starter_code


def test_get_by_id():
    q = get_question_by_id("sql_01_retention_cohort")
    assert q is not None
    assert q.title == "Monthly User Retention Cohort Analysis"

    non_existent = get_question_by_id("non_existent_id")
    assert non_existent is None
