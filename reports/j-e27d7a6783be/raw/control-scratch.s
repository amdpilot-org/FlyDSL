	.amdgcn_target "amdgcn-amd-amdhsa-unknown-gfx950"
	.amdhsa_code_object_version 6
	.text
	.globl	flyc_bwd_dkdv
	.p2align	8
	.type	flyc_bwd_dkdv,@function
flyc_bwd_dkdv:
	s_load_dwordx4 s[68:71], s[0:1], 0x98
	s_mov_b64 s[42:43], s[0:1]
	s_mov_b32 s6, s3
	v_readfirstlane_b32 s7, v0
	s_waitcnt lgkmcnt(0)
	s_ashr_i32 s29, s71, 31
	s_mov_b32 s28, s71
	v_cvt_f32_u32_e32 v1, s28
	v_cvt_f32_u32_e32 v2, s29
	s_ashr_i32 s71, s70, 31
	s_or_b64 s[0:1], s[70:71], s[28:29]
	s_cmp_lg_u32 s1, 0
	s_cbranch_scc0 .LBB0_2
	v_fmamk_f32 v3, v2, 0x4f800000, v1
	v_rcp_f32_e32 v3, v3
	s_sub_u32 s0, 0, s28
	s_subb_u32 s1, 0, s29
	s_mov_b64 s[8:9], 0
	v_mul_f32_e32 v3, 0x5f7ffffc, v3
	v_mul_f32_e32 v4, 0x2f800000, v3
	v_trunc_f32_e32 v4, v4
	v_fmamk_f32 v3, v4, 0xcf800000, v3
	v_cvt_u32_f32_e32 v4, v4
	v_cvt_u32_f32_e32 v3, v3
	v_readfirstlane_b32 s3, v4
	v_readfirstlane_b32 s5, v3
	s_mul_hi_u32 s11, s0, s5
	s_mul_i32 s12, s0, s3
	s_mul_i32 s10, s1, s5
	s_add_i32 s11, s11, s12
	s_add_i32 s11, s11, s10
	s_mul_i32 s13, s0, s5
	s_mul_i32 s12, s5, s11
	s_mul_hi_u32 s14, s5, s13
	s_mul_hi_u32 s10, s5, s11
	s_add_u32 s12, s14, s12
	s_addc_u32 s10, 0, s10
	s_mul_hi_u32 s14, s3, s13
	s_mul_i32 s13, s3, s13
	s_add_u32 s12, s12, s13
	s_addc_u32 s10, s10, s14
	s_mul_hi_u32 s12, s3, s11
	s_addc_u32 s12, s12, 0
	s_mul_i32 s11, s3, s11
	s_add_u32 s10, s10, s11
	s_addc_u32 s11, 0, s12
	s_add_u32 s5, s5, s10
	s_addc_u32 s3, s3, s11
	s_mul_i32 s10, s0, s5
	s_mul_i32 s13, s0, s3
	s_mul_hi_u32 s0, s0, s5
	s_add_i32 s0, s0, s13
	s_mul_i32 s1, s1, s5
	s_add_i32 s0, s0, s1
	s_mul_hi_u32 s11, s3, s10
	s_mul_i32 s12, s3, s10
	s_mul_i32 s13, s5, s0
	s_mul_hi_u32 s10, s5, s10
	s_mul_hi_u32 s1, s5, s0
	s_add_u32 s10, s10, s13
	s_addc_u32 s1, 0, s1
	s_add_u32 s10, s10, s12
	s_addc_u32 s1, s1, s11
	s_mul_hi_u32 s10, s3, s0
	s_addc_u32 s10, s10, 0
	s_mul_i32 s0, s3, s0
	s_add_u32 s0, s1, s0
	s_addc_u32 s1, 0, s10
	s_add_u32 s0, s5, s0
	s_addc_u32 s1, s3, s1
	s_mul_i32 s5, s70, s1
	s_mul_hi_u32 s10, s70, s0
	s_mul_hi_u32 s3, s70, s1
	s_add_u32 s5, s10, s5
	s_addc_u32 s3, 0, s3
	s_mul_hi_u32 s10, s71, s0
	s_mul_i32 s0, s71, s0
	s_add_u32 s0, s5, s0
	s_addc_u32 s0, s3, s10
	s_mul_hi_u32 s3, s71, s1
	s_addc_u32 s3, s3, 0
	s_mul_i32 s1, s71, s1
	s_add_u32 s5, s0, s1
	s_addc_u32 s3, 0, s3
	s_mul_i32 s0, s28, s3
	s_mul_hi_u32 s1, s28, s5
	s_add_i32 s0, s1, s0
	s_mul_i32 s1, s29, s5
	s_add_i32 s10, s0, s1
	s_sub_i32 s11, s71, s10
	s_mul_i32 s0, s28, s5
	s_sub_u32 s12, s70, s0
	s_cselect_b64 s[0:1], -1, 0
	s_subb_u32 s11, s11, s29
	s_sub_u32 s13, s12, s28
	s_subb_u32 s11, s11, 0
	s_cmp_ge_u32 s11, s29
	s_cselect_b32 s14, -1, 0
	s_cmp_ge_u32 s13, s28
	s_cselect_b32 s13, -1, 0
	s_cmp_eq_u32 s11, s29
	s_cselect_b32 s11, s13, s14
	s_add_u32 s13, s5, 1
	s_addc_u32 s14, s3, 0
	s_add_u32 s15, s5, 2
	s_addc_u32 s16, s3, 0
	s_cmp_lg_u32 s11, 0
	s_cselect_b32 s11, s15, s13
	s_cselect_b32 s13, s16, s14
	s_cmp_lg_u64 s[0:1], 0
	s_subb_u32 s0, s71, s10
	s_cmp_ge_u32 s0, s29
	s_cselect_b32 s1, -1, 0
	s_cmp_ge_u32 s12, s28
	s_cselect_b32 s10, -1, 0
	s_cmp_eq_u32 s0, s29
	s_cselect_b32 s0, s10, s1
	s_cmp_lg_u32 s0, 0
	s_cselect_b32 s73, s13, s3
	s_cselect_b32 s72, s11, s5
	s_branch .LBB0_3
.LBB0_2:
	s_mov_b64 s[8:9], -1
.LBB0_3:
	s_and_b64 s[0:1], s[8:9], exec
	s_cselect_b32 s0, 1, 0
	s_cmp_lg_u32 s0, 1
	s_cbranch_scc1 .LBB0_5
	v_cvt_f32_u32_e32 v3, s28
	s_sub_i32 s0, 0, s28
	s_mov_b32 s73, 0
	v_rcp_iflag_f32_e32 v3, v3
	s_nop 0
	v_mul_f32_e32 v3, 0x4f7ffffe, v3
	v_cvt_u32_f32_e32 v3, v3
	s_nop 0
	v_readfirstlane_b32 s1, v3
	s_mul_i32 s0, s0, s1
	s_mul_hi_u32 s0, s1, s0
	s_add_i32 s1, s1, s0
	s_mul_hi_u32 s0, s70, s1
	s_mul_i32 s3, s0, s28
	s_sub_i32 s3, s70, s3
	s_add_i32 s1, s0, 1
	s_sub_i32 s5, s3, s28
	s_cmp_ge_u32 s3, s28
	s_cselect_b32 s0, s1, s0
	s_cselect_b32 s3, s5, s3
	s_add_i32 s1, s0, 1
	s_cmp_ge_u32 s3, s28
	s_cselect_b32 s72, s1, s0
.LBB0_5:
	s_ashr_i32 s3, s2, 31
	s_or_b64 s[0:1], s[2:3], s[28:29]
	s_cmp_lg_u32 s1, 0
	s_cbranch_scc0 .LBB0_7
	v_fmamk_f32 v1, v2, 0x4f800000, v1
	v_rcp_f32_e32 v1, v1
	s_sub_u32 s0, 0, s28
	s_subb_u32 s1, 0, s29
	s_mov_b64 s[8:9], 0
	v_mul_f32_e32 v1, 0x5f7ffffc, v1
	v_mul_f32_e32 v2, 0x2f800000, v1
	v_trunc_f32_e32 v2, v2
	v_fmamk_f32 v1, v2, 0xcf800000, v1
	v_cvt_u32_f32_e32 v2, v2
	v_cvt_u32_f32_e32 v1, v1
	v_readfirstlane_b32 s5, v2
	v_readfirstlane_b32 s10, v1
	s_mul_hi_u32 s12, s0, s10
	s_mul_i32 s13, s0, s5
	s_mul_i32 s11, s1, s10
	s_add_i32 s12, s12, s13
	s_add_i32 s12, s12, s11
	s_mul_i32 s14, s0, s10
	s_mul_i32 s13, s10, s12
	s_mul_hi_u32 s15, s10, s14
	s_mul_hi_u32 s11, s10, s12
	s_add_u32 s13, s15, s13
	s_addc_u32 s11, 0, s11
	s_mul_hi_u32 s15, s5, s14
	s_mul_i32 s14, s5, s14
	s_add_u32 s13, s13, s14
	s_addc_u32 s11, s11, s15
	s_mul_hi_u32 s13, s5, s12
	s_addc_u32 s13, s13, 0
	s_mul_i32 s12, s5, s12
	s_add_u32 s11, s11, s12
	s_addc_u32 s12, 0, s13
	s_add_u32 s10, s10, s11
	s_addc_u32 s5, s5, s12
	s_mul_i32 s11, s0, s10
	s_mul_i32 s14, s0, s5
	s_mul_hi_u32 s0, s0, s10
	s_add_i32 s0, s0, s14
	s_mul_i32 s1, s1, s10
	s_add_i32 s0, s0, s1
	s_mul_hi_u32 s12, s5, s11
	s_mul_i32 s13, s5, s11
	s_mul_i32 s14, s10, s0
	s_mul_hi_u32 s11, s10, s11
	s_mul_hi_u32 s1, s10, s0
	s_add_u32 s11, s11, s14
	s_addc_u32 s1, 0, s1
	s_add_u32 s11, s11, s13
	s_addc_u32 s1, s1, s12
	s_mul_hi_u32 s11, s5, s0
	s_addc_u32 s11, s11, 0
	s_mul_i32 s0, s5, s0
	s_add_u32 s0, s1, s0
	s_addc_u32 s1, 0, s11
	s_add_u32 s0, s10, s0
	s_addc_u32 s1, s5, s1
	s_mul_i32 s10, s2, s1
	s_mul_hi_u32 s11, s2, s0
	s_mul_hi_u32 s5, s2, s1
	s_add_u32 s10, s11, s10
	s_addc_u32 s5, 0, s5
	s_mul_hi_u32 s11, s3, s0
	s_mul_i32 s0, s3, s0
	s_add_u32 s0, s10, s0
	s_addc_u32 s0, s5, s11
	s_mul_hi_u32 s5, s3, s1
	s_addc_u32 s5, s5, 0
	s_mul_i32 s1, s3, s1
	s_add_u32 s10, s0, s1
	s_addc_u32 s5, 0, s5
	s_mul_i32 s0, s28, s5
	s_mul_hi_u32 s1, s28, s10
	s_add_i32 s0, s1, s0
	s_mul_i32 s1, s29, s10
	s_add_i32 s11, s0, s1
	s_sub_i32 s12, s3, s11
	s_mul_i32 s0, s28, s10
	s_sub_u32 s13, s2, s0
	s_cselect_b64 s[0:1], -1, 0
	s_subb_u32 s12, s12, s29
	s_sub_u32 s14, s13, s28
	s_subb_u32 s12, s12, 0
	s_cmp_ge_u32 s12, s29
	s_cselect_b32 s15, -1, 0
	s_cmp_ge_u32 s14, s28
	s_cselect_b32 s14, -1, 0
	s_cmp_eq_u32 s12, s29
	s_cselect_b32 s12, s14, s15
	s_add_u32 s14, s10, 1
	s_addc_u32 s15, s5, 0
	s_add_u32 s16, s10, 2
	s_addc_u32 s17, s5, 0
	s_cmp_lg_u32 s12, 0
	s_cselect_b32 s12, s16, s14
	s_cselect_b32 s14, s17, s15
	s_cmp_lg_u64 s[0:1], 0
	s_subb_u32 s0, s3, s11
	s_cmp_ge_u32 s0, s29
	s_cselect_b32 s1, -1, 0
	s_cmp_ge_u32 s13, s28
	s_cselect_b32 s11, -1, 0
	s_cmp_eq_u32 s0, s29
	s_cselect_b32 s0, s11, s1
	s_cmp_lg_u32 s0, 0
	s_cselect_b32 s75, s14, s5
	s_cselect_b32 s74, s12, s10
	s_branch .LBB0_8
.LBB0_7:
	s_mov_b64 s[8:9], -1
.LBB0_8:
	s_and_b64 s[0:1], s[8:9], exec
	s_cselect_b32 s0, 1, 0
	s_cmp_lg_u32 s0, 1
	s_cbranch_scc1 .LBB0_10
	v_cvt_f32_u32_e32 v1, s28
	s_sub_i32 s0, 0, s28
	s_mov_b32 s75, 0
	v_rcp_iflag_f32_e32 v1, v1
	s_nop 0
	v_mul_f32_e32 v1, 0x4f7ffffe, v1
	v_cvt_u32_f32_e32 v1, v1
	s_nop 0
	v_readfirstlane_b32 s1, v1
	s_mul_i32 s0, s0, s1
	s_mul_hi_u32 s0, s1, s0
	s_add_i32 s1, s1, s0
	s_mul_hi_u32 s0, s2, s1
	s_mul_i32 s5, s0, s28
	s_sub_i32 s5, s2, s5
	s_add_i32 s1, s0, 1
	s_sub_i32 s8, s5, s28
	s_cmp_ge_u32 s5, s28
	s_cselect_b32 s0, s1, s0
	s_cselect_b32 s5, s8, s5
	s_add_i32 s1, s0, 1
	s_cmp_ge_u32 s5, s28
	s_cselect_b32 s74, s1, s0
.LBB0_10:
	s_load_dwordx4 s[8:11], s[42:43], 0x68
	s_load_dwordx16 s[44:59], s[42:43], 0x20
	s_ashr_i32 s5, s4, 31
	s_mov_b32 s67, 0
	s_mov_b32 s0, 0
	s_waitcnt lgkmcnt(0)
	s_bfe_u32 s1, s8, 0x20001
	s_cbranch_scc0 .LBB0_12
	s_lshl_b64 s[12:13], s[4:5], 2
	s_add_u32 s12, s54, s12
	s_addc_u32 s13, s55, s13
	s_load_dword s0, s[12:13], 0x0
.LBB0_12:
	s_cmp_eq_u32 s1, 1
	s_cselect_b64 s[98:99], -1, 0
	s_add_i32 s12, s4, 1
	s_ashr_i32 s13, s12, 31
	s_cmp_lg_u32 s1, 1
	s_cbranch_scc1 .LBB0_14
	s_lshl_b64 s[14:15], s[12:13], 2
	s_add_u32 s14, s54, s14
	s_addc_u32 s15, s55, s15
	s_load_dword s67, s[14:15], 0x0
.LBB0_14:
	s_bfe_u32 s14, s8, 0x20003
	s_cmp_eq_u32 s14, 2
	s_cselect_b64 s[64:65], -1, 0
	s_cmp_lg_u32 s14, 2
	s_mov_b32 s36, 0
	s_mov_b32 s22, 0
	s_cbranch_scc1 .LBB0_16
	s_lshl_b64 s[20:21], s[4:5], 2
	s_add_u32 s20, s56, s20
	s_addc_u32 s21, s57, s21
	s_load_dword s22, s[20:21], 0x0
.LBB0_16:
	s_bfe_u32 s38, s8, 0x20009
	s_cbranch_scc0 .LBB0_18
	s_lshl_b64 s[20:21], s[4:5], 2
	s_add_u32 s20, s58, s20
	s_addc_u32 s21, s59, s21
	s_load_dword s36, s[20:21], 0x0
.LBB0_18:
	s_cmp_eq_u32 s38, 1
	s_mov_b32 s37, 0
	s_cselect_b64 s[20:21], -1, 0
	s_cmp_lg_u32 s38, 1
	s_mov_b32 s40, 0
	s_cbranch_scc1 .LBB0_20
	s_lshl_b64 s[12:13], s[12:13], 2
	s_add_u32 s12, s58, s12
	s_addc_u32 s13, s59, s13
	s_load_dword s40, s[12:13], 0x0
.LBB0_20:
	s_bfe_u32 s39, s8, 0x2000b
	s_cmp_eq_u32 s39, 2
	s_cselect_b64 s[30:31], -1, 0
	s_cmp_lg_u32 s39, 2
	s_cbranch_scc1 .LBB0_22
	s_load_dwordx2 s[12:13], s[42:43], 0x60
	s_lshl_b64 s[34:35], s[4:5], 2
	s_waitcnt lgkmcnt(0)
	s_add_u32 s12, s12, s34
	s_addc_u32 s13, s13, s35
	s_load_dword s37, s[12:13], 0x0
.LBB0_22:
	s_bitcmp1_b32 s8, 0
	s_cselect_b64 s[34:35], -1, 0
	s_cmp_eq_u32 s14, 1
	s_cselect_b64 s[96:97], -1, 0
	s_and_b64 s[14:15], s[96:97], s[34:35]
	s_ashr_i32 s13, s9, 31
	s_and_b64 s[14:15], s[14:15], exec
	s_cselect_b32 s14, 1, 0
	s_mov_b32 s12, s9
	s_mov_b32 s33, 0
	s_cmp_lg_u32 s14, 1
	s_mov_b32 s23, 0
	s_cbranch_scc1 .LBB0_24
	s_lshl_b64 s[14:15], s[12:13], 2
	s_add_u32 s14, s54, s14
	s_addc_u32 s15, s55, s15
	s_load_dword s23, s[14:15], 0x0
.LBB0_24:
	s_and_b64 s[14:15], s[64:65], s[34:35]
	s_and_b64 s[14:15], s[14:15], exec
	s_cselect_b32 s14, 1, 0
	s_cmp_lg_u32 s14, 1
	s_cbranch_scc1 .LBB0_26
	s_lshl_b64 s[12:13], s[12:13], 2
	s_add_u32 s12, s56, s12
	s_addc_u32 s13, s57, s13
	s_load_dword s33, s[12:13], 0x0
.LBB0_26:
	s_nop 0
	s_load_dwordx4 s[12:15], s[42:43], 0x80
	s_load_dwordx2 s[54:55], s[42:43], 0x90
	s_lshr_b32 s66, s7, 6
	s_mov_b64 s[92:93], 0
	s_mov_b64 s[94:95], 0
	s_waitcnt lgkmcnt(0)
	s_cmp_eq_u64 s[12:13], 0
	s_cbranch_scc1 .LBB0_28
	s_load_dwordx2 s[94:95], s[12:13], 0x0
.LBB0_28:
	s_cmp_eq_u64 s[14:15], 0
	s_cbranch_scc1 .LBB0_30
	s_load_dwordx2 s[92:93], s[14:15], 0x0
