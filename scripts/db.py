# import sys
import random
import os
import json

import click
from psycopg2.extras import NumericRange
from flask.cli import pass_script_info
from pgcli.main import PGCli

from app import db as db_, models
from scripts.cli import cli


def generate_users(amount=100):
    users = [models.User(username='user%s' % i,
                         email='email%s@gmail.com' % i,
                         password='00000000'
                         ) for i in xrange(amount)]
    db_.session.add_all(users)
    return users


def generate_exercises(users, amount=1000):
    categories = [
        models.Category(name=name) for name in
        'relaxatie concentratie associatie confrontatie overig'.split()
    ]
    ranges = [NumericRange(0, 5), NumericRange(5, 15), NumericRange(15, None)]

    exercises = [models.Exercise(title='title%s' % i,
                                 description='desc%s' % i,
                                 author=random.choice(users),
                                 category=random.choice(categories),
                                 duration=random.choice(ranges),
                                 difficulty=random.choice([0, 1, 2]),
                                 ) for i in xrange(amount)]

    db_.session.add_all(exercises)
    return exercises


def generate_ratings(users, exercises):
    db_.session.add_all(
        models.Rating(user=user,
                      exercise=exercise,
                      fun=random.choice((1, 2, 3, 4, 5)),
                      clear=random.choice((1, 2, 3, 4, 5)),
                      effective=random.choice((1, 2, 3, 4, 5)),
                      )
        for exercise in exercises
        for user in users
        # randomize the mount of ratings a bit. Every user should rate about
        # onr third of exercises.
        if random.choice([False, False, True])
    )


@cli.group(chain=True)
def db():
    '''Database operations.'''


@db.command()
@click.pass_context
def drop(ctx):
    '''Drop all database tables.'''
    models.Base.metadata.drop_all(db_.engine)
    click.echo('Dropped all tables')


@db.command()
@click.option('-d', is_flag=True, default=False)
@click.pass_context
def create(ctx, d):
    '''Optionally drop and create all database tables.'''
    if d:
        ctx.invoke(drop)
    models.Base.metadata.create_all(db_.engine)
    click.echo('Created all tables')


