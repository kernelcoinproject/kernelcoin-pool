# Update ip/user/pass for local rpc
#!/usr/bin/env python3
import aiohttp
import asyncio
import json
from aiohttp import web

RPC_URL = "http://127.0.0.1:9332"
RPC_AUTH = aiohttp.BasicAuth("mike", "x")

async def forward_rpc(payload):
    async with aiohttp.ClientSession(auth=RPC_AUTH) as session:
        async with session.post(RPC_URL, json=payload) as resp:
            return await resp.text()

def patch_call(call):
    if not isinstance(call, dict):
        return call

    if call.get("method") == "getblocktemplate":
        # Miningcore sends params as:
        # [ { "capabilities": [...], "rules": [...], ... } ]
        if call.get("params") and isinstance(call["params"], list) and len(call["params"]) > 0:
            p = call["params"][0]

            if isinstance(p, dict):
                # Only replace the rules key
                p["rules"] = ["segwit", "mweb"]

    return call

async def handle(request):
    try:
        body = await request.text()
        data = json.loads(body)

        # Batch vs single
        if isinstance(data, list):
            patched = [patch_call(call) for call in data]
        else:
            patched = patch_call(data)

        response_text = await forward_rpc(patched)
        return web.Response(text=response_text, content_type="application/json")

    except Exception as e:
        print(str(e))
        err = {"error": "internal proxy error"}
        return web.Response(text=json.dumps(err), content_type="application/json", status=500)

app = web.Application()
app.router.add_post("/", handle)

web.run_app(app, port=9333)