.LBB0_30:
	s_sub_i32 s7, s40, s36
	s_cmp_eq_u32 s38, 2
	s_cselect_b32 s14, s36, s11
	s_and_b64 s[12:13], s[20:21], exec
	s_cselect_b32 s26, s7, s14
	s_ashr_i32 s7, s6, 31
	s_ashr_i32 s27, s26, 31
	s_lshl_b64 s[12:13], s[6:7], 6
	v_mov_b64_e32 v[2:3], s[26:27]
	v_cmp_ge_u64_e32 vcc, s[12:13], v[2:3]
	s_cbranch_vccnz .LBB0_41
	s_bfe_i32 s14, s8, 0x10008
	s_mul_i32 s15, s11, s4
	s_and_b32 s20, s8, 0x100
	s_and_b32 s14, s14, s15
	s_cmp_eq_u32 s39, 1
	s_load_dwordx4 s[16:19], s[42:43], 0xa8
	s_cselect_b32 s21, s36, s14
	s_and_b64 s[14:15], s[30:31], exec
	s_cselect_b32 s27, s37, s21
	s_cmp_eq_u32 s20, 0
	s_mul_i32 s14, s74, s29
	s_mul_hi_u32 s15, s74, s28
	s_cselect_b32 s36, s4, 0
	s_add_i32 s14, s15, s14
	s_mul_i32 s15, s75, s28
	s_add_i32 s14, s14, s15
	s_mul_i32 s15, s74, s28
	s_load_dwordx16 s[76:91], s[42:43], 0xf8
	s_sub_u32 s37, s2, s15
	v_and_b32_e32 v4, 15, v0
	s_subb_u32 s38, s3, s14
	v_lshrrev_b32_e32 v2, 6, v0
	s_ashr_i32 s28, s36, 31
	s_ashr_i32 s29, s27, 31
	s_waitcnt lgkmcnt(0)
	s_ashr_i32 s31, s16, 31
	s_cmp_eq_u32 s26, 0
	v_lshl_or_b32 v1, v2, 4, v4
	v_mov_b32_e32 v191, 0
	s_mov_b32 s7, 0
	v_bfe_u32 v184, v0, 4, 2
	s_mov_b32 s30, s16
	s_cselect_b64 s[40:41], -1, 0
	s_ashr_i32 s25, s17, 31
	s_mov_b32 s24, s17
	v_or_b32_e32 v182, s12, v1
	v_cmp_lt_i64_e64 s[2:3], s[72:73], 1
	s_and_b64 vcc, exec, s[2:3]
	s_mov_b64 s[56:57], s[76:77]
	s_mov_b64 s[58:59], s[78:79]
	s_mov_b64 s[62:63], s[82:83]
	s_mov_b64 s[2:3], exec
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s56, 0
	v_writelane_b32 v1, s57, 1
	v_writelane_b32 v1, s58, 2
	v_writelane_b32 v1, s59, 3
	v_writelane_b32 v1, s60, 4
	v_writelane_b32 v1, s61, 5
	v_writelane_b32 v1, s62, 6
	v_writelane_b32 v1, s63, 7
	v_writelane_b32 v1, s64, 8
	v_writelane_b32 v1, s65, 9
	v_writelane_b32 v1, s66, 10
	v_writelane_b32 v1, s67, 11
	v_writelane_b32 v1, s68, 12
	v_writelane_b32 v1, s69, 13
	v_writelane_b32 v1, s70, 14
	v_writelane_b32 v1, s71, 15
	scratch_store_dword off, v1, off offset:16
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[2:3]
	s_cbranch_vccnz .LBB0_39
	s_mov_b64 s[2:3], exec
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s44, 0
	v_writelane_b32 v1, s45, 1
	v_writelane_b32 v1, s46, 2
	v_writelane_b32 v1, s47, 3
	v_writelane_b32 v1, s48, 4
	v_writelane_b32 v1, s49, 5
	v_writelane_b32 v1, s50, 6
	v_writelane_b32 v1, s51, 7
	v_writelane_b32 v1, s52, 8
	v_writelane_b32 v1, s53, 9
	v_writelane_b32 v1, s54, 10
	v_writelane_b32 v1, s55, 11
	v_writelane_b32 v1, s56, 12
	v_writelane_b32 v1, s57, 13
	v_writelane_b32 v1, s58, 14
	v_writelane_b32 v1, s59, 15
	scratch_store_dword off, v1, off offset:80
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[2:3]
	s_load_dwordx4 s[44:47], s[42:43], 0x0
	s_load_dwordx2 s[2:3], s[42:43], 0x10
	v_mov_b32_e32 v183, s13
	v_lshlrev_b32_e32 v190, 3, v184
	s_mov_b64 s[12:13], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s42, 0
	v_writelane_b32 v1, s43, 1
	scratch_store_dword off, v1, off offset:324
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[12:13]
	s_mov_b64 s[76:77], s[54:55]
	s_load_dwordx16 s[48:63], s[42:43], 0xb8
	s_waitcnt lgkmcnt(0)
	s_sub_i32 s15, s30, s58
	s_and_b64 s[12:13], s[40:41], exec
	s_mul_i32 s14, s58, s26
	s_cselect_b32 s12, 0, s15
	s_add_i32 s39, s12, s14
	s_mul_i32 s12, s54, s28
	s_mul_hi_u32 s13, s54, s36
	s_mul_i32 s15, s37, s57
	s_mul_hi_u32 s20, s37, s56
	s_add_i32 s12, s13, s12
	s_mul_i32 s13, s55, s36
	s_add_i32 s15, s20, s15
	s_mul_i32 s20, s38, s56
	s_add_i32 s12, s12, s13
	s_mul_i32 s13, s54, s36
	s_add_i32 s15, s15, s20
	s_mul_i32 s20, s37, s56
	s_add_u32 s13, s20, s13
	s_addc_u32 s15, s15, s12
	s_mul_i32 s12, s58, s29
	s_mul_hi_u32 s20, s58, s27
	s_add_i32 s12, s20, s12
	s_mul_i32 s20, s59, s27
	s_add_i32 s20, s12, s20
	s_mul_i32 s12, s58, s27
	s_add_u32 s12, s13, s12
	s_addc_u32 s13, s15, s20
	s_lshl_b64 s[12:13], s[12:13], 1
	s_add_u32 s80, s12, s46
	s_mov_b64 s[14:15], exec
	s_mov_b64 exec, 15
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s44, 0
	v_writelane_b32 v1, s45, 1
	v_writelane_b32 v1, s46, 2
	v_writelane_b32 v1, s47, 3
	scratch_store_dword off, v1, off offset:152
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[14:15]
	s_addc_u32 s42, s13, s47
	s_mov_b64 s[46:47], s[10:11]
	s_mov_b32 s54, s23
	s_mov_b64 s[56:57], exec
	s_mov_b64 s[44:45], s[8:9]
	s_mov_b32 s86, s18
	s_mov_b32 s43, s22
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v1, off offset:404
	scratch_load_dword v1, off, off offset:16
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v1, 0
	v_readlane_b32 s9, v1, 1
	v_readlane_b32 s10, v1, 2
	v_readlane_b32 s11, v1, 3
	v_readlane_b32 s12, v1, 4
	v_readlane_b32 s13, v1, 5
	v_readlane_b32 s14, v1, 6
	v_readlane_b32 s15, v1, 7
	v_readlane_b32 s16, v1, 8
	v_readlane_b32 s17, v1, 9
	v_readlane_b32 s18, v1, 10
	v_readlane_b32 s19, v1, 11
	v_readlane_b32 s20, v1, 12
	v_readlane_b32 s21, v1, 13
	v_readlane_b32 s22, v1, 14
	v_readlane_b32 s23, v1, 15
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[56:57]
	s_sub_i32 s20, s24, s8
	s_mov_b32 s12, s26
	s_mov_b64 s[18:19], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s12, 0
	v_writelane_b32 v1, s13, 1
	scratch_store_dword off, v1, off offset:348
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[18:19]
	s_mul_i32 s21, s8, s26
	s_mov_b64 s[12:13], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s40, 0
	v_writelane_b32 v1, s41, 1
	scratch_store_dword off, v1, off offset:380
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[12:13]
	s_and_b64 s[12:13], s[40:41], exec
	s_cselect_b32 s12, 0, s20
	s_add_i32 s20, s12, s21
	s_mov_b64 s[12:13], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s28, 0
	scratch_store_dword off, v1, off offset:376
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[12:13]
	s_mul_i32 s12, s60, s28
	s_mul_hi_u32 s13, s60, s36
	s_add_i32 s12, s13, s12
	s_mul_i32 s13, s61, s36
	s_add_i32 s12, s12, s13
	s_mov_b64 s[18:19], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s36, 0
	scratch_store_dword off, v1, off offset:360
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[18:19]
	s_mul_i32 s21, s37, s63
	s_mul_hi_u32 s28, s37, s62
	s_add_i32 s21, s28, s21
	s_mul_i32 s28, s38, s62
	s_mul_i32 s13, s60, s36
	s_add_i32 s21, s21, s28
	s_mul_i32 s28, s37, s62
	s_add_u32 s13, s28, s13
	s_addc_u32 s21, s21, s12
	s_mov_b64 s[18:19], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s29, 0
	scratch_store_dword off, v1, off offset:368
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[18:19]
	s_mul_i32 s12, s8, s29
	s_mul_hi_u32 s28, s8, s27
	s_add_i32 s12, s28, s12
	s_mul_i32 s28, s9, s27
	s_add_i32 s28, s12, s28
	s_mov_b64 s[18:19], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v1, off offset:404
	v_writelane_b32 v1, s27, 0
	scratch_store_dword off, v1, off offset:356
	scratch_load_dword v1, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[18:19]
	s_mul_i32 s12, s8, s27
	s_add_u32 s12, s13, s12
	s_addc_u32 s13, s21, s28
	s_lshl_b64 s[12:13], s[12:13], 1
	s_add_u32 s12, s12, s2
	v_mul_lo_u32 v5, s58, v182
	s_addc_u32 s2, s13, s3
	s_and_b32 s81, s42, 0xffff
	s_lshl_b32 s82, s39, 1
	s_mov_b32 s83, 0x27000
	v_add_lshl_u32 v1, v5, v190, 1
	buffer_load_dwordx4 v[20:23], v1, s[80:83], 0 offen
	v_cmp_gt_i64_e32 vcc, s[30:31], v[190:191]
	v_mov_b32_e32 v1, 0xffff
	v_or_b32_e32 v6, 1, v190
	v_mov_b32_e32 v7, s7
	v_cndmask_b32_e32 v24, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[6:7]
	v_mov_b32_e32 v3, 0xffff0000
	v_mov_b32_e32 v9, s7
	v_cndmask_b32_e32 v25, 0, v3, vcc
	v_or_b32_e32 v8, v24, v25
	v_accvgpr_write_b32 a6, v8
	v_or_b32_e32 v8, 2, v190
	v_cmp_gt_i64_e32 vcc, s[30:31], v[8:9]
	v_or_b32_e32 v10, 3, v190
	v_mov_b32_e32 v11, s7
	v_cndmask_b32_e32 v26, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[10:11]
	v_or_b32_e32 v12, 4, v190
	v_mov_b32_e32 v13, s7
	v_cndmask_b32_e32 v27, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[12:13]
	v_or_b32_e32 v14, 5, v190
	v_mov_b32_e32 v15, s7
	v_cndmask_b32_e32 v28, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[14:15]
	v_mov_b32_e32 v17, s7
	v_or_b32_e32 v18, 7, v190
	v_cndmask_b32_e32 v29, 0, v3, vcc
	v_or_b32_e32 v16, v28, v29
	v_accvgpr_write_b32 a106, v16
	v_or_b32_e32 v16, 6, v190
	v_cmp_gt_i64_e32 vcc, s[30:31], v[16:17]
	v_mov_b32_e32 v19, s7
	v_or_b32_e32 v57, v26, v27
	v_cndmask_b32_e32 v30, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[18:19]
	v_or_b32_e32 v76, 36, v190
	v_mov_b32_e32 v77, s7
	v_cndmask_b32_e32 v31, 0, v3, vcc
	v_or_b32_e32 v33, v30, v31
	v_accvgpr_write_b32 a3, v33
	v_or_b32_e32 v78, 37, v190
	v_mov_b32_e32 v79, s7
	v_or_b32_e32 v80, 38, v190
	v_mov_b32_e32 v81, s7
	v_or_b32_e32 v82, 39, v190
	v_mov_b32_e32 v83, s7
	v_or_b32_e32 v84, 64, v190
	v_mov_b32_e32 v85, s7
	v_or_b32_e32 v86, 0x41, v190
	v_mov_b32_e32 v87, s7
	v_or_b32_e32 v88, 0x42, v190
	v_mov_b32_e32 v89, s7
	v_or_b32_e32 v90, 0x43, v190
	v_mov_b32_e32 v91, s7
	v_or_b32_e32 v92, 0x44, v190
	v_mov_b32_e32 v93, s7
	v_or_b32_e32 v94, 0x45, v190
	v_mov_b32_e32 v95, s7
	v_or_b32_e32 v96, 0x46, v190
	v_mov_b32_e32 v97, s7
	v_or_b32_e32 v98, 0x47, v190
	v_mov_b32_e32 v99, s7
	v_or_b32_e32 v100, 0x60, v190
	v_mov_b32_e32 v101, s7
	v_or_b32_e32 v102, 0x61, v190
	v_mov_b32_e32 v103, s7
	v_or_b32_e32 v104, 0x62, v190
	v_mov_b32_e32 v105, s7
	v_or_b32_e32 v106, 0x63, v190
	v_mov_b32_e32 v107, s7
	v_or_b32_e32 v108, 0x64, v190
	v_mov_b32_e32 v109, s7
	v_or_b32_e32 v110, 0x65, v190
	v_mov_b32_e32 v111, s7
	v_or_b32_e32 v112, 0x66, v190
	v_mov_b32_e32 v113, s7
	v_or_b32_e32 v114, 0x67, v190
	v_mov_b32_e32 v115, s7
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v23, v30, v23, v31 bitop3:0xc8
	v_bitop3_b32 v22, v28, v22, v29 bitop3:0xc8
	v_bitop3_b32 v21, v26, v21, v27 bitop3:0xc8
	v_bitop3_b32 v20, v24, v20, v25 bitop3:0xc8
	v_accvgpr_write_b32 a8, v20
	v_accvgpr_write_b32 a9, v21
	v_accvgpr_write_b32 a10, v22
	v_accvgpr_write_b32 a11, v23
	v_or_b32_e32 v20, 32, v190
	v_add_lshl_u32 v22, v5, v20, 1
	buffer_load_dwordx4 v[28:31], v22, s[80:83], 0 offen
	v_mov_b32_e32 v21, s7
	v_cmp_gt_i64_e32 vcc, s[30:31], v[20:21]
	v_or_b32_e32 v22, 33, v190
	v_mov_b32_e32 v23, s7
	v_cndmask_b32_e32 v32, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[22:23]
	v_mov_b32_e32 v25, s7
	v_or_b32_e32 v26, 35, v190
	v_cndmask_b32_e32 v33, 0, v3, vcc
	v_or_b32_e32 v24, v32, v33
	v_accvgpr_write_b32 a26, v24
	v_or_b32_e32 v24, 34, v190
	v_cmp_gt_i64_e32 vcc, s[30:31], v[24:25]
	v_mov_b32_e32 v27, s7
	v_or_b32_e32 v116, 0x80, v190
	v_cndmask_b32_e32 v34, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[26:27]
	v_mov_b32_e32 v117, s7
	v_or_b32_e32 v118, 0x81, v190
	v_cndmask_b32_e32 v35, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[76:77]
	v_or_b32_e32 v37, v34, v35
	v_accvgpr_write_b32 a1, v37
	v_cndmask_b32_e32 v36, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[78:79]
	v_mov_b32_e32 v119, s7
	v_or_b32_e32 v120, 0x82, v190
	v_cndmask_b32_e32 v37, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[80:81]
	v_or_b32_e32 v62, v36, v37
	v_mov_b32_e32 v121, s7
	v_cndmask_b32_e32 v38, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[82:83]
	v_or_b32_e32 v122, 0x83, v190
	v_mov_b32_e32 v123, s7
	v_cndmask_b32_e32 v39, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[84:85]
	v_or_b32_e32 v63, v38, v39
	v_or_b32_e32 v126, 0x84, v190
	v_mov_b32_e32 v127, s7
	v_or_b32_e32 v128, 0x85, v190
	v_mov_b32_e32 v129, s7
	v_or_b32_e32 v130, 0x86, v190
	v_mov_b32_e32 v131, s7
	v_or_b32_e32 v132, 0x87, v190
	v_mov_b32_e32 v133, s7
	v_or_b32_e32 v134, 0xa0, v190
	v_mov_b32_e32 v135, s7
	v_or_b32_e32 v136, 0xa1, v190
	v_mov_b32_e32 v137, s7
	v_or_b32_e32 v138, 0xa2, v190
	v_mov_b32_e32 v139, s7
	v_or_b32_e32 v140, 0xa3, v190
	v_mov_b32_e32 v141, s7
	v_or_b32_e32 v142, 0xa4, v190
	v_mov_b32_e32 v143, s7
	v_or_b32_e32 v144, 0xa5, v190
	v_mov_b32_e32 v145, s7
	v_or_b32_e32 v146, 0xa6, v190
	v_mov_b32_e32 v147, s7
	v_or_b32_e32 v148, 0xa7, v190
	v_mov_b32_e32 v149, s7
	v_or_b32_e32 v150, 0xc0, v190
	v_mov_b32_e32 v151, s7
	v_or_b32_e32 v152, 0xc1, v190
	v_mov_b32_e32 v153, s7
	v_or_b32_e32 v154, 0xc2, v190
	v_mov_b32_e32 v155, s7
	v_or_b32_e32 v156, 0xc3, v190
	v_mov_b32_e32 v157, s7
	v_or_b32_e32 v158, 0xc4, v190
	v_mov_b32_e32 v159, s7
	v_or_b32_e32 v160, 0xc5, v190
	v_mov_b32_e32 v161, s7
	v_or_b32_e32 v162, 0xc6, v190
	v_mov_b32_e32 v163, s7
	v_or_b32_e32 v164, 0xc7, v190
	v_mov_b32_e32 v165, s7
	v_or_b32_e32 v166, 0xe0, v190
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v31, v38, v31, v39 bitop3:0xc8
	v_bitop3_b32 v30, v36, v30, v37 bitop3:0xc8
	v_bitop3_b32 v29, v34, v29, v35 bitop3:0xc8
	v_bitop3_b32 v28, v32, v28, v33 bitop3:0xc8
	v_accvgpr_write_b32 a16, v28
	v_accvgpr_write_b32 a17, v29
	v_accvgpr_write_b32 a18, v30
	v_accvgpr_write_b32 a19, v31
	v_add_lshl_u32 v28, v5, v84, 1
	buffer_load_dwordx4 v[28:31], v28, s[80:83], 0 offen
	v_cndmask_b32_e32 v32, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[86:87]
	v_mov_b32_e32 v167, s7
	v_or_b32_e32 v168, 0xe1, v190
	v_cndmask_b32_e32 v33, 0, v3, vcc
	v_or_b32_e32 v34, v32, v33
	v_cmp_gt_i64_e32 vcc, s[30:31], v[88:89]
	v_accvgpr_write_b32 a24, v34
	v_mov_b32_e32 v169, s7
	v_cndmask_b32_e32 v34, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[90:91]
	v_or_b32_e32 v170, 0xe2, v190
	v_mov_b32_e32 v171, s7
	v_cndmask_b32_e32 v35, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[92:93]
	v_or_b32_e32 v65, v34, v35
	v_or_b32_e32 v172, 0xe3, v190
	v_cndmask_b32_e32 v36, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[94:95]
	v_mov_b32_e32 v173, s7
	v_or_b32_e32 v174, 0xe4, v190
	v_cndmask_b32_e32 v37, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[96:97]
	v_or_b32_e32 v70, v36, v37
	v_mov_b32_e32 v175, s7
	v_cndmask_b32_e32 v38, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[98:99]
	v_or_b32_e32 v176, 0xe5, v190
	v_mov_b32_e32 v177, s7
	v_cndmask_b32_e32 v39, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[100:101]
	v_or_b32_e32 v71, v38, v39
	v_or_b32_e32 v178, 0xe6, v190
	v_mov_b32_e32 v179, s7
	v_or_b32_e32 v180, 0xe7, v190
	v_mov_b32_e32 v181, s7
	s_mov_b32 s56, s8
	s_mov_b64 s[22:23], s[14:15]
	s_and_b32 s13, s2, 0xffff
	s_lshl_b32 s14, s20, 1
	s_mov_b32 s15, s83
	s_mov_b64 s[62:63], s[22:23]
	v_accvgpr_write_b32 a37, v57
	v_accvgpr_write_b32 a100, v62
	v_accvgpr_write_b32 a102, v70
	v_accvgpr_write_b32 a2, v184
	s_mov_b64 s[78:79], s[50:51]
	s_mov_b64 s[8:9], exec
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v31, v38, v31, v39 bitop3:0xc8
	v_bitop3_b32 v30, v36, v30, v37 bitop3:0xc8
	v_bitop3_b32 v29, v34, v29, v35 bitop3:0xc8
	v_bitop3_b32 v28, v32, v28, v33 bitop3:0xc8
	v_accvgpr_write_b32 a28, v28
	v_accvgpr_write_b32 a29, v29
	v_accvgpr_write_b32 a30, v30
	v_accvgpr_write_b32 a31, v31
	v_add_lshl_u32 v28, v5, v100, 1
	buffer_load_dwordx4 v[28:31], v28, s[80:83], 0 offen
	v_cndmask_b32_e32 v32, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[102:103]
	s_nop 1
	v_cndmask_b32_e32 v33, 0, v3, vcc
	v_or_b32_e32 v34, v32, v33
	v_cmp_gt_i64_e32 vcc, s[30:31], v[104:105]
	v_accvgpr_write_b32 a36, v34
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v28, v32, v28, v33 bitop3:0xc8
	v_cndmask_b32_e32 v34, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[106:107]
	s_nop 1
	v_cndmask_b32_e32 v35, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[108:109]
	v_bitop3_b32 v29, v34, v29, v35 bitop3:0xc8
	v_or_b32_e32 v73, v34, v35
	v_cndmask_b32_e32 v36, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[110:111]
	s_nop 1
	v_cndmask_b32_e32 v37, 0, v3, vcc
	v_or_b32_e32 v38, v36, v37
	v_cmp_gt_i64_e32 vcc, s[30:31], v[112:113]
	v_accvgpr_write_b32 a38, v38
	v_bitop3_b32 v30, v36, v30, v37 bitop3:0xc8
	v_cndmask_b32_e32 v38, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[114:115]
	s_nop 1
	v_cndmask_b32_e32 v39, 0, v3, vcc
	v_bitop3_b32 v31, v38, v31, v39 bitop3:0xc8
	v_accvgpr_write_b32 a43, v31
	v_accvgpr_write_b32 a42, v30
	v_accvgpr_write_b32 a41, v29
	v_accvgpr_write_b32 a40, v28
	v_add_lshl_u32 v28, v5, v116, 1
	buffer_load_dwordx4 v[28:31], v28, s[80:83], 0 offen
	v_cmp_gt_i64_e32 vcc, s[30:31], v[116:117]
	v_or_b32_e32 v41, v38, v39
	v_accvgpr_write_b32 a5, v41
	v_cndmask_b32_e32 v32, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[118:119]
	s_nop 1
	v_cndmask_b32_e32 v33, 0, v3, vcc
	v_or_b32_e32 v34, v32, v33
	v_cmp_gt_i64_e32 vcc, s[30:31], v[120:121]
	v_accvgpr_write_b32 a48, v34
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v28, v32, v28, v33 bitop3:0xc8
	v_cndmask_b32_e32 v34, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[122:123]
	s_nop 1
	v_cndmask_b32_e32 v37, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[126:127]
	v_bitop3_b32 v29, v34, v29, v37 bitop3:0xc8
	v_or_b32_e32 v35, v34, v37
	v_cndmask_b32_e32 v38, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[128:129]
	v_accvgpr_write_b32 a7, v35
	s_nop 0
	v_cndmask_b32_e32 v39, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[130:131]
	v_bitop3_b32 v30, v38, v30, v39 bitop3:0xc8
	v_or_b32_e32 v36, v38, v39
	v_cndmask_b32_e32 v40, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[132:133]
	v_accvgpr_write_b32 a50, v36
	s_nop 0
	v_cndmask_b32_e32 v41, 0, v3, vcc
	v_bitop3_b32 v31, v40, v31, v41 bitop3:0xc8
	v_accvgpr_write_b32 a55, v31
	v_accvgpr_write_b32 a54, v30
	v_accvgpr_write_b32 a53, v29
	v_accvgpr_write_b32 a52, v28
	v_add_lshl_u32 v28, v5, v134, 1
	buffer_load_dwordx4 v[28:31], v28, s[80:83], 0 offen
	v_cmp_gt_i64_e32 vcc, s[30:31], v[134:135]
	v_or_b32_e32 v35, v40, v41
	s_nop 0
	v_cndmask_b32_e32 v32, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[136:137]
	s_nop 1
	v_cndmask_b32_e32 v33, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[138:139]
	v_or_b32_e32 v44, v32, v33
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v28, v32, v28, v33 bitop3:0xc8
	v_cndmask_b32_e32 v34, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[140:141]
	s_nop 1
	v_cndmask_b32_e32 v38, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[142:143]
	v_bitop3_b32 v29, v34, v29, v38 bitop3:0xc8
	v_or_b32_e32 v37, v34, v38
	v_cndmask_b32_e32 v39, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[144:145]
	s_nop 1
	v_cndmask_b32_e32 v40, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[146:147]
	v_bitop3_b32 v30, v39, v30, v40 bitop3:0xc8
	v_or_b32_e32 v36, v39, v40
	v_cndmask_b32_e32 v41, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[148:149]
	v_accvgpr_write_b32 a60, v36
	s_nop 0
	v_cndmask_b32_e32 v45, 0, v3, vcc
	v_bitop3_b32 v31, v41, v31, v45 bitop3:0xc8
	v_accvgpr_write_b32 a65, v31
	v_accvgpr_write_b32 a64, v30
	v_accvgpr_write_b32 a63, v29
	v_accvgpr_write_b32 a62, v28
	v_add_lshl_u32 v28, v5, v150, 1
	buffer_load_dwordx4 v[28:31], v28, s[80:83], 0 offen
	v_cmp_gt_i64_e32 vcc, s[30:31], v[150:151]
	v_or_b32_e32 v43, v41, v45
	v_add_lshl_u32 v5, v5, v166, 1
	v_cndmask_b32_e32 v32, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[152:153]
	s_nop 1
	v_cndmask_b32_e32 v33, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[154:155]
	v_or_b32_e32 v50, v32, v33
	s_nop 0
	v_cndmask_b32_e32 v34, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[156:157]
	s_nop 1
	v_cndmask_b32_e32 v38, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[158:159]
	v_or_b32_e32 v45, v34, v38
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v47, v34, v29, v38 bitop3:0xc8
	v_cndmask_b32_e32 v39, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[160:161]
	s_nop 1
	v_cndmask_b32_e32 v40, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[162:163]
	v_bitop3_b32 v48, v39, v30, v40 bitop3:0xc8
	v_or_b32_e32 v52, v39, v40
	v_cndmask_b32_e32 v41, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[164:165]
	s_nop 1
	v_cndmask_b32_e32 v46, 0, v3, vcc
	v_or_b32_e32 v51, v41, v46
	v_bitop3_b32 v49, v41, v31, v46 bitop3:0xc8
	v_bitop3_b32 v46, v32, v28, v33 bitop3:0xc8
	buffer_load_dwordx4 v[28:31], v5, s[80:83], 0 offen
	v_cmp_gt_i64_e32 vcc, s[30:31], v[166:167]
	s_mov_b64 s[80:81], s[52:53]
	s_nop 0
	v_cndmask_b32_e32 v5, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[168:169]
	s_nop 1
	v_cndmask_b32_e32 v32, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[170:171]
	v_or_b32_e32 v56, v5, v32
	s_nop 0
	v_cndmask_b32_e32 v33, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[172:173]
	s_nop 1
	v_cndmask_b32_e32 v34, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[174:175]
	v_or_b32_e32 v39, v33, v34
	v_accvgpr_write_b32 a25, v39
	v_cndmask_b32_e32 v38, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[176:177]
	s_nop 1
	v_cndmask_b32_e32 v39, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[178:179]
	v_or_b32_e32 v36, v38, v39
	v_accvgpr_write_b32 a74, v36
	v_cndmask_b32_e32 v40, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[30:31], v[180:181]
	s_nop 1
	v_cndmask_b32_e32 v41, 0, v3, vcc
	v_or_b32_e32 v53, v40, v41
	v_cmp_gt_i64_e32 vcc, s[24:25], v[190:191]
	v_accvgpr_write_b32 a27, v53
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v41, v40, v31, v41 bitop3:0xc8
	v_bitop3_b32 v40, v38, v30, v39 bitop3:0xc8
	v_bitop3_b32 v38, v5, v28, v32 bitop3:0xc8
	v_mul_lo_u32 v5, s56, v182
	v_add_lshl_u32 v28, v5, v190, 1
	v_bitop3_b32 v39, v33, v29, v34 bitop3:0xc8
	buffer_load_dwordx4 v[28:31], v28, s[12:15], 0 offen
	v_cndmask_b32_e32 v32, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[6:7]
	s_nop 1
	v_cndmask_b32_e32 v6, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[8:9]
	v_or_b32_e32 v34, v32, v6
	v_accvgpr_write_b32 a80, v34
	v_cndmask_b32_e32 v7, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[10:11]
	s_nop 1
	v_cndmask_b32_e32 v8, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[12:13]
	v_or_b32_e32 v61, v7, v8
	s_nop 0
	v_cndmask_b32_e32 v9, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[14:15]
	s_nop 1
	v_cndmask_b32_e32 v10, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[16:17]
	v_or_b32_e32 v12, v9, v10
	v_accvgpr_write_b32 a82, v12
	v_cndmask_b32_e32 v11, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[18:19]
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v10, v9, v30, v10 bitop3:0xc8
	v_cndmask_b32_e32 v12, 0, v3, vcc
	v_or_b32_e32 v67, v11, v12
	v_bitop3_b32 v11, v11, v31, v12 bitop3:0xc8
	v_bitop3_b32 v9, v7, v29, v8 bitop3:0xc8
	v_bitop3_b32 v8, v32, v28, v6 bitop3:0xc8
	v_add_lshl_u32 v6, v5, v20, 1
	v_accvgpr_write_b32 a87, v11
	v_accvgpr_write_b32 a86, v10
	v_accvgpr_write_b32 a85, v9
	v_accvgpr_write_b32 a84, v8
	buffer_load_dwordx4 v[6:9], v6, s[12:15], 0 offen
	v_cmp_gt_i64_e32 vcc, s[24:25], v[20:21]
	s_nop 1
	v_cndmask_b32_e32 v10, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[22:23]
	s_nop 1
	v_cndmask_b32_e32 v11, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[24:25]
	v_or_b32_e32 v74, v10, v11
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v20, v10, v6, v11 bitop3:0xc8
	v_cndmask_b32_e32 v12, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[26:27]
	v_add_lshl_u32 v6, v5, v84, 1
	s_nop 0
	v_cndmask_b32_e32 v13, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[76:77]
	v_bitop3_b32 v21, v12, v7, v13 bitop3:0xc8
	v_or_b32_e32 v69, v12, v13
	v_cndmask_b32_e32 v14, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[78:79]
	s_nop 1
	v_cndmask_b32_e32 v15, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[80:81]
	v_bitop3_b32 v22, v14, v8, v15 bitop3:0xc8
	v_or_b32_e32 v18, v14, v15
	v_cndmask_b32_e32 v16, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[82:83]
	s_nop 1
	v_cndmask_b32_e32 v17, 0, v3, vcc
	v_bitop3_b32 v23, v16, v9, v17 bitop3:0xc8
	buffer_load_dwordx4 v[6:9], v6, s[12:15], 0 offen
	v_cmp_gt_i64_e32 vcc, s[24:25], v[84:85]
	v_or_b32_e32 v75, v16, v17
	s_nop 0
	v_cndmask_b32_e32 v10, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[86:87]
	s_nop 1
	v_cndmask_b32_e32 v11, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[88:89]
	v_or_b32_e32 v82, v10, v11
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v24, v10, v6, v11 bitop3:0xc8
	v_cndmask_b32_e32 v12, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[90:91]
	v_add_lshl_u32 v6, v5, v100, 1
	s_nop 0
	v_cndmask_b32_e32 v13, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[92:93]
	v_bitop3_b32 v25, v12, v7, v13 bitop3:0xc8
	v_or_b32_e32 v77, v12, v13
	v_cndmask_b32_e32 v14, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[94:95]
	s_nop 1
	v_cndmask_b32_e32 v15, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[96:97]
	v_bitop3_b32 v26, v14, v8, v15 bitop3:0xc8
	v_or_b32_e32 v94, v14, v15
	v_cndmask_b32_e32 v16, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[98:99]
	s_nop 1
	v_cndmask_b32_e32 v17, 0, v3, vcc
	v_bitop3_b32 v27, v16, v9, v17 bitop3:0xc8
	buffer_load_dwordx4 v[6:9], v6, s[12:15], 0 offen
	v_cmp_gt_i64_e32 vcc, s[24:25], v[100:101]
	v_or_b32_e32 v83, v16, v17
	s_nop 0
	v_cndmask_b32_e32 v10, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[102:103]
	s_nop 1
	v_cndmask_b32_e32 v11, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[104:105]
	v_or_b32_e32 v90, v10, v11
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v30, v10, v6, v11 bitop3:0xc8
	v_cndmask_b32_e32 v12, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[106:107]
	v_add_lshl_u32 v6, v5, v116, 1
	s_nop 0
	v_cndmask_b32_e32 v13, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[108:109]
	v_bitop3_b32 v31, v12, v7, v13 bitop3:0xc8
	v_or_b32_e32 v85, v12, v13
	v_cndmask_b32_e32 v14, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[110:111]
	s_nop 1
	v_cndmask_b32_e32 v15, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[112:113]
	v_bitop3_b32 v32, v14, v8, v15 bitop3:0xc8
	v_or_b32_e32 v102, v14, v15
	v_cndmask_b32_e32 v16, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[114:115]
	s_nop 1
	v_cndmask_b32_e32 v17, 0, v3, vcc
	v_bitop3_b32 v33, v16, v9, v17 bitop3:0xc8
	buffer_load_dwordx4 v[6:9], v6, s[12:15], 0 offen
	v_cmp_gt_i64_e32 vcc, s[24:25], v[116:117]
	v_or_b32_e32 v91, v16, v17
	s_nop 0
	v_cndmask_b32_e32 v10, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[118:119]
	s_nop 1
	v_cndmask_b32_e32 v11, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[120:121]
	v_or_b32_e32 v98, v10, v11
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v6, v10, v6, v11 bitop3:0xc8
	v_cndmask_b32_e32 v12, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[122:123]
	s_nop 1
	v_cndmask_b32_e32 v13, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[126:127]
	v_bitop3_b32 v7, v12, v7, v13 bitop3:0xc8
	v_or_b32_e32 v93, v12, v13
	v_cndmask_b32_e32 v14, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[128:129]
	s_nop 1
	v_cndmask_b32_e32 v15, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[130:131]
	v_bitop3_b32 v8, v14, v8, v15 bitop3:0xc8
	v_or_b32_e32 v100, v14, v15
	v_cndmask_b32_e32 v16, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[132:133]
	s_nop 1
	v_cndmask_b32_e32 v17, 0, v3, vcc
	v_bitop3_b32 v9, v16, v9, v17 bitop3:0xc8
	v_accvgpr_write_b32 a111, v9
	v_accvgpr_write_b32 a110, v8
	v_accvgpr_write_b32 a109, v7
	v_accvgpr_write_b32 a108, v6
	v_add_lshl_u32 v6, v5, v134, 1
	buffer_load_dwordx4 v[6:9], v6, s[12:15], 0 offen
	v_cmp_gt_i64_e32 vcc, s[24:25], v[134:135]
	v_or_b32_e32 v99, v16, v17
	s_nop 0
	v_cndmask_b32_e32 v10, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[136:137]
	s_nop 1
	v_cndmask_b32_e32 v11, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[138:139]
	v_or_b32_e32 v106, v10, v11
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v110, v10, v6, v11 bitop3:0xc8
	v_cndmask_b32_e32 v12, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[140:141]
	v_add_lshl_u32 v6, v5, v150, 1
	v_add_lshl_u32 v5, v5, v166, 1
	v_cndmask_b32_e32 v13, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[142:143]
	v_bitop3_b32 v111, v12, v7, v13 bitop3:0xc8
	v_or_b32_e32 v101, v12, v13
	v_cndmask_b32_e32 v14, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[144:145]
	s_nop 1
	v_cndmask_b32_e32 v15, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[146:147]
	v_bitop3_b32 v112, v14, v8, v15 bitop3:0xc8
	v_or_b32_e32 v108, v14, v15
	v_cndmask_b32_e32 v16, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[148:149]
	s_nop 1
	v_cndmask_b32_e32 v17, 0, v3, vcc
	v_bitop3_b32 v113, v16, v9, v17 bitop3:0xc8
	buffer_load_dwordx4 v[6:9], v6, s[12:15], 0 offen
	v_cmp_gt_i64_e32 vcc, s[24:25], v[150:151]
	v_or_b32_e32 v107, v16, v17
	s_nop 0
	v_cndmask_b32_e32 v10, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[152:153]
	s_nop 1
	v_cndmask_b32_e32 v11, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[154:155]
	v_or_b32_e32 v114, v10, v11
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v118, v10, v6, v11 bitop3:0xc8
	v_cndmask_b32_e32 v12, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[156:157]
	s_nop 1
	v_cndmask_b32_e32 v13, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[158:159]
	v_bitop3_b32 v119, v12, v7, v13 bitop3:0xc8
	v_or_b32_e32 v109, v12, v13
	v_cndmask_b32_e32 v14, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[160:161]
	s_nop 1
	v_cndmask_b32_e32 v15, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[162:163]
	v_bitop3_b32 v120, v14, v8, v15 bitop3:0xc8
	v_or_b32_e32 v116, v14, v15
	v_cndmask_b32_e32 v16, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[164:165]
	s_nop 1
	v_cndmask_b32_e32 v17, 0, v3, vcc
	v_bitop3_b32 v121, v16, v9, v17 bitop3:0xc8
	buffer_load_dwordx4 v[6:9], v5, s[12:15], 0 offen
	s_add_u32 s12, s92, s76
	s_addc_u32 s13, s93, s77
	s_sub_i32 s14, s67, s0
	v_cmp_gt_i64_e32 vcc, s[24:25], v[166:167]
	s_cmp_eq_u32 s1, 2
	s_cselect_b32 s1, s0, s46
	v_cndmask_b32_e32 v5, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[168:169]
	s_and_b64 s[2:3], s[98:99], exec
	s_cselect_b32 s2, s14, s1
	v_cndmask_b32_e32 v10, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[170:171]
	s_mul_i32 s1, s46, s4
	s_and_b64 s[14:15], s[34:35], exec
	v_cndmask_b32_e32 v11, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[172:173]
	s_cselect_b32 s1, s1, 0
	s_and_b64 s[14:15], s[96:97], exec
	v_cndmask_b32_e32 v12, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[174:175]
	s_cselect_b32 s3, s0, s1
	s_and_b64 s[0:1], s[64:65], exec
	v_cndmask_b32_e32 v13, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[176:177]
	s_mul_i32 s0, s46, s45
	s_cselect_b32 s26, s43, s3
	v_cndmask_b32_e32 v14, 0, v3, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[178:179]
	s_cselect_b32 s3, s33, s0
	s_and_b64 s[0:1], s[96:97], exec
	v_cndmask_b32_e32 v1, 0, v1, vcc
	v_cmp_gt_i64_e32 vcc, s[24:25], v[180:181]
	s_cselect_b32 s3, s54, s3
	s_and_b64 s[0:1], s[34:35], exec
	v_cndmask_b32_e32 v3, 0, v3, vcc
	s_cselect_b32 s27, s3, s46
	s_cselect_b32 s18, 0, s5
	s_cselect_b32 s3, 0, s4
	s_ashr_i32 s22, s2, 31
	v_or_b32_e32 v123, v1, v3
	s_mul_i32 s0, s80, s22
	s_mul_hi_u32 s1, s80, s2
	s_add_i32 s0, s1, s0
	s_mul_i32 s1, s81, s2
	s_ashr_i32 s36, s26, 31
	s_add_i32 s1, s0, s1
	v_or_b32_e32 v115, v16, v17
	v_or_b32_e32 v122, v5, v10
	v_or_b32_e32 v117, v11, v12
	v_or_b32_e32 v124, v13, v14
	s_mul_i32 s0, s80, s2
	s_sub_u32 s5, s30, s80
	s_mov_b64 s[76:77], s[48:49]
	s_waitcnt vmcnt(0)
	v_bitop3_b32 v126, v5, v6, v10 bitop3:0xc8
	v_and_b32_e32 v6, 3, v0
	v_bitop3_b32 v129, v1, v9, v3 bitop3:0xc8
	v_lshrrev_b32_e32 v1, 2, v4
	v_mul_u32_u24_e32 v3, 0x220, v6
	v_lshl_add_u32 v3, v1, 7, v3
	v_mul_u32_u24_e32 v1, 0x220, v1
	v_lshl_add_u32 v1, v184, 7, v1
	v_lshlrev_b32_e32 v4, 2, v0
	v_bitop3_b32 v128, v13, v8, v14 bitop3:0xc8
	v_bitop3_b32 v127, v11, v7, v12 bitop3:0xc8
	v_or_b32_e32 v3, v3, v190
	v_and_or_b32 v1, v4, 12, v1
	v_mov_b32_e32 v7, s7
	s_mov_b64 exec, 3
	scratch_store_dword off, v4, off offset:404
	v_writelane_b32 v4, s30, 0
	v_writelane_b32 v4, s31, 1
	scratch_store_dword off, v4, off offset:332
	scratch_load_dword v4, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_subb_u32 s9, s31, s81
	s_mov_b64 s[50:51], s[10:11]
	s_mov_b64 s[54:55], s[62:63]
	s_sub_u32 s14, s24, s54
	s_mov_b64 s[10:11], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v4, off offset:404
	v_writelane_b32 v4, s24, 0
	v_writelane_b32 v4, s25, 1
	scratch_store_dword off, v4, off offset:340
	scratch_load_dword v4, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[10:11]
	s_subb_u32 s15, s25, s55
	s_cmp_eq_u32 s2, 0
	s_cselect_b32 s5, 0, s5
	s_cselect_b32 s9, 0, s9
	s_mul_hi_u32 s20, s76, s3
	s_mul_i32 s21, s76, s18
	s_cselect_b32 s28, 0, s14
	s_cselect_b32 s29, 0, s15
	s_add_u32 s0, s5, s0
	s_mul_i32 s19, s77, s3
	s_addc_u32 s1, s9, s1
	s_add_i32 s5, s20, s21
	s_add_i32 s5, s5, s19
	s_mul_i32 s14, s80, s36
	s_mul_hi_u32 s19, s80, s26
	s_lshl_b64 s[42:43], s[0:1], 1
	s_mul_i32 s0, s54, s22
	s_mul_hi_u32 s1, s54, s2
	s_mul_i32 s15, s81, s26
	s_add_i32 s14, s19, s14
	s_add_i32 s0, s1, s0
	s_mul_i32 s1, s55, s2
	s_add_i32 s14, s14, s15
	s_add_i32 s1, s0, s1
	s_mul_i32 s0, s54, s2
	s_add_u32 s0, s28, s0
	s_mul_i32 s18, s50, s18
	s_mul_hi_u32 s19, s50, s3
	s_mul_i32 s20, s54, s36
	s_mul_hi_u32 s21, s54, s26
	s_addc_u32 s1, s29, s1
	s_add_i32 s18, s19, s18
	s_mul_i32 s19, s51, s3
	s_add_i32 s20, s21, s20
	s_mul_i32 s21, s55, s26
	s_add_i32 s18, s18, s19
	s_mul_i32 s19, s50, s3
	s_add_i32 s20, s20, s21
	s_lshl_b64 s[50:51], s[0:1], 1
	s_add_u32 s0, s2, 31
	s_addc_u32 s1, s22, 0
	s_lshr_b64 s[0:1], s[0:1], 5
	s_add_u32 s0, s0, 1
	s_mul_i32 s97, s66, 0x440
	s_mul_i32 s34, s37, s73
	s_mul_hi_u32 s35, s37, s72
	s_addc_u32 s31, s1, 0
	s_and_b32 s30, s0, -2
	s_add_i32 s98, s97, 0x1100
	s_add_i32 s99, s97, 0x2200
	s_add_i32 s39, s97, 0x3300
	s_add_i32 s33, s97, 0x8800
	s_add_i32 s88, s97, 0x9900
	s_add_i32 s89, s97, 0xaa00
	s_add_i32 s40, s97, 0xbb00
	s_add_i32 s28, s97, 0x4400
	s_add_i32 s29, s97, 0x5500
	s_add_i32 s64, s97, 0x6600
	s_add_i32 s65, s97, 0x7700
	s_add_i32 s0, s97, 0xcc00
	s_add_i32 s1, s97, 0xdd00
	s_add_i32 s96, s97, 0xee00
	s_add_i32 s92, s97, 0xff00
	s_add_i32 s34, s35, s34
	s_mul_i32 s9, s76, s3
	s_mul_i32 s15, s80, s26
	s_mul_i32 s21, s54, s26
	s_mov_b32 s10, s54
	s_mov_b64 s[24:25], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v4, off offset:404
	v_writelane_b32 v4, s38, 0
	scratch_store_dword off, v4, off offset:372
	scratch_load_dword v4, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[24:25]
	s_mul_i32 s35, s38, s72
	s_add_i32 s34, s34, s35
	s_mov_b64 s[24:25], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v4, off offset:404
	v_writelane_b32 v4, s37, 0
	scratch_store_dword off, v4, off offset:364
	scratch_load_dword v4, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[24:25]
	s_mul_i32 s35, s37, s72
	s_add_u32 s16, s35, s74
	s_mov_b64 s[24:25], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v4, off offset:404
	v_writelane_b32 v4, s16, 0
	scratch_store_dword off, v4, off offset:244
	scratch_load_dword v4, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[24:25]
	s_addc_u32 s16, s34, s75
	s_mov_b64 s[24:25], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v4, off offset:404
	v_writelane_b32 v4, s16, 0
	scratch_store_dword off, v4, off offset:248
	scratch_load_dword v4, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[24:25]
	v_mov_b32_e32 v5, 0x3fb8aa3b
	s_mov_b32 s22, s86
	s_mov_b64 s[24:25], exec
	s_mov_b64 exec, 15
	scratch_store_dword off, v4, off offset:404
	v_writelane_b32 v4, s20, 0
	v_writelane_b32 v4, s21, 1
	v_writelane_b32 v4, s22, 2
	v_writelane_b32 v4, s23, 3
	scratch_store_dword off, v4, off offset:388
	scratch_load_dword v4, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[24:25]
	v_mul_f32_e32 v4, s86, v5
	s_add_u32 s9, s15, s9
	s_mov_b64 s[24:25], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s9, 0
	scratch_store_dword off, v8, off offset:252
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[24:25]
	s_addc_u32 s5, s14, s5
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s5, 0
	scratch_store_dword off, v8, off offset:256
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_add_u32 s5, s21, s19
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s5, 0
	scratch_store_dword off, v8, off offset:260
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_addc_u32 s5, s20, s18
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s5, 0
	scratch_store_dword off, v8, off offset:264
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_ashr_i32 s5, s27, 31
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s5, 0
	scratch_store_dword off, v8, off offset:268
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mul_hi_i32 s5, s3, s70
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s5, 0
	scratch_store_dword off, v8, off offset:272
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mul_i32 s5, s3, s70
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s5, 0
	scratch_store_dword off, v8, off offset:276
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mul_hi_i32 s5, s3, s27
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s27, 0
	scratch_store_dword off, v8, off offset:236
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mul_i32 s3, s3, s27
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s26, 0
	scratch_store_dword off, v8, off offset:232
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_add_u32 s3, s3, s26
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s36, 0
	scratch_store_dword off, v8, off offset:240
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_addc_u32 s5, s5, s36
	s_mul_i32 s9, s3, s71
	s_mul_hi_u32 s14, s3, s70
	s_add_i32 s9, s14, s9
	s_mul_i32 s5, s5, s70
	s_add_i32 s5, s9, s5
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s5, 0
	scratch_store_dword off, v8, off offset:280
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mul_i32 s3, s3, s70
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s3, 0
	scratch_store_dword off, v8, off offset:284
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_and_b32 s3, s44, 0x30000
	s_cselect_b64 s[8:9], 0, -1
	s_mov_b64 s[24:25], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s8, 0
	v_writelane_b32 v8, s9, 1
	scratch_store_dword off, v8, off offset:288
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[24:25]
	s_and_b64 s[8:9], s[8:9], exec
	s_cselect_b32 s5, 1, s70
	s_mul_hi_i32 s3, s2, s5
	s_mul_i32 s2, s2, s5
	s_lshl_b64 s[74:75], s[2:3], 2
	s_mul_i32 s2, s70, s4
	s_mov_b64 s[4:5], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s2, 0
	scratch_store_dword off, v8, off offset:296
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[4:5]
	s_add_i32 s4, s47, 3
	s_ashr_i32 s2, s4, 31
	s_lshr_b32 s2, s2, 30
	s_add_i32 s2, s4, s2
	s_ashr_i32 s8, s2, 2
	s_and_b32 s2, s2, -4
	s_cmp_lg_u32 s4, s2
	s_cselect_b64 s[2:3], -1, 0
	s_cmp_lt_i32 s4, 0
	s_cselect_b64 s[4:5], -1, 0
	s_and_b64 s[2:3], s[4:5], s[2:3]
	s_subb_u32 s93, s8, 0
	s_ashr_i32 s90, s93, 31
	s_mul_hi_i32 s2, s93, s46
	s_mov_b64 s[4:5], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s2, 0
	scratch_store_dword off, v8, off offset:300
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[4:5]
	s_mul_i32 s2, s93, s46
	s_mov_b64 s[4:5], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v8, off offset:404
	v_writelane_b32 v8, s2, 0
	scratch_store_dword off, v8, off offset:304
	scratch_load_dword v8, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[4:5]
	v_lshrrev_b32_e32 v8, 1, v0
	v_lshlrev_b32_e32 v0, 3, v0
	v_and_or_b32 v2, v8, 28, v2
	v_and_b32_e32 v0, 56, v0
	v_mul_lo_u32 v8, s80, v2
	v_or_b32_e32 v9, 64, v0
	v_or_b32_e32 v10, 0x80, v0
	v_or_b32_e32 v11, 0xc0, v0
	v_mul_lo_u32 v2, s10, v2
	v_add_lshl_u32 v97, v8, v0, 1
	v_add_lshl_u32 v12, v8, v9, 1
	v_add_lshl_u32 v59, v8, v10, 1
	v_add_lshl_u32 v62, v8, v11, 1
	v_add_lshl_u32 v68, v2, v0, 1
	v_add_lshl_u32 v95, v2, v9, 1
	v_add_lshl_u32 v10, v2, v10, 1
	v_add_lshl_u32 v11, v2, v11, 1
	s_lshl_b32 s2, s80, 6
	s_mov_b64 s[4:5], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v0, off offset:404
	v_writelane_b32 v0, s2, 0
	scratch_store_dword off, v0, off offset:308
	scratch_load_dword v0, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[4:5]
	s_lshl_b32 s2, s54, 6
	s_mov_b64 s[4:5], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v0, off offset:404
	v_writelane_b32 v0, s2, 0
	scratch_store_dword off, v0, off offset:312
	scratch_load_dword v0, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[4:5]
	v_lshlrev_b32_e32 v125, 1, v3
	v_lshrrev_b32_e32 v2, 30, v183
	v_mov_b32_e32 v3, s7
	v_lshl_add_u64 v[2:3], v[182:183], 0, v[2:3]
	v_ashrrev_i64 v[8:9], 2, v[2:3]
	v_and_b32_e32 v2, -4, v2
	s_cmp_lt_i32 s6, 0
	v_cmp_ne_u64_e32 vcc, v[182:183], v[2:3]
	s_cselect_b64 s[2:3], -1, 0
	s_and_b64 s[2:3], s[2:3], vcc
	v_cndmask_b32_e64 v0, 0, 1, s[2:3]
	v_sub_co_u32_e32 v2, vcc, v8, v0
	v_lshlrev_b32_e32 v34, 1, v1
	s_nop 0
	v_subbrev_co_u32_e32 v3, vcc, 0, v9, vcc
	v_lshl_add_u64 v[0:1], s[12:13], 0, v[2:3]
	v_accvgpr_write_b32 a0, v182
	s_add_i32 s46, s94, 0x9e3779b9
	s_add_i32 s47, s95, 0xbb67ae85
	s_add_i32 s34, s94, 0x3c6ef372
	s_add_i32 s35, s95, 0x76cf5d0a
	s_add_i32 s91, s94, 0xdaa66d2b
	s_add_i32 s66, s95, 0x32370b8f
	s_add_i32 s67, s94, 0x78dde6e4
	s_add_i32 s52, s95, 0xed9eba14
	s_add_i32 s53, s94, 0x1715609d
	s_add_i32 s56, s95, 0xa9066899
	s_add_i32 s57, s94, 0xb54cda56
	s_add_i32 s58, s95, 0x646e171e
	s_add_i32 s59, s94, 0x5384540f
	s_add_i32 s60, s95, 0x1fd5c5a3
	s_add_i32 s61, s94, 0xf1bbcdc8
	s_add_i32 s62, s95, 0xdb3d7428
	s_add_i32 s63, s94, 0x8ff34781
	s_add_i32 s36, s95, 0x96a522ad
	v_cmp_eq_u64_e64 s[2:3], 1, v[6:7]
	v_cmp_eq_u64_e64 s[4:5], 2, v[6:7]
	v_cmp_eq_u64_e64 s[6:7], 3, v[6:7]
	v_add_u32_e32 v28, 0x80, v125
	v_accvgpr_write_b32 a105, v1
	v_accvgpr_write_b32 a104, v0
	s_mov_b32 s70, s69
	s_mov_b32 s71, s69
	s_lshl_b32 s37, s80, 7
	s_lshl_b32 s38, s54, 7
	s_mul_i32 s8, s54, 0xc0
	s_mov_b64 s[10:11], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v0, off offset:404
	v_writelane_b32 v0, s8, 0
	scratch_store_dword off, v0, off offset:316
	scratch_load_dword v0, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[10:11]
	s_mov_b64 s[10:11], s[78:79]
	s_mov_b64 s[24:25], exec
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v0, off offset:404
	v_writelane_b32 v0, s8, 0
	v_writelane_b32 v0, s9, 1
	v_writelane_b32 v0, s10, 2
	v_writelane_b32 v0, s11, 3
	v_writelane_b32 v0, s12, 4
	v_writelane_b32 v0, s13, 5
	v_writelane_b32 v0, s14, 6
	v_writelane_b32 v0, s15, 7
	v_writelane_b32 v0, s16, 8
	v_writelane_b32 v0, s17, 9
	v_writelane_b32 v0, s18, 10
	v_writelane_b32 v0, s19, 11
	v_writelane_b32 v0, s20, 12
	v_writelane_b32 v0, s21, 13
	v_writelane_b32 v0, s22, 14
	v_writelane_b32 v0, s23, 15
	scratch_store_dword off, v0, off offset:168
	scratch_load_dword v0, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[24:25]
	s_mul_i32 s8, s80, 0xc0
	s_mov_b64 s[12:13], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v0, off offset:404
	v_writelane_b32 v0, s8, 0
	scratch_store_dword off, v0, off offset:320
	scratch_load_dword v0, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[12:13]
	v_mov_b32_e32 v0, v191
	v_mov_b32_e32 v1, v191
	v_mov_b32_e32 v2, v191
	v_accvgpr_write_b32 a4, v190
	v_mov_b32_e32 v3, v191
	s_mov_b64 s[54:55], 0
	s_mov_b32 s10, s42
	s_mov_b64 s[12:13], exec
	s_mov_b64 exec, 15
	scratch_store_dword off, v6, off offset:404
	v_writelane_b32 v6, s8, 0
	v_writelane_b32 v6, s9, 1
	v_writelane_b32 v6, s10, 2
	v_writelane_b32 v6, s11, 3
	scratch_store_dword off, v6, off
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[12:13]
	s_mov_b32 s82, s42
	s_mov_b32 s78, s50
	s_mov_b32 s79, s83
	s_mov_b32 s75, s83
	s_mov_b32 s41, 0xd2511f53
	s_mov_b32 s42, 0xcd9e8d57
	v_mov_b64_e32 v[176:177], v[2:3]
	v_mov_b64_e32 v[174:175], v[0:1]
	v_mov_b64_e32 v[184:185], v[2:3]
	v_mov_b64_e32 v[182:183], v[0:1]
	v_mov_b64_e32 v[192:193], v[2:3]
	v_mov_b64_e32 v[190:191], v[0:1]
	v_mov_b64_e32 v[200:201], v[2:3]
	v_mov_b64_e32 v[198:199], v[0:1]
	v_mov_b64_e32 v[208:209], v[2:3]
	v_mov_b64_e32 v[206:207], v[0:1]
	v_mov_b64_e32 v[216:217], v[2:3]
	v_mov_b64_e32 v[214:215], v[0:1]
	v_mov_b64_e32 v[224:225], v[2:3]
	v_mov_b64_e32 v[222:223], v[0:1]
	v_mov_b64_e32 v[228:229], v[2:3]
	v_mov_b64_e32 v[226:227], v[0:1]
	v_mov_b64_e32 v[232:233], v[2:3]
	v_mov_b64_e32 v[230:231], v[0:1]
	v_mov_b64_e32 v[236:237], v[2:3]
	v_mov_b64_e32 v[234:235], v[0:1]
	v_mov_b64_e32 v[240:241], v[2:3]
	v_mov_b64_e32 v[238:239], v[0:1]
	v_mov_b64_e32 v[244:245], v[2:3]
	v_mov_b64_e32 v[242:243], v[0:1]
	v_mov_b64_e32 v[248:249], v[2:3]
	v_mov_b64_e32 v[246:247], v[0:1]
	v_mov_b64_e32 v[252:253], v[2:3]
	v_mov_b64_e32 v[250:251], v[0:1]
	v_mov_b64_e32 v[132:133], v[2:3]
	v_mov_b64_e32 v[130:131], v[0:1]
	v_mov_b64_e32 v[136:137], v[2:3]
	v_mov_b64_e32 v[134:135], v[0:1]
	v_mov_b64_e32 v[140:141], v[2:3]
	v_mov_b64_e32 v[138:139], v[0:1]
	v_mov_b64_e32 v[144:145], v[2:3]
	v_mov_b64_e32 v[142:143], v[0:1]
	v_mov_b64_e32 v[148:149], v[2:3]
	v_mov_b64_e32 v[146:147], v[0:1]
	v_mov_b64_e32 v[152:153], v[2:3]
	v_mov_b64_e32 v[150:151], v[0:1]
	v_mov_b64_e32 v[156:157], v[2:3]
	v_mov_b64_e32 v[154:155], v[0:1]
	v_mov_b64_e32 v[160:161], v[2:3]
	v_mov_b64_e32 v[158:159], v[0:1]
	v_mov_b64_e32 v[164:165], v[2:3]
	v_mov_b64_e32 v[162:163], v[0:1]
	v_mov_b64_e32 v[168:169], v[2:3]
	v_mov_b64_e32 v[166:167], v[0:1]
	v_mov_b64_e32 v[172:173], v[2:3]
	v_mov_b64_e32 v[170:171], v[0:1]
	v_mov_b64_e32 v[180:181], v[2:3]
	v_mov_b64_e32 v[178:179], v[0:1]
	v_mov_b64_e32 v[188:189], v[2:3]
	v_mov_b64_e32 v[186:187], v[0:1]
	v_mov_b64_e32 v[196:197], v[2:3]
	v_mov_b64_e32 v[194:195], v[0:1]
	v_mov_b64_e32 v[204:205], v[2:3]
	v_mov_b64_e32 v[202:203], v[0:1]
	v_mov_b64_e32 v[212:213], v[2:3]
	v_mov_b64_e32 v[210:211], v[0:1]
	v_mov_b64_e32 v[220:221], v[2:3]
	v_mov_b64_e32 v[218:219], v[0:1]
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v6, off offset:404
	v_writelane_b32 v6, s72, 0
	v_writelane_b32 v6, s73, 1
	scratch_store_dword off, v6, off offset:144
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
.LBB0_33:
	s_cmp_eq_u32 s54, 0
	s_cbranch_scc1 .LBB0_35
	s_waitcnt vmcnt(0)
	s_barrier
