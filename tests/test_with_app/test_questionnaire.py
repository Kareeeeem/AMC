import random
import functools

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func

import pytest  # noqa

from app import models

# generate answers to questionnaire
values = [random.randrange(3) for i in range(10)]


def generate_response(answers, questionnaire):
    choices = []
    for i, question in enumerate(questionnaire.questions):
        choices.append(dict(question_id=question.id, value=answers[i]))
    return dict(choices=choices)

generate_response = functools.partial(generate_response, values)


def test_no_two_answers_for_one_question(amisos, user, session):
    resp = generate_response(amisos)
    resp['choices'][1]['question_id'] = resp['choices'][0]['question_id']
    user.questionnaire_responses.append(amisos.create_response(**resp))
    with pytest.raises(IntegrityError):
        session.commit()


def test_response_score(amisos, user, session):
    resp = generate_response(amisos)
    user.questionnaire_responses.append(amisos.create_response(**resp))
    session.commit()

    score = session.query(func.sum(models.AnswerResponse.value)).\
        join(models.QuestionnaireResponse).\
        filter(models.QuestionnaireResponse.user_id == user.id).\
        group_by(models.QuestionnaireResponse.id).\
        scalar()

    assert score == sum(c['value'] for c in resp['choices'])


def test_delete_questionnaire(user, amisos, session):
    session.delete(amisos)
    session.commit()
    count = session.query(models.Question, models.Answer).\
        join(models.Answer).\
        count()
    assert count == 0
