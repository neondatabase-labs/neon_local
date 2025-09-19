#!/usr/bin/env python3

import asyncio
import websockets
import socket
import logging
import os
import sys
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class NeonWebSocketProxy:
    """WebSocket proxy that handles raw PostgreSQL wire protocol for Neon serverless driver."""
    
    def __init__(self):
        self.port = int(os.environ.get('WSPROXY_PORT', 8080))
        self.pgbouncer_host = os.environ.get('PGBOUNCER_HOST', '127.0.0.1')
        self.pgbouncer_port = int(os.environ.get('PGBOUNCER_PORT', 6432))
    
    async def start_server(self):
        """Start the WebSocket server."""
        logger.info(f"Starting Neon WebSocket proxy on port {self.port}")
        logger.info(f"Will proxy to PgBouncer at {self.pgbouncer_host}:{self.pgbouncer_port}")
        
        server = await websockets.serve(
            self.handle_websocket_connection,
            "0.0.0.0",
            self.port,
            ping_interval=None,  # Disable ping/pong for raw protocol
            ping_timeout=None
        )
        
        logger.info(f"Neon WebSocket proxy listening on port {self.port}")
        return server
    
    async def handle_websocket_connection(self, websocket, path):
        """Handle incoming WebSocket connections from Neon serverless driver."""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Got Neon WebSocket connection from {client_addr}")
        
        try:
            # Create TCP connection to PgBouncer
            reader, writer = await asyncio.open_connection(
                self.pgbouncer_host, 
                self.pgbouncer_port
            )
            
            logger.info(f"Connected to PgBouncer at {self.pgbouncer_host}:{self.pgbouncer_port} for {client_addr}")
            
            # Start bidirectional proxying
            await asyncio.gather(
                self.websocket_to_tcp(websocket, writer, client_addr),
                self.tcp_to_websocket(reader, websocket, client_addr),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Error handling WebSocket connection from {client_addr}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            logger.info(f"Closed connection for {client_addr}")
    
    async def websocket_to_tcp(self, websocket, writer, client_addr):
        """Forward messages from WebSocket to TCP (PgBouncer)."""
        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    # Binary message - forward as-is
                    logger.info(f"Forwarding {len(message)} bytes from WebSocket to PgBouncer for {client_addr}")
                    writer.write(message)
                    await writer.drain()
                else:
                    # Text message - encode and forward
                    logger.info(f"Forwarding text message from WebSocket to PgBouncer for {client_addr}")
                    writer.write(message.encode('utf-8'))
                    await writer.drain()
                    
        except (ConnectionClosedError, ConnectionClosedOK):
            logger.info(f"WebSocket connection closed for {client_addr}")
        except Exception as e:
            logger.error(f"Error in websocket_to_tcp for {client_addr}: {e}")
    
    async def tcp_to_websocket(self, reader, websocket, client_addr):
        """Forward messages from TCP (PgBouncer) to WebSocket."""
        try:
            while True:
                # Read data from PgBouncer
                data = await reader.read(8192)
                if not data:
                    logger.info(f"PgBouncer connection closed for {client_addr}")
                    break
                
                # Forward to WebSocket as binary
                logger.info(f"Forwarding {len(data)} bytes from PgBouncer to WebSocket for {client_addr}")
                await websocket.send(data)
                
        except (ConnectionClosedError, ConnectionClosedOK):
            logger.info(f"WebSocket connection closed for {client_addr}")
        except Exception as e:
            logger.error(f"Error in tcp_to_websocket for {client_addr}: {e}")

async def main():
    """Main function to start the Neon WebSocket proxy."""
    proxy = NeonWebSocketProxy()
    server = await proxy.start_server()
    
    try:
        # Keep the server running
        await server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Shutting down Neon WebSocket proxy...")
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Neon WebSocket proxy stopped")
        sys.exit(0)