.LBB0_35:
	s_mov_b32 m0, s97
	s_mov_b64 s[10:11], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:244
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[10:11]
	s_add_u32 s10, s8, s54
	s_mov_b64 s[12:13], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:248
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[12:13]
	s_addc_u32 s11, s8, s55
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:168
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	v_readlane_b32 s13, v6, 1
	v_readlane_b32 s14, v6, 2
	v_readlane_b32 s15, v6, 3
	v_readlane_b32 s16, v6, 4
	v_readlane_b32 s17, v6, 5
	v_readlane_b32 s18, v6, 6
	v_readlane_b32 s19, v6, 7
	v_readlane_b32 s20, v6, 8
	v_readlane_b32 s21, v6, 9
	v_readlane_b32 s22, v6, 10
	v_readlane_b32 s23, v6, 11
	v_readlane_b32 s24, v6, 12
	v_readlane_b32 s25, v6, 13
	v_readlane_b32 s26, v6, 14
	v_readlane_b32 s27, v6, 15
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mul_i32 s8, s10, s15
	s_mul_hi_u32 s9, s10, s14
	s_add_i32 s8, s9, s8
	s_mul_i32 s9, s11, s14
	s_add_i32 s9, s8, s9
	s_mul_i32 s8, s10, s14
	s_mov_b64 s[14:15], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:252
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[14:15]
	s_add_u32 s8, s12, s8
	s_mov_b64 s[14:15], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:256
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[14:15]
	s_addc_u32 s9, s12, s9
	s_lshl_b64 s[8:9], s[8:9], 1
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 15
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:152
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	v_readlane_b32 s13, v6, 1
	v_readlane_b32 s14, v6, 2
	v_readlane_b32 s15, v6, 3
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_add_u32 s80, s8, s12
	s_addc_u32 s8, s9, s13
	s_and_b32 s81, s8, 0xffff
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:16
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	v_readlane_b32 s13, v6, 1
	v_readlane_b32 s14, v6, 2
	v_readlane_b32 s15, v6, 3
	v_readlane_b32 s16, v6, 4
	v_readlane_b32 s17, v6, 5
	v_readlane_b32 s18, v6, 6
	v_readlane_b32 s19, v6, 7
	v_readlane_b32 s20, v6, 8
	v_readlane_b32 s21, v6, 9
	v_readlane_b32 s22, v6, 10
	v_readlane_b32 s23, v6, 11
	v_readlane_b32 s24, v6, 12
	v_readlane_b32 s25, v6, 13
	v_readlane_b32 s26, v6, 14
	v_readlane_b32 s27, v6, 15
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mov_b64 s[12:13], s[16:17]
	s_mul_i32 s8, s10, s13
	s_mul_hi_u32 s9, s10, s12
	s_add_i32 s8, s9, s8
	s_mul_i32 s9, s11, s12
	s_mov_b64 s[16:17], s[20:21]
	s_mov_b64 s[18:19], s[22:23]
	s_mov_b64 s[20:21], s[24:25]
	s_mov_b64 s[22:23], s[26:27]
	s_add_i32 s9, s8, s9
	s_mul_i32 s8, s10, s12
	s_mov_b64 s[14:15], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:260
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[14:15]
	s_add_u32 s8, s12, s8
	s_mov_b64 s[14:15], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:264
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[14:15]
	s_addc_u32 s9, s12, s9
	s_mov_b64 s[44:45], exec
	s_lshl_b64 s[8:9], s[8:9], 1
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:80
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	v_readlane_b32 s13, v6, 1
	v_readlane_b32 s14, v6, 2
	v_readlane_b32 s15, v6, 3
	v_readlane_b32 s16, v6, 4
	v_readlane_b32 s17, v6, 5
	v_readlane_b32 s18, v6, 6
	v_readlane_b32 s19, v6, 7
	v_readlane_b32 s20, v6, 8
	v_readlane_b32 s21, v6, 9
	v_readlane_b32 s22, v6, 10
	v_readlane_b32 s23, v6, 11
	v_readlane_b32 s24, v6, 12
	v_readlane_b32 s25, v6, 13
	v_readlane_b32 s26, v6, 14
	v_readlane_b32 s27, v6, 15
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[44:45]
	s_add_u32 s76, s8, s12
	s_addc_u32 s8, s9, s13
	s_and_b32 s77, s8, 0xffff
	s_mov_b64 s[12:13], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:276
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[12:13]
	s_add_u32 s8, s10, s8
	s_mov_b64 s[12:13], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:272
	s_waitcnt vmcnt(0)
	v_readlane_b32 s9, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[12:13]
	s_addc_u32 s9, s11, s9
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:268
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_mul_i32 s12, s8, s12
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:236
	s_waitcnt vmcnt(0)
	v_readlane_b32 s14, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_mul_hi_u32 s13, s8, s14
	s_add_i32 s12, s13, s12
	s_mul_i32 s9, s9, s14
	s_add_i32 s12, s12, s9
	s_mul_i32 s8, s8, s14
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:232
	s_waitcnt vmcnt(0)
	v_readlane_b32 s9, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_add_u32 s13, s8, s9
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:240
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_addc_u32 s12, s12, s8
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:284
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_add_u32 s14, s10, s8
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:280
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_addc_u32 s11, s11, s8
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:288
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	v_readlane_b32 s9, v6, 1
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_and_b64 s[8:9], s[8:9], exec
	s_cselect_b32 s9, s12, s11
	s_cselect_b32 s8, s13, s14
	s_lshl_b64 s[8:9], s[8:9], 2
	s_add_u32 s72, s8, s18
	s_addc_u32 s11, s9, s19
	s_and_b32 s73, s11, 0xffff
	s_add_u32 s84, s8, s20
	s_addc_u32 s8, s9, s21
	s_and_b32 s85, s8, 0xffff
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:296
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_add_i32 s8, s8, s10
	s_ashr_i32 s9, s8, 31
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:304
	s_waitcnt vmcnt(0)
	v_readlane_b32 s11, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_mul_i32 s9, s11, s9
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:300
	s_waitcnt vmcnt(0)
	v_readlane_b32 s10, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_mul_i32 s10, s10, s8
	v_mov_b32_e32 v6, s8
	v_accvgpr_read_b32 v8, a104
	v_accvgpr_read_b32 v9, a105
	s_add_i32 s10, s9, s10
	v_mad_u64_u32 v[254:255], s[8:9], s11, v6, v[8:9]
	v_add_u32_e32 v255, s10, v255
	s_mov_b64 s[16:17], exec
	s_mov_b64 exec, 15
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	v_readlane_b32 s9, v6, 1
	v_readlane_b32 s10, v6, 2
	v_readlane_b32 s11, v6, 3
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_mov_b32 s8, s80
	s_mov_b32 s9, s81
	s_mov_b32 s11, s83
	buffer_load_dwordx4 v97, s[8:11], 0 offen lds
	s_mov_b32 m0, s98
	s_mov_b32 s48, s76
	buffer_load_dwordx4 v12, s[8:11], 0 offen lds
	s_mov_b32 m0, s99
	s_mov_b32 s49, s77
	buffer_load_dwordx4 v59, s[8:11], 0 offen lds
	s_mov_b32 m0, s39
	s_mov_b32 s51, s83
	buffer_load_dwordx4 v62, s[8:11], 0 offen lds
	s_mov_b32 m0, s28
	s_mov_b64 s[16:17], exec
	buffer_load_dwordx4 v68, s[48:51], 0 offen lds
	s_mov_b32 m0, s29
	s_nop 0
	buffer_load_dwordx4 v95, s[48:51], 0 offen lds
	s_mov_b32 m0, s64
	s_nop 0
	buffer_load_dwordx4 v10, s[48:51], 0 offen lds
	s_mov_b32 m0, s65
	s_nop 0
	buffer_load_dwordx4 v11, s[48:51], 0 offen lds
	s_mov_b32 m0, s33
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:308
	s_waitcnt vmcnt(0)
	v_readlane_b32 s12, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	s_nop 1
	buffer_load_dwordx4 v97, s[8:11], s12 offen lds
	s_mov_b32 m0, s88
	s_mov_b32 s14, s10
	buffer_load_dwordx4 v12, s[8:11], s12 offen lds
	s_mov_b32 m0, s89
	s_mov_b64 s[16:17], exec
	buffer_load_dwordx4 v59, s[8:11], s12 offen lds
	s_mov_b32 m0, s40
	s_mov_b64 exec, 15
	scratch_store_dword off, v6, off offset:404
	v_writelane_b32 v6, s12, 0
	v_writelane_b32 v6, s13, 1
	v_writelane_b32 v6, s14, 2
	v_writelane_b32 v6, s15, 3
	scratch_store_dword off, v6, off
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[16:17]
	buffer_load_dwordx4 v62, s[8:11], s12 offen lds
	s_mov_b32 m0, s0
	s_mov_b64 s[10:11], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:312
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[10:11]
	s_nop 1
	buffer_load_dwordx4 v68, s[48:51], s8 offen lds
	s_mov_b32 m0, s1
	v_accvgpr_read_b32 v6, a2
	buffer_load_dwordx4 v95, s[48:51], s8 offen lds
	s_mov_b32 m0, s96
	v_accvgpr_write_b32 a39, v12
	buffer_load_dwordx4 v10, s[48:51], s8 offen lds
	s_mov_b32 m0, s92
	v_mov_b32_e32 v103, v10
	buffer_load_dwordx4 v11, s[48:51], s8 offen lds
	v_mov_b32_e32 v105, v11
	v_lshlrev_b32_e32 v29, 5, v6
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:320
	s_waitcnt vmcnt(0)
	v_readlane_b32 s43, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:316
	s_waitcnt vmcnt(0)
	v_readlane_b32 s44, v6, 0
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	s_mov_b32 s45, s38
	s_mov_b32 s51, s37
	s_mov_b64 s[48:49], 0
	v_accvgpr_mov_b32 a116, a4
	v_accvgpr_read_b32 v42, a6
	v_accvgpr_read_b32 v55, a37
	v_accvgpr_read_b32 v53, a3
	v_accvgpr_mov_b32 a15, a11
	v_accvgpr_mov_b32 a14, a10
	v_accvgpr_mov_b32 a13, a9
	v_accvgpr_mov_b32 a12, a8
	v_accvgpr_read_b32 v57, a1
	v_accvgpr_read_b32 v64, a100
	v_accvgpr_mov_b32 a23, a19
	v_accvgpr_mov_b32 a22, a18
	v_accvgpr_mov_b32 a21, a17
	v_accvgpr_mov_b32 a20, a16
	v_accvgpr_read_b32 v58, a24
	v_accvgpr_read_b32 v60, a26
	v_accvgpr_read_b32 v72, a102
	v_accvgpr_mov_b32 a35, a31
	v_accvgpr_mov_b32 a34, a30
	v_accvgpr_mov_b32 a33, a29
	v_accvgpr_mov_b32 a32, a28
	v_accvgpr_read_b32 v66, a36
	v_accvgpr_read_b32 v70, a38
	v_accvgpr_read_b32 v81, a5
	v_accvgpr_mov_b32 a47, a43
	v_accvgpr_mov_b32 a46, a42
	v_accvgpr_mov_b32 a45, a41
	v_accvgpr_mov_b32 a44, a40
	v_accvgpr_read_b32 v78, a48
	v_accvgpr_read_b32 v79, a7
	v_accvgpr_read_b32 v80, a50
	v_accvgpr_mov_b32 a59, a55
	v_accvgpr_mov_b32 a58, a54
	v_accvgpr_mov_b32 a57, a53
	v_accvgpr_mov_b32 a56, a52
	v_accvgpr_read_b32 v76, a60
	v_accvgpr_mov_b32 a69, a65
	v_accvgpr_mov_b32 a68, a64
	v_accvgpr_mov_b32 a67, a63
	v_accvgpr_mov_b32 a66, a62
	v_accvgpr_read_b32 v87, a25
	v_accvgpr_read_b32 v86, a74
	v_accvgpr_read_b32 v89, a27
	v_accvgpr_read_b32 v88, a80
	v_accvgpr_read_b32 v84, a82
	v_accvgpr_read_b32 v92, a106
	v_mov_b32_e32 v104, v102
	v_accvgpr_mov_b32 a115, a111
	v_accvgpr_mov_b32 a114, a110
	v_accvgpr_mov_b32 a113, a109
	v_accvgpr_mov_b32 a112, a108
