import aiohttp
import asyncio
import json
import string
import secrets
import time
import enum
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, PKCS1_v1_5, AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import unpad, pad
from base64 import b64encode, b64decode

def _pad_string(value):
    length = len(value)
    pad_size = AES.block_size - (length % AES.block_size)
    return value.ljust(length + pad_size, b'\x00')

async def setup_secure_connection(ip_address, authkey):
    async def __receive(ws):
        msg = await ws.receive()
        msg = msg.data[:-1]
        print(f"Received raw: {msg}")
        return json.loads(msg)

    async def __send(ws, data):
        msg = json.dumps(data) 
        print(f"Send raw: {msg}")
        await ws.send_str(msg)

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://{ip_address}/") as ws:
            try:
                msg = await __receive(ws)
                deviceId = msg['payload']['device_id']
                connectionId = msg['payload']['connection_id']
                
                await __send(ws, {
                    "type_int":11,
                    "mc":-1,
                    "payload":{
                        "client_type":"shl-app",
                        "client_id":"c956e43f999f8004",
                        "client_version":"1.1.0",
                        "connection_id":connectionId
                        }
                    })

                msg = await __receive(ws)
                await __send(ws, {"type_int":14,"mc":-1})

                msg = await __receive(ws)
                publicKey = msg['payload']['public_key']

                rsa = RSA.import_key(publicKey)

                key = get_random_bytes(32)
                iv = get_random_bytes(16)

                cipher = PKCS1_v1_5.new(rsa)
                secret = b64encode(cipher.encrypt((key.hex() + ":::" + iv.hex()).encode()))
                print(f"secret: {secret}")
                secret = secret.decode()
                print(f"secret: {secret}")

                await __send(ws, {"type_int":16,"mc":-1,"payload":{"secret": secret}})

                connection = SecureBridgeConnection(ws, key, iv)

                msg = await connection.receive()

                if msg['type_int'] != 17:
                    raise Exception('Failed to establish secure connection')

                return connection
            except:
                await ws.close()
                raise

class SecureBridgeConnection:
    def __init__(self, websocket, key, iv):
        self.websocket = websocket
        self.key = key
        self.iv = iv

    def __cipher(self):
        return AES.new(self.key, AES.MODE_CBC, self.iv)

    async def close(self):
        await self.websocket.close()
    
    async def receive(self):
        msg = await self.websocket.receive()
        msg = msg.data
        ct = b64decode(msg)
        msg = self.__cipher().decrypt(ct)
        msg = msg.rstrip(b'\x00')
        print(f"Received decrypted: {msg}")

        if not msg:
            return {}

        return json.loads(msg.decode())

    async def send(self, data):
        msg = json.dumps(data) 
        print(f"Send raw: {msg}")
        msg = _pad_string(msg.encode())
        msg = self.__cipher().encrypt(msg)
        msg = b64encode(msg).decode() + '\u0004'
        await self.websocket.send_str(msg)

class Bridge:
    def __init__(self, ip_address:str, authkey:str):
        self.ip_address = ip_address
        self.authkey = authkey
        self.connection = None

    @staticmethod
    async def connect(ip_address:str, authkey:str):
        bc = Bridge(ip_address, authkey)
        await bc.__connect()
        return bc

    async def __connect(self):
        self.connection = await setup_secure_connection(self.ip_address, self.authkey)

    async def close(self):
        if isinstance(self.connection, SecureBridgeConnection):
            await self.connection.close()
