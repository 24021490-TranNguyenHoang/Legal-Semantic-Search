"""Bound preview consumer for eight table owners; no dataset/index side effects."""
import copy
from pathlib import Path

from src.assessment_evidence import check_files
from src.experimental_dataset import load, rows
from src.source_contracts import canonical, digest
from src.ingestion import tt35_owner_tables as original, encoder_views

CAPABILITIES = {'whole-owned-table-read.v1', 'physical-cell-source-read.v1', 'bounded-dependency-read.v1'}


def require_capabilities(capabilities):
    if not CAPABILITIES <= set(capabilities):
        raise ValueError('Consumer missing table-owner capability')


class TableOwnerConsumer:
    def __init__(self, settings, capabilities=CAPABILITIES):
        require_capabilities(capabilities)
        cfg, base, physical, units, data, _, _, files, texts, pages = original.source_inputs(settings['source_config'])
        original.validate(settings['source_config'], settings['source_run'])
        self.physical = physical
        self.records, self.views, self.crosswalk = [], [], []
        old = rows(Path(settings['source_run']) / 'tables.preview.jsonl')
        views = {v['source_record']['record_id']: v for v in rows(Path(settings['source_run']) / 'encoder_views.jsonl')}
        tables, cells, annexes = (rows(physical / (n + '.jsonl')) for n in ['tables', 'cells', 'annexes'])
        overrides = {x['owner_unit_id']: x for x in settings['overrides']}
        if len(overrides) != len(settings['overrides']): raise ValueError('Duplicate owner override')
        by = {u['unit_id']: u for u in units}
        for spec, prior in zip(cfg['owners'], old):
            selected = copy.deepcopy(spec); change = overrides.get(spec['owner_unit_id'])
            if change:
                unit = by[change['evidence_unit_id']]
                if (digest(canonical(unit).encode()) != change['evidence_unit_sha256']
                        or change['literal'] not in unit['text_original']
                        or selected['required_annexes'] != change['before_annexes']
                        or digest(Path(change['image_ref']).read_bytes()) != change['image_sha256']):
                    raise ValueError('Annex correction source/proof binding mismatch')
                selected['required_annexes'] = change['after_annexes']
            record = original.compose(selected, units, tables, cells, data, base, annexes, physical)
            original.check_record(record, record, texts, pages, files)
            if record['text_for_search'] != prior['text_for_search'] or record['cells'] != prior['cells']:
                raise ValueError('Dependency adapter must preserve source content and encoder input')
            view = copy.deepcopy(views[prior['record_id']])
            view['source_record'] = record
            view['identity']['source_record_sha256'] = digest(canonical(record).encode())
            view['record_id'] = 'rv_' + digest(canonical(view['identity']).encode())
            encoder_views.validate(view, 256)
            self.records.append(record); self.views.append(view)
            self.crosswalk.append({'old_record_id': prior['record_id'], 'new_record_id': record['record_id'],
                                   'old_view_record_id': views[prior['record_id']]['record_id'], 'new_view_record_id': view['record_id'],
                                   'unit_id': record['owner_unit_id'], 'reason': change['reason'] if change else 'Payload unchanged',
                                   'identity_change': ['required_dependencies'] if change else [],
                                   'encoder_input_unchanged': True, 'token_ids_unchanged': True})
        if set(overrides) - {r['owner_unit_id'] for r in self.records}: raise ValueError('Unknown override owner')

    def read(self, record_id, capabilities=CAPABILITIES):
        require_capabilities(capabilities)
        record = next(r for r in self.records if r['record_id'] == record_id)
        return original.read_record(record, self.physical)

    def validate_record(self, record):
        expected = next((r for r in self.records if r['record_id'] == record.get('record_id')), None)
        if expected is None or record != expected: raise ValueError('Owner/header/cell/dependency/proof differs from bound table record')
