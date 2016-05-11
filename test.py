from flask import Flask, jsonify, request, abort
from config import config
from app.database import Database
from app.models import Exercise
from app.lib import Auth

app = Flask(__name__)

# config bevat alle configuratie voor bijvoorbeeld de gegevens over de locatie
# en credentials van de database
app.config.from_object(config)

# initialiseer een interface naar de database met de config waarden van de app
db = Database(app)

# registreer de Auth class met de app
auth = Auth(app)


@app.route('/exercises', methods=['GET'])
def get_exercises():
    '''Retrieve the collection of exercises.'''
    exercises = db.session.query(Exercise).all()
    # jsonify is een functie die een dictionary response omzet in een response
    # met de Content-Type application/json. Een dictionary is aan python
    # datastructuur met keys en values zoals bijvoorbeeld:
    # {
    #     'id': 1,
    #     'title': 'Een mooie oefening',
    #      'description': 'Deze oefening is gewweldig, je hoeft niks te doen.'
    #  }
    return jsonify(exercises.to_dict())


@app.route('/exercises/<id>', methods=['GET'])
def get_exercise(id):
    '''Retrieve an exercise.'''
    exercise = db.session.query(Exercise).filter_by(id=id).first()
    if not exercise:
        # Geef de client een 404 niet gevonden response terug wanneer de
        # oefening niet bestaat.
        abort(404)
    return jsonify(exercise.to_dict())


@app.route('/exercises', methods=['POST'])
@auth.token_required
def post_exercises():
    '''Post a new exercise.'''
    data = request.get_json()
    # haal de json data uit de huidige request object en voer het
    # aan de Exercise constructor. De **data syntax pakt de dictionary uit
    # in individuele key, value parameters.
    exercise = Exercise(**data)
    # Maak de huidig geauthenticeerde user de auteur.
    exercise.author = auth.current_user
    # Voeg de exercise toe aan de database sessie.
    db.session.add(exercise)
    # commit de huidige sessie naar de database. Hierna bestaat de exercise
    # echt.
    db.session.commit()
    return jsonify(exercise.to_dict()), 204


@app.route('/exercises/<id>', methods=['PUT'])
def put_exercise(id):
    '''Update an exercise.'''
    exercise = db.session.query(Exercise).filter_by(id=id).first()

    if not exercise:
        abort(404)

    if exercise.author != auth.current_user:
        # Alleen de auteur mag een oefening aanpassen. Als iemand anders
        # dit probeert breken we af met een 401 Unauthorized status code.
        abort(401)

    data = request.get_json()
    for key, value in data.iteritems():
        # Voor elke ket, value paar in de data updated we het attribuut van
        # de exercise.
        setattr(exercise, key, value)

    db.session.commit()
    return jsonify(exercise.to_dict())


@app.route('/exercises/<id>', methods=['DELETE'])
def delete_exercise(id):
    '''Delete an exercise.'''
    exercise = db.session.query(Exercise).filter_by(id=id).first()

    if not exercise:
        abort(404)

    if exercise.author != auth.current_user:
        abort(401)

    db.session.delete(exercise)
    db.session.commit()

    return {}, 204
