// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2025 FlyDSL Project Contributors
// RUN: %fly-opt %s -verify-diagnostics

// Structural layout-algebra failures must be diagnosed at the operation rather
// than asserting in the attribute implementation or producing a bogus layout.

func.func @make_layout_requires_congruent_shape_and_stride() {
  %shape = fly.static : !fly.int_tuple<((4, 8), 2)>
  %stride = fly.static : !fly.int_tuple<(1, (4, 32))>
  // expected-error@+1 {{shape and stride must have congruent tuple structure}}
  %layout = fly.make_layout(%shape, %stride) : (!fly.int_tuple<((4, 8), 2)>, !fly.int_tuple<(1, (4, 32))>) -> !fly.layout<((4,8),2):(1,(4,32))>
  return
}

func.func @composition_rejects_inadmissible_static_stride(
    %outer: !fly.layout<(4,8):(1,8)>, %inner: !fly.layout<2:6>) {
  // expected-error@+1 {{inner stride is not admissible for the outer layout mode structure}}
  %result = fly.composition(%outer, %inner) : (!fly.layout<(4,8):(1,8)>, !fly.layout<2:6>) -> !fly.layout<2:48>
  return
}

func.func @logical_divide_requires_static_divisibility(
    %layout: !fly.layout<16:1>, %divisor: !fly.layout<6:1>) {
  // expected-error@+1 {{static divisor size must evenly divide layout size; got 6 and 16}}
  %result = fly.logical_divide(%layout, %divisor) : (!fly.layout<16:1>, !fly.layout<6:1>) -> !fly.layout<(6,3):(1,6)>
  return
}

func.func @right_inverse_requires_contiguous_static_domain(
    %layout: !fly.layout<(4,8):(2,8)>) {
  // expected-error@+1 {{static layout must describe an invertible contiguous domain}}
  %result = fly.right_inverse(%layout) : (!fly.layout<(4,8):(2,8)>) -> !fly.layout<1:0>
  return
}

// Dynamic values retain a congruent profile and remain legal. Whether the
// runtime extents divide, address the outer domain, or are invertible is not
// statically knowable from these types.
func.func @dynamic_make_layout_control(%m: i32, %n: i32, %s0: i32, %s1: i32) {
  %shape = fly.make_int_tuple(%m, %n) : (i32, i32) -> !fly.int_tuple<(?, ?)>
  %stride = fly.make_int_tuple(%s0, %s1) : (i32, i32) -> !fly.int_tuple<(?, ?)>
  %layout = fly.make_layout(%shape, %stride) : (!fly.int_tuple<(?, ?)>, !fly.int_tuple<(?, ?)>) -> !fly.layout<(?, ?):(?, ?)>
  return
}

func.func @dynamic_inverse_control(%layout: !fly.layout<?{i32}:1>) {
  %result = fly.right_inverse(%layout) : (!fly.layout<?{i32}:1>) -> !fly.layout<1:0>
  return
}

func.func @dynamic_composition_control(
    %outer: !fly.layout<(4,8):(1,8)>, %inner: !fly.layout<2:?{i32}>) {
  %result = fly.composition(%outer, %inner) : (!fly.layout<(4,8):(1,8)>, !fly.layout<2:?{i32}>) -> !fly.layout<(?,?):(?,?{div=8})>
  return
}

func.func @dynamic_divide_control(
    %layout: !fly.layout<?{i32}:1>, %divisor: !fly.layout<?{i32}:1>) {
  %result = fly.logical_divide(%layout, %divisor) : (!fly.layout<?{i32}:1>, !fly.layout<?{i32}:1>) -> !fly.layout<(?{i32},?{i32}):(1,?{i32})>
  return
}
