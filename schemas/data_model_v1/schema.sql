-- VTLS data model 1.0.0. Offline build; serving database is read-only.
PRAGMA foreign_keys=ON;

CREATE TABLE legal_document (
  law_id TEXT PRIMARY KEY NOT NULL,
  source_id TEXT NOT NULL UNIQUE,
  law_title TEXT NOT NULL,
  document_type TEXT NOT NULL CHECK(document_type IN ('law','decree','circular','regulation')),
  issued_date TEXT NOT NULL,
  document_effective_from TEXT,
  source_url TEXT NOT NULL,
  scope_note TEXT NOT NULL
);

CREATE TABLE source_file (
  file_id TEXT PRIMARY KEY NOT NULL,
  law_id TEXT NOT NULL REFERENCES legal_document(law_id),
  source_set_id TEXT NOT NULL,
  file_role TEXT NOT NULL CHECK(file_role IN ('main','continuation','annex','alternate')),
  part_order INTEGER NOT NULL CHECK(part_order>=1) CHECK(typeof(part_order)='integer'),
  filename TEXT NOT NULL,
  raw_file_ref TEXT NOT NULL,
  download_url TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK(size_bytes>0) CHECK(typeof(size_bytes)='integer'),
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  retrieved_at TEXT NOT NULL,
  UNIQUE(law_id,sha256),
  UNIQUE(law_id,source_set_id,part_order)
);

CREATE TABLE extraction (
  extraction_id TEXT PRIMARY KEY NOT NULL,
  file_id TEXT NOT NULL REFERENCES source_file(file_id),
  method TEXT NOT NULL CHECK(method IN ('pdf_text','html_text','doc_text','ocr')),
  tool_version TEXT NOT NULL,
  text_ref TEXT NOT NULL,
  text_sha256 TEXT NOT NULL CHECK(length(text_sha256)=64),
  char_count INTEGER NOT NULL CHECK(char_count>=0) CHECK(typeof(char_count)='integer'),
  review_status TEXT NOT NULL CHECK(review_status IN ('pending','verified','rejected')),
  created_at TEXT NOT NULL
);

CREATE TABLE legal_unit (
  unit_id TEXT PRIMARY KEY NOT NULL,
  law_id TEXT NOT NULL REFERENCES legal_document(law_id),
  parent_unit_id TEXT,
  unit_type TEXT NOT NULL CHECK(unit_type IN ('document','chapter','section','article','clause','point','annex','table','table_row','figure')),
  designation TEXT NOT NULL,
  canonical_path TEXT NOT NULL,
  citation_path TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK(ordinal>=0) CHECK(typeof(ordinal)='integer'),
  title TEXT NOT NULL,
  text_original TEXT NOT NULL,
  text_sha256 TEXT NOT NULL CHECK(length(text_sha256)=64),
  UNIQUE(unit_id,law_id),
  FOREIGN KEY(parent_unit_id,law_id) REFERENCES legal_unit(unit_id,law_id)
);

CREATE TABLE source_span (
  span_id TEXT PRIMARY KEY NOT NULL,
  unit_id TEXT NOT NULL REFERENCES legal_unit(unit_id),
  extraction_id TEXT NOT NULL REFERENCES extraction(extraction_id),
  field_name TEXT NOT NULL CHECK(field_name IN ('title','text_original')),
  span_order INTEGER NOT NULL CHECK(span_order>=0) CHECK(typeof(span_order)='integer'),
  char_start INTEGER NOT NULL CHECK(char_start>=0) CHECK(typeof(char_start)='integer'),
  char_end INTEGER NOT NULL CHECK(char_end>char_start) CHECK(typeof(char_end)='integer'),
  locator_json TEXT NOT NULL CHECK(json_valid(locator_json)),
  quote_sha256 TEXT NOT NULL CHECK(length(quote_sha256)=64),
  UNIQUE(unit_id,field_name,span_order)
);

CREATE TABLE legal_reference (
  reference_id TEXT PRIMARY KEY NOT NULL,
  from_unit_id TEXT NOT NULL REFERENCES legal_unit(unit_id),
  target_citation TEXT NOT NULL,
  to_unit_id TEXT REFERENCES legal_unit(unit_id),
  resolution_status TEXT NOT NULL CHECK(resolution_status IN ('resolved','external','unresolved')),
  relation_type TEXT NOT NULL
);

CREATE TABLE corpus (
  corpus_version TEXT PRIMARY KEY NOT NULL,
  snapshot_date TEXT NOT NULL CHECK(snapshot_date='2025-01-01'),
  schema_version TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('draft','validated','frozen')),
  built_at TEXT NOT NULL,
  processing_config_ref TEXT NOT NULL,
  manifest_ref TEXT NOT NULL,
  supported_topics_json TEXT NOT NULL CHECK(json_valid(supported_topics_json)),
  exclusions_json TEXT NOT NULL CHECK(json_valid(exclusions_json)),
  coverage_report_ref TEXT NOT NULL
);

CREATE TABLE corpus_document (
  corpus_version TEXT NOT NULL REFERENCES corpus(corpus_version),
  law_id TEXT NOT NULL REFERENCES legal_document(law_id),
  usage_role TEXT NOT NULL CHECK(usage_role IN ('retrieval','supporting')),
  PRIMARY KEY(corpus_version,law_id)
);

