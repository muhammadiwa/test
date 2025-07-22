import hmac
import hashlib
import time
import json
import httpx
import asyncio
from websockets.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed
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
        
        # Validate credentials
        if not self.api_key or not self.api_secret:
            logger.warning("MEXC API credentials are missing or incomplete. API functions requiring authentication will not work.")
        else:
            logger.debug(f"Initialized MEXC API with key: {self.api_key[:5]}...")
            
        # API endpoints
        self.base_url = "https://api.mexc.com"
        self.ws_url = "wss://wbs.mexc.com/ws"
        self.ws = None
    
    def _generate_signature(self, params):
        """Generate HMAC SHA-256 signature for API authentication.
        
        According to MEXC API documentation, the signature is generated using HMAC SHA-256 
        where the key is the API secret and the data is the query string.
        """
        # Make sure api_secret is not None
        if not self.api_secret:
            logger.error("API Secret key is missing or empty")
            return ""
        
        # Handle different parameter types and convert to proper string format
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, bool):
                # Convert booleans to lowercase string (true/false)
                processed_params[key] = str(value).lower()
            elif isinstance(value, (int, float)):
                # Keep numeric values as-is
                processed_params[key] = value
            else:
                # Convert everything else to string
                processed_params[key] = str(value)
        
        # Sort parameters by key to ensure consistent order and convert to string
        # Use the direct string format that MEXC expects
        params_str = '&'.join([f'{k}={v}' for k, v in sorted(processed_params.items())])
        
        # Generate the signature using HMAC SHA-256
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            params_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"Signature generated for: {params_str}")
        
        logger.debug(f"Generating signature for: {params_str}")
        return signature
    
    async def _http_request(self, method, endpoint, params=None, signed=False):
        """Make HTTP request to MEXC REST API."""
        base_url = f"{self.base_url}{endpoint}"
        headers = {}
        
        # Check if API key is available
        if not self.api_key and signed:
            logger.error("API Key is required for signed requests")
            raise ValueError("API Key is missing")
        
        # Set up parameters
        if params is None:
            params = {}
            
        url = base_url
        
        # For signed requests, we need to add timestamp and signature
        if signed:
            # Add API key to headers (this is critical!)
            headers['X-MEXC-APIKEY'] = self.api_key
            
            # Add timestamp and recvWindow to parameters
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000  # Optional, helps prevent replay attacks
            
            # Convert parameters to string for signing
            params_str = '&'.join([f'{k}={v}' for k, v in sorted(params.items())])
            
            # Generate signature
            signature = self._generate_signature(params)
            
            # Construct final URL with parameters and signature
            url = f"{base_url}?{params_str}&signature={signature}"
            
            logger.info(f"Final URL with signature: {url}")
            
            logger.debug(f"Sending signed request to {url}")
            logger.debug(f"With headers: {headers}")
            
            # For signed requests, we'll pass empty params since they're in the URL
            params = {}
        
        try:
            async with httpx.AsyncClient() as client:
                # Different handling based on HTTP method
                if method.upper() == 'GET':
                    if signed:
                        # For signed requests, we've already included params in the URL
                        response = await client.get(url, headers=headers)
                    else:
                        # For non-signed requests, params go in the URL query string
                        response = await client.get(url, params=params, headers=headers)
                elif method.upper() == 'POST':
                    if signed:
                        # For signed requests, use the URL with signature
                        response = await client.post(url, headers=headers)
                    else:
                        # For POST requests with MEXC API, we need to decide whether to send 
                        # the data as form data or JSON based on the endpoint
                        
                        # Check Content-Type, as MEXC may expect form data for some endpoints
                        if 'Content-Type' in headers and headers['Content-Type'] == 'application/json':
                            # Send as JSON in request body
                            response = await client.post(url, json=params, headers=headers)
                        else:
                            # Send as form data in URL params (this is what MEXC expects for most endpoints)
                            response = await client.post(url, params=params, headers=headers)
                elif method.upper() == 'DELETE':
                    if signed:
                        response = await client.delete(url, headers=headers)
                    else:
                        response = await client.delete(url, params=params, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Log the full request for debugging
                logger.debug(f"Sent {method} request to: {response.request.url}")
                logger.debug(f"With headers: {headers}")
                
                # Check if the request was successful
                try:
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error occurred: {e.response.text}")
                    raise
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error making request to MEXC API: {e}")
            raise
    
    async def get_account_info(self):
        """Get account information."""
        # This endpoint requires authentication
        logger.debug("Getting account info...")
        try:
            result = await self._http_request('GET', self.ACCOUNT_ENDPOINT, signed=True)
            return result
        except Exception as e:
            logger.error(f"Failed to get account info: {str(e)}")
            return None
    
    async def get_exchange_info(self):
        """Get exchange information including trading pairs and rules."""
        return await self._http_request('GET', self.EXCHANGE_INFO_ENDPOINT)
    
    async def get_ticker_price(self, symbol=None):
        """Get latest price for a specific symbol or all symbols."""
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()
        
        try:
            result = await self._http_request('GET', self.TICKER_PRICE_ENDPOINT, params)
            return result
        except Exception as e:
            logger.error(f"Failed to get ticker price for {symbol}: {str(e)}")
            return None
            
    async def get_multiple_ticker_prices(self, symbols):
        """Get latest prices for multiple symbols."""
        if not symbols:
            return []
            
        try:
            # Get all ticker prices
            all_tickers = await self.get_ticker_price()
            if not all_tickers:
                return []
                
            # Filter for the requested symbols
            symbols_upper = [s.upper() for s in symbols]
            filtered_tickers = [t for t in all_tickers if t.get('symbol') in symbols_upper]
            
            return filtered_tickers
        except Exception as e:
            logger.error(f"Failed to get multiple ticker prices: {str(e)}")
            return []
    
    async def get_order_book(self, symbol, limit=100):
        """Get order book for a specific symbol."""
        params = {'symbol': symbol, 'limit': limit}
        return await self._http_request('GET', self.DEPTH_ENDPOINT, params)
    
    async def create_market_buy_order(self, symbol, quantity):
        """Create a market buy order."""
        # For MEXC API, market buy orders typically use quoteOrderQty (USDT amount)
        # rather than quantity (asset amount) for market buys
        
        # MEXC requires minimum transaction amount of 1 USDT
        min_transaction = 1.0
        
        # Convert to float and ensure minimum amount
        quantity = float(quantity)
        if quantity < min_transaction:
            logger.warning(f"Order amount {quantity} USDT is below minimum requirement of {min_transaction} USDT. Adjusting to {min_transaction} USDT.")
            quantity = min_transaction
        
        # Format the amount with proper precision to avoid floating point issues
        quantity = round(quantity, 4)
        
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': quantity,  # This is USDT amount for market buy
        }
        logger.info(f"Creating market buy order: {symbol}, amount: {quantity} USDT")
        
        # Make sure symbol is in uppercase
        params['symbol'] = params['symbol'].upper()
        
        try:
            result = await self._http_request('POST', self.ORDER_ENDPOINT, params, signed=True)
            logger.info(f"Market buy order created: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to create market buy order: {str(e)}")
            raise
    
    async def create_market_sell_order(self, symbol, quantity):
        """Create a market sell order."""
        params = {
            'symbol': symbol.upper(),
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': quantity,  # For sell orders, this is the quantity of the base asset
        }
        logger.info(f"Creating market sell order: {symbol}, quantity: {quantity}")
        
        try:
            result = await self._http_request('POST', self.ORDER_ENDPOINT, params, signed=True)
            logger.info(f"Market sell order created: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to create market sell order: {str(e)}")
            raise
    
    async def get_order_status(self, symbol, order_id):
        """Check the status of an order."""
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }
        try:
            logger.info(f"Checking status of order {order_id} for symbol {symbol}")
            result = await self._http_request('GET', self.ORDER_ENDPOINT, params, signed=True)
            return result
        except Exception as e:
            logger.error(f"Failed to get order status for order {order_id}: {str(e)}")
            return None
    
    async def cancel_order(self, symbol, order_id):
        """Cancel an order."""
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }
        try:
            logger.info(f"Cancelling order {order_id} for symbol {symbol}")
            result = await self._http_request('DELETE', self.ORDER_ENDPOINT, params, signed=True)
            logger.info(f"Order cancelled: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {str(e)}")
            return None
    
    async def get_open_orders(self, symbol=None):
        """Get all open orders for a symbol or all symbols."""
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()
            
        try:
            logger.info(f"Getting open orders for {symbol if symbol else 'all symbols'}")
            result = await self._http_request('GET', self.OPEN_ORDERS_ENDPOINT, params, signed=True)
            return result
        except Exception as e:
            logger.error(f"Failed to get open orders: {str(e)}")
            return []
    
    async def connect_websocket(self, callback):
        """Connect to MEXC WebSocket and set up a listener."""
        logger.info("Connecting to MEXC WebSocket...")
        self.ws = await ws_connect(self.ws_url)
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
        except ConnectionClosed:
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
