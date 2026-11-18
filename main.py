from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import secrets
import string

BASE_DIR = Path(__file__).parent
rooms = {}
rooms_lock = asyncio.Lock()
MAX_PLAYERS = 3
SYMBOLS = ["A", "B", "C"]
WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]

class Room:
    def __init__(self, code):
        self.code = code
        self.players = {}  # player_id -> {name, symbol, websocket}
        self.board = [""] * 9
        self.turn = 0
        self.winner = None
        self.lock = asyncio.Lock()

    def public_state(self):
        return {
            "type": "state",
            "room": self.code,
            "players": [
                {"id": pid, "name": p["name"], "symbol": p["symbol"]}
                for pid, p in self.players.items()
            ],
            "board": self.board,
            "turn": self.turn,
            "current_symbol": (list(p["symbol"] for p in self.players.values())[self.turn % len(self.players)] if self.players else SYMBOLS[0]),
            "winner": self.winner,
            "max_players": MAX_PLAYERS,
        }

def make_code():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(5))

async def broadcast(room):
    state = room.public_state()
    stale = []
    for pid, player in list(room.players.items()):
        ws = player.get("websocket")
        if ws:
            try:
                await ws.send_json(state)
            except Exception:
                stale.append(pid)
    for pid in stale:
        room.players.pop(pid, None)

app = FastAPI(title="MultiPlay Engine", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "rooms": len(rooms)}

@app.post("/api/rooms")
async def create_room():
    async with rooms_lock:
        code = make_code()
        while code in rooms:
            code = make_code()
        rooms[code] = Room(code)
    return {"room": code, "max_players": MAX_PLAYERS}

@app.get("/api/rooms/{code}")
async def room_info(code: str):
    room = rooms.get(code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada.")
    return {
        "room": room.code,
        "players": len(room.players),
        "max_players": MAX_PLAYERS,
        "started": len(room.players) > 0,
    }

@app.websocket("/ws/{code}")
async def room_socket(websocket: WebSocket, code: str, name: str = "Jogador"):
    code = code.upper()
    await websocket.accept()
    room = rooms.get(code)
    if room is None:
        await websocket.send_json({"type": "error", "message": "Sala não encontrada."})
        await websocket.close(code=1008)
        return

    player_id = secrets.token_urlsafe(8)
    safe_name = " ".join(name.strip().split())[:18] or "Jogador"

    async with room.lock:
        if len(room.players) >= MAX_PLAYERS:
            await websocket.send_json({"type": "error", "message": "A sala já está cheia (máximo de 3 jogadores)."})
            await websocket.close(code=1008)
            return
        symbol = SYMBOLS[len(room.players)]
        room.players[player_id] = {
            "name": safe_name,
            "symbol": symbol,
            "websocket": websocket,
        }
        await broadcast(room)

    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            async with room.lock:
                if player_id not in room.players:
                    break
                player = room.players[player_id]

                if action == "move":
                    index = message.get("index")
                    if room.winner:
                        await websocket.send_json({"type": "notice", "message": "A partida terminou. Reinicie para jogar novamente."})
                        continue
                    if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= 9:
                        await websocket.send_json({"type": "notice", "message": "Posição inválida."})
                        continue
                    active_symbols = [p["symbol"] for p in room.players.values()]
                    expected_symbol = active_symbols[room.turn % len(active_symbols)]
                    if player["symbol"] != expected_symbol:
                        await websocket.send_json({"type": "notice", "message": "Ainda não é a sua vez."})
                        continue
                    if room.board[index]:
                        await websocket.send_json({"type": "notice", "message": "Essa casa já está ocupada."})
                        continue

                    room.board[index] = player["symbol"]
                    if any(all(room.board[i] == player["symbol"] for i in line) for line in WIN_LINES):
                        room.winner = {"symbol": player["symbol"], "name": player["name"]}
                    elif all(room.board):
                        room.winner = {"symbol": None, "name": "Empate"}
                    else:
                        active_symbols = [p["symbol"] for p in room.players.values()]
                        room.turn = (room.turn + 1) % len(active_symbols)
                    await broadcast(room)

                elif action == "reset":
                    # Any connected player can request a new round.
                    room.board = [""] * 9
                    room.turn = 0
                    room.winner = None
                    await broadcast(room)

                else:
                    await websocket.send_json({"type": "notice", "message": "Ação desconhecida."})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        async with room.lock:
            room.players.pop(player_id, None)
            if not room.players:
                rooms.pop(code, None)
            else:
                await broadcast(room)
