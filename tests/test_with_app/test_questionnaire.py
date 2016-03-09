import random

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func

import pytest

from app import models


def generate_response(questionnaire):
    choices = []
    for question in questionnaire.questions:
        choice = dict(question_id=question.id,
                      value=random.choice(question.options).value)
        choices.append(choice)
    return dict(choices=choices)


def test_no_two_answers_for_one_question(amisos, user, session):
    resp = generate_response(amisos)
    resp['choices'][1]['question_id'] = resp['choices'][0]['question_id']
    user.fill_in_questionnaire(amisos, **resp)
    with pytest.raises(IntegrityError):
        session.commit()


def test_response_score(amisos, user, session):
    resp = generate_response(amisos)
    user.fill_in_questionnaire(amisos, **resp)
    session.commit()

    score = session.query(func.sum(models.Choice.value)).\
        join(models.QuestionnaireResponse).\
        filter(models.QuestionnaireResponse.user_id == user.id).\
        group_by(models.QuestionnaireResponse.id).\
        scalar()

    assert score == sum(c['value'] for c in resp['choices'])


def test_delete_questionnaire(user, amisos, session):
    session.delete(amisos)
    session.commit()
    count = session.query(models.Question, models.Option).\
        join(models.Option).\
        count()
    assert count == 0


def test_questionnaire_response_score(user, amisos, session):
    choices1 = []
    for question in amisos.questions:
        choice = dict(question_id=question.id, value=0)
        choices1.append(choice)
    response1 = dict(choices=choices1)
    resp1 = user.fill_in_questionnaire(amisos, **response1)

    choices2 = []
    for question in amisos.questions:
        choice = dict(question_id=question.id, value=2)
        choices2.append(choice)
    response2 = dict(choices=choices2)
    resp2 = user.fill_in_questionnaire(amisos, **response2)

    choices3 = []
    for question in amisos.questions:
        choice = dict(question_id=question.id, value=1)
        choices3.append(choice)
    response3 = dict(choices=choices3)
    resp3 = user.fill_in_questionnaire(amisos, **response3)

    session.commit()

    assert [resp1.score.name,
            resp2.score.name,
            resp3.score.name] == ['subklinisch', 'ernstig', 'matig']
