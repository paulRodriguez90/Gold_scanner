from pathlib import Path
from gold_scanner.macro_state import load_state, save_state, update_released_surprises, active_surprise_score


def test_state_roundtrip(tmp_path):
    p = tmp_path / 'state.json'
    state = load_state(p)
    state['macro_context']['cpi_all_items'] = {'value': 333.9, 'date': '2026-07'}
    save_state(state, p)
    loaded = load_state(p)
    assert loaded['macro_context']['cpi_all_items']['value'] == 333.9


def test_latest_surprise_stays_active(tmp_path):
    p = tmp_path / 'state.json'
    state = load_state(p)
    result = {'events': [{'key':'cpi','metric':'mom','label':'CPI MOM','actual':0.2,'consensus':0.4,'previous':0.1,'surprise':-0.2,'score':100.0,'date':'2026-09-09','source':'Forex Factory'}]}
    state = update_released_surprises(state, result)
    save_state(state, p)
    assert active_surprise_score(state, {'cpi':1.0}) == 100.0


def test_new_release_replaces_old_metric():
    state = {'surprises': {'cpi|mom|2026-09-09': {'key':'cpi','metric':'mom','date':'2026-09-09','score':-50.0}}}
    result = {'events': [{'key':'cpi','metric':'mom','label':'CPI MOM','actual':0.1,'consensus':0.4,'previous':0.2,'surprise':-0.3,'score':100.0,'date':'2026-09-10','source':'Forex Factory'}]}
    state = update_released_surprises(state, result)
    assert active_surprise_score(state, {'cpi':1.0}) == 100.0


def test_future_surprise_is_removed_from_state():
    from gold_scanner.macro_state import update_released_surprises, active_surprise_score
    state = {'surprises': {'cpi|mom|2999-01-01': {'key':'cpi','metric':'mom','date':'2999-01-01','score':100.0}}}
    state = update_released_surprises(state, {'events': []})
    assert active_surprise_score(state, {'cpi': 1.0}) == 0.0


def test_calculate_surprise_refreshes_stale_persisted_score():
    from types import SimpleNamespace
    from gold_scanner.macro_scoring import calculate_surprise_impact
    state = {
        'surprises': {
            'core_cpi|value|2026-08-12': {
                'key': 'core_cpi', 'metric': 'value', 'date': '2026-08-12',
                'actual': 2.6, 'consensus': 2.5, 'score': -800.0,
                'label': 'Core CPI'
            }
        }
    }
    event = SimpleNamespace(
        key='core_cpi', metric='value', date='2026-08-12', actual=2.6,
        consensus=2.5, previous=2.5, released=True, source='test', release_time=None
    )
    result = calculate_surprise_impact({}, [event], state)
    row = next(r for r in result['events'] if r['key'] == 'core_cpi')
    assert row['score'] == -100.0
