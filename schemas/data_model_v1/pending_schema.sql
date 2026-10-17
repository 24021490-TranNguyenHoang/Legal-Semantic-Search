-- Registration-only staging layer. Not the official DDD schema or serving data.
PRAGMA foreign_keys=ON;
CREATE TABLE pending_document (
 law_id TEXT PRIMARY KEY NOT NULL,
 source_id TEXT NOT NULL UNIQUE,
 record_json TEXT NOT NULL CHECK(json_valid(record_json))
);
CREATE TABLE pending_file (
 file_id TEXT PRIMARY KEY NOT NULL,
 law_id TEXT NOT NULL REFERENCES pending_document(law_id),
 source_set_id TEXT NOT NULL,
 part_order INTEGER NOT NULL CHECK(typeof(part_order)='integer' AND part_order>=1),
 sha256 TEXT NOT NULL CHECK(length(sha256)=64),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 UNIQUE(law_id,sha256),
 UNIQUE(law_id,source_set_id,part_order),
 UNIQUE(file_id,law_id)
);
CREATE TABLE pending_quality_issue (
 issue_id TEXT PRIMARY KEY NOT NULL,
 law_id TEXT NOT NULL REFERENCES pending_document(law_id),
 file_id TEXT,
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 FOREIGN KEY(file_id,law_id) REFERENCES pending_file(file_id,law_id)
);
