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
    result = {'events': [{'key':'cpi','metric':'mom','label':'CPI MOM','actual':0.2,'consensus':0.4,'previous':0.1,'surprise':-0.2,'score':100.0,'date':'2026-09-11','source':'Forex Factory'}]}
    state = update_released_surprises(state, result)
    save_state(state, p)
    assert active_surprise_score(state, {'cpi':1.0}) == 100.0


def test_new_release_replaces_old_metric():
    state = {'surprises': {'cpi|mom|2026-09-11': {'key':'cpi','metric':'mom','date':'2026-09-11','score':-50.0}}}
    result = {'events': [{'key':'cpi','metric':'mom','label':'CPI MOM','actual':0.1,'consensus':0.4,'previous':0.2,'surprise':-0.3,'score':100.0,'date':'2026-10-14','source':'Forex Factory'}]}
    state = update_released_surprises(state, result)
    assert active_surprise_score(state, {'cpi':1.0}) == 100.0
