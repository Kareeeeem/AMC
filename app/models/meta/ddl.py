# create a function to calculate the bayesian score based on a 5 star rating
# system.
# http://julesjacobs.github.io/2015/08/17/bayesian-scoring-of-ratings.html
# Will return the default popularity if id is NULL. Which is usefull for
# setting it in a trigger.

UTILITIES = '-5, 2, 3, 4 10'
PRETEND_VOTES = '1, 1, 1, 1, 1'

bayesian = '''
CREATE OR REPLACE FUNCTION bayesian(id bigint) returns FLOAT AS $$
DECLARE
utilities INT[];
pretend_votes INT[];
votes_count INT[];
votes INT[];
sum_vu INT;
ex_id BIGINT;
does_exist BOOLEAN;
BEGIN
    ex_id := id;
    utilities := '{%s}'::INT[];
    pretend_votes := '{%s}'::INT[];
    SELECT INTO votes_count ARRAY[
        coalesce(count(rating) filter (where rating >= 1 and rating < 1.5), 0),
        coalesce(count(rating) filter (where rating >= 1.5 and rating < 2.5), 0),
        coalesce(count(rating) filter (where rating >= 2.5 and rating < 3.5), 0),
        coalesce(count(rating) filter (where rating >= 3.5 and rating < 4.5), 0),
        coalesce(count(rating) filter (where rating >= 4.5 and rating <= 5), 0)
    ] FROM rating where exercise_id = ex_id;

    SELECT INTO votes array(SELECT a+b FROM unnest(pretend_votes, votes_count) x(a,b));
    SELECT INTO sum_vu SUM(v) FROM UNNEST(array(SELECT a*b FROM unnest(votes, utilities) x(a,b))) v;
    RETURN sum_vu / (SELECT SUM(v)::FLOAT FROM UNNEST(votes) v);
END;
$$ LANGUAGE plpgsql strict;
''' % (UTILITIES, PRETEND_VOTES)

drop_bayesian = 'DROP FUNCTION IF EXISTS bayesian(bigint)'

post_create_rating = '''
CREATE OR REPLACE FUNCTION rating_trigger() RETURNS trigger as $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        UPDATE exercise
        SET popularity=bayesian(old.exercise_id),
            avg_rating=(SELECT avg(rating) FROM rating WHERE exercise_id=old.exercise_id),
            avg_fun_rating=(SELECT avg(fun) FROM rating WHERE exercise_id=old.exercise_id),
            avg_effective_rating=(SELECT avg(effective) FROM rating WHERE exercise_id=old.exercise_id),
            avg_clear_rating=(SELECT avg(clear) FROM rating WHERE exercise_id=old.exercise_id)
        WHERE id=old.exercise_id;
        RETURN OLD;
    ELSE
        UPDATE exercise
        SET popularity=bayesian(new.exercise_id),
            avg_rating=(SELECT avg(rating) FROM rating WHERE exercise_id=new.exercise_id),
            avg_fun_rating=(SELECT avg(fun) FROM rating WHERE exercise_id=new.exercise_id),
            avg_effective_rating=(SELECT avg(effective) FROM rating WHERE exercise_id=new.exercise_id),
            avg_clear_rating=(SELECT avg(clear) FROM rating WHERE exercise_id=new.exercise_id)
        WHERE id=new.exercise_id;
        RETURN new;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_ratings AFTER INSERT OR UPDATE OR DELETE
ON %(table)s FOR EACH ROW EXECUTE PROCEDURE rating_trigger();

CREATE OR REPLACE FUNCTION set_avg() RETURNS trigger AS $$
BEGIN
    new.rating := (new.fun + new.clear + new.effective) / 3.0;
    RETURN new;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_avg_trigger BEFORE INSERT OR UPDATE
ON %(table)s FOR EACH ROW EXECUTE PROCEDURE set_avg();
'''

pre_drop_rating = '''
DROP FUNCTION IF EXISTS rating_trigger() CASCADE;
DROP FUNCTION IF EXISTS set_avg() CASCADE;
'''

post_create_exercise = '''
CREATE OR REPLACE FUNCTION default_popularity() RETURNS trigger as $$
BEGIN
    new.popularity := bayesian(new.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_default_popularity BEFORE INSERT
ON %(table)s FOR EACH ROW EXECUTE PROCEDURE default_popularity();
'''

pre_drop_exercise = '''
DROP FUNCTION IF EXISTS default_popularity() CASCADE;
'''
