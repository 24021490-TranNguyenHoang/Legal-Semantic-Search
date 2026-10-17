"""Technical source readers. No cleaning, Unicode normalization or OCR here."""
from collections import Counter
from io import BytesIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class UnsupportedSource(ValueError):
    pass


def node(kind, locator, *, children=None, raw_text=None, separator="\n"):
    result = {"kind": kind, "locator": locator, "separator": separator}
    if children is not None:
        result["children"] = children
    if raw_text is not None:
        result["raw_text"] = raw_text
    return result


class DocxReader:
    def __init__(self, config):
        self.config = config
        self.issues = []
        self.table_index = 0

    def issue(self, code, locator, detail, severity="warning"):
        self.issues.append({"code": code, "locator": locator, "detail": detail, "severity": severity})

    def children(self, element, xpath):
        counts = Counter()
        for child in element:
            counts[child.tag] += 1
            local = child.tag.split("}")[-1]
            yield child, f"{xpath}/w:{local}[{counts[child.tag]}]", counts[child.tag] - 1

    def paragraph(self, element, locator):
        text = []
        for entry in element.iter():
            if entry.tag in {W + "t", W + "delText"}:
                text.append(entry.text or "")
            elif entry.tag == W + "tab":
                text.append("\t")
            elif entry.tag in {W + "br", W + "cr"}:
                text.append("\n")
            elif entry.tag == W + "noBreakHyphen":
                text.append("\u2011")
            elif entry.tag == W + "softHyphen":
                text.append("\u00ad")
            elif entry.tag in {W + "drawing", W + "pict", W + "object", W + "sym"}:
                self.issue("DOCX_VISUAL_OR_SYMBOL_REVIEW", locator,
                           "Visual/symbol content needs review; descendant w:t retained, no OCR/visual decoding.")
            elif entry.tag in {W + "ins", W + "del", W + "moveFrom", W + "moveTo"}:
                self.issue("DOCX_TRACKED_CHANGE_REVIEW", locator,
                           "Both present text and delText retained in XML order; revision decision required.")
            elif entry.tag in {W + "instrText", W + "fldSimple", W + "numPr"}:
                self.issue("DOCX_GENERATED_CONTENT_REVIEW", locator,
                           "Field instructions/automatic numbering not rendered; review original XML.")
            elif entry.tag in {W + "footnoteReference", W + "endnoteReference"}:
                self.issue("DOCX_NOTE_REFERENCE", {**locator, "reference_id": entry.get(W + "id")},
                           "Note text appended as a separate part; reference marker is metadata.")
        return node("paragraph", locator, raw_text="".join(text))

    def tagged(self, element, path, tag):
        for child, child_path, index in self.children(element, path):
            if child.tag == W + tag:
                yield child, child_path, index
            elif child.tag in {W + "sdt", W + "sdtContent", W + "customXml"}:
                yield from self.tagged(child, child_path, tag)
            elif any(e.tag in {W + "t", W + "delText"} for e in child.iter()):
                self.issue("DOCX_UNSUPPORTED_STRUCTURE", {"format": "docx", "xpath": child_path},
                           f"Unexpected content outside {tag}; retained in raw, needs review.", "error")

    def table(self, element, locator):
        table_index = self.table_index
        self.table_index += 1
        locator = {**locator, "table_index": table_index}
        rows = []
        for row, row_path, row_index in self.tagged(element, locator["xpath"], "tr"):
            row_locator = {**locator, "xpath": row_path, "row_index": row_index}
            cells = []
            for cell, cell_path, cell_index in self.tagged(row, row_path, "tc"):
                props = cell.find(W + "tcPr")
                span = props.find(W + "gridSpan") if props is not None else None
                merge = props.find(W + "vMerge") if props is not None else None
                cell_locator = {**row_locator, "xpath": cell_path, "cell_index": cell_index,
                                "grid_span": span.get(W + "val") if span is not None else "1",
                                "v_merge": merge.get(W + "val", "continue") if merge is not None else None}
                cells.append(node("cell", cell_locator,
                                  children=self.blocks(cell, cell_locator), separator=self.config["block_separator"]))
            rows.append(node("row", row_locator, children=cells, separator=self.config["cell_separator"]))
        return node("table", locator, children=rows, separator=self.config["block_separator"])

    def blocks(self, element, locator):
        result = []
        for child, path, index in self.children(element, locator["xpath"]):
            child_locator = {**locator, "xpath": path}
            if child.tag == W + "p":
                result.append(self.paragraph(child, {**child_locator, "paragraph_index": index}))
            elif child.tag == W + "tbl":
                result.append(self.table(child, child_locator))
            elif child.tag in {W + "sdt", W + "sdtContent", W + "customXml", W + "footnote", W + "endnote"}:
                result.extend(self.blocks(child, child_locator))
            elif child.tag in {W + "sectPr", W + "tcPr", W + "sdtPr", W + "customXmlPr"}:
                continue
            elif child.tag == W + "altChunk" or any(e.tag in {W + "t", W + "delText"} for e in child.iter()):
                self.issue("DOCX_UNSUPPORTED_STRUCTURE", child_locator,
                           "Unprocessed body structure retained in raw; file is partial, not complete.", "error")
        return result

    def read(self, data):
        with ZipFile(BytesIO(data)) as archive:
            main = ET.fromstring(archive.read("word/document.xml"))
            body = main.find(W + "body")
            if body is None:
                raise ValueError("DOCX has no document body")
            locator = {"format": "docx", "part": "word/document.xml", "xpath": "/w:document/w:body"}
            parts = [node("part", locator, children=self.blocks(body, locator), separator=self.config["block_separator"])]
            extras = sorted(n for n in archive.namelist() if n.endswith(".xml") and
                            n.startswith(("word/header", "word/footer", "word/footnotes", "word/endnotes")))
            for name in extras:
                root = ET.fromstring(archive.read(name))
                part_locator = {"format": "docx", "part": name, "xpath": "/w:" + root.tag.split("}")[-1]}
                parts.append(node("part", part_locator, children=self.blocks(root, part_locator),
                                  separator=self.config["block_separator"]))
            if extras:
                self.issue("DOCX_ANCILLARY_PARTS_APPENDED", {"format": "docx", "parts": extras},
                           "Ancillary parts appended in part-name order; no rendered page order is inferred.")
        tree = node("document", {"format": "docx", "scope": "main_body_then_ancillary_parts"},
                    children=parts, separator=self.config["block_separator"])
        return tree, self.issues, "doc_text"


