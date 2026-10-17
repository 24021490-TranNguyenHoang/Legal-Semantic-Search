-- Stage 3 pending-only storage. No official source_file or corpus fabrication.
PRAGMA foreign_keys=ON;
CREATE TABLE pending_source (
 file_id TEXT PRIMARY KEY NOT NULL,
 law_id TEXT NOT NULL,
 record_json TEXT NOT NULL CHECK(json_valid(record_json))
);
CREATE TABLE pending_extraction (
 extraction_id TEXT PRIMARY KEY NOT NULL,
 file_id TEXT NOT NULL REFERENCES pending_source(file_id),
 review_status TEXT NOT NULL CHECK(review_status='pending'),
 technical_status TEXT NOT NULL CHECK(technical_status IN ('complete','partial')),
 record_json TEXT NOT NULL CHECK(json_valid(record_json))
);
CREATE TABLE pending_locator (
 locator_id TEXT PRIMARY KEY NOT NULL,
 extraction_id TEXT NOT NULL REFERENCES pending_extraction(extraction_id),
 parent_locator_id TEXT,
 char_start INTEGER NOT NULL CHECK(typeof(char_start)='integer' AND char_start>=0),
 char_end INTEGER NOT NULL CHECK(typeof(char_end)='integer' AND char_end>=char_start),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 UNIQUE(extraction_id,locator_id),
 FOREIGN KEY(extraction_id,parent_locator_id) REFERENCES pending_locator(extraction_id,locator_id)
);
CREATE TABLE pending_extraction_issue (
 issue_id TEXT PRIMARY KEY NOT NULL,
 file_id TEXT NOT NULL REFERENCES pending_source(file_id),
 extraction_id TEXT REFERENCES pending_extraction(extraction_id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json))
);
