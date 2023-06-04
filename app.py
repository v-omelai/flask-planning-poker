import datetime
import os
import uuid

import randomname
from flask import Flask, redirect, render_template, url_for, request

from helpers import Session


app = Flask(__name__)
session = Session(url=os.getenv('REDIS_URL'))  # sudo service redis-server start


@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('session_'))


@app.route('/session/', methods=['GET'])
@app.route('/session/<key>', methods=['GET'])
def session_(key=None):
    if key is None or not session.exists(key):
        key, creator = str(uuid.uuid4()), str(uuid.uuid4())
        session.set(key, {'vote': {'started': None, 'creator': creator, 'participants': {}}})
        return render_template('creator.html', key=key, creator=creator,
                               link=url_for('session_', key=key))
    else:
        # https://github.com/beasteers/randomname
        alternative = randomname.get_name(
            adj=('colors', ), noun=('coding', ), sep=' '
        ).title()
        return render_template('invited.html', key=key, alternative=alternative)


@app.route('/vote/', methods=['POST'])
def vote():
    form = {**request.form}
    if all(
        k in form.keys() for k in ('key', 'name', 'alternative', 'value', 'unit')
    ):
        key, voter = form['key'], f'{form["name"]} aka {form["alternative"]}'
        td = datetime.timedelta(**{form['unit']: int(form['value'])})
        dt = datetime.datetime.now(datetime.timezone.utc)
        current = session.get(key)
        current['vote']['participants'][voter] = (td, dt)
        session.set(key, current)
        return 'OK', 200
    return 'Bad Request', 400


@app.route('/start/', methods=['POST'])
def start():
    form = {**request.form}
    if all(
        k in form.keys() for k in ('key', 'creator')
    ):
        key, creator = form['key'], form['creator']
        current = session.get(key)
        if current['vote']['creator'] != creator:
            return 'Forbidden', 403
        current['vote']['started'] = datetime.datetime.now(datetime.timezone.utc)
        session.set(key, current)
        return 'OK', 200
    return 'Bad Request', 400


@app.route('/stop/', methods=['POST'])
def stop():
    form = {**request.form}
    if all(
        k in form.keys() for k in ('key', 'creator')
    ):
        key, creator = form['key'], form['creator']
        current = session.get(key)
        if current['vote']['creator'] != creator:
            return 'Forbidden', 403
        started = current['vote']['started']
        finished = datetime.datetime.now(datetime.timezone.utc)
        participants = current['vote']['participants']
        new = {}
        for voter in participants.keys():
            td, dt = participants[voter]
            if started < dt < finished:
                new[voter] = td, dt
        current['vote']['participants'] = new
        session.set(key, current)

        results = {}
        if new:
            tds = [td for td, dt in new.values()]
            results['votes'] = {voter: str(td) for voter, (td, dt) in new.items()}
            results['min'] = str(min(tds))
            results['max'] = str(max(tds))
            results['average'] = str(sum(tds, datetime.timedelta()) / len(tds))
        return results, 200
    return 'Bad Request', 400
