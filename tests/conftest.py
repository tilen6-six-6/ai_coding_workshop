"""Shared pytest fixtures."""

import textwrap

import pytest

from loginspect.parsers.snapshot_text import SnapshotTextParser

SAMPLE_LOG = textwrap.dedent(
    """\
    [2026-06-11 15:25:55.003]
      main_sw: DW5060-GCU-P_MAIN
      service_state: IDLE
      service_status: OK
      temperature: 3698
      veeprom_error_cntr: 0
      bldc_status_stmcsdk_faults_active: NONE
      diverter_state: POS_0

    [2026-06-11 15:25:56.003]
      main_sw: DW5060-GCU-P_MAIN
      service_state: RUN
      service_status: ERROR
      temperature: 12000
      veeprom_error_cntr: 2
      bldc_status_stmcsdk_faults_active: UNDER_VOLT
      diverter_state: GARBAGE
    """
)


@pytest.fixture()
def sample_log_path(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text(SAMPLE_LOG, encoding="utf-8")
    return str(p)


@pytest.fixture()
def sample_log(sample_log_path):
    return SnapshotTextParser().parse(sample_log_path)