.LBB0_36:
	s_mov_b64 s[8:9], s[48:49]
	s_add_u32 s48, s8, 2
	s_addc_u32 s49, s9, 0
	s_lshl_b64 s[14:15], s[8:9], 5
	s_waitcnt vmcnt(8)
	s_barrier
	ds_read_b128 v[6:9], v125
	ds_read_b128 v[10:13], v125 offset:64
	ds_read_b128 v[14:17], v125 offset:4352
	v_accvgpr_write_b32 a91, v23
	v_accvgpr_write_b32 a90, v22
	s_waitcnt lgkmcnt(2)
	v_and_b32_e32 v9, v9, v53
	v_and_b32_e32 v8, v8, v92
	v_and_b32_e32 v7, v7, v55
	v_and_b32_e32 v6, v6, v42
	s_waitcnt lgkmcnt(1)
	v_and_b32_e32 v13, v13, v63
	v_and_b32_e32 v12, v12, v64
	v_and_b32_e32 v11, v11, v57
	v_and_b32_e32 v10, v10, v60
	v_mfma_f32_16x16x32_f16 v[6:9], v[6:9], a[12:15], 0
	v_accvgpr_write_b32 a89, v21
	v_accvgpr_write_b32 a88, v20
	v_accvgpr_write_b32 a95, v27
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[20:23], v[6:9]
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v17, v71
	v_and_b32_e32 v12, v16, v72
	v_and_b32_e32 v11, v15, v65
	v_and_b32_e32 v10, v14, v58
	ds_read_b128 v[14:17], v125 offset:17472
	v_accvgpr_write_b32 a94, v26
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[32:35], v[6:9]
	ds_read_b128 v[10:13], v125 offset:4416
	s_waitcnt lgkmcnt(1)
	v_and_b32_e32 v17, v17, v75
	v_and_b32_e32 v16, v16, v18
	v_and_b32_e32 v15, v15, v69
	v_and_b32_e32 v14, v14, v74
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v81
	v_and_b32_e32 v12, v12, v70
	v_and_b32_e32 v11, v11, v73
	v_and_b32_e32 v10, v10, v66
	v_accvgpr_write_b32 a93, v25
	v_accvgpr_write_b32 a92, v24
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[44:47], v[6:9]
	ds_read_b128 v[10:13], v125 offset:8704
	v_accvgpr_write_b32 a79, v41
	v_accvgpr_write_b32 a78, v40
	v_accvgpr_write_b32 a77, v39
	v_accvgpr_write_b32 a76, v38
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v35
	v_and_b32_e32 v12, v12, v80
	v_and_b32_e32 v11, v11, v79
	v_and_b32_e32 v10, v10, v78
	v_mov_b32_e32 v96, v18
	v_accvgpr_write_b32 a99, v33
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[56:59], v[6:9]
	ds_read_b128 v[10:13], v125 offset:8768
	v_accvgpr_write_b32 a98, v32
	v_accvgpr_write_b32 a97, v31
	v_accvgpr_write_b32 a96, v30
	s_mul_i32 s10, s15, s93
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v43
	v_and_b32_e32 v12, v12, v76
	v_and_b32_e32 v11, v11, v37
	v_and_b32_e32 v10, v10, v44
	v_accvgpr_write_b32 a73, v49
	v_accvgpr_write_b32 a72, v48
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[66:69], v[6:9]
	ds_read_b128 v[10:13], v125 offset:13056
	v_accvgpr_write_b32 a71, v47
	v_accvgpr_write_b32 a70, v46
	s_mov_b32 s86, s74
	s_mov_b32 s87, s75
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v51
	v_and_b32_e32 v12, v12, v52
	v_and_b32_e32 v11, v11, v45
	v_and_b32_e32 v10, v10, v50
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], v[46:49], v[6:9]
	ds_read_b128 v[10:13], v125 offset:13120
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v89
	v_and_b32_e32 v12, v12, v86
	v_and_b32_e32 v11, v11, v87
	v_and_b32_e32 v10, v10, v56
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], v[38:41], v[6:9]
	ds_read_b128 v[10:13], v125 offset:17408
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v67
	v_and_b32_e32 v12, v12, v84
	v_and_b32_e32 v11, v11, v61
	v_and_b32_e32 v10, v10, v88
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[10:13], a[84:87], 0
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[20:23], v[10:13]
	ds_read_b128 v[14:17], v125 offset:21760
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v83
	v_and_b32_e32 v16, v16, v94
	v_and_b32_e32 v15, v15, v77
	v_and_b32_e32 v14, v14, v82
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[24:27], v[10:13]
	ds_read_b128 v[14:17], v125 offset:21824
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v91
	v_and_b32_e32 v16, v16, v104
	v_and_b32_e32 v15, v15, v85
	v_and_b32_e32 v14, v14, v90
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[30:33], v[10:13]
	ds_read_b128 v[14:17], v125 offset:26112
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v99
	v_and_b32_e32 v16, v16, v100
	v_and_b32_e32 v15, v15, v93
	v_and_b32_e32 v14, v14, v98
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[112:115], v[10:13]
	ds_read_b128 v[14:17], v125 offset:26176
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v107
	v_and_b32_e32 v16, v16, v108
	v_and_b32_e32 v15, v15, v101
	v_and_b32_e32 v14, v14, v106
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[110:113], v[10:13]
	ds_read_b128 v[14:17], v125 offset:30464
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v115
	v_and_b32_e32 v16, v16, v116
	v_and_b32_e32 v15, v15, v109
	v_and_b32_e32 v14, v14, v114
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[118:121], v[10:13]
	ds_read_b128 v[14:17], v125 offset:30528
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v123
	v_and_b32_e32 v16, v16, v124
	v_and_b32_e32 v15, v15, v117
	v_and_b32_e32 v14, v14, v122
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[22:25], v[14:17], v[126:129], v[10:13]
	ds_read_b128 v[14:17], v28 offset:64
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v63
	ds_read_b128 v[10:13], v28
	v_and_b32_e32 v16, v16, v64
	v_and_b32_e32 v15, v15, v57
	v_and_b32_e32 v14, v14, v60
	s_nop 0
	v_pk_mul_f32 v[22:23], v[22:23], s[70:71]
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v53
	v_and_b32_e32 v12, v12, v92
	v_and_b32_e32 v11, v11, v55
	v_and_b32_e32 v10, v10, v42
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[10:13], a[12:15], 0
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[20:23], v[10:13]
	ds_read_b128 v[14:17], v28 offset:4352
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v71
	v_and_b32_e32 v16, v16, v72
	v_and_b32_e32 v15, v15, v65
	v_and_b32_e32 v14, v14, v58
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[32:35], v[10:13]
	ds_read_b128 v[14:17], v28 offset:4416
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v81
	v_and_b32_e32 v16, v16, v70
	v_and_b32_e32 v15, v15, v73
	v_and_b32_e32 v14, v14, v66
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[44:47], v[10:13]
	ds_read_b128 v[14:17], v28 offset:8704
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v35
	v_and_b32_e32 v16, v16, v80
	v_and_b32_e32 v15, v15, v79
	v_and_b32_e32 v14, v14, v78
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[56:59], v[10:13]
	ds_read_b128 v[14:17], v28 offset:8768
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v43
	v_and_b32_e32 v16, v16, v76
	v_and_b32_e32 v15, v15, v37
	v_and_b32_e32 v14, v14, v44
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[66:69], v[10:13]
	ds_read_b128 v[14:17], v28 offset:13056
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v51
	v_and_b32_e32 v16, v16, v52
	v_and_b32_e32 v15, v15, v45
	v_and_b32_e32 v14, v14, v50
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[46:49], v[10:13]
	ds_read_b128 v[14:17], v28 offset:13120
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v89
	v_and_b32_e32 v16, v16, v86
	v_and_b32_e32 v15, v15, v87
	v_and_b32_e32 v14, v14, v56
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[38:41], v[14:17], a[76:79], v[10:13]
	ds_read_b128 v[14:17], v28 offset:17472
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v75
	ds_read_b128 v[10:13], v28 offset:17408
	v_and_b32_e32 v16, v16, v18
	v_and_b32_e32 v15, v15, v69
	v_and_b32_e32 v14, v14, v74
	s_nop 0
	v_mov_b32_e32 v26, v38
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v67
	v_and_b32_e32 v12, v12, v84
	v_and_b32_e32 v11, v11, v61
	v_and_b32_e32 v10, v10, v88
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[10:13], a[84:87], 0
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[88:91], v[10:13]
	ds_read_b128 v[14:17], v28 offset:21760
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v83
	v_and_b32_e32 v16, v16, v94
	v_and_b32_e32 v15, v15, v77
	v_and_b32_e32 v14, v14, v82
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[92:95], v[10:13]
	ds_read_b128 v[14:17], v28 offset:21824
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v91
	v_and_b32_e32 v16, v16, v104
	v_and_b32_e32 v15, v15, v85
	v_and_b32_e32 v14, v14, v90
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[30:33], v[10:13]
	ds_read_b128 v[14:17], v28 offset:26112
	v_mov_b32_e32 v32, v6
	v_mov_b32_e32 v30, v8
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v99
	v_and_b32_e32 v16, v16, v100
	v_and_b32_e32 v15, v15, v93
	v_and_b32_e32 v14, v14, v98
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[112:115], v[10:13]
	ds_read_b128 v[14:17], v28 offset:26176
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v107
	v_and_b32_e32 v16, v16, v108
	v_and_b32_e32 v15, v15, v101
	v_and_b32_e32 v14, v14, v106
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[110:113], v[10:13]
	ds_read_b128 v[14:17], v28 offset:30464
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v115
	v_and_b32_e32 v16, v16, v116
	v_and_b32_e32 v15, v15, v109
	v_and_b32_e32 v14, v14, v114
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[118:121], v[10:13]
	ds_read_b128 v[14:17], v28 offset:30528
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v21, v17, v123
	v_and_b32_e32 v20, v16, v124
	v_and_b32_e32 v19, v15, v117
	v_and_b32_e32 v18, v14, v122
	buffer_load_dwordx4 v[14:17], v29, s[72:75], 0 offen
	s_waitcnt vmcnt(0)
	v_mov_b32_e32 v33, v14
	v_mov_b32_e32 v14, v7
	v_mov_b32_e32 v31, v16
	v_mov_b32_e32 v16, v9
	buffer_load_dwordx4 v[6:9], v29, s[72:75], 0 offen offset:16
	v_mfma_f32_16x16x32_f16 v[10:13], v[18:21], v[126:129], v[10:13]
	v_accvgpr_read_b32 v18, a116
	v_or_b32_e32 v18, s14, v18
	v_mul_lo_u32 v19, v18, s90
	v_mov_b32_e32 v20, v40
	v_pk_mul_f32 v[14:15], v[14:15], v[4:5]
	s_waitcnt vmcnt(0)
	v_mov_b32_e32 v27, v6
	v_mov_b32_e32 v6, v39
	v_mad_u64_u32 v[38:39], s[8:9], v18, s93, v[254:255]
	v_add3_u32 v19, s10, v39, v19
	v_xor_b32_e32 v19, s94, v19
	v_mad_u64_u32 v[38:39], s[8:9], v38, s41, 0
	v_mul_hi_u32 v40, v19, s41
	v_xor_b32_e32 v38, v38, v40
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v40, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mov_b32_e32 v21, v8
	v_mov_b32_e32 v8, v41
	v_mul_hi_u32 v41, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v40, v40, v41
	v_mul_lo_u32 v19, v19, s41
	v_mul_hi_u32 v41, v39, s41
	v_xor_b32_e32 v19, v19, v41
	v_xor_b32_e32 v19, s35, v19
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v41, v19, s42
	v_xor_b32_e32 v40, s34, v40
	v_xor_b32_e32 v38, v38, v41
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v41, v40, s41
	v_xor_b32_e32 v39, v39, v41
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v19, v19, s42
	v_mul_hi_u32 v41, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v19, v19, v41
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v41, v38, s41
	v_xor_b32_e32 v40, v40, v41
	v_xor_b32_e32 v40, s52, v40
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v41, v40, s42
	v_xor_b32_e32 v19, s67, v19
	v_xor_b32_e32 v41, v39, v41
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v39, v19, s41
	v_xor_b32_e32 v38, v38, v39
	v_xor_b32_e32 v46, s56, v38
	v_mul_lo_u32 v38, v40, s42
	v_mul_hi_u32 v39, v46, s42
	v_xor_b32_e32 v40, v38, v39
	v_or_b32_e32 v38, 1, v18
	v_mul_lo_u32 v47, v38, s90
	v_mad_u64_u32 v[38:39], s[8:9], v38, s93, v[254:255]
	v_add3_u32 v39, s10, v39, v47
	v_xor_b32_e32 v47, s94, v39
	v_mad_u64_u32 v[38:39], s[8:9], v38, s41, 0
	v_mul_hi_u32 v48, v47, s41
	v_xor_b32_e32 v38, v38, v48
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v48, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v47, v47, v49
	v_xor_b32_e32 v47, s35, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v48, s34, v48
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v39, v39, v49
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v48, v48, v49
	v_xor_b32_e32 v48, s52, v48
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v47, s67, v47
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v38, v38, v49
	v_xor_b32_e32 v38, s56, v38
	v_mul_lo_u32 v48, v48, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s53, v39
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v41, s53, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v19, v19, s41
	v_mul_hi_u32 v49, v41, s41
	v_xor_b32_e32 v19, v19, v49
	v_xor_b32_e32 v47, s58, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v19, s58, v19
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v46, v46, s42
	v_mul_hi_u32 v49, v19, s42
	v_xor_b32_e32 v48, s57, v48
	v_xor_b32_e32 v46, v46, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v40, s57, v40
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v49, v40, s41
	v_xor_b32_e32 v41, v41, v49
	v_xor_b32_e32 v39, s60, v39
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v41, s60, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v19, v19, s42
	v_mul_hi_u32 v49, v41, s42
	v_xor_b32_e32 v38, s59, v38
	v_xor_b32_e32 v19, v19, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v46, s59, v46
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v49, v46, s41
	v_xor_b32_e32 v40, v40, v49
	v_xor_b32_e32 v48, s62, v48
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v40, s62, v40
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v41, v41, s42
	v_mul_hi_u32 v49, v40, s42
	v_xor_b32_e32 v47, s61, v47
	v_xor_b32_e32 v41, v41, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v19, s61, v19
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v49, v19, s41
	v_xor_b32_e32 v39, s63, v39
	v_mul_lo_u32 v48, v48, s42
	v_xor_b32_e32 v46, v46, v49
	v_cndmask_b32_e64 v39, v39, v48, s[2:3]
	v_xor_b32_e32 v41, s63, v41
	v_mul_lo_u32 v40, v40, s42
	v_xor_b32_e32 v38, s36, v38
	v_cndmask_b32_e64 v40, v41, v40, s[2:3]
	v_cndmask_b32_e64 v38, v39, v38, s[4:5]
	v_xor_b32_e32 v39, s36, v46
	v_cndmask_b32_e64 v39, v40, v39, s[4:5]
	v_mul_lo_u32 v40, v47, s41
	v_mul_lo_u32 v19, v19, s41
	v_cndmask_b32_e64 v38, v38, v40, s[6:7]
	v_cndmask_b32_e64 v19, v39, v19, s[6:7]
	v_cmp_lt_i32_e32 vcc, s68, v38
	v_cmp_lt_i32_e64 s[8:9], s68, v19
	v_or_b32_e32 v19, 2, v18
	v_cndmask_b32_e32 v39, 0, v23, vcc
	v_cndmask_b32_e64 v38, 0, v22, s[8:9]
	v_pk_mul_f32 v[22:23], v[24:25], s[70:71]
	v_mul_lo_u32 v40, v19, s90
	v_mad_u64_u32 v[24:25], s[12:13], v19, s93, v[254:255]
	v_add3_u32 v19, s10, v25, v40
	v_xor_b32_e32 v19, s94, v19
	v_mad_u64_u32 v[24:25], s[12:13], v24, s41, 0
	v_mul_hi_u32 v40, v19, s41
	v_xor_b32_e32 v24, v24, v40
	v_xor_b32_e32 v25, s95, v25
	v_xor_b32_e32 v24, s47, v24
	v_mul_lo_u32 v40, v25, s42
	v_mul_hi_u32 v25, v25, s42
	v_mul_hi_u32 v41, v24, s42
	v_xor_b32_e32 v25, s46, v25
	v_xor_b32_e32 v40, v40, v41
	v_mul_lo_u32 v19, v19, s41
	v_mul_hi_u32 v41, v25, s41
	v_xor_b32_e32 v19, v19, v41
	v_xor_b32_e32 v19, s35, v19
	v_mul_lo_u32 v24, v24, s42
	v_mul_hi_u32 v41, v19, s42
	v_xor_b32_e32 v40, s34, v40
	v_xor_b32_e32 v24, v24, v41
	v_mul_lo_u32 v25, v25, s41
	v_mul_hi_u32 v41, v40, s41
	v_xor_b32_e32 v25, v25, v41
	v_xor_b32_e32 v25, s66, v25
	v_mul_lo_u32 v19, v19, s42
	v_mul_hi_u32 v41, v25, s42
	v_xor_b32_e32 v24, s91, v24
	v_xor_b32_e32 v19, v19, v41
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v41, v24, s41
	v_xor_b32_e32 v40, v40, v41
	v_xor_b32_e32 v40, s52, v40
	v_mul_lo_u32 v25, v25, s42
	v_mul_hi_u32 v41, v40, s42
	v_xor_b32_e32 v19, s67, v19
	v_xor_b32_e32 v41, v25, v41
	v_mul_lo_u32 v24, v24, s41
	v_mul_hi_u32 v25, v19, s41
	v_xor_b32_e32 v24, v24, v25
	v_xor_b32_e32 v46, s56, v24
	v_mul_lo_u32 v24, v40, s42
	v_mul_hi_u32 v25, v46, s42
	v_xor_b32_e32 v40, v24, v25
	v_or_b32_e32 v24, 3, v18
	v_mul_lo_u32 v47, v24, s90
	v_mad_u64_u32 v[24:25], s[12:13], v24, s93, v[254:255]
	v_add3_u32 v25, s10, v25, v47
	v_xor_b32_e32 v47, s94, v25
	v_mad_u64_u32 v[24:25], s[10:11], v24, s41, 0
	v_mul_hi_u32 v48, v47, s41
	v_xor_b32_e32 v24, v24, v48
	v_xor_b32_e32 v25, s95, v25
	v_xor_b32_e32 v24, s47, v24
	v_mul_lo_u32 v48, v25, s42
	v_mul_hi_u32 v25, v25, s42
	v_mul_hi_u32 v49, v24, s42
	v_xor_b32_e32 v25, s46, v25
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v25, s41
	v_xor_b32_e32 v47, v47, v49
	v_xor_b32_e32 v47, s35, v47
	v_mul_lo_u32 v24, v24, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v48, s34, v48
	v_xor_b32_e32 v24, v24, v49
	v_mul_lo_u32 v25, v25, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v25, v25, v49
	v_xor_b32_e32 v25, s66, v25
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v25, s42
	v_xor_b32_e32 v24, s91, v24
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v24, s41
	v_xor_b32_e32 v48, v48, v49
	v_xor_b32_e32 v48, s52, v48
	v_mul_lo_u32 v25, v25, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v47, s67, v47
	v_xor_b32_e32 v25, v25, v49
	v_mul_lo_u32 v24, v24, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v24, v24, v49
	v_xor_b32_e32 v24, s56, v24
	v_mul_lo_u32 v48, v48, s42
	v_mul_hi_u32 v49, v24, s42
	v_xor_b32_e32 v25, s53, v25
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v25, s41
	v_xor_b32_e32 v41, s53, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v19, v19, s41
	v_mul_hi_u32 v49, v41, s41
	v_xor_b32_e32 v19, v19, v49
	v_xor_b32_e32 v47, s58, v47
	v_mul_lo_u32 v24, v24, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v19, s58, v19
	v_xor_b32_e32 v24, v24, v49
	v_mul_lo_u32 v46, v46, s42
	v_mul_hi_u32 v49, v19, s42
	v_xor_b32_e32 v48, s57, v48
	v_xor_b32_e32 v46, v46, v49
	v_mul_lo_u32 v25, v25, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v40, s57, v40
	v_xor_b32_e32 v25, v25, v49
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v49, v40, s41
	v_xor_b32_e32 v41, v41, v49
	v_xor_b32_e32 v25, s60, v25
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v25, s42
	v_xor_b32_e32 v41, s60, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v19, v19, s42
	v_mul_hi_u32 v49, v41, s42
	v_xor_b32_e32 v24, s59, v24
	v_xor_b32_e32 v19, v19, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v24, s41
	v_xor_b32_e32 v46, s59, v46
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v49, v46, s41
	v_xor_b32_e32 v40, v40, v49
	v_xor_b32_e32 v48, s62, v48
	v_mul_lo_u32 v25, v25, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v40, s62, v40
	v_xor_b32_e32 v25, v25, v49
	v_mul_lo_u32 v41, v41, s42
	v_mul_hi_u32 v49, v40, s42
	v_xor_b32_e32 v47, s61, v47
	v_xor_b32_e32 v41, v41, v49
	v_mul_lo_u32 v24, v24, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v19, s61, v19
	v_xor_b32_e32 v24, v24, v49
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v49, v19, s41
	v_xor_b32_e32 v25, s63, v25
	v_mul_lo_u32 v48, v48, s42
	v_xor_b32_e32 v46, v46, v49
	v_cndmask_b32_e64 v25, v25, v48, s[2:3]
	v_xor_b32_e32 v41, s63, v41
	v_mul_lo_u32 v40, v40, s42
	v_xor_b32_e32 v24, s36, v24
	v_cndmask_b32_e64 v40, v41, v40, s[2:3]
	v_cndmask_b32_e64 v24, v25, v24, s[4:5]
	v_xor_b32_e32 v25, s36, v46
	v_cndmask_b32_e64 v25, v40, v25, s[4:5]
	v_mul_lo_u32 v40, v47, s41
	v_mul_lo_u32 v19, v19, s41
	v_cndmask_b32_e64 v24, v24, v40, s[6:7]
	v_cndmask_b32_e64 v19, v25, v19, s[6:7]
	v_cmp_lt_i32_e64 s[10:11], s68, v24
	v_cmp_lt_i32_e64 s[12:13], s68, v19
	v_mov_b32_e32 v19, s15
	v_cndmask_b32_e64 v41, 0, v23, s[10:11]
	v_cndmask_b32_e64 v40, 0, v22, s[12:13]
	buffer_load_dwordx4 v[22:25], v29, s[84:87], 0 offen
	v_pk_mul_f32 v[10:11], v[10:11], s[70:71]
	v_pk_mul_f32 v[12:13], v[12:13], s[70:71]
	v_pk_mul_f32 v[6:7], v[6:7], v[4:5]
	v_pk_mul_f32 v[8:9], v[8:9], v[4:5]
	s_waitcnt vmcnt(0)
	v_pk_add_f32 v[22:23], v[38:39], v[22:23] neg_lo:[0,1] neg_hi:[0,1]
	v_lshl_add_u64 v[38:39], v[18:19], 0, 4
	v_pk_add_f32 v[24:25], v[40:41], v[24:25] neg_lo:[0,1] neg_hi:[0,1]
	v_mul_lo_u32 v40, v38, s90
	v_mul_lo_u32 v41, v39, s93
	v_mad_u64_u32 v[38:39], s[14:15], v38, s93, v[254:255]
	v_add3_u32 v39, v41, v39, v40
	v_xor_b32_e32 v40, s94, v39
	v_mad_u64_u32 v[38:39], s[14:15], v38, s41, 0
	v_mul_hi_u32 v41, v40, s41
	v_xor_b32_e32 v38, v38, v41
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v41, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v46, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v41, v41, v46
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v46, v39, s41
	v_xor_b32_e32 v40, v40, v46
	v_xor_b32_e32 v40, s35, v40
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v46, v40, s42
	v_xor_b32_e32 v41, s34, v41
	v_xor_b32_e32 v38, v38, v46
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v46, v41, s41
	v_xor_b32_e32 v39, v39, v46
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v40, v40, s42
	v_mul_hi_u32 v46, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v40, v40, v46
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v46, v38, s41
	v_xor_b32_e32 v41, v41, v46
	v_xor_b32_e32 v41, s52, v41
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v46, v41, s42
	v_xor_b32_e32 v40, s67, v40
	v_xor_b32_e32 v46, v39, v46
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v39, v40, s41
	v_xor_b32_e32 v38, v38, v39
	v_xor_b32_e32 v47, s56, v38
	v_mul_lo_u32 v38, v41, s42
	v_mul_hi_u32 v39, v47, s42
	v_xor_b32_e32 v41, v38, v39
	v_lshl_add_u64 v[38:39], v[18:19], 0, 5
	v_mul_lo_u32 v48, v38, s90
	v_mul_lo_u32 v49, v39, s93
	v_mad_u64_u32 v[38:39], s[14:15], v38, s93, v[254:255]
	v_add3_u32 v39, v49, v39, v48
	v_xor_b32_e32 v48, s94, v39
	v_mad_u64_u32 v[38:39], s[14:15], v38, s41, 0
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v38, v38, v49
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v49, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v36, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v36, v49, v36
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v48, v48, v49
	v_xor_b32_e32 v48, s35, v48
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v36, s34, v36
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v36, s41
	v_xor_b32_e32 v39, v39, v49
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v48, v48, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v36, v36, v49
	v_xor_b32_e32 v36, s52, v36
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v36, s42
	v_xor_b32_e32 v48, s67, v48
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v38, v38, v49
	v_xor_b32_e32 v38, s56, v38
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s53, v39
	v_xor_b32_e32 v36, v36, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v46, s53, v46
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v49, v46, s41
	v_xor_b32_e32 v40, v40, v49
	v_xor_b32_e32 v48, s58, v48
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v40, s58, v40
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v40, s42
	v_xor_b32_e32 v36, s57, v36
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v36, s41
	v_xor_b32_e32 v41, s57, v41
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v49, v41, s41
	v_xor_b32_e32 v46, v46, v49
	v_xor_b32_e32 v39, s60, v39
	v_mul_lo_u32 v48, v48, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v46, s60, v46
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v40, v40, s42
	v_mul_hi_u32 v49, v46, s42
	v_xor_b32_e32 v38, s59, v38
	v_xor_b32_e32 v40, v40, v49
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v47, s59, v47
	v_xor_b32_e32 v36, v36, v49
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v41, v41, v49
	v_xor_b32_e32 v36, s62, v36
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v36, s42
	v_xor_b32_e32 v41, s62, v41
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v46, v46, s42
	v_mul_hi_u32 v49, v41, s42
	v_xor_b32_e32 v48, s61, v48
	v_xor_b32_e32 v46, v46, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v40, s61, v40
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v40, s41
	v_xor_b32_e32 v39, s63, v39
	v_mul_lo_u32 v36, v36, s42
	v_xor_b32_e32 v47, v47, v49
	v_cndmask_b32_e64 v36, v39, v36, s[2:3]
	v_xor_b32_e32 v39, s63, v46
	v_mul_lo_u32 v41, v41, s42
	v_xor_b32_e32 v38, s36, v38
	v_cndmask_b32_e64 v39, v39, v41, s[2:3]
	v_cndmask_b32_e64 v36, v36, v38, s[4:5]
	v_xor_b32_e32 v38, s36, v47
	v_cndmask_b32_e64 v38, v39, v38, s[4:5]
	v_mul_lo_u32 v39, v48, s41
	v_cndmask_b32_e64 v36, v36, v39, s[6:7]
	v_mul_lo_u32 v39, v40, s41
	v_cndmask_b32_e64 v38, v38, v39, s[6:7]
	v_cmp_lt_i32_e64 s[16:17], s68, v38
	v_lshl_add_u64 v[38:39], v[18:19], 0, 6
	v_cmp_lt_i32_e64 s[14:15], s68, v36
	v_mul_lo_u32 v36, v38, s90
	v_mul_lo_u32 v40, v39, s93
	v_mad_u64_u32 v[38:39], s[18:19], v38, s93, v[254:255]
	v_add3_u32 v36, v40, v39, v36
	v_xor_b32_e32 v36, s94, v36
	v_mad_u64_u32 v[38:39], s[18:19], v38, s41, 0
	v_mul_hi_u32 v40, v36, s41
	v_xor_b32_e32 v38, v38, v40
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v40, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v41, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v40, v40, v41
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v41, v39, s41
	v_xor_b32_e32 v36, v36, v41
	v_xor_b32_e32 v36, s35, v36
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v41, v36, s42
	v_xor_b32_e32 v40, s34, v40
	v_xor_b32_e32 v38, v38, v41
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v41, v40, s41
	v_xor_b32_e32 v39, v39, v41
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v41, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v36, v36, v41
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v41, v38, s41
	v_xor_b32_e32 v40, v40, v41
	v_xor_b32_e32 v40, s52, v40
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v41, v40, s42
	v_xor_b32_e32 v36, s67, v36
	v_xor_b32_e32 v41, v39, v41
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v39, v36, s41
	v_xor_b32_e32 v38, v38, v39
	v_xor_b32_e32 v46, s56, v38
	v_mul_lo_u32 v38, v40, s42
	v_mul_hi_u32 v39, v46, s42
	v_xor_b32_e32 v40, v38, v39
	v_lshl_add_u64 v[38:39], v[18:19], 0, 7
	v_mul_lo_u32 v47, v38, s90
	v_mul_lo_u32 v48, v39, s93
	v_mad_u64_u32 v[38:39], s[18:19], v38, s93, v[254:255]
	v_add3_u32 v39, v48, v39, v47
	v_xor_b32_e32 v47, s94, v39
	v_mad_u64_u32 v[38:39], s[18:19], v38, s41, 0
	v_mul_hi_u32 v48, v47, s41
	v_xor_b32_e32 v38, v38, v48
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v48, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v47, v47, v49
	v_xor_b32_e32 v47, s35, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v48, s34, v48
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v39, v39, v49
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v48, v48, v49
	v_xor_b32_e32 v48, s52, v48
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v47, s67, v47
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v38, v38, v49
	v_xor_b32_e32 v38, s56, v38
	v_mul_lo_u32 v48, v48, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s53, v39
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v41, s53, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v49, v41, s41
	v_xor_b32_e32 v36, v36, v49
	v_xor_b32_e32 v47, s58, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v36, s58, v36
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v46, v46, s42
	v_mul_hi_u32 v49, v36, s42
	v_xor_b32_e32 v48, s57, v48
	v_xor_b32_e32 v46, v46, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v40, s57, v40
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v49, v40, s41
	v_xor_b32_e32 v41, v41, v49
	v_xor_b32_e32 v39, s60, v39
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v41, s60, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v49, v41, s42
	v_xor_b32_e32 v38, s59, v38
	v_xor_b32_e32 v36, v36, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v46, s59, v46
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v49, v46, s41
	v_xor_b32_e32 v40, v40, v49
	v_xor_b32_e32 v48, s62, v48
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v40, s62, v40
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v41, v41, s42
	v_mul_hi_u32 v49, v40, s42
	v_xor_b32_e32 v47, s61, v47
	v_xor_b32_e32 v41, v41, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v36, s61, v36
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v49, v36, s41
	v_xor_b32_e32 v39, s63, v39
	v_mul_lo_u32 v48, v48, s42
	v_xor_b32_e32 v46, v46, v49
	v_cndmask_b32_e64 v39, v39, v48, s[2:3]
	v_xor_b32_e32 v41, s63, v41
	v_mul_lo_u32 v40, v40, s42
	v_xor_b32_e32 v38, s36, v38
	v_cndmask_b32_e64 v40, v41, v40, s[2:3]
	v_cndmask_b32_e64 v38, v39, v38, s[4:5]
	v_xor_b32_e32 v39, s36, v46
	v_cndmask_b32_e64 v39, v40, v39, s[4:5]
	v_mul_lo_u32 v40, v47, s41
	v_cndmask_b32_e64 v38, v38, v40, s[6:7]
	v_mul_lo_u32 v36, v36, s41
	v_cndmask_b32_e64 v36, v39, v36, s[6:7]
	v_cmp_lt_i32_e64 s[18:19], s68, v38
	buffer_load_dwordx4 v[38:41], v29, s[84:87], 0 offen offset:16
	v_cndmask_b32_e64 v11, 0, v11, s[14:15]
	v_cndmask_b32_e64 v10, 0, v10, s[16:17]
	v_cmp_lt_i32_e64 s[20:21], s68, v36
	v_cndmask_b32_e64 v47, 0, v13, s[18:19]
	s_nop 0
	v_cndmask_b32_e64 v46, 0, v12, s[20:21]
	s_waitcnt vmcnt(0)
	v_pk_add_f32 v[12:13], v[10:11], v[38:39] neg_lo:[0,1] neg_hi:[0,1]
	v_pk_mul_f32 v[38:39], v[16:17], v[4:5]
	v_pk_mul_f32 v[16:17], v[32:33], v[4:5]
	v_mov_b32_e32 v33, v14
	v_mov_b32_e32 v32, v16
	v_mov_b32_e32 v14, v17
	v_pk_mul_f32 v[16:17], v[30:31], v[4:5]
	v_mov_b32_e32 v31, v38
	v_mov_b32_e32 v30, v16
	v_mov_b32_e32 v38, v17
	v_pk_mul_f32 v[16:17], v[26:27], v[4:5]
	v_mov_b32_e32 v27, v6
	v_mov_b32_e32 v26, v16
	v_mov_b32_e32 v6, v17
	v_pk_add_f32 v[6:7], v[26:27], v[6:7] neg_lo:[0,1] neg_hi:[0,1]
	v_pk_add_f32 v[14:15], v[32:33], v[14:15] neg_lo:[0,1] neg_hi:[0,1]
	v_exp_f32_e32 v16, v6
	v_exp_f32_e32 v17, v7
	v_pk_mul_f32 v[6:7], v[20:21], v[4:5]
	v_mov_b32_e32 v21, v8
	v_mov_b32_e32 v20, v6
	v_mov_b32_e32 v8, v7
	v_pk_add_f32 v[6:7], v[20:21], v[8:9] neg_lo:[0,1] neg_hi:[0,1]
	v_exp_f32_e32 v14, v14
	v_exp_f32_e32 v20, v6
	v_exp_f32_e32 v21, v7
	v_pk_add_f32 v[6:7], v[30:31], v[38:39] neg_lo:[0,1] neg_hi:[0,1]
	;;#ASMSTART
	s_nop 0
	;;#ASMEND
	v_exp_f32_e32 v15, v15
	v_exp_f32_e32 v26, v6
	v_exp_f32_e32 v27, v7
	v_cvt_f16_f32_e32 v6, v16
	v_cvt_f16_f32_e32 v7, v17
	v_cvt_f16_f32_e32 v8, v20
	v_cvt_f16_f32_e32 v9, v21
	v_cndmask_b32_e64 v6, 0, v6, s[16:17]
	v_cndmask_b32_e64 v7, 0, v7, s[14:15]
	v_cndmask_b32_e64 v8, 0, v8, s[20:21]
	v_cndmask_b32_e64 v9, 0, v9, s[18:19]
	v_pack_b32_f16 v9, v8, v9
	v_pack_b32_f16 v8, v6, v7
	;;#ASMSTART
	s_nop 0
	;;#ASMEND
	v_pk_add_f32 v[10:11], v[46:47], v[40:41] neg_lo:[0,1] neg_hi:[0,1]
	v_cvt_f16_f32_e32 v6, v26
	v_cvt_f16_f32_e32 v7, v27
	v_cvt_f16_f32_e32 v30, v15
	v_pk_mul_f32 v[10:11], v[10:11], v[20:21]
	v_cndmask_b32_e64 v6, 0, v6, s[12:13]
	v_cndmask_b32_e64 v7, 0, v7, s[10:11]
	v_pack_b32_f16 v7, v6, v7
	v_cvt_f16_f32_e32 v6, v14
	v_cndmask_b32_e32 v30, 0, v30, vcc
	v_cndmask_b32_e64 v6, 0, v6, s[8:9]
	v_pack_b32_f16 v6, v6, v30
	ds_read_b64_tr_b16 v[30:31], v34 offset:17408
	ds_read_b64_tr_b16 v[32:33], v34 offset:17536
	;;#ASMSTART
	s_nop 1
	;;#ASMEND
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[218:221], v[30:33], v[6:9], v[218:221]
	ds_read_b64_tr_b16 v[30:31], v34 offset:17440
	ds_read_b64_tr_b16 v[32:33], v34 offset:17568
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[210:213], v[30:33], v[6:9], v[210:213]
	ds_read_b64_tr_b16 v[30:31], v34 offset:17472
	ds_read_b64_tr_b16 v[32:33], v34 offset:17600
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[202:205], v[30:33], v[6:9], v[202:205]
	ds_read_b64_tr_b16 v[30:31], v34 offset:17504
	ds_read_b64_tr_b16 v[32:33], v34 offset:17632
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[194:197], v[30:33], v[6:9], v[194:197]
	ds_read_b64_tr_b16 v[30:31], v34 offset:21760
	ds_read_b64_tr_b16 v[32:33], v34 offset:21888
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[186:189], v[30:33], v[6:9], v[186:189]
	ds_read_b64_tr_b16 v[30:31], v34 offset:21792
	ds_read_b64_tr_b16 v[32:33], v34 offset:21920
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[178:181], v[30:33], v[6:9], v[178:181]
	ds_read_b64_tr_b16 v[30:31], v34 offset:21824
	ds_read_b64_tr_b16 v[32:33], v34 offset:21952
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[170:173], v[30:33], v[6:9], v[170:173]
	ds_read_b64_tr_b16 v[30:31], v34 offset:21856
	ds_read_b64_tr_b16 v[32:33], v34 offset:21984
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[166:169], v[30:33], v[6:9], v[166:169]
	ds_read_b64_tr_b16 v[30:31], v34 offset:26112
	ds_read_b64_tr_b16 v[32:33], v34 offset:26240
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[162:165], v[30:33], v[6:9], v[162:165]
	ds_read_b64_tr_b16 v[30:31], v34 offset:26144
	ds_read_b64_tr_b16 v[32:33], v34 offset:26272
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[158:161], v[30:33], v[6:9], v[158:161]
	ds_read_b64_tr_b16 v[30:31], v34 offset:26176
	ds_read_b64_tr_b16 v[32:33], v34 offset:26304
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[154:157], v[30:33], v[6:9], v[154:157]
	ds_read_b64_tr_b16 v[30:31], v34 offset:26208
	ds_read_b64_tr_b16 v[32:33], v34 offset:26336
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[150:153], v[30:33], v[6:9], v[150:153]
	ds_read_b64_tr_b16 v[30:31], v34 offset:30464
	ds_read_b64_tr_b16 v[32:33], v34 offset:30592
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[146:149], v[30:33], v[6:9], v[146:149]
	ds_read_b64_tr_b16 v[30:31], v34 offset:30496
	ds_read_b64_tr_b16 v[32:33], v34 offset:30624
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[142:145], v[30:33], v[6:9], v[142:145]
	ds_read_b64_tr_b16 v[30:31], v34 offset:30528
	ds_read_b64_tr_b16 v[32:33], v34 offset:30656
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[138:141], v[30:33], v[6:9], v[138:141]
	ds_read_b64_tr_b16 v[30:31], v34 offset:30560
	ds_read_b64_tr_b16 v[32:33], v34 offset:30688
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[134:137], v[30:33], v[6:9], v[134:137]
	v_mul_f32_e64 v6, v22, v14
	v_mul_f32_e64 v7, v23, v15
	v_pk_mul_f32 v[8:9], v[24:25], v[26:27]
	v_cvt_pk_f16_f32 v6, v6, v7
	v_cvt_pk_f16_f32 v7, v8, v9
	v_pk_mul_f32 v[8:9], v[12:13], v[16:17]
	ds_read_b64_tr_b16 v[14:15], v34 offset:32
	ds_read_b64_tr_b16 v[16:17], v34 offset:160
	v_cvt_pk_f16_f32 v8, v8, v9
	v_cvt_pk_f16_f32 v9, v10, v11
	ds_read_b64_tr_b16 v[12:13], v34 offset:128
	ds_read_b64_tr_b16 v[10:11], v34
	;;#ASMSTART
	s_nop 1
	;;#ASMEND
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[130:133], v[10:13], v[6:9], v[130:133]
	ds_read_b64_tr_b16 v[10:11], v34 offset:64
	ds_read_b64_tr_b16 v[12:13], v34 offset:192
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[246:249], v[10:13], v[6:9], v[246:249]
	ds_read_b64_tr_b16 v[10:11], v34 offset:96
	ds_read_b64_tr_b16 v[12:13], v34 offset:224
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[242:245], v[10:13], v[6:9], v[242:245]
	ds_read_b64_tr_b16 v[10:11], v34 offset:4352
	ds_read_b64_tr_b16 v[12:13], v34 offset:4480
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[238:241], v[10:13], v[6:9], v[238:241]
	ds_read_b64_tr_b16 v[10:11], v34 offset:4384
	ds_read_b64_tr_b16 v[12:13], v34 offset:4512
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[234:237], v[10:13], v[6:9], v[234:237]
	ds_read_b64_tr_b16 v[10:11], v34 offset:4416
	ds_read_b64_tr_b16 v[12:13], v34 offset:4544
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[230:233], v[10:13], v[6:9], v[230:233]
	ds_read_b64_tr_b16 v[10:11], v34 offset:4448
	ds_read_b64_tr_b16 v[12:13], v34 offset:4576
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[226:229], v[10:13], v[6:9], v[226:229]
	ds_read_b64_tr_b16 v[10:11], v34 offset:8704
	ds_read_b64_tr_b16 v[12:13], v34 offset:8832
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[222:225], v[10:13], v[6:9], v[222:225]
	ds_read_b64_tr_b16 v[10:11], v34 offset:8736
	ds_read_b64_tr_b16 v[12:13], v34 offset:8864
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[214:217], v[10:13], v[6:9], v[214:217]
	ds_read_b64_tr_b16 v[10:11], v34 offset:8768
	ds_read_b64_tr_b16 v[12:13], v34 offset:8896
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[206:209], v[10:13], v[6:9], v[206:209]
	ds_read_b64_tr_b16 v[10:11], v34 offset:8800
	ds_read_b64_tr_b16 v[12:13], v34 offset:8928
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[198:201], v[10:13], v[6:9], v[198:201]
	ds_read_b64_tr_b16 v[10:11], v34 offset:13056
	ds_read_b64_tr_b16 v[12:13], v34 offset:13184
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[190:193], v[10:13], v[6:9], v[190:193]
	ds_read_b64_tr_b16 v[10:11], v34 offset:13088
	ds_read_b64_tr_b16 v[12:13], v34 offset:13216
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[182:185], v[10:13], v[6:9], v[182:185]
	ds_read_b64_tr_b16 v[10:11], v34 offset:13120
	ds_read_b64_tr_b16 v[12:13], v34 offset:13248
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[174:177], v[10:13], v[6:9], v[174:177]
	ds_read_b64_tr_b16 v[10:11], v34 offset:13152
	ds_read_b64_tr_b16 v[12:13], v34 offset:13280
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[250:253], v[14:17], v[6:9], v[250:253]
	v_mfma_f32_16x16x32_f16 v[0:3], v[10:13], v[6:9], v[0:3]
	s_mov_b32 m0, s97
	s_barrier
	buffer_load_dwordx4 v97, s[80:83], s51 offen lds
	s_mov_b32 m0, s98
	v_accvgpr_read_b32 v54, a39
	buffer_load_dwordx4 v54, s[80:83], s51 offen lds
	s_mov_b32 m0, s99
	s_nop 0
	buffer_load_dwordx4 v59, s[80:83], s51 offen lds
	s_mov_b32 m0, s39
	s_nop 0
	buffer_load_dwordx4 v62, s[80:83], s51 offen lds
	s_mov_b32 m0, s28
	s_nop 0
	buffer_load_dwordx4 v68, s[76:79], s45 offen lds
	s_mov_b32 m0, s29
	s_nop 0
	buffer_load_dwordx4 v95, s[76:79], s45 offen lds
	s_mov_b32 m0, s64
	s_nop 0
	buffer_load_dwordx4 v103, s[76:79], s45 offen lds
	s_mov_b32 m0, s65
	s_nop 0
	buffer_load_dwordx4 v105, s[76:79], s45 offen lds
	s_waitcnt vmcnt(8)
	s_barrier
	ds_read_b128 v[6:9], v125 offset:34816
	ds_read_b128 v[10:13], v125 offset:34880
	ds_read_b128 v[14:17], v125 offset:39168
	s_waitcnt lgkmcnt(2)
	v_and_b32_e32 v9, v9, v53
	v_and_b32_e32 v8, v8, v92
	v_and_b32_e32 v7, v7, v55
	v_and_b32_e32 v6, v6, v42
	s_waitcnt lgkmcnt(1)
	v_and_b32_e32 v13, v13, v63
	v_and_b32_e32 v12, v12, v64
	v_and_b32_e32 v11, v11, v57
	v_and_b32_e32 v10, v10, v60
	v_mfma_f32_16x16x32_f16 v[6:9], v[6:9], a[12:15], 0
	s_nop 0
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[20:23], v[6:9]
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v17, v71
	v_and_b32_e32 v12, v16, v72
	v_and_b32_e32 v11, v15, v65
	v_and_b32_e32 v10, v14, v58
	ds_read_b128 v[14:17], v125 offset:52288
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v75
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[32:35], v[6:9]
	ds_read_b128 v[10:13], v125 offset:39232
	v_and_b32_e32 v16, v16, v96
	v_and_b32_e32 v15, v15, v69
	v_and_b32_e32 v14, v14, v74
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v81
	v_and_b32_e32 v12, v12, v70
	v_and_b32_e32 v11, v11, v73
	v_and_b32_e32 v10, v10, v66
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[44:47], v[6:9]
	ds_read_b128 v[10:13], v125 offset:43520
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v35
	v_and_b32_e32 v12, v12, v80
	v_and_b32_e32 v11, v11, v79
	v_and_b32_e32 v10, v10, v78
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[56:59], v[6:9]
	ds_read_b128 v[10:13], v125 offset:43584
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v43
	v_and_b32_e32 v12, v12, v76
	v_and_b32_e32 v11, v11, v37
	v_and_b32_e32 v10, v10, v44
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[66:69], v[6:9]
	ds_read_b128 v[10:13], v125 offset:47872
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v51
	v_and_b32_e32 v12, v12, v52
	v_and_b32_e32 v11, v11, v45
	v_and_b32_e32 v10, v10, v50
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[70:73], v[6:9]
	ds_read_b128 v[10:13], v125 offset:47936
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v89
	v_and_b32_e32 v12, v12, v86
	v_and_b32_e32 v11, v11, v87
	v_and_b32_e32 v10, v10, v56
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[6:9], v[10:13], a[76:79], v[6:9]
	ds_read_b128 v[10:13], v125 offset:52224
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v67
	v_and_b32_e32 v12, v12, v84
	v_and_b32_e32 v11, v11, v61
	v_and_b32_e32 v10, v10, v88
	s_nop 1
	v_mov_b32_e32 v32, v6
	v_mov_b32_e32 v30, v8
	v_mfma_f32_16x16x32_f16 v[10:13], v[10:13], a[84:87], 0
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[88:91], v[10:13]
	ds_read_b128 v[14:17], v125 offset:56576
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v83
	v_and_b32_e32 v16, v16, v94
	v_and_b32_e32 v15, v15, v77
	v_and_b32_e32 v14, v14, v82
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[92:95], v[10:13]
	ds_read_b128 v[14:17], v125 offset:56640
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v91
	v_and_b32_e32 v16, v16, v104
	v_and_b32_e32 v15, v15, v85
	v_and_b32_e32 v14, v14, v90
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[96:99], v[10:13]
	ds_read_b128 v[14:17], v125 offset:60928
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v99
	v_and_b32_e32 v16, v16, v100
	v_and_b32_e32 v15, v15, v93
	v_and_b32_e32 v14, v14, v98
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[112:115], v[10:13]
	ds_read_b128 v[14:17], v125 offset:60992
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v107
	v_and_b32_e32 v16, v16, v108
	v_and_b32_e32 v15, v15, v101
	v_and_b32_e32 v14, v14, v106
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[110:113], v[10:13]
	ds_read_b128 v[14:17], v125 offset:65280
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v115
	v_and_b32_e32 v16, v16, v116
	v_and_b32_e32 v15, v15, v109
	v_and_b32_e32 v14, v14, v114
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[118:121], v[10:13]
	ds_read_b128 v[14:17], v125 offset:65344
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v123
	v_and_b32_e32 v16, v16, v124
	v_and_b32_e32 v15, v15, v117
	v_and_b32_e32 v14, v14, v122
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[22:25], v[14:17], v[126:129], v[10:13]
	ds_read_b128 v[14:17], v28 offset:34880
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v63
	ds_read_b128 v[10:13], v28 offset:34816
	v_and_b32_e32 v16, v16, v64
	v_and_b32_e32 v15, v15, v57
	v_and_b32_e32 v14, v14, v60
	s_nop 0
	v_pk_mul_f32 v[22:23], v[22:23], s[70:71]
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v53
	v_and_b32_e32 v12, v12, v92
	v_and_b32_e32 v11, v11, v55
	v_and_b32_e32 v10, v10, v42
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[10:13], a[12:15], 0
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[20:23], v[10:13]
	ds_read_b128 v[14:17], v28 offset:39168
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v71
	v_and_b32_e32 v16, v16, v72
	v_and_b32_e32 v15, v15, v65
	v_and_b32_e32 v14, v14, v58
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[32:35], v[10:13]
	ds_read_b128 v[14:17], v28 offset:39232
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v81
	v_and_b32_e32 v16, v16, v70
	v_and_b32_e32 v15, v15, v73
	v_and_b32_e32 v14, v14, v66
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[44:47], v[10:13]
	ds_read_b128 v[14:17], v28 offset:43520
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v35
	v_and_b32_e32 v16, v16, v80
	v_and_b32_e32 v15, v15, v79
	v_and_b32_e32 v14, v14, v78
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[56:59], v[10:13]
	ds_read_b128 v[14:17], v28 offset:43584
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v43
	v_and_b32_e32 v16, v16, v76
	v_and_b32_e32 v15, v15, v37
	v_and_b32_e32 v14, v14, v44
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[66:69], v[10:13]
	ds_read_b128 v[14:17], v28 offset:47872
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v51
	v_and_b32_e32 v16, v16, v52
	v_and_b32_e32 v15, v15, v45
	v_and_b32_e32 v14, v14, v50
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[70:73], v[10:13]
	ds_read_b128 v[14:17], v28 offset:47936
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v89
	v_and_b32_e32 v16, v16, v86
	v_and_b32_e32 v15, v15, v87
	v_and_b32_e32 v14, v14, v56
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[38:41], v[14:17], a[76:79], v[10:13]
	ds_read_b128 v[14:17], v28 offset:52288
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v75
	ds_read_b128 v[10:13], v28 offset:52224
	v_and_b32_e32 v16, v16, v96
	v_and_b32_e32 v15, v15, v69
	v_and_b32_e32 v14, v14, v74
	s_nop 0
	v_mov_b32_e32 v26, v38
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v13, v13, v67
	v_and_b32_e32 v12, v12, v84
	v_and_b32_e32 v11, v11, v61
	v_and_b32_e32 v10, v10, v88
	v_mov_b32_e32 v20, v40
	s_nop 0
	v_mfma_f32_16x16x32_f16 v[10:13], v[10:13], a[84:87], 0
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[88:91], v[10:13]
	ds_read_b128 v[14:17], v28 offset:56576
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v83
	v_and_b32_e32 v16, v16, v94
	v_and_b32_e32 v15, v15, v77
	v_and_b32_e32 v14, v14, v82
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[92:95], v[10:13]
	ds_read_b128 v[14:17], v28 offset:56640
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v91
	v_and_b32_e32 v16, v16, v104
	v_and_b32_e32 v15, v15, v85
	v_and_b32_e32 v14, v14, v90
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[96:99], v[10:13]
	ds_read_b128 v[14:17], v28 offset:60928
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v99
	v_and_b32_e32 v16, v16, v100
	v_and_b32_e32 v15, v15, v93
	v_and_b32_e32 v14, v14, v98
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], a[112:115], v[10:13]
	ds_read_b128 v[14:17], v28 offset:60992
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v107
	v_and_b32_e32 v16, v16, v108
	v_and_b32_e32 v15, v15, v101
	v_and_b32_e32 v14, v14, v106
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[110:113], v[10:13]
	ds_read_b128 v[14:17], v28 offset:65280
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v17, v17, v115
	v_and_b32_e32 v16, v16, v116
	v_and_b32_e32 v15, v15, v109
	v_and_b32_e32 v14, v14, v114
	s_nop 1
	v_mfma_f32_16x16x32_f16 v[10:13], v[14:17], v[118:121], v[10:13]
	ds_read_b128 v[14:17], v28 offset:65344
	s_waitcnt lgkmcnt(0)
	v_and_b32_e32 v49, v17, v123
	v_and_b32_e32 v48, v16, v124
	v_and_b32_e32 v47, v15, v117
	v_and_b32_e32 v46, v14, v122
	buffer_load_dwordx4 v[14:17], v29, s[72:75], 0 offen offset:128
	s_waitcnt vmcnt(0)
	v_mov_b32_e32 v33, v14
	v_mov_b32_e32 v14, v7
	v_mov_b32_e32 v31, v16
	v_mov_b32_e32 v16, v9
	buffer_load_dwordx4 v[6:9], v29, s[72:75], 0 offen offset:144
	v_mfma_f32_16x16x32_f16 v[10:13], v[46:49], v[126:129], v[10:13]
	v_mul_f32_e64 v14, v14, v4
	v_mul_f32_e64 v15, v15, v5
	s_waitcnt vmcnt(0)
	v_mov_b32_e32 v27, v6
	v_mov_b32_e32 v6, v39
	v_lshl_add_u64 v[38:39], v[18:19], 0, 32
	v_mul_lo_u32 v36, v38, s90
	v_mul_lo_u32 v40, v39, s93
	v_mad_u64_u32 v[38:39], s[8:9], v38, s93, v[254:255]
	v_add3_u32 v36, v40, v39, v36
	v_xor_b32_e32 v36, s94, v36
	v_mad_u64_u32 v[38:39], s[8:9], v38, s41, 0
	v_mul_hi_u32 v40, v36, s41
	v_xor_b32_e32 v38, v38, v40
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v40, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mov_b32_e32 v21, v8
	v_mov_b32_e32 v8, v41
	v_mul_hi_u32 v41, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v40, v40, v41
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v41, v39, s41
	v_xor_b32_e32 v36, v36, v41
	v_xor_b32_e32 v36, s35, v36
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v41, v36, s42
	v_xor_b32_e32 v40, s34, v40
	v_xor_b32_e32 v38, v38, v41
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v41, v40, s41
	v_xor_b32_e32 v39, v39, v41
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v41, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v36, v36, v41
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v41, v38, s41
	v_xor_b32_e32 v40, v40, v41
	v_xor_b32_e32 v40, s52, v40
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v41, v40, s42
	v_xor_b32_e32 v36, s67, v36
	v_xor_b32_e32 v41, v39, v41
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v39, v36, s41
	v_xor_b32_e32 v38, v38, v39
	v_xor_b32_e32 v46, s56, v38
	v_mul_lo_u32 v38, v40, s42
	v_mul_hi_u32 v39, v46, s42
	v_xor_b32_e32 v40, v38, v39
	v_lshl_add_u64 v[38:39], v[18:19], 0, 33
	v_mul_lo_u32 v47, v38, s90
	v_mul_lo_u32 v48, v39, s93
	v_mad_u64_u32 v[38:39], s[8:9], v38, s93, v[254:255]
	v_add3_u32 v39, v48, v39, v47
	v_xor_b32_e32 v47, s94, v39
	v_mad_u64_u32 v[38:39], s[8:9], v38, s41, 0
	v_mul_hi_u32 v48, v47, s41
	v_xor_b32_e32 v38, v38, v48
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v48, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v47, v47, v49
	v_xor_b32_e32 v47, s35, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v48, s34, v48
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v39, v39, v49
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v48, v48, v49
	v_xor_b32_e32 v48, s52, v48
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v47, s67, v47
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v38, v38, v49
	v_xor_b32_e32 v38, s56, v38
	v_mul_lo_u32 v48, v48, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s53, v39
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v41, s53, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v49, v41, s41
	v_xor_b32_e32 v36, v36, v49
	v_xor_b32_e32 v47, s58, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v36, s58, v36
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v46, v46, s42
	v_mul_hi_u32 v49, v36, s42
	v_xor_b32_e32 v48, s57, v48
	v_xor_b32_e32 v46, v46, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v40, s57, v40
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v49, v40, s41
	v_xor_b32_e32 v41, v41, v49
	v_xor_b32_e32 v39, s60, v39
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v41, s60, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v49, v41, s42
	v_xor_b32_e32 v38, s59, v38
	v_xor_b32_e32 v36, v36, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v46, s59, v46
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v49, v46, s41
	v_xor_b32_e32 v40, v40, v49
	v_xor_b32_e32 v48, s62, v48
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v40, s62, v40
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v41, v41, s42
	v_mul_hi_u32 v49, v40, s42
	v_xor_b32_e32 v47, s61, v47
	v_xor_b32_e32 v41, v41, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v36, s61, v36
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v49, v36, s41
	v_xor_b32_e32 v39, s63, v39
	v_mul_lo_u32 v48, v48, s42
	v_xor_b32_e32 v46, v46, v49
	v_cndmask_b32_e64 v39, v39, v48, s[2:3]
	v_xor_b32_e32 v41, s63, v41
	v_mul_lo_u32 v40, v40, s42
	v_xor_b32_e32 v38, s36, v38
	v_cndmask_b32_e64 v40, v41, v40, s[2:3]
	v_cndmask_b32_e64 v38, v39, v38, s[4:5]
	v_xor_b32_e32 v39, s36, v46
	v_cndmask_b32_e64 v39, v40, v39, s[4:5]
	v_mul_lo_u32 v40, v47, s41
	v_mul_lo_u32 v36, v36, s41
	v_cndmask_b32_e64 v38, v38, v40, s[6:7]
	v_cndmask_b32_e64 v36, v39, v36, s[6:7]
	v_cmp_lt_i32_e32 vcc, s68, v38
	v_cmp_lt_i32_e64 s[8:9], s68, v36
	v_pk_mul_f32 v[10:11], v[10:11], s[70:71]
	v_cndmask_b32_e32 v39, 0, v23, vcc
	v_cndmask_b32_e64 v38, 0, v22, s[8:9]
	v_pk_mul_f32 v[22:23], v[24:25], s[70:71]
	v_lshl_add_u64 v[24:25], v[18:19], 0, 34
	v_mul_lo_u32 v36, v24, s90
	v_mul_lo_u32 v40, v25, s93
	v_mad_u64_u32 v[24:25], s[10:11], v24, s93, v[254:255]
	v_add3_u32 v25, v40, v25, v36
	v_xor_b32_e32 v36, s94, v25
	v_mad_u64_u32 v[24:25], s[10:11], v24, s41, 0
	v_mul_hi_u32 v40, v36, s41
	v_xor_b32_e32 v24, v24, v40
	v_xor_b32_e32 v25, s95, v25
	v_xor_b32_e32 v24, s47, v24
	v_mul_lo_u32 v40, v25, s42
	v_mul_hi_u32 v25, v25, s42
	v_mul_hi_u32 v41, v24, s42
	v_xor_b32_e32 v25, s46, v25
	v_xor_b32_e32 v40, v40, v41
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v41, v25, s41
	v_xor_b32_e32 v36, v36, v41
	v_xor_b32_e32 v36, s35, v36
	v_mul_lo_u32 v24, v24, s42
	v_mul_hi_u32 v41, v36, s42
	v_xor_b32_e32 v40, s34, v40
	v_xor_b32_e32 v24, v24, v41
	v_mul_lo_u32 v25, v25, s41
	v_mul_hi_u32 v41, v40, s41
	v_xor_b32_e32 v25, v25, v41
	v_xor_b32_e32 v25, s66, v25
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v41, v25, s42
	v_xor_b32_e32 v24, s91, v24
	v_xor_b32_e32 v36, v36, v41
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v41, v24, s41
	v_xor_b32_e32 v40, v40, v41
	v_xor_b32_e32 v40, s52, v40
	v_mul_lo_u32 v25, v25, s42
	v_mul_hi_u32 v41, v40, s42
	v_xor_b32_e32 v36, s67, v36
	v_xor_b32_e32 v41, v25, v41
	v_mul_lo_u32 v24, v24, s41
	v_mul_hi_u32 v25, v36, s41
	v_xor_b32_e32 v24, v24, v25
	v_xor_b32_e32 v46, s56, v24
	v_mul_lo_u32 v24, v40, s42
	v_mul_hi_u32 v25, v46, s42
	v_xor_b32_e32 v40, v24, v25
	v_lshl_add_u64 v[24:25], v[18:19], 0, 35
	v_mul_lo_u32 v47, v24, s90
	v_mul_lo_u32 v48, v25, s93
	v_mad_u64_u32 v[24:25], s[10:11], v24, s93, v[254:255]
	v_add3_u32 v25, v48, v25, v47
	v_xor_b32_e32 v47, s94, v25
	v_mad_u64_u32 v[24:25], s[10:11], v24, s41, 0
	v_mul_hi_u32 v48, v47, s41
	v_xor_b32_e32 v24, v24, v48
	v_xor_b32_e32 v25, s95, v25
	v_xor_b32_e32 v24, s47, v24
	v_mul_lo_u32 v48, v25, s42
	v_mul_hi_u32 v25, v25, s42
	v_mul_hi_u32 v49, v24, s42
	v_xor_b32_e32 v25, s46, v25
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v25, s41
	v_xor_b32_e32 v47, v47, v49
	v_xor_b32_e32 v47, s35, v47
	v_mul_lo_u32 v24, v24, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v48, s34, v48
	v_xor_b32_e32 v24, v24, v49
	v_mul_lo_u32 v25, v25, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v25, v25, v49
	v_xor_b32_e32 v25, s66, v25
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v25, s42
	v_xor_b32_e32 v24, s91, v24
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v24, s41
	v_xor_b32_e32 v48, v48, v49
	v_xor_b32_e32 v48, s52, v48
	v_mul_lo_u32 v25, v25, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v47, s67, v47
	v_xor_b32_e32 v25, v25, v49
	v_mul_lo_u32 v24, v24, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v24, v24, v49
	v_xor_b32_e32 v24, s56, v24
	v_mul_lo_u32 v48, v48, s42
	v_mul_hi_u32 v49, v24, s42
	v_xor_b32_e32 v25, s53, v25
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v25, s41
	v_xor_b32_e32 v41, s53, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v49, v41, s41
	v_xor_b32_e32 v36, v36, v49
	v_xor_b32_e32 v47, s58, v47
	v_mul_lo_u32 v24, v24, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v36, s58, v36
	v_xor_b32_e32 v24, v24, v49
	v_mul_lo_u32 v46, v46, s42
	v_mul_hi_u32 v49, v36, s42
	v_xor_b32_e32 v48, s57, v48
	v_xor_b32_e32 v46, v46, v49
	v_mul_lo_u32 v25, v25, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v40, s57, v40
	v_xor_b32_e32 v25, v25, v49
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v49, v40, s41
	v_xor_b32_e32 v41, v41, v49
	v_xor_b32_e32 v25, s60, v25
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v25, s42
	v_xor_b32_e32 v41, s60, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v49, v41, s42
	v_xor_b32_e32 v24, s59, v24
	v_xor_b32_e32 v36, v36, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v24, s41
	v_xor_b32_e32 v46, s59, v46
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v49, v46, s41
	v_xor_b32_e32 v40, v40, v49
	v_xor_b32_e32 v48, s62, v48
	v_mul_lo_u32 v25, v25, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v40, s62, v40
	v_xor_b32_e32 v25, v25, v49
	v_mul_lo_u32 v41, v41, s42
	v_mul_hi_u32 v49, v40, s42
	v_xor_b32_e32 v47, s61, v47
	v_xor_b32_e32 v41, v41, v49
	v_mul_lo_u32 v24, v24, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v36, s61, v36
	v_xor_b32_e32 v24, v24, v49
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v49, v36, s41
	v_xor_b32_e32 v25, s63, v25
	v_mul_lo_u32 v48, v48, s42
	v_xor_b32_e32 v46, v46, v49
	v_cndmask_b32_e64 v25, v25, v48, s[2:3]
	v_xor_b32_e32 v41, s63, v41
	v_mul_lo_u32 v40, v40, s42
	v_xor_b32_e32 v24, s36, v24
	v_cndmask_b32_e64 v40, v41, v40, s[2:3]
	v_cndmask_b32_e64 v24, v25, v24, s[4:5]
	v_xor_b32_e32 v25, s36, v46
	v_cndmask_b32_e64 v25, v40, v25, s[4:5]
	v_mul_lo_u32 v40, v47, s41
	v_mul_lo_u32 v36, v36, s41
	v_cndmask_b32_e64 v24, v24, v40, s[6:7]
	v_cndmask_b32_e64 v25, v25, v36, s[6:7]
	v_cmp_lt_i32_e64 s[10:11], s68, v24
	v_cmp_lt_i32_e64 s[12:13], s68, v25
	v_pk_mul_f32 v[12:13], v[12:13], s[70:71]
	v_cndmask_b32_e64 v41, 0, v23, s[10:11]
	v_cndmask_b32_e64 v40, 0, v22, s[12:13]
	buffer_load_dwordx4 v[22:25], v29, s[84:87], 0 offen offset:128
	v_pk_mul_f32 v[6:7], v[6:7], v[4:5]
	v_pk_mul_f32 v[8:9], v[8:9], v[4:5]
	s_waitcnt vmcnt(0)
	v_pk_add_f32 v[22:23], v[38:39], v[22:23] neg_lo:[0,1] neg_hi:[0,1]
	v_lshl_add_u64 v[38:39], v[18:19], 0, 36
	v_pk_add_f32 v[24:25], v[40:41], v[24:25] neg_lo:[0,1] neg_hi:[0,1]
	v_mul_lo_u32 v36, v38, s90
	v_mul_lo_u32 v40, v39, s93
	v_mad_u64_u32 v[38:39], s[14:15], v38, s93, v[254:255]
	v_add3_u32 v36, v40, v39, v36
	v_xor_b32_e32 v36, s94, v36
	v_mad_u64_u32 v[38:39], s[14:15], v38, s41, 0
	v_mul_hi_u32 v40, v36, s41
	v_xor_b32_e32 v38, v38, v40
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v40, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v41, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v40, v40, v41
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v41, v39, s41
	v_xor_b32_e32 v36, v36, v41
	v_xor_b32_e32 v36, s35, v36
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v41, v36, s42
	v_xor_b32_e32 v40, s34, v40
	v_xor_b32_e32 v38, v38, v41
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v41, v40, s41
	v_xor_b32_e32 v39, v39, v41
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v41, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v36, v36, v41
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v41, v38, s41
	v_xor_b32_e32 v40, v40, v41
	v_xor_b32_e32 v40, s52, v40
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v41, v40, s42
	v_xor_b32_e32 v36, s67, v36
	v_xor_b32_e32 v41, v39, v41
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v39, v36, s41
	v_xor_b32_e32 v38, v38, v39
	v_xor_b32_e32 v46, s56, v38
	v_mul_lo_u32 v38, v40, s42
	v_mul_hi_u32 v39, v46, s42
	v_xor_b32_e32 v40, v38, v39
	v_lshl_add_u64 v[38:39], v[18:19], 0, 37
	v_mul_lo_u32 v47, v38, s90
	v_mul_lo_u32 v48, v39, s93
	v_mad_u64_u32 v[38:39], s[14:15], v38, s93, v[254:255]
	v_add3_u32 v39, v48, v39, v47
	v_xor_b32_e32 v47, s94, v39
	v_mad_u64_u32 v[38:39], s[14:15], v38, s41, 0
	v_mul_hi_u32 v48, v47, s41
	v_xor_b32_e32 v38, v38, v48
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v48, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v47, v47, v49
	v_xor_b32_e32 v47, s35, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v48, s34, v48
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v39, v39, v49
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v48, v48, v49
	v_xor_b32_e32 v48, s52, v48
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v47, s67, v47
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v38, v38, v49
	v_xor_b32_e32 v38, s56, v38
	v_mul_lo_u32 v48, v48, s42
	v_mul_hi_u32 v49, v38, s42
	v_xor_b32_e32 v39, s53, v39
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v47, v47, s41
	v_mul_hi_u32 v49, v39, s41
	v_xor_b32_e32 v41, s53, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v49, v41, s41
	v_xor_b32_e32 v36, v36, v49
	v_xor_b32_e32 v47, s58, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v49, v47, s42
	v_xor_b32_e32 v36, s58, v36
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v46, v46, s42
	v_mul_hi_u32 v49, v36, s42
	v_xor_b32_e32 v48, s57, v48
	v_xor_b32_e32 v46, v46, v49
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v49, v48, s41
	v_xor_b32_e32 v40, s57, v40
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v49, v40, s41
	v_xor_b32_e32 v41, v41, v49
	v_xor_b32_e32 v39, s60, v39
	v_mul_lo_u32 v47, v47, s42
	v_mul_hi_u32 v49, v39, s42
	v_xor_b32_e32 v41, s60, v41
	v_xor_b32_e32 v47, v47, v49
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v49, v41, s42
	v_xor_b32_e32 v38, s59, v38
	v_xor_b32_e32 v36, v36, v49
	v_mul_lo_u32 v48, v48, s41
	v_mul_hi_u32 v49, v38, s41
	v_xor_b32_e32 v46, s59, v46
	v_xor_b32_e32 v48, v48, v49
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v49, v46, s41
	v_xor_b32_e32 v40, v40, v49
	v_xor_b32_e32 v48, s62, v48
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v49, v48, s42
	v_xor_b32_e32 v40, s62, v40
	v_xor_b32_e32 v39, v39, v49
	v_mul_lo_u32 v41, v41, s42
	v_mul_hi_u32 v49, v40, s42
	v_xor_b32_e32 v47, s61, v47
	v_xor_b32_e32 v41, v41, v49
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v49, v47, s41
	v_xor_b32_e32 v36, s61, v36
	v_xor_b32_e32 v38, v38, v49
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v49, v36, s41
	v_xor_b32_e32 v39, s63, v39
	v_mul_lo_u32 v48, v48, s42
	v_xor_b32_e32 v46, v46, v49
	v_cndmask_b32_e64 v39, v39, v48, s[2:3]
	v_xor_b32_e32 v41, s63, v41
	v_mul_lo_u32 v40, v40, s42
	v_xor_b32_e32 v38, s36, v38
	v_cndmask_b32_e64 v40, v41, v40, s[2:3]
	v_cndmask_b32_e64 v38, v39, v38, s[4:5]
	v_xor_b32_e32 v39, s36, v46
	v_cndmask_b32_e64 v39, v40, v39, s[4:5]
	v_mul_lo_u32 v40, v47, s41
	v_cndmask_b32_e64 v38, v38, v40, s[6:7]
	v_mul_lo_u32 v36, v36, s41
	v_cndmask_b32_e64 v36, v39, v36, s[6:7]
	v_cmp_lt_i32_e64 s[14:15], s68, v38
	v_lshl_add_u64 v[38:39], v[18:19], 0, 38
	v_cmp_lt_i32_e64 s[16:17], s68, v36
	v_mul_lo_u32 v36, v38, s90
	v_mul_lo_u32 v40, v39, s93
	v_mad_u64_u32 v[38:39], s[18:19], v38, s93, v[254:255]
	v_add3_u32 v36, v40, v39, v36
	v_xor_b32_e32 v36, s94, v36
	v_mad_u64_u32 v[38:39], s[18:19], v38, s41, 0
	v_mul_hi_u32 v40, v36, s41
	v_xor_b32_e32 v38, v38, v40
	v_xor_b32_e32 v39, s95, v39
	v_xor_b32_e32 v38, s47, v38
	v_mul_lo_u32 v40, v39, s42
	v_mul_hi_u32 v39, v39, s42
	v_mul_hi_u32 v41, v38, s42
	v_xor_b32_e32 v39, s46, v39
	v_xor_b32_e32 v40, v40, v41
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v41, v39, s41
	v_xor_b32_e32 v36, v36, v41
	v_xor_b32_e32 v36, s35, v36
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v41, v36, s42
	v_xor_b32_e32 v40, s34, v40
	v_xor_b32_e32 v38, v38, v41
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v41, v40, s41
	v_xor_b32_e32 v39, v39, v41
	v_xor_b32_e32 v39, s66, v39
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v41, v39, s42
	v_xor_b32_e32 v38, s91, v38
	v_xor_b32_e32 v36, v36, v41
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v41, v38, s41
	v_xor_b32_e32 v40, v40, v41
	v_xor_b32_e32 v40, s52, v40
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v41, v40, s42
	v_xor_b32_e32 v36, s67, v36
	v_xor_b32_e32 v39, v39, v41
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v41, v36, s41
	v_xor_b32_e32 v38, v38, v41
	v_xor_b32_e32 v38, s56, v38
	v_mul_lo_u32 v40, v40, s42
	v_mul_hi_u32 v41, v38, s42
	v_lshl_add_u64 v[18:19], v[18:19], 0, 39
	v_xor_b32_e32 v40, v40, v41
	v_mul_lo_u32 v41, v18, s90
	v_mul_lo_u32 v46, v19, s93
	v_mad_u64_u32 v[18:19], s[18:19], v18, s93, v[254:255]
	v_add3_u32 v19, v46, v19, v41
	v_xor_b32_e32 v41, s94, v19
	v_mad_u64_u32 v[18:19], s[18:19], v18, s41, 0
	v_mul_hi_u32 v46, v41, s41
	v_xor_b32_e32 v18, v18, v46
	v_xor_b32_e32 v19, s95, v19
	v_xor_b32_e32 v18, s47, v18
	v_mul_lo_u32 v46, v19, s42
	v_mul_hi_u32 v19, v19, s42
	v_mul_hi_u32 v47, v18, s42
	v_xor_b32_e32 v19, s46, v19
	v_xor_b32_e32 v46, v46, v47
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v47, v19, s41
	v_xor_b32_e32 v41, v41, v47
	v_xor_b32_e32 v41, s35, v41
	v_mul_lo_u32 v18, v18, s42
	v_mul_hi_u32 v47, v41, s42
	v_xor_b32_e32 v46, s34, v46
	v_xor_b32_e32 v18, v18, v47
	v_mul_lo_u32 v19, v19, s41
	v_mul_hi_u32 v47, v46, s41
	v_xor_b32_e32 v19, v19, v47
	v_xor_b32_e32 v19, s66, v19
	v_mul_lo_u32 v41, v41, s42
	v_mul_hi_u32 v47, v19, s42
	v_xor_b32_e32 v18, s91, v18
	v_xor_b32_e32 v41, v41, v47
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v47, v18, s41
	v_xor_b32_e32 v46, v46, v47
	v_xor_b32_e32 v46, s52, v46
	v_mul_lo_u32 v19, v19, s42
	v_mul_hi_u32 v47, v46, s42
	v_xor_b32_e32 v41, s67, v41
	v_xor_b32_e32 v19, v19, v47
	v_mul_lo_u32 v18, v18, s41
	v_mul_hi_u32 v47, v41, s41
	v_xor_b32_e32 v18, v18, v47
	v_xor_b32_e32 v18, s56, v18
	v_mul_lo_u32 v46, v46, s42
	v_mul_hi_u32 v47, v18, s42
	v_xor_b32_e32 v19, s53, v19
	v_xor_b32_e32 v46, v46, v47
	v_mul_lo_u32 v41, v41, s41
	v_mul_hi_u32 v47, v19, s41
	v_xor_b32_e32 v39, s53, v39
	v_xor_b32_e32 v41, v41, v47
	v_mul_lo_u32 v36, v36, s41
	v_mul_hi_u32 v47, v39, s41
	v_xor_b32_e32 v36, v36, v47
	v_xor_b32_e32 v41, s58, v41
	v_mul_lo_u32 v18, v18, s42
	v_mul_hi_u32 v47, v41, s42
	v_xor_b32_e32 v36, s58, v36
	v_xor_b32_e32 v18, v18, v47
	v_mul_lo_u32 v38, v38, s42
	v_mul_hi_u32 v47, v36, s42
	v_xor_b32_e32 v46, s57, v46
	v_xor_b32_e32 v38, v38, v47
	v_mul_lo_u32 v19, v19, s41
	v_mul_hi_u32 v47, v46, s41
	v_xor_b32_e32 v40, s57, v40
	v_xor_b32_e32 v19, v19, v47
	v_mul_lo_u32 v39, v39, s41
	v_mul_hi_u32 v47, v40, s41
	v_xor_b32_e32 v39, v39, v47
	v_xor_b32_e32 v19, s60, v19
	v_mul_lo_u32 v41, v41, s42
	v_mul_hi_u32 v47, v19, s42
	v_xor_b32_e32 v39, s60, v39
	v_xor_b32_e32 v41, v41, v47
	v_mul_lo_u32 v36, v36, s42
	v_mul_hi_u32 v47, v39, s42
	v_xor_b32_e32 v18, s59, v18
	v_xor_b32_e32 v36, v36, v47
	v_mul_lo_u32 v46, v46, s41
	v_mul_hi_u32 v47, v18, s41
	v_xor_b32_e32 v38, s59, v38
	v_xor_b32_e32 v46, v46, v47
	v_mul_lo_u32 v40, v40, s41
	v_mul_hi_u32 v47, v38, s41
	v_xor_b32_e32 v40, v40, v47
	v_xor_b32_e32 v46, s62, v46
	v_mul_lo_u32 v19, v19, s42
	v_mul_hi_u32 v47, v46, s42
	v_xor_b32_e32 v40, s62, v40
	v_xor_b32_e32 v19, v19, v47
	v_mul_lo_u32 v39, v39, s42
	v_mul_hi_u32 v47, v40, s42
	v_xor_b32_e32 v41, s61, v41
	v_xor_b32_e32 v39, v39, v47
	v_mul_lo_u32 v18, v18, s41
	v_mul_hi_u32 v47, v41, s41
	v_xor_b32_e32 v36, s61, v36
	v_xor_b32_e32 v18, v18, v47
	v_mul_lo_u32 v38, v38, s41
	v_mul_hi_u32 v47, v36, s41
	v_xor_b32_e32 v19, s63, v19
	v_mul_lo_u32 v46, v46, s42
	v_xor_b32_e32 v38, v38, v47
	v_cndmask_b32_e64 v19, v19, v46, s[2:3]
	v_xor_b32_e32 v39, s63, v39
	v_mul_lo_u32 v40, v40, s42
	v_xor_b32_e32 v18, s36, v18
	v_cndmask_b32_e64 v39, v39, v40, s[2:3]
	v_cndmask_b32_e64 v18, v19, v18, s[4:5]
	v_xor_b32_e32 v19, s36, v38
	v_mul_lo_u32 v38, v41, s41
	v_cndmask_b32_e64 v19, v39, v19, s[4:5]
	v_cndmask_b32_e64 v18, v18, v38, s[6:7]
	buffer_load_dwordx4 v[38:41], v29, s[84:87], 0 offen offset:144
	v_mul_lo_u32 v36, v36, s41
	v_cndmask_b32_e64 v19, v19, v36, s[6:7]
	v_cndmask_b32_e64 v11, 0, v11, s[14:15]
	v_cndmask_b32_e64 v10, 0, v10, s[16:17]
	v_cmp_lt_i32_e64 s[18:19], s68, v18
	v_cmp_lt_i32_e64 s[20:21], s68, v19
	v_accvgpr_read_b32 v46, a70
	v_cndmask_b32_e64 v19, 0, v13, s[18:19]
	v_cndmask_b32_e64 v18, 0, v12, s[20:21]
	v_accvgpr_read_b32 v47, a71
	v_accvgpr_read_b32 v48, a72
	v_accvgpr_read_b32 v49, a73
	s_waitcnt vmcnt(0)
	v_pk_add_f32 v[12:13], v[10:11], v[38:39] neg_lo:[0,1] neg_hi:[0,1]
	v_pk_mul_f32 v[38:39], v[16:17], v[4:5]
	v_pk_mul_f32 v[16:17], v[32:33], v[4:5]
	v_pk_add_f32 v[10:11], v[18:19], v[40:41] neg_lo:[0,1] neg_hi:[0,1]
	v_mov_b32_e32 v18, v16
	v_mov_b32_e32 v19, v14
	v_mov_b32_e32 v14, v17
	v_pk_mul_f32 v[16:17], v[30:31], v[4:5]
	v_mov_b32_e32 v31, v38
	v_mov_b32_e32 v30, v16
	v_mov_b32_e32 v38, v17
	v_pk_mul_f32 v[16:17], v[26:27], v[4:5]
	v_pk_add_f32 v[14:15], v[18:19], v[14:15] neg_lo:[0,1] neg_hi:[0,1]
	v_mov_b32_e32 v18, v16
	v_mov_b32_e32 v19, v6
	v_mov_b32_e32 v6, v17
	v_pk_add_f32 v[6:7], v[18:19], v[6:7] neg_lo:[0,1] neg_hi:[0,1]
	v_mov_b32_e32 v19, v8
	v_exp_f32_e32 v16, v6
	v_exp_f32_e32 v17, v7
	v_pk_mul_f32 v[6:7], v[20:21], v[4:5]
	v_exp_f32_e32 v14, v14
	v_mov_b32_e32 v18, v6
	v_mov_b32_e32 v8, v7
	v_pk_add_f32 v[6:7], v[18:19], v[8:9] neg_lo:[0,1] neg_hi:[0,1]
	v_exp_f32_e32 v15, v15
	v_exp_f32_e32 v18, v6
	v_exp_f32_e32 v19, v7
	v_pk_add_f32 v[6:7], v[30:31], v[38:39] neg_lo:[0,1] neg_hi:[0,1]
	;;#ASMSTART
	s_nop 0
	;;#ASMEND
	ds_read_b64_tr_b16 v[30:31], v34 offset:52224
	ds_read_b64_tr_b16 v[32:33], v34 offset:52352
	v_exp_f32_e32 v20, v6
	v_exp_f32_e32 v21, v7
	v_cvt_f16_f32_e32 v6, v16
	v_cvt_f16_f32_e32 v7, v17
	v_cvt_f16_f32_e32 v8, v18
	v_cvt_f16_f32_e32 v9, v19
	v_cndmask_b32_e64 v6, 0, v6, s[16:17]
	v_cndmask_b32_e64 v7, 0, v7, s[14:15]
	v_cndmask_b32_e64 v8, 0, v8, s[20:21]
	v_cndmask_b32_e64 v9, 0, v9, s[18:19]
	v_pack_b32_f16 v9, v8, v9
	v_pack_b32_f16 v8, v6, v7
	;;#ASMSTART
	s_nop 0
	;;#ASMEND
	v_pk_mul_f32 v[10:11], v[10:11], v[18:19]
	v_cvt_f16_f32_e32 v6, v20
	v_cvt_f16_f32_e32 v7, v21
	v_cvt_f16_f32_e32 v26, v15
	v_accvgpr_read_b32 v38, a76
	v_cndmask_b32_e64 v6, 0, v6, s[12:13]
	v_cndmask_b32_e64 v7, 0, v7, s[10:11]
	v_pack_b32_f16 v7, v6, v7
	v_cvt_f16_f32_e32 v6, v14
	v_cndmask_b32_e32 v26, 0, v26, vcc
	v_accvgpr_read_b32 v39, a77
	v_accvgpr_read_b32 v40, a78
	v_cndmask_b32_e64 v6, 0, v6, s[8:9]
	v_pack_b32_f16 v6, v6, v26
	;;#ASMSTART
	s_nop 1
	;;#ASMEND
	v_accvgpr_read_b32 v41, a79
	v_accvgpr_read_b32 v26, a94
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[218:221], v[30:33], v[6:9], v[218:221]
	ds_read_b64_tr_b16 v[30:31], v34 offset:52256
	ds_read_b64_tr_b16 v[32:33], v34 offset:52384
	v_accvgpr_read_b32 v27, a95
	v_mov_b32_e32 v18, v96
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[210:213], v[30:33], v[6:9], v[210:213]
	ds_read_b64_tr_b16 v[30:31], v34 offset:52288
	ds_read_b64_tr_b16 v[32:33], v34 offset:52416
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[202:205], v[30:33], v[6:9], v[202:205]
	ds_read_b64_tr_b16 v[30:31], v34 offset:52320
	ds_read_b64_tr_b16 v[32:33], v34 offset:52448
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[194:197], v[30:33], v[6:9], v[194:197]
	ds_read_b64_tr_b16 v[30:31], v34 offset:56576
	ds_read_b64_tr_b16 v[32:33], v34 offset:56704
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[186:189], v[30:33], v[6:9], v[186:189]
	ds_read_b64_tr_b16 v[30:31], v34 offset:56608
	ds_read_b64_tr_b16 v[32:33], v34 offset:56736
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[178:181], v[30:33], v[6:9], v[178:181]
	ds_read_b64_tr_b16 v[30:31], v34 offset:56640
	ds_read_b64_tr_b16 v[32:33], v34 offset:56768
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[170:173], v[30:33], v[6:9], v[170:173]
	ds_read_b64_tr_b16 v[30:31], v34 offset:56672
	ds_read_b64_tr_b16 v[32:33], v34 offset:56800
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[166:169], v[30:33], v[6:9], v[166:169]
	ds_read_b64_tr_b16 v[30:31], v34 offset:60928
	ds_read_b64_tr_b16 v[32:33], v34 offset:61056
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[162:165], v[30:33], v[6:9], v[162:165]
	ds_read_b64_tr_b16 v[30:31], v34 offset:60960
	ds_read_b64_tr_b16 v[32:33], v34 offset:61088
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[158:161], v[30:33], v[6:9], v[158:161]
	ds_read_b64_tr_b16 v[30:31], v34 offset:60992
	ds_read_b64_tr_b16 v[32:33], v34 offset:61120
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[154:157], v[30:33], v[6:9], v[154:157]
	ds_read_b64_tr_b16 v[30:31], v34 offset:61024
	ds_read_b64_tr_b16 v[32:33], v34 offset:61152
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[150:153], v[30:33], v[6:9], v[150:153]
	ds_read_b64_tr_b16 v[30:31], v34 offset:65280
	ds_read_b64_tr_b16 v[32:33], v34 offset:65408
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[146:149], v[30:33], v[6:9], v[146:149]
	ds_read_b64_tr_b16 v[30:31], v34 offset:65312
	ds_read_b64_tr_b16 v[32:33], v34 offset:65440
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[142:145], v[30:33], v[6:9], v[142:145]
	ds_read_b64_tr_b16 v[30:31], v34 offset:65344
	ds_read_b64_tr_b16 v[32:33], v34 offset:65472
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[138:141], v[30:33], v[6:9], v[138:141]
	ds_read_b64_tr_b16 v[30:31], v34 offset:65376
	ds_read_b64_tr_b16 v[32:33], v34 offset:65504
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[134:137], v[30:33], v[6:9], v[134:137]
	v_mul_f32_e64 v6, v22, v14
	v_mul_f32_e64 v7, v23, v15
	v_pk_mul_f32 v[8:9], v[24:25], v[20:21]
	v_cvt_pk_f16_f32 v6, v6, v7
	v_cvt_pk_f16_f32 v7, v8, v9
	v_pk_mul_f32 v[8:9], v[12:13], v[16:17]
	ds_read_b64_tr_b16 v[14:15], v34 offset:34848
	ds_read_b64_tr_b16 v[16:17], v34 offset:34976
	v_cvt_pk_f16_f32 v8, v8, v9
	v_cvt_pk_f16_f32 v9, v10, v11
	ds_read_b64_tr_b16 v[12:13], v34 offset:34944
	ds_read_b64_tr_b16 v[10:11], v34 offset:34816
	;;#ASMSTART
	s_nop 1
	;;#ASMEND
	v_accvgpr_read_b32 v30, a96
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[130:133], v[10:13], v[6:9], v[130:133]
	ds_read_b64_tr_b16 v[10:11], v34 offset:34880
	ds_read_b64_tr_b16 v[12:13], v34 offset:35008
	v_accvgpr_read_b32 v31, a97
	v_accvgpr_read_b32 v32, a98
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[246:249], v[10:13], v[6:9], v[246:249]
	ds_read_b64_tr_b16 v[10:11], v34 offset:34912
	ds_read_b64_tr_b16 v[12:13], v34 offset:35040
	v_accvgpr_read_b32 v33, a99
	v_accvgpr_read_b32 v24, a92
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[242:245], v[10:13], v[6:9], v[242:245]
	ds_read_b64_tr_b16 v[10:11], v34 offset:39168
	ds_read_b64_tr_b16 v[12:13], v34 offset:39296
	v_accvgpr_read_b32 v25, a93
	v_accvgpr_read_b32 v20, a88
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[238:241], v[10:13], v[6:9], v[238:241]
	ds_read_b64_tr_b16 v[10:11], v34 offset:39200
	ds_read_b64_tr_b16 v[12:13], v34 offset:39328
	v_accvgpr_read_b32 v21, a89
	v_accvgpr_read_b32 v22, a90
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[234:237], v[10:13], v[6:9], v[234:237]
	ds_read_b64_tr_b16 v[10:11], v34 offset:39232
	ds_read_b64_tr_b16 v[12:13], v34 offset:39360
	v_accvgpr_read_b32 v23, a91
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[230:233], v[10:13], v[6:9], v[230:233]
	ds_read_b64_tr_b16 v[10:11], v34 offset:39264
	ds_read_b64_tr_b16 v[12:13], v34 offset:39392
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[226:229], v[10:13], v[6:9], v[226:229]
	ds_read_b64_tr_b16 v[10:11], v34 offset:43520
	ds_read_b64_tr_b16 v[12:13], v34 offset:43648
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[222:225], v[10:13], v[6:9], v[222:225]
	ds_read_b64_tr_b16 v[10:11], v34 offset:43552
	ds_read_b64_tr_b16 v[12:13], v34 offset:43680
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[214:217], v[10:13], v[6:9], v[214:217]
	ds_read_b64_tr_b16 v[10:11], v34 offset:43584
	ds_read_b64_tr_b16 v[12:13], v34 offset:43712
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[206:209], v[10:13], v[6:9], v[206:209]
	ds_read_b64_tr_b16 v[10:11], v34 offset:43616
	ds_read_b64_tr_b16 v[12:13], v34 offset:43744
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[198:201], v[10:13], v[6:9], v[198:201]
	ds_read_b64_tr_b16 v[10:11], v34 offset:47872
	ds_read_b64_tr_b16 v[12:13], v34 offset:48000
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[190:193], v[10:13], v[6:9], v[190:193]
	ds_read_b64_tr_b16 v[10:11], v34 offset:47904
	ds_read_b64_tr_b16 v[12:13], v34 offset:48032
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[182:185], v[10:13], v[6:9], v[182:185]
	ds_read_b64_tr_b16 v[10:11], v34 offset:47936
	ds_read_b64_tr_b16 v[12:13], v34 offset:48064
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[174:177], v[10:13], v[6:9], v[174:177]
	ds_read_b64_tr_b16 v[10:11], v34 offset:47968
	ds_read_b64_tr_b16 v[12:13], v34 offset:48096
	s_waitcnt lgkmcnt(0)
	v_mfma_f32_16x16x32_f16 v[250:253], v[14:17], v[6:9], v[250:253]
	v_mfma_f32_16x16x32_f16 v[0:3], v[10:13], v[6:9], v[0:3]
	s_mov_b32 m0, s33
	s_barrier
	buffer_load_dwordx4 v97, s[80:83], s43 offen lds
	s_mov_b32 m0, s88
	v_mov_b64_e32 v[6:7], s[48:49]
	buffer_load_dwordx4 v54, s[80:83], s43 offen lds
	s_mov_b32 m0, s89
	v_cmp_gt_u64_e32 vcc, s[30:31], v[6:7]
	buffer_load_dwordx4 v59, s[80:83], s43 offen lds
	s_mov_b32 m0, s40
	s_add_i32 s51, s51, s37
	buffer_load_dwordx4 v62, s[80:83], s43 offen lds
	s_mov_b32 m0, s0
	s_add_i32 s45, s45, s38
	buffer_load_dwordx4 v68, s[76:79], s44 offen lds
	s_mov_b32 m0, s1
	v_add_u32_e32 v29, 0x100, v29
	buffer_load_dwordx4 v95, s[76:79], s44 offen lds
	s_mov_b32 m0, s96
	s_and_b64 vcc, exec, vcc
	buffer_load_dwordx4 v103, s[76:79], s44 offen lds
	s_mov_b32 m0, s92
	s_add_i32 s43, s43, s37
	buffer_load_dwordx4 v105, s[76:79], s44 offen lds
	s_add_i32 s44, s44, s38
	s_cbranch_vccnz .LBB0_36
	s_add_u32 s54, s54, 1
	s_addc_u32 s55, s55, 0
	s_mov_b64 s[8:9], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v6, off offset:404
	scratch_load_dword v6, off, off offset:144
	s_waitcnt vmcnt(0)
	v_readlane_b32 s72, v6, 0
	v_readlane_b32 s73, v6, 1
	scratch_load_dword v6, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[8:9]
	v_mov_b64_e32 v[6:7], s[72:73]
	v_cmp_lt_i64_e32 vcc, s[54:55], v[6:7]
	v_accvgpr_read_b32 v12, a39
	v_mov_b32_e32 v10, v103
	v_mov_b32_e32 v11, v105
	s_cbranch_vccnz .LBB0_33
	s_mov_b64 s[4:5], exec
	s_mov_b64 exec, 15
	scratch_store_dword off, v4, off offset:404
	scratch_load_dword v4, off, off offset:388
	s_waitcnt vmcnt(0)
	v_readlane_b32 s0, v4, 0
	v_readlane_b32 s1, v4, 1
	v_readlane_b32 s2, v4, 2
	v_readlane_b32 s3, v4, 3
	scratch_load_dword v4, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[4:5]
	s_mov_b32 s0, s69
	v_pk_mul_f32 v[60:61], v[132:133], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[62:63], v[130:131], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[52:53], v[252:253], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[58:59], v[250:251], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[48:49], v[248:249], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[56:57], v[246:247], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[44:45], v[244:245], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[54:55], v[242:243], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[40:41], v[240:241], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[50:51], v[238:239], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[36:37], v[236:237], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[46:47], v[234:235], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[32:33], v[232:233], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[42:43], v[230:231], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[28:29], v[228:229], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[38:39], v[226:227], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[24:25], v[224:225], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[34:35], v[222:223], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[20:21], v[216:217], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[30:31], v[214:215], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[16:17], v[208:209], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[26:27], v[206:207], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[12:13], v[200:201], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[22:23], v[198:199], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[8:9], v[192:193], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[18:19], v[190:191], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[6:7], v[184:185], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[14:15], v[182:183], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[4:5], v[176:177], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[10:11], v[174:175], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[2:3], v[2:3], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[0:1], v[0:1], s[2:3] op_sel_hi:[1,0]
	v_pk_mul_f32 v[190:191], v[220:221], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[124:125], v[218:219], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[120:121], v[212:213], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[122:123], v[210:211], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[116:117], v[204:205], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[118:119], v[202:203], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[112:113], v[196:197], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[114:115], v[194:195], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[108:109], v[188:189], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[110:111], v[186:187], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[104:105], v[180:181], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[106:107], v[178:179], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[100:101], v[172:173], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[102:103], v[170:171], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[96:97], v[168:169], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[98:99], v[166:167], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[92:93], v[164:165], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[94:95], v[162:163], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[88:89], v[160:161], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[90:91], v[158:159], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[84:85], v[156:157], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[86:87], v[154:155], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[80:81], v[152:153], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[82:83], v[150:151], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[76:77], v[148:149], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[78:79], v[146:147], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[72:73], v[144:145], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[74:75], v[142:143], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[68:69], v[140:141], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[70:71], v[138:139], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[64:65], v[136:137], s[0:1] op_sel_hi:[1,0]
	v_pk_mul_f32 v[66:67], v[134:135], s[0:1] op_sel_hi:[1,0]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:324
	s_waitcnt vmcnt(0)
	v_readlane_b32 s42, v126, 0
	v_readlane_b32 s43, v126, 1
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:332
	s_waitcnt vmcnt(0)
	v_readlane_b32 s30, v126, 0
	v_readlane_b32 s31, v126, 1
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:80
	s_waitcnt vmcnt(0)
	v_readlane_b32 s44, v126, 0
	v_readlane_b32 s45, v126, 1
	v_readlane_b32 s46, v126, 2
	v_readlane_b32 s47, v126, 3
	v_readlane_b32 s48, v126, 4
	v_readlane_b32 s49, v126, 5
	v_readlane_b32 s50, v126, 6
	v_readlane_b32 s51, v126, 7
	v_readlane_b32 s52, v126, 8
	v_readlane_b32 s53, v126, 9
	v_readlane_b32 s54, v126, 10
	v_readlane_b32 s55, v126, 11
	v_readlane_b32 s56, v126, 12
	v_readlane_b32 s57, v126, 13
	v_readlane_b32 s58, v126, 14
	v_readlane_b32 s59, v126, 15
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:340
	s_waitcnt vmcnt(0)
	v_readlane_b32 s24, v126, 0
	v_readlane_b32 s25, v126, 1
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:348
	s_waitcnt vmcnt(0)
	v_readlane_b32 s26, v126, 0
	v_readlane_b32 s27, v126, 1
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:356
	s_waitcnt vmcnt(0)
	v_readlane_b32 s27, v126, 0
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:360
	s_waitcnt vmcnt(0)
	v_readlane_b32 s36, v126, 0
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:364
	s_waitcnt vmcnt(0)
	v_readlane_b32 s37, v126, 0
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:368
	s_waitcnt vmcnt(0)
	v_readlane_b32 s29, v126, 0
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:372
	s_waitcnt vmcnt(0)
	v_readlane_b32 s38, v126, 0
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 1
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:376
	s_waitcnt vmcnt(0)
	v_readlane_b32 s28, v126, 0
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 3
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:380
	s_waitcnt vmcnt(0)
	v_readlane_b32 s40, v126, 0
	v_readlane_b32 s41, v126, 1
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	v_accvgpr_read_b32 v182, a0
	v_accvgpr_read_b32 v184, a2
	s_branch .LBB0_40
