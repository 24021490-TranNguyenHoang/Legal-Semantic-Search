"""PDF layout adapter for the frozen paragraph grammar; original PDF offsets win.

The legacy grammar's DOCX tags are private compatibility tokens, never source
metadata. Exported spans always reference the real immutable PDF page trace.
"""
from collections import Counter
import copy
from io import BytesIO
import re
import unicodedata

from src.ingestion import legal_tree as grammar
from src.source_contracts import canonical, digest

VERSION = "pdf-paragraph-layout.v1"


def page_lines(pdf, record, text, trace):
    """Align measured PDF text lines exactly to Stage3, failing on any mismatch."""
    nodes = [n for n in trace["nodes"] if n["kind"] == "page"]
    if len(nodes) != len(pdf.pages):
        raise ValueError("PDF/trace page count mismatch")
    result = []
    for page_no, (page, node) in enumerate(zip(pdf.pages, nodes), 1):
        raw_lines = page.extract_text_lines()
        source = text[node["char_start"]:node["char_end"]]
        if "\n".join(unicodedata.normalize("NFC", l["text"]) for l in raw_lines) != source:
            raise ValueError("PDF layout lines do not exactly align with normalized page text")
        cursor = node["char_start"]
        for i, line in enumerate(raw_lines):
            value = unicodedata.normalize("NFC", line["text"])
            result.append({"page": page_no, "line_index": i, "char_start": cursor,
                "char_end": cursor + len(value), "text": value, "locator": node["locator"],
                "bbox": [line[k] for k in ["x0", "top", "x1", "bottom"]],
                "bold": all("Bold" in c["fontname"] for c in line["chars"] if c["text"].strip()),
                "chars": line["chars"]})
            cursor += len(value) + 1
    return result


def select_blocks(lines, table_specs):
    """Only observed full-width paragraph markers; tables never introduce units."""
    blocks, supporting = [], []
    active = None
    ended = False
    seen_headers = set()
    for line in lines:
        value = line["text"]
        if line["line_index"] == 0 and "CÔNG BÁO/Số 1355 + 1356/Ngày 18-12-2024" in value:
            if str(20 + line["page"]) not in value.split():
                raise ValueError("Unexpected printed Gazette page")
            supporting.append({**line, "reason": "GAZETTE_RUNNING_HEADER"})
            seen_headers.add(line["page"])
            continue
        if value == "KT. BỘ TRƯỞNG":
            ended = True
        if ended:
            supporting.append({**line, "reason": "SIGNATURE"})
            continue
        selected_table = next((t for t in table_specs if t["page"] == line["page"] and
            (t["bbox"][1]-0.5 <= (line["bbox"][1]+line["bbox"][3])/2 <= t["bbox"][3]+0.5
             or value == "Bảng " + str(t["number"]))), None)
        if selected_table:
            key = selected_table["number"]
            if active is None or active.get("table_number") != key:
                active = {"kind": "table", "lines": [], "table_number": key}; blocks.append(active)
            active["lines"].append(line)
            continue
        marker = bool(grammar.CHAPTER.match(value) or grammar.SECTION.match(value)
                      or grammar.CLAUSE.match(value) or grammar.POINT.match(value)
                      or line["bold"] and grammar.ARTICLE.match(value))
        heading = line["bold"] and bool(grammar.CHAPTER.match(value) or grammar.SECTION.match(value) or grammar.ARTICLE.match(value))
        if (marker or active is None or active["kind"] == "table"
                or active.get("heading") and not line["bold"]):
            active = {"kind": "paragraph", "lines": [], "heading": heading}; blocks.append(active)
        active["lines"].append(line)
    if len(seen_headers) != len({l["page"] for l in lines}):
        raise ValueError("Every page must have its observed running header")
    return blocks, supporting


def project(blocks, eid):
    """Derived grammar coordinates, not an extraction or a claimed DOCX source."""
    view, pieces, nodes, position = [], [], [], 0
    nodes.extend([{"node_index": 0, "kind": "document", "parent_index": None, "locator": {},
                   "char_start": 0, "char_end": 0, "locator_id": "grammar-root"},
                  {"node_index": 1, "kind": "part", "parent_index": 0, "locator": {},
                   "char_start": 0, "char_end": 0, "locator_id": "grammar-body"}])
    for j, b in enumerate(blocks):
        if j: view.append("\n"); position += 1
        start = position
        for i, line in enumerate(b["lines"]):
            if i: view.append("\n"); position += 1
            pieces.append({"start": position, "end": position+len(line["text"]), "source": line})
            view.append(line["text"]); position += len(line["text"])
        # Private compatibility shape only. No such locator is persisted/exported.
        nodes.append({"node_index": len(nodes), "kind": b["kind"], "parent_index": 1,
            "locator": {"part": grammar.BODY_PART, "projection_block": j},
            "char_start": start, "char_end": position, "locator_id": f"grammar-{j}", "extraction_id": eid})
    nodes[0]["char_end"] = nodes[1]["char_end"] = position
    return "".join(view), {"nodes": nodes, "separators": []}, pieces


