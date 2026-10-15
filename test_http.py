"""Test sul trasporto StreamableHTTP reale (server in un processo separato, client via HTTP).

Prerequisito: eseguire prima `python test_e2e.py`, che crea database e cartelle di esempio in _test/.
Uso:  python test_http.py            (server stateful)
      python test_http.py stateless  (server con stateless_http=True)
"""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CreateMessageResult, ListRootsResult, Root, TextContent

STATELESS = len(sys.argv) > 1 and sys.argv[1] == "stateless"
BASE = Path(__file__).parent.resolve() / "_test"
ROOT = BASE / "SIC"
PORT = "8765"

env = dict(os.environ,
           CMMS_DB_URL=f"sqlite:///{BASE / 'cmms.db'}",
           MATRICOLA_REPORT_DIR=str(ROOT / "Report"),
           MATRICOLA_AUDIT_LOG=str(BASE / "audit_http.jsonl"),
           MATRICOLA_ROOTS=str(ROOT),
           MATRICOLA_TRANSPORT="streamable-http",
           MATRICOLA_PORT=PORT)
if STATELESS:
    env["MATRICOLA_STATELESS"] = "1"
proc = subprocess.Popen([sys.executable, "server.py"], cwd=Path(__file__).parent, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

sampled, log, prog = [], [], []


async def sampling_cb(ctx, params):
    sampled.append(1)
    return CreateMessageResult(role="assistant", model="test",
                               content=TextContent(type="text", text="Estratto dell'avviso"))


async def roots_cb(ctx):
    return ListRootsResult(roots=[Root(uri=f"file://{ROOT}", name="SIC")])


async def log_cb(p):
    log.append(p.data)


async def prog_cb(p, total, msg):
    prog.append(p)


async def main():
    async with streamablehttp_client(f"http://127.0.0.1:{PORT}/mcp") as (read, write, get_session_id):
        async with ClientSession(read, write, sampling_callback=sampling_cb,
                                 list_roots_callback=roots_cb, logging_callback=log_cb) as s:
            await s.initialize()
            print("mcp-session-id:", get_session_id() or "nessuno")
            r = await s.call_tool("scadenze", {"entro_giorni": 30})
            print("richiesta -> risultato:", "OK" if not r.isError else "ERRORE")
            r = await s.call_tool("riassumi_avviso",
                                  {"percorso": str(ROOT / "Avvisi_FSN" / "FSN_Aerion_VX500.txt")})
            via = "sampling dal client" if sampled else "fallback senza sampling"
            print("riassumi_avviso:", "OK" if not r.isError else "ERRORE", f"({via})")
            r = await s.call_tool("report_conformita", {"anno": time.localtime().tm_year},
                                  progress_callback=prog_cb)
            await asyncio.sleep(0.5)
            print("report_conformita:", "OK" if not r.isError else "ERRORE",
                  f"| log ricevuti: {len(log)} | progress ricevuti: {len(prog)}")


try:
    asyncio.run(main())
finally:
    proc.terminate()
