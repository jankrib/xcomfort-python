import aiohttp
import asyncio
import json
import string
import secrets
import time
import rx
from enum import Enum
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, PKCS1_v1_5, AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import unpad, pad
from base64 import b64encode, b64decode
import rx.operators as ops

class ConnectionState(Enum):
    Initial = 1
    Loading = 2
    Loaded = 3

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

async def setup_secure_connection(session, ip_address, authkey):
    async def __receive(ws):
        msg = await ws.receive()
        msg = msg.data[:-1]
        # print(f"Received raw: {msg}")
        return json.loads(msg)

    async def __send(ws, data):
        msg = json.dumps(data) 
        # print(f"Send raw: {msg}")
        await ws.send_str(msg)

    ws = await session.ws_connect(f"http://{ip_address}/")

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
                "client_version":"2.0.0",
                "connection_id":connectionId
                }
            })

        msg = await __receive(ws)

        if msg['type_int'] == 13:
            raise Exception(msg["payload"]["error_message"])

        await __send(ws, {"type_int":14,"mc":-1})

        msg = await __receive(ws)
        publicKey = msg['payload']['public_key']

        rsa = RSA.import_key(publicKey)

        key = get_random_bytes(32)
        iv = get_random_bytes(16)

        cipher = PKCS1_v1_5.new(rsa)
        secret = b64encode(cipher.encrypt((key.hex() + ":::" + iv.hex()).encode()))
        # print(f"secret: {secret}")
        secret = secret.decode()
        # print(f"secret: {secret}")

        await __send(ws, {"type_int":16,"mc":-1,"payload":{"secret": secret}})

        connection = SecureBridgeConnection(ws, key, iv, deviceId)

        # Start LOGIN

        msg = await connection.receive()
        
        if msg['type_int'] != 17:
            raise Exception('Failed to establish secure connection')

        salt = generateSalt()
        password = hash(deviceId.encode(), authkey.encode(), salt.encode())

        await connection.send_message(30, {
            "username":"default",
            "password":password,
            "salt": salt
        })
        
        msg = await connection.receive()

        if msg['type_int'] != 32:
            raise Exception("Login failed")

        token = msg['payload']['token']
        await connection.send_message(33,{"token":token})

        msg = await connection.receive()# {"type_int":34,"mc":-1,"payload":{"valid":true,"remaining":8640000}}

        # Renew token
        await connection.send_message(37,{"token":token})

        msg = await connection.receive()

        if msg['type_int'] != 38:
            raise Exception("Login failed")

        token = msg['payload']['token']

        await connection.send_message(33,{"token":token})

        msg = await connection.receive()# {"type_int":34,"mc":-1,"payload":{"valid":true,"remaining":8640000}}

        return connection
    except:
        await ws.close()
        raise

class SecureBridgeConnection:
    def __init__(self, websocket, key, iv, device_id):
        self.websocket = websocket
        self.key = key
        self.iv = iv
        self.device_id = device_id

        self.state = ConnectionState.Initial
        self._messageSubject = rx.subject.Subject()
        self.mc = 0

        self.messages = self._messageSubject.pipe(
            ops.as_observable()
        )

    def __cipher(self):
        return AES.new(self.key, AES.MODE_CBC, self.iv)

    def __decrypt(self, data):
        ct = b64decode(data)
        data = self.__cipher().decrypt(ct)
        data = data.rstrip(b'\x00')
        # print(f"Received decrypted: {data}")

        if not data:
            return {}

        return json.loads(data.decode())

    async def pump(self):
        self.state = ConnectionState.Loading

        await self.send_message(240, {})
        await self.send_message(242, {})
        await self.send_message(2, {})

        async for msg in self.websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                result = self.__decrypt(msg.data)

                if 'mc' in result:
                    await self.send({"type_int":1,"ref":result['mc']}) #ACK
                
                if 'payload' in result:
                    self._messageSubject.on_next(result)

            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
    
    async def close(self):
        await self.websocket.close()

    async def receive(self):
        msg = await self.websocket.receive()

        return self.__decrypt(msg.data)
    
    async def send_message(self, message_type, payload):
        self.mc += 1

        if isinstance(message_type, Messages):
            message_type = message_type.value

        await self.send({"type_int":message_type,"mc":self.mc,"payload":payload})

    async def send(self, data):
        msg = json.dumps(data) 
        # print(f"Send raw: {msg}")
        msg = _pad_string(msg.encode())
        msg = self.__cipher().encrypt(msg)
        msg = b64encode(msg).decode() + '\u0004'
        await self.websocket.send_str(msg)

    