def remap_interval(a, b, pieces):
    result = []
    for p in pieces:
        lo, hi = max(a, p["start"]), min(b, p["end"])
        if lo < hi:
            line = p["source"]
            result.append((line["char_start"]+lo-p["start"], line["char_start"]+hi-p["start"], line["locator"]))
    return result


def parse_layout(record, text, trace, lines, specs):
    eid = record["extraction"]["extraction_id"]
    blocks, supporting = select_blocks(lines, specs)
    view, virtual_trace, pieces = project(blocks, eid)
    # The frozen API uses doc_text as its block-grammar mode. This is a transient
    # view, NOT the source extraction record; real metadata remains pdf_text.
    transient = {"law_id": record["law_id"], "extraction": {"extraction_id": eid, "method": "doc_text"}}
    old = grammar.parse_extraction(transient, view, virtual_trace, [])
    drafts = []
    for s in old["spans"]:
        for a, b, loc in remap_interval(s["char_start"], s["char_end"], pieces):
            drafts.append({"old_unit_id": s["unit_id"], "field_name": s["field_name"], "char_start": a,
                           "char_end": b, "locator_json": canonical(loc)})
    title_start = text.index("THÔNG TƯ\n")
    title_end = text.index("\nCăn cứ", title_start)
    root_old = old["units"][0]["unit_id"]
    # Source-backed circular title; the frozen DOCX policy recognizes only laws/decrees.
    drafts = [s for s in drafts if not (s["old_unit_id"] == root_old and
               title_start <= s["char_start"] and s["char_end"] <= title_end)]
    for line in lines:
        if title_start <= line["char_start"] < line["char_end"] <= title_end:
            drafts.append({"old_unit_id": root_old, "field_name": "title", "char_start": line["char_start"],
                           "char_end": line["char_end"], "locator_json": canonical(line["locator"])})
    units, spans, mapping = [], [], {}
    for old_u in old["units"]:
        u = copy.deepcopy(old_u); u["parent_unit_id"] = mapping.get(old_u["parent_unit_id"])
        own = []
        for field in ["title", "text_original"]:
            group = sorted([s for s in drafts if s["old_unit_id"] == old_u["unit_id"] and s["field_name"] == field], key=lambda s:s["char_start"])
            u[field] = "\n".join(text[s["char_start"]:s["char_end"]] for s in group)
            for order, d in enumerate(group):
                own.append({k:v for k,v in d.items() if k != "old_unit_id"} | {"extraction_id": eid,
                    "span_order": order, "quote_sha256": digest(text[d["char_start"]:d["char_end"]].encode())})
        u["text_sha256"] = digest(u["text_original"].encode()); u["unit_id"] = grammar.unit_id(u)
        mapping[old_u["unit_id"]] = u["unit_id"]; units.append(u)
        for s in own:
            s["unit_id"] = u["unit_id"]; s["span_id"] = grammar.span_id(s); spans.append(s)
    issues, table_regions = [], []
    for t in old["tables"]:
        ranges = remap_interval(t["char_start"], t["char_end"], pieces)
        owner = mapping[t["context_unit_id"]]
        spec = next(s for s in specs if s["page"] == ranges[0][2]["page_start"] and
                    text[ranges[0][0]:ranges[0][1]] == "Bảng " + str(s["number"]))
        table_regions.append({"number": spec["number"], "page": spec["page"], "context_unit_id": owner,
            "char_start": ranges[0][0], "char_end": ranges[-1][1], "locator": ranges[0][2], "extraction_id": eid})
    for q in old["issues"]:
        ranges = remap_interval(q["char_start"], q["char_end"], pieces)
        if not ranges: raise ValueError("Unmapped parser issue")
        payload = {**{k:v for k,v in q.items() if k not in {"issue_id", "locator", "char_start", "char_end"}},
                   "locator": ranges[0][2], "char_start": ranges[0][0], "char_end": ranges[-1][1]}
        issues.append({"issue_id": grammar.hashed("pqi_", payload), **payload})
    # Explicit dependency: weather clause refers to table values in point a.
    affected = [u["unit_id"] for u in units if u["canonical_path"].endswith("article:11/clause:2/point:b")]
    if affected:
        t = next(t for t in table_regions if t["number"] == 3)
        payload = {"law_id": record["law_id"], "extraction_id": eid, "code": "UNEXPANDED_TABLE_CROSS_REFERENCE",
            "affected_unit_ids": affected, "locator": t["locator"], "char_start": t["char_start"], "char_end": t["char_end"],
            "detail": "Point b requires comparison with point a/table3; no automatic external context expansion", "status": "pending"}
        issues.append({"issue_id": grammar.hashed("pqi_", payload), **payload})
    coverage = partition(record, text, trace, spans, supporting, table_regions, units)
    errors = grammar.validate_tree(units, spans, {eid:(record,text,trace)}, coverage)
    if errors: raise ValueError("PDF tree invariant failure: " + canonical(errors))
    return {"units": units, "spans": spans, "issues": issues, "tables": table_regions, "coverage": coverage,
            "blocks": [{"kind": b["kind"], "source_ranges": [{k:l[k] for k in ["page", "char_start", "char_end", "bbox"]} for l in b["lines"]]} for b in blocks]}