def read_pdf(data, config):
    import pdfplumber
    pages, issues = [], []
    with pdfplumber.open(BytesIO(data)) as source:
        if not source.pages:
            raise ValueError("PDF has no pages")
        for number, page in enumerate(source.pages, 1):
            locator = {"format": "pdf", "page_start": number, "page_end": number,
                       "width": float(page.width), "height": float(page.height)}
            try:
                raw = page.extract_text(**config["pdf"]) or ""
                if not raw.strip():
                    issues.append({"code": "PDF_PAGE_NO_TEXT", "severity": "warning", "locator": locator,
                                   "detail": "No extractable text: may be blank or scanned; review OCR need, no OCR performed."})
            except Exception as exc:
                raw = ""
                issues.append({"code": "PDF_PAGE_EXTRACTION_FAILED", "severity": "error", "locator": locator,
                               "detail": f"{type(exc).__name__}: {exc}"})
            pages.append(node("page", locator, raw_text=raw))
    return node("document", {"format": "pdf"}, children=pages, separator=config["block_separator"]), issues, "pdf_text"


def read_source(data, mime_type, config):
    if mime_type == DOCX_MIME:
        return DocxReader(config).read(data)
    if mime_type == "application/pdf":
        return read_pdf(data, config)
    raise UnsupportedSource(f"Unsupported source MIME: {mime_type}")
