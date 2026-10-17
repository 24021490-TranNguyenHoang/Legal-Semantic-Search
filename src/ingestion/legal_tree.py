"""Conservative legal structure on immutable Stage 3 code-point offsets.

No raw reader, normalization, legal assessment, chunking or model imports here.
"""
from collections import Counter, defaultdict
import json
import re

from src.source_contracts import canonical, digest


LABELS = {"document": "", "chapter": "Chương", "section": "Mục",
          "article": "Điều", "clause": "Khoản", "point": "Điểm"}
ALLOWED = {"document": {"chapter", "section", "article"},
           "chapter": {"section", "article"}, "section": {"article"},
           "article": {"clause", "point"}, "clause": {"point"}, "point": set()}
UNIT_FIELDS = ("law_id", "parent_unit_id", "unit_type", "designation", "canonical_path",
               "citation_path", "ordinal", "title", "text_original")
CHAPTER = re.compile(r"^(Chương)\s+([IVXLCDM]+|[1-9]\d*)(?=$|[\s.:–—-])(?:[\s.:–—-]+(.*))?$", re.I | re.S)
SECTION = re.compile(r"^(Mục)\s+([1-9]\d*)(?=$|[\s.:–—-])(?:[\s.:–—-]+(.*))?$", re.I | re.S)
ARTICLE = re.compile(r"^Điều\s+([1-9]\d*[a-zđ]?)\.\s+(.+)$", re.S)
CLAUSE = re.compile(r"^([1-9]\d*)\.\s+\S", re.S)
POINT = re.compile(r"^([a-zđ])\)\s+\S", re.S)
POINT_ORDER = "abcdđeghiklmnopqrstuvxy"
BODY_PART = "word/document.xml"
ANNEX = re.compile(r"^PHỤ LỤC(?:\s|$)", re.I)
AMENDMENT = re.compile(r"(?:sửa đổi|bổ sung|thay thế).*(?:điều|khoản|điểm|phụ lục).*(?:như sau|sau đây):$", re.I | re.S)
UNCLEAR_HEADING = re.compile(r"^(?:Điều|Chương|Mục)\s+[^\n]{0,24}[.:]\s", re.I)
NUMBER_LIKE = re.compile(r"^\d+[a-zđ]?[.)]\s", re.I)
EXPLICIT_LIST = re.compile(r"^(?:Ví dụ minh họa|Danh sách minh họa|Danh sách tham khảo)\s*:", re.I)


def hashed(prefix, value):
    return prefix + digest(canonical(value).encode("utf-8"))


def unit_id(unit):
    return hashed("u_", {"identity_schema": "unit.v1", **{k: unit[k] for k in UNIT_FIELDS}})


def span_id(span):
    return hashed("s_", {"identity_schema": "source-span.v1", **{k: v for k, v in span.items() if k != "span_id"}})


def trimmed_interval(text, start, end):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def quote_state(text, depth):
    # Curly quotation marks are nesting-aware. Straight paired quotes toggle.
    for char in text:
        if char == "“":
            depth += 1
        elif char == "”":
            depth = max(0, depth - 1)
        elif char == '"':
            depth = 0 if depth else 1
    return depth


