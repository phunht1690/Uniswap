"""Content-addressed historical replay, independent from forward Monte Carlo runs."""
import json
from pathlib import Path

from api.schemas import BacktestRecord
from src.data.backtest import load_inputs
from src.evaluation.backtest import BACKTEST_VERSION, replay, versions
from src.utils.config import load_config
from src.utils.serialization import atomic_json, digest


class BacktestService:
    def __init__(self, root):
        self.root = Path(root)
        self.settings = load_config('backtest')

    def run(self, config, persist=True):
        inputs = load_inputs(self.root, config, self.settings)
        run_id = digest({'kind': 'historical_backtest', 'config': config.model_dump(mode='json'),
                         'data_hash': inputs['data_hash'], 'settings': self.settings,
                         'model_version': BACKTEST_VERSION, 'versions': versions()})
        path = self.root / 'outputs/backtests' / (run_id + '.json')
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))['result']
        result = replay(inputs, config, self.settings)
        result['meta'].update(run_id=run_id, data_hash=inputs['data_hash'], seed=config.seed,
                              effective_config=config.model_dump(mode='json'), numerical_versions=versions(), settings=self.settings)
        if persist:
            atomic_json(path, BacktestRecord(config=config, result=result).model_dump(mode='json'))
        return result

    def get(self, run_id):
        return BacktestRecord.model_validate_json((self.root / 'outputs/backtests' / (run_id+'.json')).read_text(encoding='utf-8'))
