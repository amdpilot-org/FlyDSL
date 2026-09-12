import json

from flydsl.tools.isa_analyzer import analyze_isa, main


SAMPLE = """
kernel0:
  v_mfma_f32_16x16x16_f16 a[0:3], v0, v1, a[0:3]
  buffer_load_dwordx4 v[4:7], v2, s[0:3], 0 offen
  ds_read_b128 v[8:11], v3
  s_waitcnt vmcnt(0) lgkmcnt(0)
  buffer_store_dwordx4 v[4:7], v2, s[0:3], 0 offen
  s_barrier
.amdhsa_kernel kernel0
  .amdhsa_group_segment_fixed_size 32768
  .amdhsa_private_segment_fixed_size 0
  .amdhsa_next_free_vgpr 96
  .amdhsa_next_free_sgpr 40
  .amdhsa_wavefront_size32 0
.end_amdhsa_kernel
"""


def test_analyze_final_isa_counts_instructions_and_resources():
    report = analyze_isa(SAMPLE)
    assert report["instruction_count"] == 6
    assert report["families"] == {
        "mfma_wmma": 1,
        "vmem_load": 1,
        "vmem_store": 1,
        "lds_read": 1,
        "lds_write": 0,
        "waitcnt": 1,
        "barrier": 1,
    }
    assert report["kernels"]["kernel0"] == {
        "lds_bytes": 32768,
        "scratch_bytes": 0,
        "next_free_vgpr": 96,
        "next_free_sgpr": 40,
        "wavefront_size32": 0,
    }


def test_comments_labels_and_malformed_metadata_do_not_inflate_claims():
    report = analyze_isa(
        """
// v_mfma_f32_16x16x16_f16 and buffer_load_dwordx4 are commentary
.text
label: // ds_read_b128
  s_nop 0 /* buffer_store_dword */
.amdhsa_kernel odd
  .amdhsa_next_free_vgpr unknown
.end_amdhsa_kernel
"""
    )
    assert report["instruction_count"] == 1
    assert report["opcodes"] == {"s_nop": 1}
    assert report["kernels"] == {"odd": {}}


def test_cli_emits_machine_readable_json(tmp_path, capsys):
    isa = tmp_path / "kernel.s"
    isa.write_text(SAMPLE)
    assert main([str(isa)]) == 0
    assert json.loads(capsys.readouterr().out)["families"]["mfma_wmma"] == 1
