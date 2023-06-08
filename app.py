import datetime
import json
import os
import uuid

import randomname
import redis
from flask import Flask, redirect, render_template, url_for, request


app = Flask(__name__)
r = redis.Redis.from_url(url=os.getenv('REDIS_URL', 'redis://127.0.0.1:6379'))


@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('session'))


@app.route('/session/', methods=['GET'])
@app.route('/session/<key>', methods=['GET'])
def session(key=None):
    if key is None or not r.exists(key):
        key = str(uuid.uuid4())
        r.set(key, json.dumps({'started': None, 'participants': {}}))
        return render_template('creator.html', key=key, link=url_for('session', key=key))
    alternative = randomname.get_name(adj=('colors', ), noun=('coding', ), sep=' ').title()
    return render_template('participant.html', key=key, alternative=alternative)


@app.route('/vote/', methods=['POST'])
def vote():
    form = request.form
    key, name, alternative, value = form['key'], form['name'], form['alternative'], form['value']
    voted = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data = json.loads(r.get(key))
    data['participants'][f'{name} aka {alternative}'] = (value, voted)
    r.set(key, json.dumps(data))
    return 'OK', 200


@app.route('/start/', methods=['POST'])
def start():
    form = request.form
    key = form['key']
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    r.set(key, json.dumps({'started': started, 'participants': {}}))
    return 'OK', 200


@app.route('/stop/', methods=['POST'])
def stop():
    form = request.form
    key = form['key']

    data = json.loads(r.get(key))
    participants = data['participants']

    started = datetime.datetime.fromisoformat(data['started'])
    finished = datetime.datetime.now(datetime.timezone.utc)

    results = {'votes': {}}
    values = set()

    for participant, (value, voted) in participants.items():
        voted = datetime.datetime.fromisoformat(voted)
        if started < voted < finished:
            value = float(value)
            results['votes'][participant] = value
            values.add(value)

    if values:
        results['min'] = min(values)
        results['max'] = max(values)
        results['average'] = round((min(values) + max(values)) / 2, 2)

    return results, 200
