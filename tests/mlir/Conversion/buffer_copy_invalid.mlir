// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2025 FlyDSL Project Contributors
// RUN: { %fly-opt --split-input-file --convert-fly-to-rocdl %s 2>&1 || true; } | FileCheck %s

// CHECK: BufferCopy64b load requires a 64-bit register result, got 'vector<4xi8>'
func.func @load_width_mismatch(
    %atom: !fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<64>, 8>,
    %src: !fly.memref<i8, #fly_rocdl.buffer_desc, 4:1>) -> vector<4xi8> {
  %result = fly.copy_atom_call_ssa(%atom, %src) {operandSegmentSizes = array<i32: 1, 1, 0, 0>} : (!fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<64>, 8>, !fly.memref<i8, #fly_rocdl.buffer_desc, 4:1>) -> vector<4xi8>
  return %result : vector<4xi8>
}

// -----

// CHECK: BufferCopy load requires a buffer-descriptor source
// CHECK-SAME: Convert the global-memory tensor to a buffer tensor before copying
func.func @plain_global_source(
    %atom: !fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<32>, 8>,
    %src: !fly.memref<i8, global, 4:1>) -> vector<4xi8> {
  %result = fly.copy_atom_call_ssa(%atom, %src) {operandSegmentSizes = array<i32: 1, 1, 0, 0>} : (!fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<32>, 8>, !fly.memref<i8, global, 4:1>) -> vector<4xi8>
  return %result : vector<4xi8>
}

// -----

// CHECK: BufferCopy64b store requires a 64-bit register source, got 'vector<4xi8>'
func.func @store_width_mismatch(
    %atom: !fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<64>, 8>,
    %src: vector<4xi8>,
    %dst: !fly.memref<i8, #fly_rocdl.buffer_desc, 4:1>) {
  fly.copy_atom_call_ssa(%atom, %src, %dst) {operandSegmentSizes = array<i32: 1, 1, 1, 0>} : (!fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<64>, 8>, vector<4xi8>, !fly.memref<i8, #fly_rocdl.buffer_desc, 4:1>) -> ()
  return
}

// -----

// CHECK: BufferCopy store requires a buffer-descriptor destination
// CHECK-SAME: Convert the global-memory tensor to a buffer tensor before copying
func.func @plain_global_destination(
    %atom: !fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<32>, 8>,
    %src: vector<4xi8>,
    %dst: !fly.memref<i8, global, 4:1>) {
  fly.copy_atom_call_ssa(%atom, %src, %dst) {operandSegmentSizes = array<i32: 1, 1, 1, 0>} : (!fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<32>, 8>, vector<4xi8>, !fly.memref<i8, global, 4:1>) -> ()
  return
}
