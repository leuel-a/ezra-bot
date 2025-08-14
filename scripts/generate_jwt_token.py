#!/usr/bin/env python3
import time
import jwt
import json


PRIVATE_KEY_PATH = "ezra-agent.pem"
CLIENT_ID = "Iv23liVKpKQ8DnJzfy8y" 
APP_ID = 1776125

with open(PRIVATE_KEY_PATH, "rb") as pem_file:
    signing_key = pem_file.read()

payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "iss": CLIENT_ID 
    }

encoded_jwt = jwt.encode(payload, signing_key, algorithm="RS256")
ENCODED_JWT_FILE = "jwt_encoded.json"


with open(ENCODED_JWT_FILE, "w+") as encode_file:
    encode_file.write(json.dumps({ "access_token": encoded_jwt }))
