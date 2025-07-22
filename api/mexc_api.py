import hmac
import hashlib
import time
import json
import httpx
import asyncio
import websockets
from loguru import logger
from utils.config import Config

class MexcAPI:
    """MEXC API Integration for trading and WebSocket connections."""
    
    # API Endpoints
    ORDER_ENDPOINT = '/api/v3/order'
    ACCOUNT_ENDPOINT = '/api/v3/account'
    EXCHANGE_INFO_ENDPOINT = '/api/v3/exchangeInfo'
    TICKER_PRICE_ENDPOINT = '/api/v3/ticker/price'
    DEPTH_ENDPOINT = '/api/v3/depth'
    OPEN_ORDERS_ENDPOINT = '/api/v3/openOrders'
    
    def __init__(self):
        """Initialize MEXC API with credentials from config."""
        self.api_key = Config.MEXC_API_KEY
        self.api_secret = Config.MEXC_API_SECRET
        self.base_url = "https://api.mexc.com"
        self.ws_url = "wss://wbs.mexc.com/ws"
        self.ws = None
    
    def _generate_signature(self, params):
        """Generate HMAC SHA-256 signature for API authentication."""
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.api_secret.encode('utf-8') if self.api_secret else b'',
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def _http_request(self, method, endpoint, params=None, signed=False):
        """Make HTTP request to MEXC REST API."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if signed:
            if params is None:
                params = {}
            
            # Add timestamp for signed requests
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000  # Optional, but helps prevent replay attacks
            
            # Add API key for signed requests
            params['api_key'] = self.api_key
            
            # Generate signature
            params['signature'] = self._generate_signature(params)
            
            # Add API key to headers for signed requests
            if self.api_key:
                headers['X-MEXC-APIKEY'] = self.api_key
        
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == 'GET':
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == 'POST':
                    response = await client.post(url, json=params, headers=headers)
                elif method.upper() == 'DELETE':
                    response = await client.delete(url, params=params, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error making request to MEXC API: {e}")
            raise
    
    async def get_account_info(self):
        """Get account information."""
        return await self._http_request('GET', self.ACCOUNT_ENDPOINT, signed=True)
    
    async def get_exchange_info(self):
        """Get exchange information including trading pairs and rules."""
        return await self._http_request('GET', self.EXCHANGE_INFO_ENDPOINT)
    
    async def get_ticker_price(self, symbol=None):
        """Get latest price for a specific symbol or all symbols."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._http_request('GET', self.TICKER_PRICE_ENDPOINT, params)
    
    async def get_order_book(self, symbol, limit=100):
        """Get order book for a specific symbol."""
        params = {'symbol': symbol, 'limit': limit}
        return await self._http_request('GET', self.DEPTH_ENDPOINT, params)
    
    async def create_market_buy_order(self, symbol, quantity):
        """Create a market buy order."""
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        return await self._http_request('POST', self.ORDER_ENDPOINT, params, signed=True)
    
    async def create_market_sell_order(self, symbol, quantity):
        """Create a market sell order."""
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        return await self._http_request('POST', self.ORDER_ENDPOINT, params, signed=True)
    
    async def get_order_status(self, symbol, order_id):
        """Check the status of an order."""
        params = {
            'symbol': symbol,
            'orderId': order_id,
            'timestamp': int(time.time() * 1000)
        }
        return await self._http_request('GET', self.ORDER_ENDPOINT, params, signed=True)
    
    async def cancel_order(self, symbol, order_id):
        """Cancel an order."""
        params = {
            'symbol': symbol,
            'orderId': order_id,
            'timestamp': int(time.time() * 1000)
        }
        return await self._http_request('DELETE', self.ORDER_ENDPOINT, params, signed=True)
    
    async def get_open_orders(self, symbol=None):
        """Get all open orders for a symbol or all symbols."""
        params = {'timestamp': int(time.time() * 1000)}
        if symbol:
            params['symbol'] = symbol
        return await self._http_request('GET', self.OPEN_ORDERS_ENDPOINT, params, signed=True)
    
    async def connect_websocket(self, callback):
        """Connect to MEXC WebSocket and set up a listener."""
        logger.info("Connecting to MEXC WebSocket...")
        self.ws = await websockets.connect(self.ws_url)
        logger.info("Connected to MEXC WebSocket")
        
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=30)
                    await callback(json.loads(msg))
                except asyncio.TimeoutError:
                    # Send ping to keep the connection alive
                    await self.ws.send(json.dumps({"method": "PING"}))
                    logger.debug("Sent ping to WebSocket")
        except websockets.ConnectionClosed:
            logger.warning("WebSocket connection closed. Reconnecting...")
            await self.reconnect_websocket(callback)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self.reconnect_websocket(callback)
    
    async def reconnect_websocket(self, callback):
        """Reconnect to WebSocket if the connection is lost."""
        try:
            await asyncio.sleep(5)  # Wait before reconnecting
            await self.connect_websocket(callback)
        except Exception as e:
            logger.error(f"Error reconnecting to WebSocket: {e}")
            # Try again with increasing delay
            await asyncio.sleep(10)
            await self.reconnect_websocket(callback)
    
    async def subscribe_to_new_listings(self):
        """Subscribe to new token listing notifications via WebSocket."""
        if not self.ws:
            logger.error("WebSocket not connected. Please connect first.")
            return
        
        subscription_message = {
            "method": "SUBSCRIPTION",
            "params": [
                "spot@public.deals.v3.api"  # This channel might vary depending on MEXC's API
            ]
        }
        
        try:
            await self.ws.send(json.dumps(subscription_message))
            logger.info("Subscribed to new listings channel")
        except Exception as e:
            logger.error(f"Error subscribing to new listings: {e}")
    
    async def subscribe_to_ticker(self, symbol):
        """Subscribe to ticker updates for a specific symbol."""
        if not self.ws:
            logger.error("WebSocket not connected. Please connect first.")
            return
        
        subscription_message = {
            "method": "SUBSCRIPTION",
            "params": [
                f"spot@public.ticker.v3.api@{symbol}"
            ]
        }
        
        try:
            await self.ws.send(json.dumps(subscription_message))
            logger.info(f"Subscribed to ticker updates for {symbol}")
        except Exception as e:
            logger.error(f"Error subscribing to ticker: {e}")
    
    async def close_websocket(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket connection closed")
            self.ws = None