CREATE TABLE unit_assessment (
  corpus_version TEXT NOT NULL REFERENCES corpus(corpus_version),
  unit_id TEXT NOT NULL REFERENCES legal_unit(unit_id),
  scope_status TEXT NOT NULL CHECK(scope_status IN ('included','supporting','excluded')),
  applicability_status TEXT NOT NULL CHECK(applicability_status IN ('pending_review','verified_at_snapshot','not_yet_effective','expired_at_snapshot','not_applicable')),
  effective_from TEXT,
  effective_to TEXT,
  verification_ref TEXT,
  verified_at TEXT,
  reviewer_ref TEXT,
  decision_note TEXT NOT NULL,
  PRIMARY KEY(corpus_version,unit_id),
  CHECK(effective_to IS NULL OR effective_from IS NULL OR effective_to>effective_from),
  CHECK(applicability_status!='verified_at_snapshot' OR (effective_from IS NOT NULL AND verification_ref IS NOT NULL AND verified_at IS NOT NULL AND reviewer_ref IS NOT NULL))
);

CREATE TABLE chunk (
  corpus_version TEXT NOT NULL REFERENCES corpus(corpus_version),
  chunk_id TEXT NOT NULL,
  unit_id TEXT NOT NULL REFERENCES legal_unit(unit_id),
  segment_no INTEGER NOT NULL CHECK(segment_no>=1) CHECK(typeof(segment_no)='integer'),
  unit_char_start INTEGER NOT NULL CHECK(unit_char_start>=0) CHECK(typeof(unit_char_start)='integer'),
  unit_char_end INTEGER NOT NULL CHECK(unit_char_end>unit_char_start) CHECK(typeof(unit_char_end)='integer'),
  text_original TEXT NOT NULL CHECK(length(text_original)>0),
  context_text TEXT,
  text_for_search TEXT NOT NULL CHECK(length(text_for_search)>0),
  content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
  chunk_policy_version TEXT NOT NULL,
  PRIMARY KEY(corpus_version,chunk_id),
  UNIQUE(corpus_version,unit_id,segment_no),
  FOREIGN KEY(corpus_version,unit_id) REFERENCES unit_assessment(corpus_version,unit_id)
);

CREATE TABLE chunk_context (
  corpus_version TEXT NOT NULL,
  chunk_id TEXT NOT NULL,
  context_order INTEGER NOT NULL CHECK(context_order>=0) CHECK(typeof(context_order)='integer'),
  unit_id TEXT NOT NULL REFERENCES legal_unit(unit_id),
  field_name TEXT NOT NULL CHECK(field_name IN ('title','text_original')),
  char_start INTEGER NOT NULL CHECK(char_start>=0) CHECK(typeof(char_start)='integer'),
  char_end INTEGER NOT NULL CHECK(char_end>char_start) CHECK(typeof(char_end)='integer'),
  context_role TEXT NOT NULL CHECK(context_role IN ('heading','lead_in','reference','table_header')),
  PRIMARY KEY(corpus_version,chunk_id,context_order),
  FOREIGN KEY(corpus_version,chunk_id) REFERENCES chunk(corpus_version,chunk_id),
  FOREIGN KEY(corpus_version,unit_id) REFERENCES unit_assessment(corpus_version,unit_id)
);

CREATE TABLE quality_issue (
  issue_id TEXT PRIMARY KEY NOT NULL,
  corpus_version TEXT NOT NULL REFERENCES corpus(corpus_version),
  unit_id TEXT REFERENCES legal_unit(unit_id),
  rule_id TEXT NOT NULL,
  severity TEXT NOT NULL CHECK(severity IN ('error','warning')),
  status TEXT NOT NULL CHECK(status IN ('open','resolved','excluded')),
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX idx_unit_parent ON legal_unit(parent_unit_id,ordinal);
CREATE INDEX idx_unit_law_path ON legal_unit(law_id,canonical_path);
CREATE INDEX idx_span_unit ON source_span(unit_id,span_order);
CREATE INDEX idx_file_law ON source_file(law_id);
CREATE INDEX idx_chunk_unit ON chunk(corpus_version,unit_id);
CREATE INDEX idx_issue_corpus ON quality_issue(corpus_version,status);
CREATE VIEW serving_chunks AS
SELECT c.corpus_version,c.chunk_id,c.unit_id,u.parent_unit_id,
 d.source_id,d.law_id,d.law_title,u.citation_path,d.source_url,
 c.text_original,c.context_text,c.text_for_search,c.content_sha256,
 a.effective_from,a.effective_to,a.applicability_status,
 (SELECT json_group_array(json_object('file_id',e.file_id,'span_id',s.span_id,
 'locator',json(s.locator_json))) FROM source_span s
 JOIN extraction e ON e.extraction_id=s.extraction_id
 WHERE s.unit_id=c.unit_id) AS source_locator
FROM chunk c JOIN corpus p ON p.corpus_version=c.corpus_version
JOIN legal_unit u ON u.unit_id=c.unit_id
JOIN legal_document d ON d.law_id=u.law_id
JOIN unit_assessment a ON a.corpus_version=c.corpus_version AND a.unit_id=c.unit_id
WHERE a.scope_status='included' AND a.applicability_status='verified_at_snapshot'
 AND a.effective_from<=p.snapshot_date
 AND (a.effective_to IS NULL OR p.snapshot_date<a.effective_to);
-- View supports inspection. Production release MUST pass validate_design.py.
-- This view alone does not prove context/source validity or legal correctness.
