import socketio
import json
from sqlalchemy.orm import sessionmaker
from aiohttp import web
from models import Hack, Judge, Prize, db
import utils

sio = socketio.AsyncServer(async_mode='aiohttp')
app = web.Application()
Sesh = sessionmaker(bind=db)
sio.attach(app)

tokens = ['test'] #for now

@sio.on('connect')
async def do_connect(sid, env):
    print(sid, "has connected")
    query = dict(tuple(i.split('=')) for i in env['QUERY_STRING'].split('&'))
    #security, y'all
    if 'admin' not in query or query['admin'] != 'true':
        return 'tok' in query and query['tok'] in tokens
    else:
        return 'tok' in query and query['tok'] == 'the-hash-admin-password'

async def list_all(db_obj, transformer, emit_event):
    venugopal = Sesh()
    query = venugopal.query(db_obj) #don't query A_IN_112, venugopal Seshions don't support that.
    data = []
    for obj in query:
        data.append(transformer(obj))
    venugopal.close()
    await sio.emit(emit_event, json.dumps(data))

@sio.on('list-judges')
async def list_judges(sid, data = None):
    await list_all(Judge, lambda judge: {
            'name': judge.name,
            'email': judge.email,
            'start_loc': judge.start_loc,
            'curr_loc': judge.curr_loc,
            'end_loc': judge.end_loc
        }, 'judges-list')

@sio.on('list-prizes')
async def list_prizes(sid, data = None):
    await list_all(Prize, lambda prize: {
            'name': prize.name,
            'description': prize.description,
            'is_best_overall': prize.is_best_overall
        }, 'prizes-list')

@sio.on('list-hacks')
async def list_hacks(sid, data = None):
    await list_all(Hack, lambda hack: {
            'name': hack.name,
            'description': hack.description,
            'location': hack.location
        }, 'hacks-list')

@sio.on('add-judge')
async def add_judge(sid, judge_json):
    session = Sesh()
    new_start, new_curr, new_end = await utils.allocate_judges(session)
    judge = Judge(name = judge_json['name'],
            email = judge_json['email'],
            start_loc = new_start,
            curr_loc = new_curr,
            end_loc = new_end)
    await utils.set_secret(judge)
    session.add(judge)
    session.commit()
    session.flush()
    session.close()
    await list_judges(sid)

@sio.on('devpost-scrape')
async def scrape_devpost(sid, data):
    session = Sesh()
    await utils.devpost_to_db(session, data)
    await list_hacks()
    await list_prizes()

if __name__ == "__main__":
    web.run_app(app)