class Messages(Enum):    
    NACK = 0
    ACK = 1
    HEARTBEAT = 2
    CONNECTION_START = 10
    CONNECTION_CONFIRM = 11
    CONNECTION_ESTABLISHED = 12
    CONNECTION_DECLINED = 13
    SC_INIT = 14
    SC_PUBKEY = 15
    SC_SECRET = 16
    SC_ESTABLISHED = 17
    SC_INVALID = 18
    AUTH_LOGIN = 30
    AUTH_LOGIN_DENIED = 31
    AUTH_LOGIN_SUCCESS = 32
    AUTH_APPLY_TOKEN = 33
    AUTH_APPLY_TOKEN_RESPONSE = 34
    AUTH_VERIFY_TOKEN = 35
    AUTH_VERIFY_TOKEN_RESPONSE = 36
    AUTH_RENEW_TOKEN = 37
    AUTH_RENEW_TOKEN_RESPONSE = 38
    AUTH_KILL_TOKEN = 39
    TEST_ON = 100
    TEST_OFF = 101
    TEST_CRYPTO = 102
    TEST_ALERT = 104
    TEST_DEVICE_STATE = 105
    TEST_COMMAND = 120
    INITIAL_DATA = 240
    HOME_DATA = 242
    DIAGNOSTICS = 243
    INIT_SWUPDATE = 247
    DATA_SWUPDATE = 248
    START_SWUPDATE = 249
    UPDATE_BRIDGE = 250
    START_LEARNMODE = 251
    STOP_LEARNMODE = 252
    BARCODE_DEVICE = 253
    UPDATE_DEVICE = 254
    DELETE_DEVICE = 255
    ARRANGE_DEVICES = 256
    SET_ROOM = 257
    DELETE_ROOM = 259
    ARRANGE_ROOMS = 260
    SET_SCENE = 261
    DELETE_SCENE = 263
    ARRANGE_SCENES = 264
    EDIT_RF_PWD = 270
    SET_TIME = 271
    SET_ASTRO = 272
    SET_TIMER = 273
    DELETE_TIMER = 274
    ACTION_SLIDE_DEVICE = 280
    ACTION_SWITCH_DEVICE = 281
    ACTION_SLIDE_ROOM = 283
    ACTION_SWITCH_ROOM = 284
    ACTIVATE_SCENE = 285
    ADD_DEVICE = 290
    SET_DEVICE_STATE = 291
    SET_DEVICE_INFO = 292
    SET_ROOM_STATE = 293
    SET_ROOM_INFO = 294
    APP_INFO = 295
    DEVICE_DELETED = 296
    ROOM_DELETED = 297
    SCENE_DELETED = 298
    SET_ALL_DATA = 300
    SET_ROOM_ID = 301
    SET_SCENE_ID = 302
    SET_HOME_DATA = 303
    SET_DIAGNOSTICS = 304
    SET_TIMER_ID = 305
    FOUND_COMP = 306
    ADD_COMP = 307
    SET_COMP_INFO = 308
    COMP_DELETED = 309
    SET_STATE_INFO = 310
    CONFIG_SAVED = 311
    CONFIG_LIST = 312
    RESTORE_CONFIG_RESPONSE = 313
    SET_HEATING_PROGRAM = 350
    DELETE_HEATING_PROGRAM = 351
    SET_ROOM_HEATING = 352
    SET_HEATING_STATE = 353
    SET_HEATING_PROGRAM_ID = 360
    HEATING_PROGRAM_DELETED = 362
    SET_ROOM_HEATING_STATE = 363
    SET_BRIDGE_STATE = 364
    IDLE = -1
    NACK_INFO_INVALID_ACTION = -98
    NACK_INFO_DEVICE_NOT_DIMMABLE = -99
    NACK_INFO_UNKNOWN_DEVICE = -100
    