.LBB0_39:
	v_mov_b32_e32 v190, 0
	v_mov_b32_e32 v125, 0
	v_mov_b32_e32 v124, 0
	v_mov_b32_e32 v121, 0
	v_mov_b32_e32 v120, 0
	v_mov_b32_e32 v123, 0
	v_mov_b32_e32 v122, 0
	v_mov_b32_e32 v117, 0
	v_mov_b32_e32 v116, 0
	v_mov_b32_e32 v119, 0
	v_mov_b32_e32 v118, 0
	v_mov_b32_e32 v113, 0
	v_mov_b32_e32 v112, 0
	v_mov_b32_e32 v115, 0
	v_mov_b32_e32 v114, 0
	v_mov_b32_e32 v109, 0
	v_mov_b32_e32 v108, 0
	v_mov_b32_e32 v111, 0
	v_mov_b32_e32 v110, 0
	v_mov_b32_e32 v105, 0
	v_mov_b32_e32 v104, 0
	v_mov_b32_e32 v107, 0
	v_mov_b32_e32 v106, 0
	v_mov_b32_e32 v101, 0
	v_mov_b32_e32 v100, 0
	v_mov_b32_e32 v103, 0
	v_mov_b32_e32 v102, 0
	v_mov_b32_e32 v97, 0
	v_mov_b32_e32 v96, 0
	v_mov_b32_e32 v99, 0
	v_mov_b32_e32 v98, 0
	v_mov_b32_e32 v93, 0
	v_mov_b32_e32 v92, 0
	v_mov_b32_e32 v95, 0
	v_mov_b32_e32 v94, 0
	v_mov_b32_e32 v89, 0
	v_mov_b32_e32 v88, 0
	v_mov_b32_e32 v91, 0
	v_mov_b32_e32 v90, 0
	v_mov_b32_e32 v85, 0
	v_mov_b32_e32 v84, 0
	v_mov_b32_e32 v87, 0
	v_mov_b32_e32 v86, 0
	v_mov_b32_e32 v81, 0
	v_mov_b32_e32 v80, 0
	v_mov_b32_e32 v83, 0
	v_mov_b32_e32 v82, 0
	v_mov_b32_e32 v77, 0
	v_mov_b32_e32 v76, 0
	v_mov_b32_e32 v79, 0
	v_mov_b32_e32 v78, 0
	v_mov_b32_e32 v73, 0
	v_mov_b32_e32 v72, 0
	v_mov_b32_e32 v75, 0
	v_mov_b32_e32 v74, 0
	v_mov_b32_e32 v69, 0
	v_mov_b32_e32 v68, 0
	v_mov_b32_e32 v71, 0
	v_mov_b32_e32 v70, 0
	v_mov_b32_e32 v65, 0
	v_mov_b32_e32 v64, 0
	v_mov_b32_e32 v67, 0
	v_mov_b32_e32 v66, 0
	v_mov_b32_e32 v61, 0
	v_mov_b32_e32 v60, 0
	v_mov_b32_e32 v63, 0
	v_mov_b32_e32 v62, 0
	v_mov_b32_e32 v53, 0
	v_mov_b32_e32 v52, 0
	v_mov_b32_e32 v59, 0
	v_mov_b32_e32 v58, 0
	v_mov_b32_e32 v49, 0
	v_mov_b32_e32 v48, 0
	v_mov_b32_e32 v57, 0
	v_mov_b32_e32 v56, 0
	v_mov_b32_e32 v45, 0
	v_mov_b32_e32 v44, 0
	v_mov_b32_e32 v55, 0
	v_mov_b32_e32 v54, 0
	v_mov_b32_e32 v41, 0
	v_mov_b32_e32 v40, 0
	v_mov_b32_e32 v51, 0
	v_mov_b32_e32 v50, 0
	v_mov_b32_e32 v37, 0
	v_mov_b32_e32 v36, 0
	v_mov_b32_e32 v47, 0
	v_mov_b32_e32 v46, 0
	v_mov_b32_e32 v33, 0
	v_mov_b32_e32 v32, 0
	v_mov_b32_e32 v43, 0
	v_mov_b32_e32 v42, 0
	v_mov_b32_e32 v29, 0
	v_mov_b32_e32 v28, 0
	v_mov_b32_e32 v39, 0
	v_mov_b32_e32 v38, 0
	v_mov_b32_e32 v25, 0
	v_mov_b32_e32 v24, 0
	v_mov_b32_e32 v35, 0
	v_mov_b32_e32 v34, 0
	v_mov_b32_e32 v21, 0
	v_mov_b32_e32 v20, 0
	v_mov_b32_e32 v31, 0
	v_mov_b32_e32 v30, 0
	v_mov_b32_e32 v17, 0
	v_mov_b32_e32 v16, 0
	v_mov_b32_e32 v27, 0
	v_mov_b32_e32 v26, 0
	v_mov_b32_e32 v13, 0
	v_mov_b32_e32 v12, 0
	v_mov_b32_e32 v23, 0
	v_mov_b32_e32 v22, 0
	v_mov_b32_e32 v9, 0
	v_mov_b32_e32 v8, 0
	v_mov_b32_e32 v19, 0
	v_mov_b32_e32 v18, 0
	v_mov_b32_e32 v7, 0
	v_mov_b32_e32 v6, 0
	v_mov_b32_e32 v15, 0
	v_mov_b32_e32 v14, 0
	v_mov_b32_e32 v5, 0
	v_mov_b32_e32 v4, 0
	v_mov_b32_e32 v11, 0
	v_mov_b32_e32 v10, 0
	v_mov_b32_e32 v3, 0
	v_mov_b32_e32 v2, 0
	v_mov_b32_e32 v1, 0
	v_mov_b32_e32 v0, 0
