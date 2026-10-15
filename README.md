# Matricola

**Progettazione e verifica di un server Model Context Protocol per il Servizio di Ingegneria Clinica**

Luigi Loperfido · ottobre 2026

> **Nota.** Questo repository contiene un caso di studio. La struttura sanitaria, le apparecchiature e i dati sono fittizi. Il software è stato sviluppato e verificato su dati di prova e non è in uso presso alcuna struttura sanitaria.

*English summary.* Matricola is a case study of a Model Context Protocol (MCP) server for a hospital's Clinical Engineering department. It gives an AI assistant controlled, read-only access to the medical equipment inventory, the maintenance and electrical safety inspection schedule, and manufacturers' field safety notices. The repository includes the server, automated tests, and an experiment on how MCP behaves over HTTP. Documentation is in Italian.

## Indice

1. [Contesto](#1-contesto)
2. [Funzioni](#2-funzioni)
3. [Architettura e principi di progetto](#3-architettura-e-principi-di-progetto)
4. [Installazione](#4-installazione)
5. [Configurazione](#5-configurazione)
6. [Uso con Claude Desktop](#6-uso-con-claude-desktop)
7. [Verifica](#7-verifica)
8. [Struttura del repository](#8-struttura-del-repository)
9. [Limiti](#9-limiti)
10. [Riferimenti e licenza](#10-riferimenti-e-licenza)

## 1. Contesto

Il Servizio di Ingegneria Clinica (SIC) di un ospedale gestisce la manutenzione e la sicurezza delle apparecchiature elettromedicali. Quando un fabbricante emette un avviso di sicurezza (*Field Safety Notice*, FSN) su un modello, il servizio deve individuare rapidamente gli apparecchi coinvolti confrontando il documento del fabbricante con l'inventario. Si tratta di un'attività manuale, lenta e soggetta a un errore particolarmente grave: un apparecchio coinvolto che non viene individuato.

Matricola è un server basato su [Model Context Protocol](https://modelcontextprotocol.io) (MCP), lo standard aperto che consente a un assistente di intelligenza artificiale di accedere in modo controllato a dati e strumenti esterni. Il server permette all'ingegnere clinico di interrogare in linguaggio naturale l'inventario, lo scadenziario delle manutenzioni e gli avvisi di sicurezza. L'accesso ai dati è in sola lettura e ogni decisione resta in capo al personale del servizio.

Il progetto applica i contenuti del corso *Model Context Protocol: Advanced Topics* (Claude Academy, Anthropic).

## 2. Funzioni

| Funzione | Descrizione | Tipo |
|---|---|---|
| `cerca_apparecchi` | Ricerca nell'inventario per matricola, tipo, modello, fabbricante o reparto | Lettura |
| `scadenze` | Manutenzioni preventive (MP), verifiche di sicurezza elettrica (VSE, CEI EN 62353) e controlli funzionali (CF) scaduti o in scadenza | Lettura |
| `apparecchi_coinvolti` | Confronto tra i numeri di serie di un avviso e l'inventario, con normalizzazione della scrittura | Lettura |
| `riassumi_avviso` | Estrazione dei dati operativi da un avviso di sicurezza, con citazione delle frasi di origine; il risultato è sempre una bozza | Lettura, testo generato tramite *sampling* |
| `report_conformita` | Attività eseguite in tempo, in ritardo o non eseguite, per reparto; salva un file CSV | Lettura, con notifiche di avanzamento |
| `apri_ordine_lavoro` | Creazione di un ordine di lavoro in stato di bozza, previa conferma | Unica scrittura |
| `list_roots` | Elenco delle cartelle consultabili | Lettura |
| `read_dir` | Contenuto di una cartella consentita | Lettura |

## 3. Architettura e principi di progetto

Il server è scritto in Python con la libreria ufficiale MCP (`FastMCP`). Lo stesso codice funziona in due modalità di collegamento (*trasporti*):

- **STDIO**: il server viene avviato dall'applicazione sulla stessa postazione (prima fase);
- **StreamableHTTP**: il server è raggiungibile sulla rete interna da più postazioni (seconda fase).

Principi adottati:

1. **L'AI propone, la persona decide.** I testi generati sono marcati come bozza; l'unica scrittura è un ordine di lavoro in bozza, approvato da un tecnico nel CMMS.
2. **Sola lettura.** Il server legge da una copia del database con un'utenza separata da quella di scrittura.
3. **Nessun dato di pazienti.** Il sistema tratta solo dati tecnici e gestionali.
4. **Tracciabilità.** Ogni richiesta viene registrata in un file a sola aggiunta; ogni risposta riporta fonte e istante di lettura.
5. **Nessun collegamento a Internet dal server.** Quando serve il modello AI, il server lo richiede all'applicazione tramite *sampling*.
6. **Accesso ai file limitato.** Il server apre soltanto file contenuti nelle cartelle autorizzate (*roots*); in loro assenza, nessun file è accessibile.
7. **Funzionamento garantito.** Le richieste dal server all'applicazione hanno un tempo massimo; se non vanno a buon fine, il server adotta una soluzione di riserva.

Il documento di progetto completo, con architettura, scelte tecniche, rischi e un simulatore dei messaggi, è disponibile in [`docs/documento-di-progetto.html`](docs/documento-di-progetto.html).

## 4. Installazione

Requisiti: Python 3.10 o successivo e, consigliato, [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Luislop-eng/Matricola.mcp.git
cd Matricola.mcp
uv sync                      # oppure: pip install -r requirements.txt
```

La libreria MCP è fissata alla versione 1.x: nella versione 2 la classe `FastMCP` è stata rinominata `MCPServer`.

## 5. Configurazione

Il server si configura con variabili d'ambiente.

| Variabile | Obbligatoria | Descrizione |
|---|---|---|
| `CMMS_DB_URL` | Sì | Indirizzo del database in lettura, in formato SQLAlchemy (es. `sqlite:///cmms.db`, `postgresql+psycopg://...`) |
| `CMMS_WRITE_URL` | No | Database per la scrittura degli ordini in bozza; se assente si usa `CMMS_DB_URL` |
| `MATRICOLA_ROOTS` | No | Cartelle consentite da usare se l'applicazione non le fornisce (separate da `:`) |
| `MATRICOLA_REPORT_DIR` | No | Cartella di destinazione dei report (predefinita: `Report`) |
| `MATRICOLA_AUDIT_LOG` | No | File del registro delle richieste (predefinito: `audit.jsonl`) |
| `MATRICOLA_TRANSPORT` | No | `stdio` (predefinito) oppure `streamable-http` |
| `MATRICOLA_HOST`, `MATRICOLA_PORT` | No | Indirizzo e porta in modalità HTTP (predefiniti: `127.0.0.1`, `8000`) |
| `MATRICOLA_STATELESS` | No | `1` per la modalità HTTP senza sessione |
| `MATRICOLA_JSON_RESPONSE` | No | `1` per risposte HTTP in formato JSON unico, senza streaming |
| `MATRICOLA_TIMEOUT_CLIENT` | No | Secondi di attesa per le richieste verso l'applicazione (predefinito: `60`) |

Lo schema minimo del database è descritto in [`docs/schema.sql`](docs/schema.sql).

## 6. Uso con Claude Desktop

Aggiungere il server al file di configurazione di Claude Desktop, adattando i percorsi. Un esempio è disponibile in [`docs/claude_desktop_config.example.json`](docs/claude_desktop_config.example.json).

Esempi di richieste:

- «Quali verifiche di sicurezza elettrica scadono in Terapia Intensiva nei prossimi 30 giorni?»
- «Leggi l'avviso sui ventilatori VX-500 nella cartella degli avvisi e riassumi le azioni richieste.»
- «Quali dei nostri ventilatori VX-500 sono coinvolti dall'avviso?»

## 7. Verifica

### 7.1 Test automatici

```bash
uv run test_e2e.py              # configurazione con sessione
uv run test_e2e.py stateless    # configurazione senza sessione
uv run test_http.py             # server avviato in HTTP (eseguire prima test_e2e.py)
uv run test_http.py stateless
```

`test_e2e.py` crea un database SQLite con dati fittizi e collega il server a un client MCP completo (con gestione di *sampling*, *roots*, log e avanzamento). Risultati ottenuti con Python 3.13 e `mcp` 1.30.0:

| Configurazione | Test superati |
|---|---|
| Con sessione | 21 / 21 |
| Senza sessione (soluzioni di riserva) | 19 / 19 |

I test coprono, tra l'altro: numeri di serie e nomi di modello scritti in modi diversi; un avviso contenente un'istruzione nascosta; il blocco di accessi a file esterni alle cartelle consentite; il calcolo del report; il comportamento con un client che non supporta *sampling* e *roots*; la registrazione di ogni richiesta.

### 7.2 Errore individuato durante lo sviluppo

Nella prima versione il nome del modello veniva confrontato carattere per carattere: un avviso che indicava «VX500» non individuava gli apparecchi registrati come «VX-500», senza alcuna segnalazione. L'errore è stato corretto uniformando la scrittura di fabbricante, modello e numero di serie e segnalando esplicitamente i casi in cui il modello non viene trovato.

### 7.3 Esperimento sui trasporti

`esperimento_trasporti.py` avvia un server minimo in tre configurazioni HTTP e registra quali messaggi raggiungono il client.

```bash
uv run esperimento_trasporti.py
```

| Configurazione | Richieste dal server al client (*sampling*, *roots*) | Notifiche di log e avanzamento |
|---|---|---|
| Con sessione | Funzionano | Ricevute |
| `stateless_http=True` | Non funzionano: restano in attesa fino al timeout | Ricevute |
| `stateless_http=True`, `json_response=True` | Non funzionano: restano in attesa fino al timeout | Perse |

Con la libreria utilizzata, la perdita delle notifiche dipende dall'opzione `json_response` più che dalla modalità senza sessione. Le richieste non disponibili non producono un errore immediato: per questo il server prevede un tempo massimo e una soluzione di riserva.

## 8. Struttura del repository

```
Matricola.mcp/
├── server.py                    server MCP
├── test_e2e.py                  test end-to-end in memoria
├── test_http.py                 test sul trasporto HTTP
├── esperimento_trasporti.py     esperimento sulle configurazioni HTTP
├── docs/
│   ├── documento-di-progetto.html
│   ├── schema.sql
│   └── claude_desktop_config.example.json
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

## 9. Limiti

- Il sistema è stato verificato solo con dati fittizi su SQLite; il collegamento a un database di produzione non è stato provato.
- La qualità dell'estrazione dagli avvisi non è stata misurata su documenti reali.
- L'inquadramento normativo (Regolamento (UE) 2017/745, AI Act, GDPR) descritto nel documento di progetto è un'ipotesi da validare con il referente regolatorio della struttura.

## 10. Riferimenti e licenza

- Anthropic, Claude Academy: [*Model Context Protocol: Advanced Topics*](https://academy.claude.com/courses/model-context-protocol-advanced-topics)
- [Specifica di Model Context Protocol](https://modelcontextprotocol.io)
- CEI EN 62353, *Apparecchi elettromedicali — Verifiche periodiche e prove da eseguire dopo interventi di riparazione*

Distribuito con licenza MIT (vedi [`LICENSE`](LICENSE)).
