# MultiPlay Engine

Protótipo educacional de uma ferramenta reutilizável para jogos multiplayer com Python, FastAPI e WebSockets. Inclui o jogo **Tabuleiro de Três** para até três jogadores por sala.

## Requisitos
- Python 3.10 ou superior
- Navegador moderno

## Executar localmente

### 1. Criar e ativar um ambiente virtual

Windows (PowerShell):
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependências e iniciar o servidor

```bash
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Abra http://127.0.0.1:8000 em um navegador. Para testar multiplayer, abra outras abas ou use outros dispositivos conectados à mesma rede; para outro dispositivo, use o IP local do computador que executa o servidor.

## Como jogar
1. Uma pessoa cria uma sala e compartilha o código de cinco caracteres.
2. As outras pessoas digitam o código para entrar.
3. Cada jogador recebe uma peça (A, B ou C).
4. Os jogadores alternam turnos. O servidor valida as jogadas e distribui o estado a todos os clientes.
5. Qualquer jogador conectado pode reiniciar a rodada.

## API inicial
- `GET /health` — status do servidor.
- `POST /api/rooms` — cria uma sala.
- `GET /api/rooms/{code}` — consulta uma sala.
- `WS /ws/{code}?name=Nome` — conexão em tempo real.

Mensagens WebSocket de entrada:
```json
{"action": "move", "index": 4}
```
```json
{"action": "reset"}
```

## Arquitetura
- `main.py`: API, salas e coordenação WebSocket (protótipo inicial).
- `static/`: interface web.
- Próxima refatoração recomendada: mover regras para `domain/`, casos de uso para `app/` e comunicação/armazenamento para `infrastructure/`.

## Limitações importantes
- As salas são guardadas em memória: reiniciar o servidor apaga as partidas.
- Este protótipo é para desenvolvimento local e testes. Para publicar na internet, adicione autenticação, rate limiting, validação mais rigorosa, gestão de reconexão e armazenamento persistente.
- O endpoint de reinício é compartilhado por todos os jogadores da sala.
