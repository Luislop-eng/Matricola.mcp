"""Esperimento: cosa funziona davvero con StreamableHTTP nelle tre configurazioni?

Un server minimo con uno strumento che usa log, progress, roots e sampling, avviato con:
  A) stateful (default)   B) stateless_http=True   C) stateless_http=True + json_response=True
Per ogni configurazione un client HTTP con tutte le callback registra cosa riceve.
"""
import asyncio
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CreateMessageResult, ListRootsResult, Root, TextContent

SERVER = textwrap.dedent('''
    import sys
    from mcp.server.fastmcp import FastMCP, Context
    from mcp.types import SamplingMessage, TextContent
    stateless, json_resp, port = sys.argv[1] == "1", sys.argv[2] == "1", int(sys.argv[3])
    mcp = FastMCP("esperimento", stateless_http=stateless, json_response=json_resp, port=port)

    @mcp.tool()
    async def prova(ctx: Context) -> dict:
        esito = {}
        await ctx.info("log dal server")
        await ctx.report_progress(50, 100)
        try:
            r = await asyncio.wait_for(ctx.session.list_roots(), 5)
            esito["roots"] = "ok"
        except Exception as e:
            esito["roots"] = f"fallito ({type(e).__name__})"
        try:
            r = await asyncio.wait_for(ctx.session.create_message(
                messages=[SamplingMessage(role="user", content=TextContent(type="text", text="ciao"))],
                max_tokens=10), 5)
            esito["sampling"] = "ok"
        except Exception as e:
            esito["sampling"] = f"fallito ({type(e).__name__})"
        return esito

    import asyncio
    mcp.run(transport="streamable-http")
''')

CONFIG = [("A stateful", "0", "0"), ("B stateless", "1", "0"), ("C stateless + json_response", "1", "1")]


async def prova(porta: int):
    ricevuti = {"log": 0, "progress": 0, "sampling_cb": 0, "roots_cb": 0}

    async def sampling_cb(ctx, params):
        ricevuti["sampling_cb"] += 1
        return CreateMessageResult(role="assistant", model="t", content=TextContent(type="text", text="ok"))

    async def roots_cb(ctx):
        ricevuti["roots_cb"] += 1
        return ListRootsResult(roots=[Root(uri="file:///tmp", name="tmp")])

    async def log_cb(p):
        ricevuti["log"] += 1

    async def prog_cb(p, t, m):
        ricevuti["progress"] += 1

    async with streamablehttp_client(f"http://127.0.0.1:{porta}/mcp") as (read, write, sid):
        async with ClientSession(read, write, sampling_callback=sampling_cb,
                                 list_roots_callback=roots_cb, logging_callback=log_cb) as s:
            await s.initialize()
            r = await s.call_tool("prova", {}, progress_callback=prog_cb)
            await asyncio.sleep(0.3)
            return sid(), r.content[0].text if r.content else r, ricevuti


async def main():
    src = Path(__file__).parent / "_esperimento_server.py"
    src.write_text(SERVER)
    for i, (nome, stateless, json_resp) in enumerate(CONFIG):
        porta = 8770 + i
        proc = subprocess.Popen([sys.executable, str(src), stateless, json_resp, str(porta)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        try:
            sid, esito, ricevuti = await asyncio.wait_for(prova(porta), 30)
            print(f"\n{nome}\n  session id: {'sì' if sid else 'no'}\n  esito strumento: {esito}\n  ricevuti dal client: {ricevuti}")
        except Exception as e:
            print(f"\n{nome}\n  errore: {type(e).__name__}: {e}")
        finally:
            proc.terminate()
    src.unlink()


asyncio.run(main())
