import asyncio
import websockets
import json
import logging
from typing import Dict, Set
from fastapi import FastAPI, WebSocket

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储WebSocket连接
connections: Dict[str, Set[WebSocket]] = {}

async def register_client(websocket: WebSocket, article_id: str):
    """注册客户端连接"""
    if article_id not in connections:
        connections[article_id] = set()
    connections[article_id].add(websocket)
    logger.info(f"客户端已连接到文章 {article_id}，当前连接数: {len(connections[article_id])}")

async def unregister_client(websocket: WebSocket, article_id: str):
    """注销客户端连接"""
    if article_id in connections and websocket in connections[article_id]:
        connections[article_id].remove(websocket)
        logger.info(f"客户端已断开连接文章 {article_id}，剩余连接数: {len(connections[article_id]) if article_id in connections else 0}")

async def send_progress_update(article_id: str, progress_data: dict):
    """发送进度更新到所有连接的客户端"""
    if article_id in connections:
        # 发送给所有连接到该文章的客户端
        disconnected_clients = set()
        for websocket in connections[article_id]:
            try:
                await websocket.send_text(json.dumps(progress_data))
            except Exception:
                disconnected_clients.add(websocket)
        
        # 移除断开连接的客户端
        for websocket in disconnected_clients:
            await unregister_client(websocket, article_id)

async def websocket_handler(websocket: websockets.WebSocketServerProtocol, path: str):
    """WebSocket处理函数"""
    article_id = None
    try:
        # 等待客户端发送注册消息
        message = await websocket.recv()
        data = json.loads(message)
        
        if data.get("type") == "register":
            article_id = str(data.get("article_id"))
            await register_client(websocket, article_id)
            
            # 发送确认消息
            await websocket.send(json.dumps({
                "type": "registered",
                "article_id": article_id,
                "message": "连接已建立"
            }))
            
            # 保持连接直到客户端断开
            async for message in websocket:
                # 处理客户端消息（如果需要）
                pass
                
    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端连接已关闭")
    except Exception as e:
        logger.error(f"WebSocket处理错误: {e}")
    finally:
        if article_id:
            await unregister_client(websocket, article_id)

# 启动WebSocket服务器的函数
async def start_websocket_server(host: str = "localhost", port: int = 8765):
    """启动WebSocket服务器"""
    server = await websockets.serve(websocket_handler, host, port)
    logger.info(f"WebSocket服务器已启动在 {host}:{port}")
    return server

# 用于FastAPI应用的WebSocket端点
def setup_websocket_endpoint(app: FastAPI):
    """在FastAPI应用中设置WebSocket端点"""
    @app.websocket("/ws/{article_id}")
    async def websocket_endpoint(websocket: WebSocket, article_id: str):
        """WebSocket端点"""
        await websocket.accept()
        await register_client(websocket, article_id)

        try:
            # 发送确认消息
            await websocket.send_text(json.dumps({
                "type": "registered",
                "article_id": article_id,
                "message": "连接已建立"
            }))

            # 保持连接直到客户端断开
            while True:
                try:
                    message = await websocket.receive_text()
                    # 处理客户端消息（如果需要）
                    pass
                except Exception:
                    break

        except Exception as e:
            logger.error(f"WebSocket处理错误: {e}")
        finally:
            await unregister_client(websocket, article_id)

# 导出函数
__all__ = ["send_progress_update", "setup_websocket_endpoint", "start_websocket_server"]