.LBB0_40:
	s_mov_b64 s[0:1], exec
	s_mov_b64 exec, 0xffff
	scratch_store_dword off, v126, off offset:404
	scratch_load_dword v126, off, off offset:16
	s_waitcnt vmcnt(0)
	v_readlane_b32 s8, v126, 0
	v_readlane_b32 s9, v126, 1
	v_readlane_b32 s10, v126, 2
	v_readlane_b32 s11, v126, 3
	v_readlane_b32 s12, v126, 4
	v_readlane_b32 s13, v126, 5
	v_readlane_b32 s14, v126, 6
	v_readlane_b32 s15, v126, 7
	v_readlane_b32 s16, v126, 8
	v_readlane_b32 s17, v126, 9
	v_readlane_b32 s18, v126, 10
	v_readlane_b32 s19, v126, 11
	v_readlane_b32 s20, v126, 12
	v_readlane_b32 s21, v126, 13
	v_readlane_b32 s22, v126, 14
	v_readlane_b32 s23, v126, 15
	scratch_load_dword v126, off, off offset:404
	s_waitcnt vmcnt(0)
	s_mov_b64 exec, s[0:1]
	s_sub_i32 s2, s30, s20
	s_and_b64 s[0:1], s[40:41], exec
	s_mul_i32 s12, s20, s26
	s_cselect_b32 s0, 0, s2
	s_add_i32 s5, s0, s12
	s_mul_i32 s0, s16, s28
	s_mul_hi_u32 s1, s16, s36
	s_mul_i32 s2, s37, s19
	s_mul_hi_u32 s3, s37, s18
	s_add_i32 s0, s1, s0
	s_mul_i32 s1, s17, s36
	s_add_i32 s2, s3, s2
	s_mul_i32 s3, s38, s18
	s_add_i32 s0, s0, s1
	s_mul_i32 s1, s16, s36
	s_add_i32 s2, s2, s3
	s_mul_i32 s3, s37, s18
	s_add_u32 s1, s3, s1
	s_addc_u32 s2, s2, s0
	s_mul_i32 s0, s20, s29
	s_mul_hi_u32 s3, s20, s27
	s_add_i32 s0, s3, s0
	s_mul_i32 s3, s21, s27
	s_load_dwordx4 s[8:11], s[42:43], 0x138
	s_add_i32 s3, s0, s3
	s_mul_i32 s0, s20, s27
	s_add_u32 s0, s1, s0
	s_addc_u32 s1, s2, s3
	s_lshl_b64 s[0:1], s[0:1], 1
	s_add_u32 s0, s0, s46
	s_addc_u32 s1, s1, s47
	s_waitcnt lgkmcnt(0)
	s_sub_i32 s4, s24, s10
	s_and_b64 s[2:3], s[40:41], exec
	s_mul_i32 s14, s10, s26
	s_cselect_b32 s2, 0, s4
	s_add_i32 s6, s2, s14
	s_mul_i32 s2, s22, s28
	s_mul_hi_u32 s3, s22, s36
	s_mul_i32 s4, s37, s9
	s_mul_hi_u32 s7, s37, s8
	s_add_i32 s2, s3, s2
	s_mul_i32 s3, s23, s36
	s_add_i32 s4, s7, s4
	s_mul_i32 s7, s38, s8
	s_add_i32 s2, s2, s3
	s_mul_i32 s3, s22, s36
	s_add_i32 s4, s4, s7
	s_mul_i32 s7, s37, s8
	s_add_u32 s3, s7, s3
	s_addc_u32 s4, s4, s2
	s_mul_i32 s2, s10, s29
	s_mul_hi_u32 s7, s10, s27
	s_add_i32 s2, s7, s2
	s_mul_i32 s7, s11, s27
	s_add_i32 s7, s2, s7
	s_mul_i32 s2, s10, s27
	s_add_u32 s2, s3, s2
	s_addc_u32 s3, s4, s7
	s_lshl_b64 s[2:3], s[2:3], 1
	v_mul_lo_u32 v130, s10, v182
	v_lshlrev_b32_e32 v126, 2, v184
	v_mov_b32_e32 v127, 0
	s_add_u32 s4, s2, s48
	v_cvt_pk_f16_f32 v128, v124, v125
	v_add_u32_e32 v124, v130, v126
	v_mov_b32_e32 v131, s14
	v_cmp_gt_i64_e32 vcc, s[24:25], v[126:127]
	s_addc_u32 s7, s3, s49
	s_mov_b32 s3, 0x27000
	v_cndmask_b32_e32 v124, v131, v124, vcc
	s_mov_b32 s13, 0
	s_lshl_b32 s2, s5, 1
	s_and_b32 s5, s7, 0xffff
	s_lshl_b32 s6, s6, 1
	s_mov_b32 s7, s3
	v_cvt_pk_f16_f32 v129, v190, v191
	v_lshlrev_b32_e32 v124, 1, v124
	buffer_store_dwordx2 v[128:129], v124, s[4:7], 0 offen
	v_or_b32_e32 v124, 16, v126
	v_mov_b32_e32 v125, s13
	v_cvt_pk_f16_f32 v121, v120, v121
	v_cvt_pk_f16_f32 v120, v122, v123
	v_add_u32_e32 v122, v130, v124
	v_cmp_gt_i64_e32 vcc, s[24:25], v[124:125]
	v_cvt_pk_f16_f32 v117, v116, v117
	v_cvt_pk_f16_f32 v116, v118, v119
	v_cndmask_b32_e32 v122, v131, v122, vcc
	v_lshlrev_b32_e32 v122, 1, v122
	buffer_store_dwordx2 v[120:121], v122, s[4:7], 0 offen
	v_or_b32_e32 v120, 32, v126
	v_mov_b32_e32 v121, s13
	v_add_u32_e32 v118, v130, v120
	v_cmp_gt_i64_e32 vcc, s[24:25], v[120:121]
	v_cvt_pk_f16_f32 v113, v112, v113
	v_cvt_pk_f16_f32 v112, v114, v115
	v_cndmask_b32_e32 v118, v131, v118, vcc
	v_lshlrev_b32_e32 v118, 1, v118
	buffer_store_dwordx2 v[116:117], v118, s[4:7], 0 offen
	v_or_b32_e32 v116, 48, v126
	v_mov_b32_e32 v117, s13
	v_add_u32_e32 v114, v130, v116
	v_cmp_gt_i64_e32 vcc, s[24:25], v[116:117]
	v_cvt_pk_f16_f32 v109, v108, v109
	v_cvt_pk_f16_f32 v108, v110, v111
	v_cndmask_b32_e32 v114, v131, v114, vcc
	v_lshlrev_b32_e32 v114, 1, v114
	buffer_store_dwordx2 v[112:113], v114, s[4:7], 0 offen
	v_or_b32_e32 v112, 64, v126
	v_mov_b32_e32 v113, s13
	v_add_u32_e32 v110, v130, v112
	v_cmp_gt_i64_e32 vcc, s[24:25], v[112:113]
	v_cvt_pk_f16_f32 v105, v104, v105
	v_cvt_pk_f16_f32 v104, v106, v107
	v_cndmask_b32_e32 v110, v131, v110, vcc
	v_lshlrev_b32_e32 v110, 1, v110
	buffer_store_dwordx2 v[108:109], v110, s[4:7], 0 offen
	v_or_b32_e32 v108, 0x50, v126
	v_mov_b32_e32 v109, s13
	v_add_u32_e32 v106, v130, v108
	v_cmp_gt_i64_e32 vcc, s[24:25], v[108:109]
	v_cvt_pk_f16_f32 v101, v100, v101
	v_cvt_pk_f16_f32 v100, v102, v103
	v_cndmask_b32_e32 v106, v131, v106, vcc
	v_lshlrev_b32_e32 v106, 1, v106
	buffer_store_dwordx2 v[104:105], v106, s[4:7], 0 offen
	v_or_b32_e32 v104, 0x60, v126
	v_mov_b32_e32 v105, s13
	v_add_u32_e32 v102, v130, v104
	v_cmp_gt_i64_e32 vcc, s[24:25], v[104:105]
	v_cvt_pk_f16_f32 v97, v96, v97
	v_cvt_pk_f16_f32 v96, v98, v99
	v_cndmask_b32_e32 v102, v131, v102, vcc
	v_lshlrev_b32_e32 v102, 1, v102
	buffer_store_dwordx2 v[100:101], v102, s[4:7], 0 offen
	v_or_b32_e32 v100, 0x70, v126
	v_mov_b32_e32 v101, s13
	v_add_u32_e32 v98, v130, v100
	v_cmp_gt_i64_e32 vcc, s[24:25], v[100:101]
	v_cvt_pk_f16_f32 v93, v92, v93
	v_cvt_pk_f16_f32 v92, v94, v95
	v_cndmask_b32_e32 v98, v131, v98, vcc
	v_lshlrev_b32_e32 v98, 1, v98
	buffer_store_dwordx2 v[96:97], v98, s[4:7], 0 offen
	v_or_b32_e32 v96, 0x80, v126
	v_mov_b32_e32 v97, s13
	v_add_u32_e32 v94, v130, v96
	v_cmp_gt_i64_e32 vcc, s[24:25], v[96:97]
	v_cvt_pk_f16_f32 v89, v88, v89
	v_cvt_pk_f16_f32 v88, v90, v91
	v_cndmask_b32_e32 v94, v131, v94, vcc
	v_lshlrev_b32_e32 v94, 1, v94
	buffer_store_dwordx2 v[92:93], v94, s[4:7], 0 offen
	v_or_b32_e32 v92, 0x90, v126
	v_mov_b32_e32 v93, s13
	v_add_u32_e32 v90, v130, v92
	v_cmp_gt_i64_e32 vcc, s[24:25], v[92:93]
	v_cvt_pk_f16_f32 v85, v84, v85
	v_cvt_pk_f16_f32 v84, v86, v87
	v_cndmask_b32_e32 v90, v131, v90, vcc
	v_lshlrev_b32_e32 v90, 1, v90
	buffer_store_dwordx2 v[88:89], v90, s[4:7], 0 offen
	v_or_b32_e32 v88, 0xa0, v126
	v_mov_b32_e32 v89, s13
	v_add_u32_e32 v86, v130, v88
	v_cmp_gt_i64_e32 vcc, s[24:25], v[88:89]
	v_cvt_pk_f16_f32 v81, v80, v81
	v_cvt_pk_f16_f32 v80, v82, v83
	v_cndmask_b32_e32 v86, v131, v86, vcc
	v_lshlrev_b32_e32 v86, 1, v86
	buffer_store_dwordx2 v[84:85], v86, s[4:7], 0 offen
	v_or_b32_e32 v84, 0xb0, v126
	v_mov_b32_e32 v85, s13
	v_add_u32_e32 v82, v130, v84
	v_cmp_gt_i64_e32 vcc, s[24:25], v[84:85]
	v_cvt_pk_f16_f32 v77, v76, v77
	v_cvt_pk_f16_f32 v76, v78, v79
	v_cndmask_b32_e32 v82, v131, v82, vcc
	v_lshlrev_b32_e32 v82, 1, v82
	buffer_store_dwordx2 v[80:81], v82, s[4:7], 0 offen
	v_or_b32_e32 v80, 0xc0, v126
	v_mov_b32_e32 v81, s13
	v_add_u32_e32 v78, v130, v80
	v_cmp_gt_i64_e32 vcc, s[24:25], v[80:81]
	v_cvt_pk_f16_f32 v73, v72, v73
	v_cvt_pk_f16_f32 v72, v74, v75
	v_cndmask_b32_e32 v78, v131, v78, vcc
	v_lshlrev_b32_e32 v78, 1, v78
	buffer_store_dwordx2 v[76:77], v78, s[4:7], 0 offen
	v_or_b32_e32 v76, 0xd0, v126
	v_mov_b32_e32 v77, s13
	v_add_u32_e32 v74, v130, v76
	v_cmp_gt_i64_e32 vcc, s[24:25], v[76:77]
	v_cvt_pk_f16_f32 v69, v68, v69
	v_cvt_pk_f16_f32 v68, v70, v71
	v_cndmask_b32_e32 v74, v131, v74, vcc
	v_lshlrev_b32_e32 v74, 1, v74
	buffer_store_dwordx2 v[72:73], v74, s[4:7], 0 offen
	v_or_b32_e32 v72, 0xe0, v126
	v_mov_b32_e32 v73, s13
	v_add_u32_e32 v70, v130, v72
	v_cmp_gt_i64_e32 vcc, s[24:25], v[72:73]
	v_cvt_pk_f16_f32 v65, v64, v65
	v_cvt_pk_f16_f32 v64, v66, v67
	v_cndmask_b32_e32 v70, v131, v70, vcc
	v_lshlrev_b32_e32 v70, 1, v70
	buffer_store_dwordx2 v[68:69], v70, s[4:7], 0 offen
	v_or_b32_e32 v68, 0xf0, v126
	v_mov_b32_e32 v69, s13
	v_add_u32_e32 v66, v130, v68
	v_cmp_gt_i64_e32 vcc, s[24:25], v[68:69]
	v_cvt_pk_f16_f32 v61, v60, v61
	v_cvt_pk_f16_f32 v60, v62, v63
	v_cndmask_b32_e32 v66, v131, v66, vcc
	v_lshlrev_b32_e32 v66, 1, v66
	buffer_store_dwordx2 v[64:65], v66, s[4:7], 0 offen
	v_mul_lo_u32 v64, s20, v182
	v_add_u32_e32 v62, v64, v126
	v_mov_b32_e32 v63, s12
	v_cmp_gt_i64_e32 vcc, s[30:31], v[126:127]
	v_cvt_pk_f16_f32 v53, v52, v53
	v_cvt_pk_f16_f32 v52, v58, v59
	v_cndmask_b32_e32 v62, v63, v62, vcc
	v_add_u32_e32 v58, v64, v124
	v_cmp_gt_i64_e32 vcc, s[30:31], v[124:125]
	s_and_b32 s1, s1, 0xffff
	v_lshlrev_b32_e32 v62, 1, v62
	v_cndmask_b32_e32 v58, v63, v58, vcc
	v_lshlrev_b32_e32 v58, 1, v58
	buffer_store_dwordx2 v[60:61], v62, s[0:3], 0 offen
	buffer_store_dwordx2 v[52:53], v58, s[0:3], 0 offen
	v_add_u32_e32 v52, v64, v120
	v_cmp_gt_i64_e32 vcc, s[30:31], v[120:121]
	v_cvt_pk_f16_f32 v49, v48, v49
	v_cvt_pk_f16_f32 v48, v56, v57
	v_cndmask_b32_e32 v52, v63, v52, vcc
	v_lshlrev_b32_e32 v52, 1, v52
	buffer_store_dwordx2 v[48:49], v52, s[0:3], 0 offen
	v_add_u32_e32 v48, v64, v116
	v_cmp_gt_i64_e32 vcc, s[30:31], v[116:117]
	v_cvt_pk_f16_f32 v45, v44, v45
	v_cvt_pk_f16_f32 v44, v54, v55
	v_cndmask_b32_e32 v48, v63, v48, vcc
	v_lshlrev_b32_e32 v48, 1, v48
	buffer_store_dwordx2 v[44:45], v48, s[0:3], 0 offen
	v_add_u32_e32 v44, v64, v112
	v_cmp_gt_i64_e32 vcc, s[30:31], v[112:113]
	v_cvt_pk_f16_f32 v41, v40, v41
	v_cvt_pk_f16_f32 v40, v50, v51
	v_cndmask_b32_e32 v44, v63, v44, vcc
	v_lshlrev_b32_e32 v44, 1, v44
	buffer_store_dwordx2 v[40:41], v44, s[0:3], 0 offen
	v_add_u32_e32 v40, v64, v108
	v_cmp_gt_i64_e32 vcc, s[30:31], v[108:109]
	v_cvt_pk_f16_f32 v37, v36, v37
	v_cvt_pk_f16_f32 v36, v46, v47
	v_cndmask_b32_e32 v40, v63, v40, vcc
	v_lshlrev_b32_e32 v40, 1, v40
	buffer_store_dwordx2 v[36:37], v40, s[0:3], 0 offen
	v_add_u32_e32 v36, v64, v104
	v_cmp_gt_i64_e32 vcc, s[30:31], v[104:105]
	v_cvt_pk_f16_f32 v33, v32, v33
	v_cvt_pk_f16_f32 v32, v42, v43
	v_cndmask_b32_e32 v36, v63, v36, vcc
	v_lshlrev_b32_e32 v36, 1, v36
	buffer_store_dwordx2 v[32:33], v36, s[0:3], 0 offen
	v_add_u32_e32 v32, v64, v100
	v_cmp_gt_i64_e32 vcc, s[30:31], v[100:101]
	v_cvt_pk_f16_f32 v29, v28, v29
	v_cvt_pk_f16_f32 v28, v38, v39
	v_cndmask_b32_e32 v32, v63, v32, vcc
	v_lshlrev_b32_e32 v32, 1, v32
	buffer_store_dwordx2 v[28:29], v32, s[0:3], 0 offen
	v_add_u32_e32 v28, v64, v96
	v_cmp_gt_i64_e32 vcc, s[30:31], v[96:97]
	v_cvt_pk_f16_f32 v25, v24, v25
	v_cvt_pk_f16_f32 v24, v34, v35
	v_cndmask_b32_e32 v28, v63, v28, vcc
	v_lshlrev_b32_e32 v28, 1, v28
	buffer_store_dwordx2 v[24:25], v28, s[0:3], 0 offen
	v_add_u32_e32 v24, v64, v92
	v_cmp_gt_i64_e32 vcc, s[30:31], v[92:93]
	v_cvt_pk_f16_f32 v21, v20, v21
	v_cvt_pk_f16_f32 v20, v30, v31
	v_cndmask_b32_e32 v24, v63, v24, vcc
	v_lshlrev_b32_e32 v24, 1, v24
	buffer_store_dwordx2 v[20:21], v24, s[0:3], 0 offen
	v_add_u32_e32 v20, v64, v88
	v_cmp_gt_i64_e32 vcc, s[30:31], v[88:89]
	v_cvt_pk_f16_f32 v17, v16, v17
	v_cvt_pk_f16_f32 v16, v26, v27
	v_cndmask_b32_e32 v20, v63, v20, vcc
	v_lshlrev_b32_e32 v20, 1, v20
	buffer_store_dwordx2 v[16:17], v20, s[0:3], 0 offen
	v_add_u32_e32 v16, v64, v84
	v_cmp_gt_i64_e32 vcc, s[30:31], v[84:85]
	v_cvt_pk_f16_f32 v13, v12, v13
	v_cvt_pk_f16_f32 v12, v22, v23
	v_cndmask_b32_e32 v16, v63, v16, vcc
	v_lshlrev_b32_e32 v16, 1, v16
	buffer_store_dwordx2 v[12:13], v16, s[0:3], 0 offen
	v_add_u32_e32 v12, v64, v80
	v_cmp_gt_i64_e32 vcc, s[30:31], v[80:81]
	v_cvt_pk_f16_f32 v9, v8, v9
	v_cvt_pk_f16_f32 v8, v18, v19
	v_cndmask_b32_e32 v12, v63, v12, vcc
	v_lshlrev_b32_e32 v12, 1, v12
	buffer_store_dwordx2 v[8:9], v12, s[0:3], 0 offen
	v_add_u32_e32 v8, v64, v76
	v_cmp_gt_i64_e32 vcc, s[30:31], v[76:77]
	v_cvt_pk_f16_f32 v7, v6, v7
	v_cvt_pk_f16_f32 v6, v14, v15
	v_cndmask_b32_e32 v8, v63, v8, vcc
	v_lshlrev_b32_e32 v8, 1, v8
	buffer_store_dwordx2 v[6:7], v8, s[0:3], 0 offen
	v_add_u32_e32 v6, v64, v72
	v_cmp_gt_i64_e32 vcc, s[30:31], v[72:73]
	v_cvt_pk_f16_f32 v3, v2, v3
	v_cvt_pk_f16_f32 v2, v0, v1
	v_cndmask_b32_e32 v6, v63, v6, vcc
	v_add_u32_e32 v0, v64, v68
	v_cmp_gt_i64_e32 vcc, s[30:31], v[68:69]
	v_cvt_pk_f16_f32 v5, v4, v5
	v_cvt_pk_f16_f32 v4, v10, v11
	v_cndmask_b32_e32 v0, v63, v0, vcc
	v_lshlrev_b32_e32 v6, 1, v6
	v_lshlrev_b32_e32 v0, 1, v0
	buffer_store_dwordx2 v[4:5], v6, s[0:3], 0 offen
	buffer_store_dwordx2 v[2:3], v0, s[0:3], 0 offen