def parse_extraction(record, text, trace, extraction_issues):
    """Return pending units/spans, exhaustive leaf/separator coverage and issues.

    Only whole top-level main-part paragraphs can introduce legal units. Table
    cells, auxiliary parts and quoted amendments cannot introduce such levels.
    """
    eid, law = record["extraction"]["extraction_id"], record["law_id"]
    nodes = trace["nodes"]
    drafts, coverage, issues, tables, reviews = [], [], [], [], []
    claims = defaultdict(list)
    defaults = {}

    def issue(code, node, detail):
        payload = {"extraction_id": eid, "law_id": law, "code": code,
                   "locator": node["locator"], "char_start": node["char_start"],
                   "char_end": node["char_end"], "detail": detail, "severity": "warning", "status": "pending"}
        issues.append({"issue_id": hashed("pqi_", payload), **payload})

    def new(kind, designation, parent, node=None):
        siblings = [d for d in drafts if d["parent"] is parent and parent is not None]
        draft = {"kind": kind, "designation": designation, "parent": parent,
                 "ordinal": len(siblings), "title": [], "text_original": [], "origin": node}
        drafts.append(draft)
        return draft

    root = new("document", law, None)
    chapter = section = article = clause = point = None
    pending_title = None
    last_article = 0
    depth = 0
    suspended = False
    ended = False
    title_area = False
    document_title_done = False
    annex = False
    amendment_pending = False
    undelimited_amendment = False
    quote_nodes = []

    def advance_quote(value, node):
        nonlocal depth, quote_nodes
        prior = depth
        depth = quote_state(value, depth)
        if depth:
            quote_nodes = quote_nodes + [node] if prior else [node]
        else:
            quote_nodes = []

    def own():
        return point or clause or article or section or chapter or root

    def claim(draft, field, node, start=None, end=None):
        nonlocal amendment_pending
        start = node["char_start"] if start is None else start
        end = node["char_end"] if end is None else end
        if start < end:
            draft[field].append((node, start, end))
            claims[node["node_index"]].append((start, end, draft, field))
            if field == "text_original" and not depth and not text[start:end].lstrip().startswith(('“', '"')) and AMENDMENT.search(text[start:end].strip()):
                amendment_pending = True

    # Source warnings remain open. They are not resolved by parsing around them.
    warned = defaultdict(list)
    for q in extraction_issues:
        loc = q["locator"]
        match = [n for n in nodes if n["locator"] == loc]
        review = {"source_issue_id": q["issue_id"], "law_id": law,
                  "extraction_id": eid, "code": q["code"], "locator": loc,
                  "status": "pending", "handling": "partition_ancillary_parts"}
        if match:
            n = match[0]
            warned[n["node_index"]].append(q)
            review.update(char_start=n["char_start"], char_end=n["char_end"],
                          handling="quarantine_locator_keep_source_bytes")
        reviews.append(review)

    body = [n for n in nodes if n["locator"].get("part") == BODY_PART
            and n["parent_index"] is not None
            and nodes[n["parent_index"]]["kind"] == "part"]
    if record["extraction"]["method"] != "doc_text" or not body:
        issue("UNSUPPORTED_STRUCTURAL_TRACE", nodes[0], "Only DOCX main-body block traces are parsed by this policy; source retained.")
        suspended = True

    content_blocks = [i for i, n in enumerate(body) if text[n["char_start"]:n["char_end"]].strip()]
    for body_order, node in enumerate(body):
        idx = node["node_index"]
        start, end = node["char_start"], node["char_end"]
        a, b = trimmed_interval(text, start, end)
        value = text[a:b]
        defaults[idx] = ("layout", "EMPTY_OR_EDGE_WHITESPACE")
        # An annex is accounted for, never forced into the preceding clause.
        # Its boundaries/numbering need a separate structural policy.
        if not depth and node["kind"] == "paragraph" and ANNEX.match(value):
            annex = True
            issue("ANNEX_STRUCTURE_NOT_SUPPORTED", node, "Annex marker and subsequent main-body blocks retained as unprocessed; no inferred annex hierarchy.")
        if annex:
            defaults[idx] = ("unprocessed", "ANNEX_STRUCTURE_NOT_SUPPORTED")
            if node["kind"] == "table":
                tables.append({"extraction_id": eid, "law_id": law, "locator": node["locator"],
                               "char_start": start, "char_end": end, "category": "unprocessed",
                               "reason": "ANNEX_STRUCTURE_NOT_SUPPORTED", "context": root})
            continue
        if node["kind"] == "table":
            next_order = next((i for i in content_blocks if i > body_order), None)
            at_end = next_order is None or ANNEX.match(text[body[next_order]["char_start"]:body[next_order]["char_end"]].strip())
            signature = bool(at_end and any(token in value.splitlines() for token in ("TM. CHÍNH PHỦ", "CHỦ TỊCH QUỐC HỘI", "Nơi nhận:")))
            preamble = not any(d["kind"] != "document" for d in drafts)
            category = "supporting_non_body" if preamble or ended or signature else "unprocessed"
            reason = "SIGNATURE_OR_PREAMBLE_TABLE" if category == "supporting_non_body" else "TABLE_STRUCTURE_NOT_PARSED"
            tables.append({"extraction_id": eid, "law_id": law, "locator": node["locator"],
                           "char_start": start, "char_end": end, "category": category,
                           "reason": reason, "context": own()})
            defaults[idx] = (category, reason)
            if category == "unprocessed":
                issue(reason, node, "Table retained in extraction; cells do not become clauses. Review table semantics separately.")
            if signature:
                ended = True
                pending_title = None
            # A replacement presented as a table has its own unprocessed record.
            amendment_pending = False
            continue
        if node["kind"] != "paragraph":
            defaults[idx] = ("unprocessed", "UNSUPPORTED_MAIN_BODY_BLOCK")
            issue("UNSUPPORTED_MAIN_BODY_BLOCK", node, "No inferred legal structure for this block.")
            continue
        if idx in warned:
            defaults[idx] = ("needs_review", "UNDECODED_SOURCE_CONTENT")
            issue("UNDECODED_SOURCE_CONTENT", node, "Source field/numbering/revision/visual is unresolved; no inferred text or designation.")
            suspended = True
            pending_title = None
            continue
        if not value:
            continue
        if value.startswith(("Luật này được Quốc hội", "TM. CHÍNH PHỦ", "CHỦ TỊCH QUỐC HỘI", "Nơi nhận:")):
            ended = True
        if ended:
            defaults[idx] = ("supporting_non_body", "ENACTMENT_OR_SIGNATURE")
            continue
        if amendment_pending and not depth:
            amendment_pending = False
            if not value.startswith(('“', '"')) and not AMENDMENT.search(value):
                issue("UNDELIMITED_AMENDMENT", node, "After a replacement instruction, no quotation boundary or nested replacement instruction identifies the following structure. Quarantine the remaining body; do not interpret replacement headings as this document's units.")
                undelimited_amendment = True
        if undelimited_amendment:
            defaults[idx] = ("needs_review", "UNDELIMITED_AMENDMENT_REGION")
            continue
        if depth:
            if suspended:
                defaults[idx] = ("needs_review", "STRUCTURE_SUSPENDED")
            else:
                claim(own(), "text_original", node)
                defaults[idx] = ("parsed", "QUOTED_AMENDMENT_OWN_TEXT")
            advance_quote(value, node)
            continue
        # An opening quotation is content, even if it contains a heading/number.
        if value.startswith(('“', '"')):
            if article and not suspended:
                claim(own(), "text_original", node)
                defaults[idx] = ("parsed", "QUOTED_AMENDMENT_OWN_TEXT")
            else:
                defaults[idx] = ("needs_review", "QUOTATION_WITHOUT_RELIABLE_OWNER")
            advance_quote(value, node)
            continue
        heading = CHAPTER.fullmatch(value) or SECTION.fullmatch(value)
        if heading:
            kind = "chapter" if heading.group(1).lower() == "chương" else "section"
            designation = heading.group(2)
            if heading.group(3) and not heading.group(3)[0].isupper():
                issue("HEADING_LIKE_REFERENCE", node, "Inline/prose chapter or section reference is not a heading; retain with its owner for review.")
                if article and not suspended:
                    claim(own(), "text_original", node)
                    defaults[idx] = ("parsed", "HEADING_LIKE_REFERENCE")
                else:
                    defaults[idx] = ("needs_review", "HEADING_LIKE_REFERENCE")
                continue
            if kind == "chapter" and not designation.isdigit() and not re.fullmatch(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", designation, re.I):
                issue("UNCLEAR_HEADING", node, "Invalid literal Roman designation; do not infer a chapter number.")
                defaults[idx] = ("needs_review", "UNCLEAR_HEADING")
                suspended = True
                continue
            parent = root if kind == "chapter" else chapter or root
            if any(d["parent"] is parent and d["kind"] == kind and d["designation"] == designation for d in drafts):
                defaults[idx] = ("needs_review", "DUPLICATE_STRUCTURAL_DESIGNATION")
                issue("DUPLICATE_STRUCTURAL_DESIGNATION", node, "Do not create duplicate canonical position.")
                suspended = True
                pending_title = None
                continue
            target = new(kind, designation, parent, node)
            if kind == "chapter":
                chapter, section = target, None
            else:
                section = target
            article = clause = point = None
            suspended = False
            pending_title = target
            if heading.group(3):
                title_start = a + heading.start(3)
                title_start, title_end = trimmed_interval(text, title_start, b)
                claim(target, "title", node, title_start, title_end)
            defaults[idx] = ("parsed", "HEADING_MARKER")
            continue
        am = ARTICLE.fullmatch(value)
        if am:
            number = int(re.match(r"\d+", am.group(1))[0])
            title = am.group(2)
            # Paragraph-boundary + exact syntax + plausible title + monotonic
            # designation. A reference 'Điều 2 của ...' does not match this rule.
            plausible = title[0].isupper() and not title.endswith((".", ";", ":", "!", "?"))
            if not plausible:
                # A prose citation stays in its owner's own text, never a unit.
                if article and not suspended:
                    claim(own(), "text_original", node)
                    defaults[idx] = ("parsed", "ARTICLE_LIKE_PROSE_REFERENCE")
                else:
                    defaults[idx] = ("needs_review", "AMBIGUOUS_ARTICLE_HEADING")
                issue("ARTICLE_LIKE_PROSE_REFERENCE", node, "Article-like paragraph rejected as heading by title grammar; review retained text.")
                continue
            if number <= last_article:
                defaults[idx] = ("needs_review", "NONMONOTONIC_ARTICLE")
                issue("NONMONOTONIC_ARTICLE", node, "Duplicate/backward article marker quarantined, not renumbered.")
                suspended = True
                pending_title = None
                continue
            if number != last_article + 1:
                issue("ARTICLE_SEQUENCE_GAP", node, "Observed article sequence has a gap; no missing units synthesized.")
            last_article = number
            article = new("article", am.group(1), section or chapter or root, node)
            clause = point = None
            pending_title = None
            suspended = False
            claim(article, "title", node, a + am.start(2), b)
            defaults[idx] = ("parsed", "HEADING_MARKER")
            continue
        if UNCLEAR_HEADING.match(value):
            issue("UNCLEAR_HEADING", node, "Heading-like paragraph has an unsupported designation/syntax; no guessed level or number.")
            defaults[idx] = ("needs_review", "UNCLEAR_HEADING")
            suspended = True
            pending_title = None
            continue
        # A conflict among points does not invalidate an independently explicit
        # next consecutive clause. Other unresolved source content requires a
        # reliable article/chapter before structure can resume.
        recovery = CLAUSE.match(value)
        if suspended == "points" and recovery and article:
            previous = [d for d in drafts if d["parent"] is article and d["kind"] == "clause"]
            if int(recovery.group(1)) == len(previous) + 1:
                suspended = False
        if suspended:
            defaults[idx] = ("needs_review", "STRUCTURE_SUSPENDED")
            continue
        if pending_title:
            following_order = next((i for i in content_blocks if i > body_order), None)
            following_text = "" if following_order is None else text[body[following_order]["char_start"]:body[following_order]["char_end"]].strip()
            mixed_case_title = (not pending_title["title"] and value[0].isupper()
                                and not value.endswith((".", ";", ":", "!", "?"))
                                and bool(ARTICLE.fullmatch(following_text) or SECTION.fullmatch(following_text) or CHAPTER.fullmatch(following_text)))
            if value.isupper() or mixed_case_title:
                # Multiple uppercase source paragraphs form one real heading.
                claim(pending_title, "title", node, a, b)
                defaults[idx] = ("parsed", "HEADING_TITLE")
                continue
            issue("MISSING_OR_UNRECOGNIZED_HEADING_TITLE", node, "No reliable heading-title continuation; content recorded separately.")
            pending_title = None
        if article and EXPLICIT_LIST.match(value):
            issue("AMBIGUOUS_NUMBERED_LIST", node, "Explicit illustrative/reference list is retained for review; consecutive numbers alone do not prove legal clauses.")
            defaults[idx] = ("needs_review", "AMBIGUOUS_NUMBERED_LIST")
            suspended = "list"
            continue
        cm, pm = CLAUSE.match(value), POINT.match(value)
        if cm and article:
            number = int(cm.group(1))
            prior = [d for d in drafts if d["parent"] is article and d["kind"] == "clause"]
            expected = len(prior) + 1
            if number == expected:
                clause = new("clause", cm.group(1), article, node)
                point = None
                claim(clause, "text_original", node)
                defaults[idx] = ("parsed", "EXPLICIT_CLAUSE")
                advance_quote(value, node)
                continue
            defaults[idx] = ("needs_review", "AMBIGUOUS_NUMBERED_PARAGRAPH")
            issue("AMBIGUOUS_NUMBERED_PARAGRAPH", node, "Not a consecutive clause marker; no fabricated clause or attachment to previous point.")
            suspended = True
            continue
        if pm and article:
            parent = clause or article
            prior = [d for d in drafts if d["parent"] is parent and d["kind"] == "point"]
            letter = pm.group(1)
            valid = letter in POINT_ORDER and (not prior and letter == "a" or prior and POINT_ORDER.index(letter) > POINT_ORDER.index(prior[-1]["designation"]))
            if valid:
                if prior and POINT_ORDER.index(letter) != POINT_ORDER.index(prior[-1]["designation"]) + 1:
                    issue("POINT_SEQUENCE_GAP", node, "Observed point sequence has a gap; marker retained literally, no missing point synthesized.")
                point = new("point", letter, parent, node)
                claim(point, "text_original", node)
                defaults[idx] = ("parsed", "EXPLICIT_POINT")
                advance_quote(value, node)
                continue
            defaults[idx] = ("needs_review", "AMBIGUOUS_POINT")
            issue("AMBIGUOUS_POINT", node, "Unordered/unsupported point marker; no inferred numbering.")
            # Quarantine the earlier conflicting point too; do not choose which
            # duplicate is a typo. Retain other unambiguous siblings.
            conflicts = [d for d in prior if d["designation"] == letter]
            for conflict in conflicts:
                for field in ("title", "text_original"):
                    for old_node, _, _ in conflict[field]:
                        old_idx = old_node["node_index"]
                        claims[old_idx] = [c for c in claims[old_idx] if c[2] is not conflict]
                        defaults[old_idx] = ("needs_review", "CONFLICTING_POINT_DESIGNATION")
                issue("CONFLICTING_POINT_DESIGNATION", conflict["origin"], "Same literal designation occurs again under this parent; both positions quarantined without correction.")
                drafts.remove(conflict)
            for ordinal, sibling in enumerate(d for d in drafts if d["parent"] is parent):
                sibling["ordinal"] = ordinal
            point = None
            suspended = "points"
            continue
        if article and NUMBER_LIKE.match(value):
            issue("UNCLEAR_NUMBERED_STRUCTURE", node, "Unsupported numbered marker outside quotation; do not infer a clause or attach it to the previous point.")
            defaults[idx] = ("needs_review", "UNCLEAR_NUMBERED_STRUCTURE")
            suspended = True
            continue
        if not chapter and not article:
            defaults[idx] = ("supporting_non_body", "DOCUMENT_PREAMBLE")
            # Real source document title only, not declared inventory metadata.
            if value in {"LUẬT", "NGHỊ ĐỊNH"} or value.startswith("NGHỊ ĐỊNH\n"):
                title_area = True
                claim(root, "title", node, a, b)
                if "\n" in value:
                    document_title_done = True
            elif title_area and not document_title_done and not value.startswith(("Căn cứ", "Theo đề nghị", "Quốc hội ban hành", "Chính phủ ban hành")) and not set(value) <= {"_", "-"}:
                claim(root, "title", node, a, b)
            else:
                if title_area:
                    document_title_done = True
                claim(root, "text_original", node)
            continue
        claim(own(), "text_original", node)
        defaults[idx] = ("parsed", "OWN_TEXT_CONTINUATION_OR_LEAD_IN")
        advance_quote(value, node)

    if depth:
        issue("UNCLOSED_QUOTATION", quote_nodes[0] if quote_nodes else nodes[0], "Unclosed quotation; affected paragraphs quarantined, not interpreted as this document's new legal units.")
        for node in quote_nodes:
            idx = node["node_index"]
            for _, _, draft, field in claims.pop(idx, []):
                draft[field] = [entry for entry in draft[field] if entry[0]["node_index"] != idx]
            defaults[idx] = ("needs_review", "UNCLOSED_QUOTATION_REGION")
    no_structure = not any(d["kind"] != "document" for d in drafts)
    if no_structure:
        issue("NO_RELIABLE_LEGAL_STRUCTURE", nodes[0], "No supported explicit legal heading was identified; document text retained for review, no artificial article/clause created.")
    # Ancillary parts/table cells inherit classification from the enclosing block.
    units, spans = [], []
    draft_ids = {}
    for draft in drafts:
        parent = draft["parent"]
        parent_unit = draft_ids[id(parent)] if parent else None
        segment = draft["kind"] + ":" + draft["designation"]
        parent_record = next((u for u in units if u["unit_id"] == parent_unit), None)
        path = parent_record["canonical_path"] + "/" + segment if parent_record else segment
        citation_segment = law if parent is None else LABELS[draft["kind"]] + " " + draft["designation"]
        citation = parent_record["citation_path"] + " > " + citation_segment if parent_record else citation_segment
        unit = {"law_id": law, "parent_unit_id": parent_unit, "unit_type": draft["kind"],
                "designation": draft["designation"], "canonical_path": path, "citation_path": citation,
                "ordinal": draft["ordinal"], **{field: "\n".join(text[s:e] for _, s, e in draft[field]) for field in ("title", "text_original")}}
        unit["text_sha256"] = digest(unit["text_original"].encode("utf-8"))
        unit["unit_id"] = unit_id(unit)
        draft_ids[id(draft)] = unit["unit_id"]
        units.append(unit)
        for field in ("title", "text_original"):
            for order, (node, start, end) in enumerate(draft[field]):
                span = {"unit_id": unit["unit_id"], "extraction_id": eid, "field_name": field,
                        "span_order": order, "char_start": start, "char_end": end,
                        "locator_json": canonical(node["locator"]), "quote_sha256": digest(text[start:end].encode("utf-8"))}
                span["span_id"] = span_id(span)
                spans.append(span)
    non_leaf = {n["parent_index"] for n in nodes}
    for node in nodes:
        if node["node_index"] in non_leaf:
            continue
        idx = node["node_index"]
        top = node
        while top["parent_index"] is not None and top["node_index"] not in defaults:
            top = nodes[top["parent_index"]]
        if node["locator"].get("part") != BODY_PART:
            category, reason = ("supporting_non_body", "ANCILLARY_PART_NOT_BODY")
        else:
            category, reason = defaults.get(top["node_index"], ("unprocessed", "UNSUPPORTED_STRUCTURAL_TRACE"))
        if idx in warned:
            category, reason = "needs_review", "UNDECODED_SOURCE_CONTENT"
        start, end = node["char_start"], node["char_end"]
        parts = sorted(claims[idx], key=lambda x: x[0])
        cursor = start
        intervals = []
        for s, e, draft, field in parts:
            if cursor < s:
                intervals.append((cursor, s, category, reason, None, None))
            cat = ("needs_review" if no_structure else "supporting_non_body") if draft["kind"] == "document" else "parsed"
            intervals.append((s, e, cat, "SOURCE_FIELD_" + field.upper(), draft_ids[id(draft)], field))
            cursor = e
        if cursor < end or start == end:
            intervals.append((cursor, end, category, reason, None, None))
        for s, e, cat, rule, uid, field in intervals:
            coverage.append({"extraction_id": eid, "law_id": law, "locator_id": node["locator_id"],
                             "locator": node["locator"], "char_start": s, "char_end": e,
                             "category": cat, "reason": rule, "unit_id": uid, "field_name": field})
    for sep in trace["separators"]:
        coverage.append({"extraction_id": eid, "law_id": law, "locator_id": nodes[sep["parent_index"]]["locator_id"],
                         "locator": nodes[sep["parent_index"]]["locator"], "char_start": sep["char_start"],
                         "char_end": sep["char_end"], "category": "serialization_separator",
                         "reason": sep["rule"], "unit_id": None, "field_name": None})
    for table in tables:
        table["context_unit_id"] = draft_ids[id(table.pop("context"))]
    return {"units": units, "spans": spans, "coverage": sorted(coverage, key=lambda c: (c["char_start"], c["char_end"], c["locator_id"])),
            "issues": issues, "tables": tables, "warning_reviews": reviews}


def validate_tree(units, spans, extraction_data, coverage):
    """Independent DDD invariants; bundle replay additionally checks semantics."""
    errors = []
    mapping = {u["unit_id"]: u for u in units}
    if len(mapping) != len(units):
        errors.append("DUPLICATE_UNIT_ID")
    if len({s["span_id"] for s in spans}) != len(spans):
        errors.append("DUPLICATE_SPAN_ID")
    paths, siblings, roots = set(), defaultdict(list), Counter()
    grouped = defaultdict(list)
    used = defaultdict(list)
    for u in units:
        key = (u["law_id"], u["canonical_path"])
        if key in paths:
            errors.append("DUPLICATE_CANONICAL_POSITION")
        paths.add(key)
        if type(u["ordinal"]) is not int or u["ordinal"] < 0:
            errors.append("INVALID_ORDINAL")
        if u["unit_id"] != unit_id(u) or u["text_sha256"] != digest(u["text_original"].encode("utf-8")):
            errors.append("UNIT_ID_OR_HASH")
        parent = mapping.get(u["parent_unit_id"])
        if u["parent_unit_id"] is None:
            roots[u["law_id"]] += 1
            if u["unit_type"] != "document" or u["designation"] != u["law_id"]:
                errors.append("INVALID_ROOT")
        elif not parent or parent["law_id"] != u["law_id"] or u["unit_type"] not in ALLOWED.get(parent["unit_type"], set()):
            errors.append("INVALID_PARENT_OR_FAKE_LEVEL")
        path_segment = u["unit_type"] + ":" + u["designation"]
        citation_segment = u["law_id"] if u["parent_unit_id"] is None else LABELS.get(u["unit_type"], "") + " " + u["designation"]
        if u["canonical_path"] != (parent["canonical_path"] + "/" if parent else "") + path_segment:
            errors.append("CANONICAL_PATH_PARENT")
        if u["citation_path"] != (parent["citation_path"] + " > " if parent else "") + citation_segment:
            errors.append("CITATION_PATH_PARENT")
        siblings[(u["law_id"], u["parent_unit_id"])].append(u["ordinal"])
        seen, ancestor = set(), u
        while ancestor:
            if ancestor["unit_id"] in seen:
                errors.append("CYCLE")
                break
            seen.add(ancestor["unit_id"])
            ancestor = mapping.get(ancestor["parent_unit_id"])
    if any(count != 1 for count in roots.values()) or set(roots) != {v[0]["law_id"] for v in extraction_data.values()}:
        errors.append("ROOT_COUNT")
    if any(sorted(values) != list(range(len(values))) for values in siblings.values()):
        errors.append("SIBLING_ORDER")
    for s in spans:
        u = mapping.get(s["unit_id"])
        entry = extraction_data.get(s["extraction_id"])
        if not u or not entry or entry[0]["law_id"] != u["law_id"]:
            errors.append("SPAN_RELATIONSHIP")
            continue
        record, text, trace = entry
        a, b = s["char_start"], s["char_end"]
        if type(s["span_order"]) is not int or s["span_order"] < 0:
            errors.append("SPAN_ORDER")
        if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(text):
            errors.append("SPAN_OFFSETS")
            continue
        if s["span_id"] != span_id(s) or s["quote_sha256"] != digest(text[a:b].encode("utf-8")):
            errors.append("SPAN_ID_OR_QUOTE_HASH")
        if not any(n["locator"] == json.loads(s["locator_json"]) and n["char_start"] <= a < b <= n["char_end"] for n in trace["nodes"]):
            errors.append("SPAN_LOCATOR")
        grouped[(s["unit_id"], s["field_name"])].append(s)
        used[s["extraction_id"]].append((a, b))
    for u in units:
        for field in ("title", "text_original"):
            group = sorted(grouped[(u["unit_id"], field)], key=lambda s: s["span_order"])
            if [s["span_order"] for s in group] != list(range(len(group))):
                errors.append("SPAN_ORDER")
            reconstructed = "\n".join(extraction_data[s["extraction_id"]][1][s["char_start"]:s["char_end"]] for s in group)
            if reconstructed != u[field]:
                errors.append("FIELD_ROUNDTRIP")
    for intervals in used.values():
        values = sorted(intervals)
        if any(a[1] > b[0] for a, b in zip(values, values[1:])):
            errors.append("DUPLICATED_SOURCE_IN_UNIT_FIELDS")
    for eid, (_, text, _) in extraction_data.items():
        cursor = 0
        for c in sorted((c for c in coverage if c["extraction_id"] == eid and c["char_start"] < c["char_end"]), key=lambda c: c["char_start"]):
            if c["char_start"] != cursor:
                errors.append("COVERAGE_GAP_OR_OVERLAP")
            cursor = c["char_end"]
        if cursor != len(text):
            errors.append("COVERAGE_INCOMPLETE")
    return sorted(set(errors))
