"""Synthetic PDF-layout fixtures; no fixture is a legal source/assessment."""
import copy
import unittest
from types import SimpleNamespace

from src.ingestion import pdf_layout, legal_tree, extraction_normalizer, extractors
from src.source_contracts import canonical
from src import tt38_preview


def fixture(table=False, split=False):
    content=[("CÔNG BÁO/Số 1355 + 1356/Ngày 18-12-2024 21",False),
        ("THÔNG TƯ",True),("FIXTURE — VĂN BẢN GIẢ LẬP",True),("Căn cứ giả lập.",False),
        ("Chương I",True),("FIXTURE QUY TẮC",True),("Điều 1. FIXTURE tiêu đề",True),
        ("hai dòng",True),("Đoạn dẫn Điều được giữ.",False),
        ("1. FIXTURE Không được vượt 0,25 mg/l:",False),("a) FIXTURE hành vi có chữ đ.",False)]
    if table:content += [("Bảng 1",False),("2. Ô bảng không phải Khoản",False)]
    content += [("FIXTURE tiếp nối không mất nội dung.",False),("KT. BỘ TRƯỞNG",True),("FIXTURE người ký",True)]
    pages=[content]
    if split:pages=[content[:11],[("22 CÔNG BÁO/Số 1355 + 1356/Ngày 18-12-2024",False)]+content[11:]]
    nodes=[extractors.node("page",{"format":"pdf","page_start":i+1,"page_end":i+1},raw_text="\n".join(t for t,_ in p)) for i,p in enumerate(pages)]
    text,trace=extraction_normalizer.serialize(extractors.node("document",{"format":"pdf"},children=nodes))
    lines=[]
    for pi,(p,n) in enumerate(zip(pages,[n for n in trace["nodes"] if n["kind"]=="page"]),1):
        a=n["char_start"]
        for li,(value,bold) in enumerate(p):
            lines.append({"page":pi,"line_index":li,"char_start":a,"char_end":a+len(value),"text":value,
                "locator":n["locator"],"bbox":[50,li*20,500,li*20+10],"bold":bold,"chars":[]})
            a+=len(value)+1
    rec={"law_id":"FIXTURE/TT38","extraction":{"extraction_id":"FIXTURE-extraction","method":"pdf_text"}}
    specs=[]
    if table:
        selected=[l for l in lines if l["text"] in {"Bảng 1","2. Ô bảng không phải Khoản"}]
        specs=[{"page":selected[0]["page"],"number":1,"bbox":[50,selected[0]["bbox"][1],500,selected[-1]["bbox"][3]]}]
    return rec,text,trace,lines,specs


