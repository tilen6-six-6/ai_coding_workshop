from loginspect.parsers.snapshot_text import SnapshotTextParser


def test_parses_all_snapshots(sample_log):
    assert len(sample_log) == 2


def test_parses_fields(sample_log):
    first = sample_log.snapshots[0]
    assert first.fields["service_status"] == "OK"
    assert first.as_int("temperature") == 3698
    assert first.as_int("veeprom_error_cntr") == 0


def test_timestamp_parsed(sample_log):
    assert sample_log.snapshots[0].timestamp is not None
    assert sample_log.snapshots[0].timestamp.year == 2026


def test_keys_union(sample_log):
    assert "main_sw" in sample_log.keys
    assert "diverter_state" in sample_log.keys


def test_series(sample_log):
    series = sample_log.series("service_status")
    assert series == [(0, "OK"), (1, "ERROR")]


def test_sniff_positive(sample_log_path):
    with open(sample_log_path) as fh:
        assert SnapshotTextParser().sniff(fh.read(200))


def test_sniff_negative():
    assert not SnapshotTextParser().sniff("just some text\nno timestamp")


def test_as_int_hex(tmp_path):
    p = tmp_path / "hex.txt"
    p.write_text("[2026-01-01 00:00:00]\n  reg: 0xFF\n")
    log = SnapshotTextParser().parse(str(p))
    assert log.snapshots[0].as_int("reg") == 255