.LBB0_41:
	s_endpgm
.Lfunc_end0:
	.size	flyc_bwd_dkdv, .Lfunc_end0-flyc_bwd_dkdv
	.section	.rodata,"a",@progbits
	.p2align	6, 0x0
	.amdhsa_kernel flyc_bwd_dkdv
		.amdhsa_group_segment_fixed_size 69632
		.amdhsa_private_segment_fixed_size 408
		.amdhsa_kernarg_size 352
		.amdhsa_user_sgpr_count 2
		.amdhsa_user_sgpr_dispatch_ptr 0
		.amdhsa_user_sgpr_queue_ptr 0
		.amdhsa_user_sgpr_kernarg_segment_ptr 1
		.amdhsa_user_sgpr_dispatch_id 0
		.amdhsa_user_sgpr_kernarg_preload_length 0
		.amdhsa_user_sgpr_kernarg_preload_offset 0
		.amdhsa_user_sgpr_private_segment_size 0
		.amdhsa_uses_dynamic_stack 0
		.amdhsa_enable_private_segment 1
		.amdhsa_system_sgpr_workgroup_id_x 1
		.amdhsa_system_sgpr_workgroup_id_y 1
		.amdhsa_system_sgpr_workgroup_id_z 1
		.amdhsa_system_sgpr_workgroup_info 0
		.amdhsa_system_vgpr_workitem_id 0
		.amdhsa_next_free_vgpr 373
		.amdhsa_next_free_sgpr 100
		.amdhsa_accum_offset 256
		.amdhsa_reserve_vcc 1
		.amdhsa_float_round_mode_32 0
		.amdhsa_float_round_mode_16_64 0
		.amdhsa_float_denorm_mode_32 3
		.amdhsa_float_denorm_mode_16_64 3
		.amdhsa_dx10_clamp 1
		.amdhsa_ieee_mode 1
		.amdhsa_fp16_overflow 0
		.amdhsa_tg_split 0
		.amdhsa_exception_fp_ieee_invalid_op 0
		.amdhsa_exception_fp_denorm_src 0
		.amdhsa_exception_fp_ieee_div_zero 0
		.amdhsa_exception_fp_ieee_overflow 0
		.amdhsa_exception_fp_ieee_underflow 0
		.amdhsa_exception_fp_ieee_inexact 0
		.amdhsa_exception_int_div_zero 0
	.end_amdhsa_kernel
	.text

	.set .Lflyc_bwd_dkdv.num_vgpr, 256
	.set .Lflyc_bwd_dkdv.num_agpr, 117
	.set .Lflyc_bwd_dkdv.numbered_sgpr, 100
	.set .Lflyc_bwd_dkdv.num_named_barrier, 0
	.set .Lflyc_bwd_dkdv.private_seg_size, 408
	.set .Lflyc_bwd_dkdv.uses_vcc, 1
	.set .Lflyc_bwd_dkdv.uses_flat_scratch, 0
	.set .Lflyc_bwd_dkdv.has_dyn_sized_stack, 0
	.set .Lflyc_bwd_dkdv.has_recursion, 0
	.set .Lflyc_bwd_dkdv.has_indirect_call, 0
	.p2alignl 6, 3212836864
	.fill 256, 4, 3212836864
	.section	.AMDGPU.gpr_maximums,"",@progbits
	.set amdgpu.max_num_vgpr, 0
	.set amdgpu.max_num_agpr, 0
	.set amdgpu.max_num_sgpr, 0
	.set amdgpu.max_num_named_barrier, 0
	.text
	.section	".note.GNU-stack","",@progbits
	.amdgpu_metadata
