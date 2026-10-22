"""Identification, dependence-aware descriptive regressions and bounded exports."""
import hashlib

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.main import create_app
from src.evaluation.econometrics import block_indices, fit_regressions, paired_block_interval
from src.evaluation.research import partition, study_spec
from src.utils.serialization import atomic_json


def test_panel_identification_and_time_block_quantiles():
    rng=np.random.default_rng(42);rows=[]
    for time in range(8):
        for pool in range(4):
            for policy,width in [(0,.05),(0,.1),(0,.2),(0,.4),(1,.15)]:
                vol=.3+.1*rng.normal();volume=15+rng.normal()
                rows.append({'pool':str(pool),'pair':str(pool//2),'start':f'2025-{time+1:02d}-01','width':width,
                    'rebalance_policy':policy,'vol_annual':vol,'log_volume_usd':volume,'log_width':np.log(width),
                    'fee_bps':5 if pool%2==0 else 30,'partition':'test',
                    'excess_vs_hodl':-.02*vol+.01*volume+.003*np.log(width)+.002*policy+rng.normal(0,.001)})
    settings={'hac_lags':1,'seed':42,'bootstrap_block_windows':2,'quantile_bootstrap_repetitions':3,'quantiles':[.1,.5,.9]}
    coefficients,diagnostics=fit_regressions(pd.DataFrame(rows),settings)
    assert diagnostics['status']=='descriptive_only'
    assert diagnostics['causal_identification'] is False
    assert 'z_fee_bps' not in set(coefficients.loc[coefficients.model=='pool_FE_DK','term'])
    assert 'z_fee_bps' in set(coefficients.loc[coefficients.model=='pair_FE_fee_DK','term'])
    assert np.isfinite(coefficients.coefficient).all()
    assert coefficients.loc[coefficients.model.str.startswith('quantile'),'p_value'].isna().all()
    assert diagnostics['models']['pool_FE_DK']['rank']>4


def test_paired_block_bootstrap_is_reproducible_and_preserves_pairing():
    frame=pd.DataFrame([{'pool':pool,'start':str(time),'strategy':strategy,'excess_vs_hodl':time*.001+(strategy=='optimizer')*.01}
                        for pool in ['a','b'] for time in range(8) for strategy in ['fixed','optimizer']])
    result=paired_block_interval(frame,repetitions=99)
    assert result==paired_block_interval(frame,repetitions=99)
    assert abs(result['mean_optimizer_minus_fixed']-.01)<1e-12
    assert result['ci95_low']<=.010000000001 and result['ci95_high']>=.009999999999
    indices=block_indices(8,2,np.random.default_rng(42))
    assert len(indices)==8 and all(0<=i<8 for i in indices)
    assert partition('2023-01-01')=='train' and partition('2024-01-01')=='validation' and partition('2025-01-01')=='test'
    assert 'no model/hyperparameter selection' in study_spec()['selection']


def test_research_artifacts_are_hash_verified_and_whitelisted(tmp_path):
    run_id='a'*64;directory=tmp_path/'outputs/research'/run_id;directory.mkdir(parents=True)
    payload=b'pool,return\na,0.1\n';(directory/'results.csv').write_bytes(payload)
    manifest={'research_id':run_id,'version':'test','data_kind':'historical_replay_modelled_fees','status':{},
              'files':[{'name':'results.csv','sha256':hashlib.sha256(payload).hexdigest(),'kind':'csv'}]}
    atomic_json(tmp_path/'outputs/research/latest.json',manifest)
    with TestClient(create_app(state_dir=tmp_path)) as client:
        assert client.get('/api/v1/research/status').json()['research_id']==run_id
        assert client.get('/api/v1/research/files/results.csv').content==payload
        assert client.get('/api/v1/research/files/secret.env').status_code==404
        (directory/'results.csv').write_bytes(b'tampered')
        assert client.get('/api/v1/research/files/results.csv').status_code==503
