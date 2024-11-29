from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


app = FastAPI()
html = """ <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat</title>
</head>
<body>
    <h1>WebSocket Chat</h1>
    <form id="usernameForm" onsubmit="setUsername(event)">
        <label for="username">Enter your username:</label>
        <input type="text" id="username" required>
        <button>Join Chat</button>
    </form>
    <div id="chat" style="display:none;">
        <h2>Welcome, <span id="ws-username"></span>!</h2>
        <form onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off" placeholder="Type a message..." required>
            <button>Send</button>
        </form>
        <ul id="messages"></ul>
    </div>
    <script>
        let username = null;
        let ws = null;

        function setUsername(event) {
            event.preventDefault();
            username = document.getElementById("username").value.trim();
            if (username) {
                document.getElementById("ws-username").textContent = username;
                document.getElementById("usernameForm").style.display = "none";
                document.getElementById("chat").style.display = "block";
                ws = new WebSocket(`ws://${location.host}/ws/${username}`); // Dynamically set WebSocket URL
                ws.onmessage = function (event) {
                    const messages = document.getElementById('messages');
                    const message = document.createElement('li');
                    const content = document.createTextNode(event.data);
                    message.appendChild(content);
                    messages.appendChild(message);
                };
                ws.onclose = function () {
                    alert("Disconnected from server");
                };
            }
        }

        function sendMessage(event) {
            event.preventDefault();
            const input = document.getElementById("messageText");
            if (input.value.trim()) {
                ws.send(input.value.trim());
                input.value = '';
            }
        }
    </script>
</body>
</html>"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, exclude: WebSocket = None):
        for connection in self.active_connections.values():
            if connection != exclude:
                await connection.send_text(message)


manager = ConnectionManager()


@app.get("/{username}")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_message(f"You wrote: {data}", websocket)

            await manager.broadcast(
                f"username #{username} says: {data}", exclude=websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"username #{username} left the chat")
