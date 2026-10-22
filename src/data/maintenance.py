"""Refresh derived features, catalog and provenance after incremental acquisition."""
import csv,json
import pandas as pd
from src.data.common import atomic_bytes,utc_now
from src.data.ingest import catalog
from src.data.quality import derive_features,audit
from src.utils.serialization import atomic_json


def finalize(context,coverage):
    root=context.root
    derive_features(context);catalog(context)
    coverage['updated_at']=utc_now();atomic_json(root/'data/coverage.json',coverage)
    atomic_bytes(root/'data/coverage.csv',pd.DataFrame(coverage['datasets']).to_csv(index=False).encode('utf-8-sig'))
    for name in ['coverage.json','coverage.csv']:context.log('local_normalization','local://coverage',root/'data'/name,len(coverage['datasets']),kind='coverage')
    path=root/'data/lineage.json'
    lineage=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'artifacts':{}}
    for row in csv.DictReader((root/'data/source_log.csv').open(encoding='utf-8',newline='')):
        previous=lineage['artifacts'].get(row['file_path'])
        if previous is None or previous['sha256']!=row['sha256']:lineage['artifacts'][row['file_path']]=row
    lineage['artifacts'].update(context.artifacts);atomic_json(path,lineage)
    quality=audit(root);atomic_json(root/'data/quality_report.json',quality)
    return quality
