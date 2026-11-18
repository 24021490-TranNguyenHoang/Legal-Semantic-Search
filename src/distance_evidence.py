"""Declared development evidence requirements for 80/81, not a legal answer engine."""
import copy

from src.source_contracts import canonical, digest

VERSION = 'distance-80-81-evidence.v1'
HEADERS = {0: 'Tốc độ lưu hành (V km/h)', 1: 'Khoảng cách an toàn (m)'}
INTERVALS = {'60 < V ≤ 80': (60, 80, 55), '80 < V ≤ 100': (80, 100, 70)}


def hashed(value):
    return digest(canonical(value).encode())


def packets(consumer, record_ids):
    """Expose physical cells and full own-condition fields through the existing resolver."""
    out = []
    for rid in record_ids:
        response = consumer.read(rid); record = response['record']; src = record.get('source_record', record)
        if response['record_type'] not in {'table-retrieval.v1', 'source-retrieval.v1'}:
            raise ValueError('Evidence requires typed table or whole-source records')
        embedded = 'source_record' in record
        owner = src.get('explicit_dependency_unit_id') if embedded else src['owner_unit_id']

        def field(uid):
            text = consumer.nodes[uid]['unit']['text_original']
            spans = sorted([s for s in consumer.spans if s['unit_id'] == uid and s['field_name'] == 'text_original'],
                           key=lambda s: s['span_order'])
            proofs = [consumer.native(s) for s in spans]
            if '\n'.join(p['quote'] for p in proofs) != text:
                raise ValueError('Condition text does not roundtrip')
            return dict(unit_id=uid, text_original=text, proofs=proofs)

        raw_cells = src.get('source_cells', []) if embedded else src['cells']
        cells = []
        for c in raw_cells:
            proofs = [consumer.native({**p, 'extraction_id': c['extraction_id']}) for p in c['source_slices']]
            cells.append(dict(cell=copy.deepcopy(c), proofs=proofs))
        out.append(dict(record_id=rid, record_type=response['record_type'], payload_sha256=hashed(record),
                        access_path='dependency:source_record/table_rows' if embedded else 'target:rows',
                        rows=copy.deepcopy(src['table_rows'] if embedded else src['rows']), cells=cells,
                        normal_conditions=field(owner),
                        adverse_conditions=field(src['unit_id']) if embedded else None))
    return out


def check(consumer, evidence):
    """Fail closed on missing facets; never fill an omitted cell from an unseen record."""
    errors = []; available = {}; normal = []; adverse = []; paths = []
    ids = [p['record_id'] for p in evidence]
    if len(set(ids)) != len(ids):
        errors.append('DUPLICATE_EVIDENCE_RECORD')
    try:
        authoritative = {p['record_id']: p for p in packets(consumer, list(dict.fromkeys(ids)))}
        for packet in evidence:
            expected = authoritative[packet['record_id']]
            for key in ('record_type', 'payload_sha256', 'access_path'):
                if packet[key] != expected[key]: raise ValueError('EVIDENCE_RECORD_BINDING')
            bycell = {p['cell']['cell_id']: p for p in expected['cells']}
            cells = {}
            for entry in packet['cells']:
                cid = entry['cell']['cell_id']
                if cid in cells or cid not in bycell or hashed(entry) != hashed(bycell[cid]):
                    raise ValueError('CELL_OR_PROOF_BINDING')
                cells[cid] = entry['cell']
                for proof in entry['proofs']:
                    consumer.reader.proof(consumer.root, proof)
            for name, dest in [('normal_conditions', normal), ('adverse_conditions', adverse)]:
                field = packet.get(name)
                if field is not None:
                    if not expected[name] or hashed(field) != hashed(expected[name]) or not field['proofs']:
                        raise ValueError('CONDITION_OR_PROOF_BINDING')
                    for proof in field['proofs']: consumer.reader.proof(consumer.root, proof)
                    dest.append(field)
            for row in packet['rows']:
                if hashed(row) not in {hashed(v) for v in expected['rows']}:
                    raise ValueError('ROW_OWNER_OR_BOUNDARY_BINDING')
                needed = row['source_cell_ids']
                if not set(needed) <= set(cells):
                    errors.append('MISSING_HEADER_OR_DATA_CELL'); continue
                selected = [cells[cid] for cid in needed]
                if any(c['table_id'] != row['table_id'] for c in selected):
                    raise ValueError('HEADER_ROW_TABLE_BINDING')
                for col, header in HEADERS.items():
                    if not any(c['row'] == 0 and c['column'] == col and c['text'] == header for c in selected):
                        errors.append('MISSING_HEADER_OR_UNIT')
                data = {c['column']: c for c in selected if c['row'] == row['row']}
                if set(data) != {0, 1}:
                    errors.append('MISSING_DATA_CELL'); continue
                interval = INTERVALS.get(data[0]['text'])
                if interval:
                    lo, hi, distance = interval
                    if data[1]['text'] != str(distance): raise ValueError('DISTANCE_VALUE_BINDING')
                    for speed in (80, 81):
                        if lo < speed <= hi:
                            available[speed] = dict(distance_m=distance, interval=data[0]['text'],
                                                    speed_cell_id=data[0]['cell_id'], distance_cell_id=data[1]['cell_id'],
                                                    record_id=packet['record_id'], access_path=packet['access_path'])
                paths.append(packet['access_path'])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        errors.append(str(exc))
    for speed in (80, 81):
        if speed not in available: errors.append('MISSING_SPEED_' + str(speed))
    if not normal: errors.append('MISSING_NORMAL_CONDITIONS')
    if not adverse: errors.append('MISSING_ADVERSE_CONDITIONS')
    ok = not errors
    return dict(contract=VERSION, sufficient_for_declared_requirements=ok, errors=sorted(set(errors)),
                values=available, comparison_normal_only=(dict(speed_80_minimum_m=55, speed_81_minimum_m=70,
                    difference_m=15, ordered='55 < 70') if ok else None),
                normal_conditions=normal, adverse_conditions=adverse,
                adverse_fixed_distance=None, access_paths=sorted(set(paths)),
                limitation='Only declared evidence requirements; normal minima are not unconditional distances.',
                legal_verified=False, human_review=None, accepted_completeness_changed=False)
