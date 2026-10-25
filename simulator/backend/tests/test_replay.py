from simulator.backend.replay import ReplaySample, parse_csv, samples_to_csv


def test_csv_round_trip():
    original = [ReplaySample(0.0, [1500] * 16), ReplaySample(0.1, [1600, 1400, 1300, 1500] + [1500] * 12)]
    assert parse_csv(samples_to_csv(original)) == original