---
amdhsa.kernels:
  - .agpr_count:     117
    .args:
      - .address_space:  global
        .offset:         0
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         8
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         16
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         24
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         32
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         40
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         48
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         56
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         64
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         72
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         80
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         88
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         96
        .size:           8
        .value_kind:     global_buffer
      - .offset:         104
        .size:           4
        .value_kind:     by_value
      - .offset:         108
        .size:           4
        .value_kind:     by_value
      - .offset:         112
        .size:           4
        .value_kind:     by_value
      - .offset:         116
        .size:           4
        .value_kind:     by_value
      - .offset:         120
        .size:           4
        .value_kind:     by_value
      - .offset:         124
        .size:           4
        .value_kind:     by_value
      - .address_space:  global
        .offset:         128
        .size:           8
        .value_kind:     global_buffer
      - .address_space:  global
        .offset:         136
        .size:           8
        .value_kind:     global_buffer
      - .offset:         144
        .size:           8
        .value_kind:     by_value
      - .offset:         152
        .size:           4
        .value_kind:     by_value
      - .offset:         156
        .size:           4
        .value_kind:     by_value
      - .offset:         160
        .size:           4
        .value_kind:     by_value
      - .offset:         164
        .size:           4
        .value_kind:     by_value
      - .offset:         168
        .size:           4
        .value_kind:     by_value
      - .offset:         172
        .size:           4
        .value_kind:     by_value
      - .offset:         176
        .size:           4
        .value_kind:     by_value
      - .offset:         184
        .size:           8
        .value_kind:     by_value
      - .offset:         192
        .size:           8
        .value_kind:     by_value
      - .offset:         200
        .size:           8
        .value_kind:     by_value
      - .offset:         208
        .size:           8
        .value_kind:     by_value
      - .offset:         216
        .size:           8
        .value_kind:     by_value
      - .offset:         224
        .size:           8
        .value_kind:     by_value
      - .offset:         232
        .size:           8
        .value_kind:     by_value
      - .offset:         240
        .size:           8
        .value_kind:     by_value
      - .offset:         248
        .size:           8
        .value_kind:     by_value
      - .offset:         256
        .size:           8
        .value_kind:     by_value
      - .offset:         264
        .size:           8
        .value_kind:     by_value
      - .offset:         272
        .size:           8
        .value_kind:     by_value
      - .offset:         280
        .size:           8
        .value_kind:     by_value
      - .offset:         288
        .size:           8
        .value_kind:     by_value
      - .offset:         296
        .size:           8
        .value_kind:     by_value
      - .offset:         304
        .size:           8
        .value_kind:     by_value
      - .offset:         312
        .size:           8
        .value_kind:     by_value
      - .offset:         320
        .size:           8
        .value_kind:     by_value
      - .offset:         328
        .size:           8
        .value_kind:     by_value
      - .offset:         336
        .size:           8
        .value_kind:     by_value
      - .offset:         344
        .size:           8
        .value_kind:     by_value
    .group_segment_fixed_size: 69632
    .kernarg_segment_align: 8
    .kernarg_segment_size: 352
    .max_flat_workgroup_size: 256
    .name:           flyc_bwd_dkdv
    .private_segment_fixed_size: 408
    .reqd_workgroup_size:
      - 256
      - 1
      - 1
    .sgpr_count:     106
    .sgpr_spill_count: 105
    .symbol:         flyc_bwd_dkdv.kd
    .uniform_work_group_size: 1
    .uses_dynamic_stack: false
    .vgpr_count:     373
    .vgpr_spill_count: 125
    .wavefront_size: 64
amdhsa.target:   amdgcn-amd-amdhsa-unknown-gfx950
amdhsa.version:
  - 1
  - 2
...

	.end_amdgpu_metadata
