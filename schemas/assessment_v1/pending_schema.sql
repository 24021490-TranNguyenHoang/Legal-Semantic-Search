-- Pending staging only; deliberately no official corpus or legal_unit stand-ins.
CREATE TABLE assessment_binding (
  binding_id TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE pending_subject (
  unit_id TEXT PRIMARY KEY,
  binding_id TEXT NOT NULL REFERENCES assessment_binding(binding_id),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE pending_evidence (
  evidence_id TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE pending_region (
  region_id TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE pending_review_basis (
  finding_id TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE pending_impact (
  impact_id TEXT PRIMARY KEY,
  unit_id TEXT REFERENCES pending_subject(unit_id),
  region_id TEXT REFERENCES pending_region(region_id),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE pending_proposal (
  proposal_id TEXT PRIMARY KEY,
  unit_id TEXT UNIQUE NOT NULL REFERENCES pending_subject(unit_id),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE pending_decision_event (
  decision_id TEXT PRIMARY KEY,
  unit_id TEXT NOT NULL REFERENCES pending_subject(unit_id),
  dimension TEXT NOT NULL CHECK(dimension IN ('scope','applicability','technical')),
  supersedes TEXT UNIQUE,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  UNIQUE(decision_id,unit_id,dimension),
  FOREIGN KEY(supersedes,unit_id,dimension) REFERENCES pending_decision_event(decision_id,unit_id,dimension)
);
CREATE TABLE pending_assessment (
  assessment_id TEXT PRIMARY KEY,
  unit_id TEXT UNIQUE NOT NULL REFERENCES pending_subject(unit_id),
  proposal_id TEXT NOT NULL REFERENCES pending_proposal(proposal_id),
  scope_decision_id TEXT REFERENCES pending_decision_event(decision_id),
  applicability_decision_id TEXT REFERENCES pending_decision_event(decision_id),
  technical_decision_id TEXT REFERENCES pending_decision_event(decision_id),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