class PdfLayoutTests(unittest.TestCase):
    def parse(self,**kwargs):
        data=fixture(**kwargs);return data,pdf_layout.parse_layout(*data)

    def test_two_line_titles_and_leads_roundtrip_with_real_pdf_locators(self):
        data,out=self.parse()
        article=next(u for u in out["units"] if u["unit_type"]=="article")
        self.assertEqual(article["title"],"FIXTURE tiêu đề\nhai dòng")
        self.assertEqual(article["text_original"],"Đoạn dẫn Điều được giữ.")
        self.assertNotIn("word/document.xml",canonical(out))
        self.assertTrue(all('"format":"pdf"' in s["locator_json"] for s in out["spans"]))
        self.assertFalse(legal_tree.validate_tree(out["units"],out["spans"],{"FIXTURE-extraction":data[:3]},out["coverage"]))

    def test_cross_page_continuation_does_not_include_running_header(self):
        data,out=self.parse(split=True)
        point=next(u for u in out["units"] if u["unit_type"]=="point")
        self.assertIn("tiếp nối không mất",point["text_original"])
        self.assertNotIn("CÔNG BÁO",point["text_original"])
        spans=[s for s in out["spans"] if s["unit_id"]==point["unit_id"]]
        self.assertGreater(len({s["locator_json"] for s in spans}),1)

    def test_signature_not_attached_to_last_point(self):
        _,out=self.parse()
        body="\n".join(u["text_original"] for u in out["units"])
        self.assertNotIn("người ký",body)
        self.assertNotIn("KT. BỘ TRƯỞNG",body)

    def test_number_in_table_is_not_an_invented_clause_and_is_covered(self):
        _,out=self.parse(table=True)
        self.assertEqual([u["designation"] for u in out["units"] if u["unit_type"]=="clause"],["1"])
        self.assertTrue(out["tables"])
        self.assertTrue(any(q["code"]=="TABLE_STRUCTURE_NOT_PARSED" for q in out["issues"]))
        self.assertTrue(any(c["category"]=="unprocessed" for c in out["coverage"]))

    def test_unrecognized_header_fails_instead_of_becoming_law_content(self):
        data=list(fixture());data[3][0]["text"]="FIXTURE wrong header"
        with self.assertRaises(ValueError):pdf_layout.parse_layout(*data)

    def test_layout_cannot_silently_change_stage3_text(self):
        page=SimpleNamespace(extract_text_lines=lambda:[{"text":"FIXTURE changed"}])
        with self.assertRaisesRegex(ValueError,"align"):
            pdf_layout.page_lines(SimpleNamespace(pages=[page]),{},"FIXTURE original",{"nodes":[{"kind":"page","char_start":0,"char_end":16}]})

    def test_bad_offset_is_rejected_by_existing_tree_validator(self):
        data,out=self.parse();spans=copy.deepcopy(out["spans"]);spans[-1]["char_end"]=len(data[1])+1
        self.assertIn("SPAN_OFFSETS",legal_tree.validate_tree(out["units"],spans,{"FIXTURE-extraction":data[:3]},out["coverage"]))

    def test_source_projection_does_not_modify_input_record_trace_or_text(self):
        data=fixture(split=True);before=copy.deepcopy(data)
        pdf_layout.parse_layout(*data)
        self.assertEqual(data,before)

    def test_table_derivative_keeps_parent_exclusion_and_row_cell_links(self):
        units=[{"unit_id":"root","unit_type":"document","parent_unit_id":None},
            {"unit_id":"article","unit_type":"article","parent_unit_id":"root","title":"FIXTURE tốc độ (trừ cao tốc)","text_original":""},
            {"unit_id":"clause","unit_type":"clause","parent_unit_id":"article","title":"","text_original":"FIXTURE trong khu đông dân cư"}]
        cells=[{"cell_id":str(i),"text":t} for i,t in enumerate(["Loại xe","km/h","Đường đôi","Đường hai chiều","FIXTURE không gồm xe gắn máy","60","50"])]
        tables=[{"number":1,"table_id":"FIXTURE-table","context_unit_id":"clause","cell_slots":[["0","1",None],[None,"2","3"],["4","5","6"]]}]
        before=copy.deepcopy((units,cells,tables));r=tt38_preview.derive_rows(tables,cells,units)[0]
        self.assertIn("trừ cao tốc",r["ancestor_context_original"][0]["title_original"])
        self.assertIn("không gồm",r["text_derived"])
        self.assertEqual(r["source_cell_ids"],["0","4","1","2","5","1","3","6"])
        self.assertEqual((units,cells,tables),before)

    def test_profile_keeps_budget_and_allows_only_rebinding_same_extraction_policy(self):
        c=tt38_preview.load(tt38_preview.DEFAULT_CONFIG)
        tt38_preview.require_config({**c,"extraction_manifest_sha256":"1"*64})
        with self.assertRaises(ValueError):tt38_preview.require_config({**c,"token_limit":512})
        with self.assertRaises(ValueError):tt38_preview.require_config({**c,"law_id":"FIXTURE/OTHER"})


if __name__=="__main__":unittest.main()
