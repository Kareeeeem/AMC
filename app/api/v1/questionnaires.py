from flask import request, abort
from sqlalchemy.orm import contains_eager
from sqlalchemy import and_

from app import auth, db
from app.models import Questionnaire, QuestionnaireResponse
from app.serializers import (
    Serializer,
    QuestionnaireSchema,
    QuestionnaireResponseSchema,
)

from app.lib import Pagination, get_or_404

from . import v1

# QUESTIONNAIRE ENDPOINTS
# ==================
# /questionnaires                         GET
# /questionnaires                         POST
# /questionnaires/<id>                    GET     retrieve a single questionnaire
# /questionnaires/<id>                    PUT     edit questionnaire
# /questionnaires/<id>                    DELETE  delete questionnaire


@v1.route('/questionnaires', methods=['GET'])
@auth.token_required
def get_questionnaires():
    '''Get questionnaires.'''
    serializer = Serializer(QuestionnaireSchema, request.args)
    query = Questionnaire.query.\
        outerjoin(QuestionnaireResponse, and_(
            QuestionnaireResponse.user_id == auth.current_user.id,
            QuestionnaireResponse.questionnaire_id == Questionnaire.id
        )).\
        options(contains_eager(Questionnaire.responses))

    page = Pagination(request, query=query)
    return serializer.dump_page(page)


@v1.route('/questionnaires/<hashid:id>', methods=['GET'])
@auth.token_optional
def get_questionnaire(id):
    '''Get questionnaire.'''

    questionnaire = Questionnaire.query.\
        outerjoin(QuestionnaireResponse, and_(
            QuestionnaireResponse.user_id == auth.current_user.id,
            QuestionnaireResponse.questionnaire_id == Questionnaire.id
        )).\
        filter(Questionnaire.id == id).\
        options(contains_eager(Questionnaire.responses)).first()

    if not questionnaire:
        abort(404)

    serializer = Serializer(QuestionnaireSchema, request.args)
    return serializer.dump(questionnaire)


@v1.route('/questionnaires/<hashid:id>/responses', methods=['POST'])
@auth.token_required
def post_response(id):
    '''Post response.'''
    questionnaire = get_or_404(Questionnaire, id)
    serializer = Serializer(QuestionnaireResponseSchema,
                            request.args,
                            context=dict(questionnaire=questionnaire))
    data = serializer.load(request.get_json())
    data.update(dict(user_id=auth.current_user.id,
                     questionnaire_id=id))
    response = QuestionnaireResponse.create(db.session, data)
    db.session.add(response)
    db.session.commit()
    return serializer.dump(response)


@v1.route('/questionnaires/<hashid:id>/responses', methods=['GET'])
@auth.token_required
def get_responses(id):
    '''Get responses.'''
    serializer = Serializer(QuestionnaireResponseSchema, request.args)
    query = QuestionnaireResponse.query.\
        filter(QuestionnaireResponse.user_id == auth.current_user.id).\
        order_by(QuestionnaireResponse.created_at.desc())
    page = Pagination(request, query=query)
    return serializer.dump_page(page)
