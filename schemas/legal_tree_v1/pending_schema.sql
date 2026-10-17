-- Separate pending legal tree; official DDD schema remains byte-identical.
PRAGMA foreign_keys=ON;
CREATE TABLE pending_source (
 file_id TEXT PRIMARY KEY NOT NULL,
 law_id TEXT NOT NULL,
 source_status TEXT NOT NULL CHECK(source_status='pending'),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 UNIQUE(file_id,law_id)
);
CREATE TABLE pending_extraction (
 extraction_id TEXT PRIMARY KEY NOT NULL,
 file_id TEXT NOT NULL,
 law_id TEXT NOT NULL,
 review_status TEXT NOT NULL CHECK(review_status='pending'),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 UNIQUE(extraction_id,law_id),
 FOREIGN KEY(file_id,law_id) REFERENCES pending_source(file_id,law_id)
);
CREATE TABLE pending_legal_unit (
 unit_id TEXT PRIMARY KEY NOT NULL,
 law_id TEXT NOT NULL,
 parent_unit_id TEXT,
 unit_type TEXT NOT NULL CHECK(unit_type IN ('document','chapter','section','article','clause','point')),
 designation TEXT NOT NULL,
 canonical_path TEXT NOT NULL,
 citation_path TEXT NOT NULL,
 ordinal INTEGER NOT NULL CHECK(typeof(ordinal)='integer' AND ordinal>=0),
 title TEXT NOT NULL,
 text_original TEXT NOT NULL,
 text_sha256 TEXT NOT NULL CHECK(length(text_sha256)=64),
 review_status TEXT NOT NULL CHECK(review_status='pending'),
 UNIQUE(unit_id,law_id),
 UNIQUE(law_id,canonical_path),
 FOREIGN KEY(parent_unit_id,law_id) REFERENCES pending_legal_unit(unit_id,law_id)
);
CREATE TABLE pending_source_span (
 span_id TEXT PRIMARY KEY NOT NULL,
 unit_id TEXT NOT NULL,
 extraction_id TEXT NOT NULL,
 law_id TEXT NOT NULL,
 field_name TEXT NOT NULL CHECK(field_name IN ('title','text_original')),
 span_order INTEGER NOT NULL CHECK(typeof(span_order)='integer' AND span_order>=0),
 char_start INTEGER NOT NULL CHECK(typeof(char_start)='integer' AND char_start>=0),
 char_end INTEGER NOT NULL CHECK(typeof(char_end)='integer' AND char_end>char_start),
 locator_json TEXT NOT NULL CHECK(json_valid(locator_json)),
 quote_sha256 TEXT NOT NULL CHECK(length(quote_sha256)=64),
 UNIQUE(unit_id,field_name,span_order),
 FOREIGN KEY(unit_id,law_id) REFERENCES pending_legal_unit(unit_id,law_id),
 FOREIGN KEY(extraction_id,law_id) REFERENCES pending_extraction(extraction_id,law_id)
);
CREATE TABLE pending_parser_issue (
 issue_id TEXT PRIMARY KEY NOT NULL,
 extraction_id TEXT NOT NULL REFERENCES pending_extraction(extraction_id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json))
);