def partition(record, text, trace, spans, supporting, tables, units):
    eid = record["extraction"]["extraction_id"]; by = {u["unit_id"]:u for u in units}
    boundaries = {0,len(text)}
    for r in spans + supporting + tables + trace["separators"]:
        boundaries.update([r["char_start"],r["char_end"]])
    result = []
    for a,b in zip(sorted(boundaries), sorted(boundaries)[1:]):
        if a == b: continue
        row = {"extraction_id":eid,"law_id":record["law_id"],"char_start":a,"char_end":b,"unit_id":None,"field_name":None}
        own = next((s for s in spans if s["char_start"] <= a < b <= s["char_end"]),None)
        table = next((t for t in tables if t["char_start"] <= a < b <= t["char_end"]),None)
        support = next((s for s in supporting if s["char_start"] <= a < b <= s["char_end"]),None)
        sep = any(s["char_start"] <= a < b <= s["char_end"] for s in trace["separators"])
        if own: row.update(category="supporting_non_body" if by[own["unit_id"]]["unit_type"]=="document" else "parsed",reason="SOURCE_FIELD",unit_id=own["unit_id"],field_name=own["field_name"])
        elif table: row.update(category="unprocessed",reason="TABLE_LINKED_CELLS_NOT_UNIT_TEXT")
        elif support: row.update(category="supporting_non_body",reason=support["reason"])
        elif sep: row.update(category="serialization_separator",reason="STAGE3_PAGE_SEPARATOR")
        elif not text[a:b].strip(): row.update(category="source_layout",reason="SOURCE_WHITESPACE")
        else: row.update(category="unprocessed",reason="UNCLAIMED_SOURCE")
        result.append(row)
    return result


def cell_evidence(pdf, lines, regions, specs, record, raw_sha, text):
    """Physical cells + exact source text slices; merged None slots remain None."""
    tables, cells = [], []
    for spec in specs:
        page = pdf.pages[spec["page"]-1]
        table = page.find_tables()[spec["detected_index"]]
        if any(abs(a-b)>0.1 for a,b in zip(table.bbox,spec["bbox"])):
            raise ValueError("Observed table geometry changed")
        region = next(t for t in regions if t["number"]==spec["number"])
        tid = grammar.hashed("pdf-table_",{"file_sha256":raw_sha,"page":spec["page"],"bbox":spec["bbox"]})
        slots = []
        for ri,row in enumerate(table.rows):
            physical = []
            for ci,bbox in enumerate(row.cells):
                if bbox is None: physical.append(None); continue
                slices = []
                for line in [l for l in lines if l["page"]==spec["page"]]:
                    cursor = 0; hits=[]
                    for ch in line["chars"]:
                        value = unicodedata.normalize("NFC",ch["text"])
                        pos=line["text"].find(value,cursor)
                        if pos<0:
                            if value.isspace(): continue
                            raise ValueError("PDF character cannot be aligned to immutable text")
                        cursor=pos+len(value)
                        x=(ch["x0"]+ch["x1"])/2; y=(ch["top"]+ch["bottom"])/2
                        if bbox[0]<=x<bbox[2] and bbox[1]<=y<bbox[3] and value.strip():hits.append((pos,pos+len(value)))
                    if hits:
                        a=line["char_start"]+min(x[0] for x in hits); b=line["char_start"]+max(x[1] for x in hits)
                        slices.append({"char_start":a,"char_end":b,"quote":text[a:b],"quote_sha256":digest(text[a:b].encode()),"locator":line["locator"]})
                cell = {"table_id":tid,"row":ri,"column":ci,"bbox":list(bbox),"page":spec["page"],
                    "extraction_id":record["extraction"]["extraction_id"],"source_pdf_sha256":raw_sha,"source_slices":slices,
                    "text":"\n".join(s["quote"] for s in slices)}
                cell["cell_id"]=grammar.hashed("pdf-cell_",cell);cells.append(cell);physical.append(cell["cell_id"])
            slots.append(physical)
        if len(slots)!=spec["rows"] or any(len(s)!=spec["columns"] for s in slots):raise ValueError("Table dimensions changed")
        tables.append({**region,"table_id":tid,"bbox":spec["bbox"],"cell_slots":slots,"status":"pending","derived_only":True})
    return tables,cells
