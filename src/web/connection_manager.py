from fastapi import WebSocket
from pydantic import BaseModel


class WebsocketManager:
    pool: dict[str, WebSocket]

    def __init__(self):
        self.pool: dict[str, WebSocket] = {}

    @staticmethod
    def get_ip_port(websocket: WebSocket) -> str:
        assert websocket.client
        return f"{websocket.client.host}:{websocket.client.port}"

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        assert websocket.client
        self.pool[WebsocketManager.get_ip_port(websocket)] = websocket

    async def disconnect(self, websocket: WebSocket):
        del self.pool[WebsocketManager.get_ip_port(websocket)]
        try:
            await websocket.close()
        except:
            pass

    async def broadcast(self, message: BaseModel):
        for key in self.pool.keys():
            try:
                client = self.pool[key]
                await client.send_text(message.model_dump_json())
            except Exception as e:
                print(e)
                await self.disconnect(client)
