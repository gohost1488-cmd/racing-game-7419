"""AHVE Racing Server v3 - racing-game-7419. Lobby + Multiplayer."""
import asyncio, json, random, uuid
from aiohttp import web

rooms = {}
players = {}

async def index(request):
    return web.FileResponse('index.html')

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    pid = str(uuid.uuid4())[:8]
    room_id = None
    
    async for msg in ws:
        data = json.loads(msg.data)
        cmd = data.get('cmd')
        
        if cmd == 'create':
            room_id = str(uuid.uuid4())[:6]
            rooms[room_id] = {'players': [], 'started': False}
            pname = data.get('name', 'Player')
            players[pid] = {'id': pid, 'name': pname, 'room': room_id, 'ready': False, 'ws': ws,
                'x': random.uniform(-10, 10), 'z': random.uniform(-10, 10), 'hp': 100, 'kills': 0,
                'color': random.choice(['#e94560','#0f3460','#533483','#f5a623'])}
            rooms[room_id]['players'].append(pid)
            plist = [{'name': players[p]['name'], 'ready': players[p]['ready']} for p in rooms[room_id]['players'] if p in players]
            await ws.send_json({'type': 'lobby', 'room': room_id, 'players': plist})
        
        elif cmd == 'join':
            room_id = data.get('room')
            if room_id in rooms and not rooms[room_id]['started']:
                pname = data.get('name', 'Player')
                players[pid] = {'id': pid, 'name': pname, 'room': room_id, 'ready': False, 'ws': ws,
                    'x': random.uniform(-10, 10), 'z': random.uniform(-10, 10), 'hp': 100, 'kills': 0,
                    'color': random.choice(['#e94560','#0f3460','#533483','#f5a623'])}
                rooms[room_id]['players'].append(pid)
                plist = [{'name': players[x]['name'], 'ready': players[x]['ready']} for x in rooms[room_id]['players'] if x in players]
                for p in rooms[room_id]['players']:
                    if p in players:
                        await players[p]['ws'].send_json({'type': 'lobby', 'room': room_id, 'players': plist})
        
        elif cmd == 'ready':
            if pid in players and players[pid]['room']:
                players[pid]['ready'] = True
                room_id = players[pid]['room']
                all_ready = all(players[p]['ready'] for p in rooms[room_id]['players'] if p in players)
                if all_ready and len(rooms[room_id]['players']) >= 1:
                    rooms[room_id]['started'] = True
                    for p in rooms[room_id]['players']:
                        if p in players:
                            await players[p]['ws'].send_json({'type': 'start', 'player_id': p, 'x': players[p]['x'], 'z': players[p]['z'], 'color': players[p]['color'], 'players': [{'id': x, 'x': players[x]['x'], 'z': players[x]['z'], 'color': players[x]['color']} for x in rooms[room_id]['players'] if x in players and x != p]})
        
        elif data.get('move') and pid in players:
            p = players[pid]
            p['x'] += data['move'].get('x', 0) * 0.3
            p['z'] += data['move'].get('z', 0) * 0.3
            if room_id and room_id in rooms:
                state = {'type': 'state', 'players': [{'id': x, 'x': players[x]['x'], 'z': players[x]['z'], 'hp': players[x]['hp'], 'kills': players[x]['kills']} for x in rooms[room_id]['players'] if x in players]}
                for p2 in rooms[room_id]['players']:
                    if p2 in players:
                        await players[p2]['ws'].send_json(state)
        
        elif data.get('shoot') and pid in players:
            p = players[pid]
            if room_id and room_id in rooms:
                for oid in rooms[room_id]['players']:
                    if oid != pid and oid in players:
                        o = players[oid]
                        dist = ((p['x'] - o['x'])**2 + (p['z'] - o['z'])**2)**0.5
                        if dist < 5:
                            o['hp'] -= 25
                            if o['hp'] <= 0:
                                o['hp'] = 100
                                o['x'] = random.uniform(-10, 10)
                                o['z'] = random.uniform(-10, 10)
                                p['kills'] += 1
                            break
    return ws

app = web.Application()
app.router.add_get('/', index)
app.router.add_get('/ws', ws_handler)

if __name__ == '__main__':
    web.run_app(app, port=5000)
