import random
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func

import pytest  # noqa

from app import models


def generate_response(questionnaire):
    choices = []
    for question in questionnaire.questions:
        x = random.randrange(len(question.answers))
        choice = dict(question_id=question.id, value=question.answers[x].value)
        choices.append(choice)
    return dict(choices=choices)


def test_no_two_answers_for_one_question(amisos, user, session):
    resp = generate_response(amisos)
    resp['choices'][1]['question_id'] = resp['choices'][0]['question_id']
    user.questionnaire_responses.append(amisos.create_response(**resp))
    with pytest.raises(IntegrityError):
        session.commit()


def test_delete_questionnaire(user, amisos, session):
    session.delete(amisos)
    session.commit()
    a = session.query(models.Answer).all()
    q = session.query(models.Question).all()
    assert not a and not q


def test_response_score(amisos, user, session):
    resp = generate_response(amisos)
    user.questionnaire_responses.append(amisos.create_response(**resp))
    session.commit()

    query = session.query(func.sum(models.AnswerResponse.value))
    query = query.join(models.QuestionnaireResponse)
    query = query.filter(models.QuestionnaireResponse.user_id == user.id)
    query = query.group_by(models.QuestionnaireResponse.id)
    score = query.scalar()

    assert score == sum(c['value'] for c in resp['choices'])
