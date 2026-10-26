-- Linaje documental del corpus sintético de clase.
-- Puede ejecutarse después de db/init.sql.

CREATE TABLE IF NOT EXISTS document_registry (
  document_code text NOT NULL,
  version text NOT NULL,
  title text NOT NULL,
  owner_name text NOT NULL,
  approver_name text NOT NULL,
  source_repository text NOT NULL,
  published_on date NOT NULL,
  valid_from date NOT NULL,
  valid_until date,
  status text NOT NULL,
  access_role text NOT NULL,
  content_sha256 text NOT NULL,
  PRIMARY KEY (document_code, version)
);

CREATE TABLE IF NOT EXISTS document_chunks (
  chunk_id text PRIMARY KEY,
  document_code text NOT NULL,
  document_version text NOT NULL,
  section_code text NOT NULL,
  section_title text NOT NULL,
  extraction_method text NOT NULL DEFAULT 'structured_text',
  embedding_model text NOT NULL DEFAULT 'semantic-demo-4d-v1',
  indexed_at timestamptz NOT NULL DEFAULT now(),
  active boolean NOT NULL DEFAULT true,
  FOREIGN KEY (document_code, document_version)
    REFERENCES document_registry(document_code, version)
);

-- Los hashes exactos se encuentran en 05_Corpus_Documental/lineage_manifest.json.
-- Este script demuestra el esquema; build_corpus.py genera el manifiesto verificable.
