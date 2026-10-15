-- Schema minimo atteso da Matricola (compatibile con SQLite e PostgreSQL).
-- In produzione le tabelle corrispondono a viste sulla replica del CMMS.

CREATE TABLE apparecchi (
    matricola   TEXT PRIMARY KEY,   -- numero d'inventario
    tipo        TEXT NOT NULL,      -- es. "Ventilatore polmonare"
    produttore  TEXT NOT NULL,
    modello     TEXT NOT NULL,
    seriale     TEXT NOT NULL,
    reparto     TEXT NOT NULL,
    classe_mdr  TEXT,               -- I, IIa, IIb, III
    stato       TEXT NOT NULL       -- "in uso", "fuori uso", ...
);

CREATE TABLE manutenzioni (
    matricola   TEXT NOT NULL REFERENCES apparecchi(matricola),
    tipo        TEXT NOT NULL,      -- MP, VSE, CF
    scadenza    DATE NOT NULL,
    eseguita    DATE                -- NULL se non ancora eseguita
);

-- Unica tabella in cui il server scrive (utenza con solo INSERT).
CREATE TABLE ordini_lavoro (
    id          INTEGER PRIMARY KEY,   -- in PostgreSQL: GENERATED ALWAYS AS IDENTITY
    matricola   TEXT NOT NULL REFERENCES apparecchi(matricola),
    tipo        TEXT NOT NULL,         -- correttiva, verifica, fsn
    descrizione TEXT NOT NULL,
    stato       TEXT NOT NULL,         -- sempre "bozza" quando creato dal server
    creato_il   TEXT NOT NULL
);