@db.command()
@click.pass_obj
def fill(obj):
    # useramount = 5
    # exerciseamount = 25
    # users = generate_users(amount=useramount)
    # exercises = generate_exercises(users, amount=exerciseamount)
    # generate_ratings(users, exercises[:exerciseamount / 2])
    # users[0].favorite_exercises = exercises[:8]
    categories = [
        models.Category(name=name) for name in
        'relaxatie concentratie associatie confrontatie overig'.split()
    ]
    db_.session.add_all(categories)
    ranges = [NumericRange(0, 5), NumericRange(5, 15), NumericRange(15, None)]

    amc = models.User(username='AMC', password='wateengeluiden')
    db_.session.add(amc)

    ex1 = models.Exercise(title='2-minuten aandacht oefening',
                          author=amc,
                          category=categories[0],
                          duration=ranges[0],
                          difficulty=0,
                          default=True,
                          description=('Ga op een plek zitten waar u rustig de oefening kunt doen. Zit rechtop, schouders en buik ontspannen, hoofd rechtop. Zet een timer op 2 minuten en sluit uw ogen.'
                                       '\n'
                                       '\n'
                                       'Merk op of en waar u spanning en ontspanning voelt en wat de hoogte van de spanning is. U kunt een cijfer tussen 0 en 100 geven als indicatie. Ga met uw aandacht naar de ademhaling.'
                                       'Merk op waar u de beweging voelt, wat het tempo is van de ademhaling en hoeveel ruimte u hebt om te ademen. Als u een gedachte hebt, merk hem op en ga rustig en zonder oordeel terug naar de oefening.'
                                       '\n'
                                       '\n'
                                       'Blijf dit herhalen totdat u merkt dat u met uw aandacht bij u ademhaling kunt blijven. Merk na 2 minuten wederom op hoe hoog de spanning in uw lichaam is. Doe rustig uw ogen open en merk op hoe u zich voelt. Geef uzelf wederom een cijfer voor de hoogte van de spanning.')
                          )
    db_.session.add(ex1)

    ex2 = models.Exercise(title='Oefening Jacobsen',
                          author=amc,
                          category=categories[0],
                          duration=ranges[0],
                          difficulty=0,
                          default=True,
                          description=('Tijdens deze ontspanningsoefening span je je spieren stevig aan, waarna je ze weer ontspant. Door het aan- en ontspannen krijg je een zwaar ontspannen gevoel in je spieren. Door regelmatig deze oefening met aandacht te herhalen leer je spanning, zowel lichamelijk als geestelijk vroegtijdig herkennen zodat je deze actief kan loslaten.'
                                       '\n'
                                       '\n'
                                       'Als u het prettig vindt om thuis te oefenen met een stem erbij kunt u op internet verschillende Jacobson-oefeningen vinden op [ioconsult](http://www.ioconsult.nl/audio/)')
                          )
    db_.session.add(ex2)

    ex3 = models.Exercise(title='Moodboard',
                          author=amc,
                          category=categories[2],
                          duration=ranges[0],
                          difficulty=0,
                          default=True,
                          description=('Met deze techniek brengt u de associaties in beeld die u met het geluid heeft. Maak uw hoofd leeg.  Concentreer u op uw misofoniegeluid. Probeer een paar minuten alleen daaraan te denken.  Registreer welk emotie, beeld, kleur, vorm, associatie dat bij u oproept. Deze [video](https://www.youtube.com/watch?v=uJWqhQQLJ1Y) laat zien hoe je een moodboard kan maken.'
                                       '\n'
                                       '\n'
                                       'Maak ook een positief moodboard over uw misofoniegeluiden. Welke positieve associaties zou u met het geluid willen hebben?'
                                       '\n'
                                       '\n'
                                       'Maak nog een tweede positief moodboard, vol associaties die u een positief gevoel geven: blijdschap, trots, vreugde, geluk, feestelijk, geroerd, ontspannen, etc. In dit moodboard komen de associaties die u bij deze positieve emoties heeft.')
                          )
    db_.session.add(ex3)

    ex4 = models.Exercise(title='Lage ademhaling',
                          author=amc,
                          category=categories[0],
                          duration=ranges[1],
                          difficulty=0,
                          default=True,
                          description=('Ga op uw rug liggen met de benen gestrekt en de armen langs uw lichaam. Handpalmen wijzen omhoog. Doe uw ogen dicht en richt uw aandacht op uw adem. Leg een hand op de plek van de romp die beweegt bij de in- en uitademing. Leg zachtjes beide handen of een voorwerp op uw buik en volg uw adem. Voel hoe uw buik met elke inademing omhoog komt en bij elke uitademing zakt.  Adem door uw neus.'
                                       '\n'
                                       '\n'
                                       'Als u het lastig vindt om met uw buik te ademen, oefen dan druk uit met uw hand op de buik tijdens de uitademing en laat uw buik uw hand weer omhoog duwen terwijl u diep inademt. Beweegt uw borst mee met de buik of blijft uw borst onbeweeglijk? Laat een paar minuten uw borst de beweging van de buik volgen. Vindt u de buikademhaling nog steeds moeilijk ga dan op uw buik liggen met u hoofd op uw gevouwen handen en duw uzelf omhoog vanuit uw buik.')
                          )
    db_.session.add(ex4)

    ex5 = models.Exercise(title='Diepe ademhaling',
                          author=amc,
                          category=categories[0],
                          duration=ranges[-1],
                          difficulty=0,
                          default=True,
                          description=('Ga op uw rug liggen met de benen gebogen en uw voeten plat op de grond. Scan uw lichaam om erachter te komen waar spanning zit. Leg een hand op uw borst en op uw buik. Adem langzaam en diep in door uw neus tot in uw buik en duw uw hand zo ver mogelijk omhoog. Zorg ervoor dat u borst licht meebeweegt, maar alleen samen met de buik.'
                                       '\n'
                                       '\n'
                                       'Als dit goed gaat ademt u in door uw neus en uit door uw mond, waarbij u een ontspannen zacht blaasgeluid produceert zoals het suizen van de wind. Uw mond, tong en kaak zijn ontspannen. Adem langzaam en diep in zodat uw buik goed omhoog komt. Concentreer u op het geluid en het gevoel van ademhalen terwijl u zich steeds meer ontspant.  Doe deze oefening dagelijks 5-10 minuten achter elkaar. Als u wilt kan u de duur geleidelijk opvoeren tot 20 minuten.'
                                       '\n'
                                       '\n'
                                       'Maak aan het einde van de sessie tijd om nogmaals de bodyscan te doen om op zoek te gaan naar spanningen. Vergelijk deze spanning met die van voor de oefening.  Wanneer u vertrouwd bent met deze oefening kunt u deze op elk moment van de dag doen, in elke liggende of staande houding.'
                                       '![Imgur](http://i.imgur.com/liZp6P0.png)')
                          )
    db_.session.add(ex5)
    basedir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(basedir, 'amisos.json')) as amisos_json:
        data = json.load(amisos_json)
        amisos = models.Questionnaire.create(db_.session, data)
        db_.session.add(amisos)

    basedir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(basedir, 'stress.json')) as stress_json:
        data = json.load(stress_json)
        stress = models.Questionnaire.create(db_.session, data)
        db_.session.add(stress)

    db_.session.commit()
    # click.echo('Inserted {} users and {} exercises.'.format(useramount,
    #                                                         exerciseamount))


@db.command()
@click.option('--pgclirc',
              default=os.path.expanduser('~/.config/pgcli/config'),
              envvar='PGCLIRC', help='Location of pgclirc file.')
@pass_script_info
def pgcli(info, pgclirc):
    '''Start a pgcli session.'''
    from flask.globals import _app_ctx_stack
    app = _app_ctx_stack.top.app
    pgcli = PGCli(pgclirc_file=pgclirc)
    pgcli.connect_uri(app.config['SQLALCHEMY_DATABASE_URI'])
    pgcli.run_cli()
