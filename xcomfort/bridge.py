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

def generateSalt():
    alphabet = string.ascii_letters + string.digits
    return  ''.join(secrets.choice(alphabet) for i in range(12))

def hash(deviceId, authKey, salt):
    hasher = SHA256.new()
    hasher.update(deviceId)
    hasher.update(authKey)
    inner = hasher.hexdigest().encode()
    hasher = SHA256.new()
    hasher.update(salt)
    hasher.update(inner)

    return hasher.hexdigest()

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

                salt = generateSalt()
                password = hash(deviceId.encode(), authkey.encode(), salt.encode())

                await connection.send({
                    "type_int":30,
                    "mc":1,
                    "payload":{
                        "username":"default",
                        "password":password,
                        "salt": salt
                        }
                    })
                
                msg = await connection.receive()

                if msg['type_int'] != 32:
                    raise Exception("Login failed")

                token = msg['payload']['token']
                await connection.send({"type_int":33,"mc":2,"payload":{"token":token}})

                msg = await connection.receive()# {"type_int":34,"mc":-1,"payload":{"valid":true,"remaining":8640000}}

                await connection.send({"type_int":240,"mc":4,"payload":{}})

                msg = await connection.receive()

                if 'mc' in msg:
                    await connection.send({"type_int":1,"ref":msg['mc']}) #ACK

                #connection.start()

                return connection
            except:
                await ws.close()
                raise

class SecureBridgeConnection:
    def __init__(self, websocket, key, iv):
        self.websocket = websocket
        self.key = key
        self.iv = iv

    def start(self):
        self.task = asyncio.create_task(self.__pump())

    def __cipher(self):
        return AES.new(self.key, AES.MODE_CBC, self.iv)

    def __decrypt(self, data):
        ct = b64decode(data)
        data = self.__cipher().decrypt(ct)
        data = data.rstrip(b'\x00')
        print(f"Received decrypted: {data}")

        if not data:
            return {}

        return json.loads(data.decode())

    async def __pump(self):
        print('pump')
        async for msg in self.websocket:
            print('receive')
            if msg.type == aiohttp.WSMsgType.TEXT:
                result = self.__decrypt(msg.data)

                if 'mc' in result:
                    self.send({"type_int":1,"ref":result['mc']}) #ACK
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
    
    async def close(self):
        await self.websocket.close()

    async def receive(self):
        msg = await self.websocket.receive()

        return self.__decrypt(msg.data)

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
