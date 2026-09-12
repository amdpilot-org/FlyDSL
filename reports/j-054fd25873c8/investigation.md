# SDK-free FlyJitRuntime investigation

At base commit `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`, the ROCm JIT wrapper included
`hip/hip_runtime.h`, CMake required the HIP package, and the target linked
`hip::host` plus `hip::amdhip64`. The prepared original wheel confirms the
runtime consequence: `readelf -d` reports `DT_NEEDED libamdhip64.so.7` and an
RPATH containing `/opt/rocm/lib`.

The change replaces those compile/link dependencies with the narrow runtime ABI
actually used by this wrapper. Opaque HIP handles are represented as pointers;
the extensible-launch structures have compile-time size/offset checks; and HIP
entry points are resolved from `libamdhip64` on first use. Loading the rebuilt
library alone leaves `/proc/self/maps` free of `libamdhip64`.

The prepared native rebuild passed. The rebuilt ELF has no HIP `DT_NEEDED`
entry and no undefined HIP symbols. A fresh CMake configure and isolated
`FlyJitRuntime` build also passed with `CMAKE_DISABLE_FIND_PACKAGE_hip=TRUE`.

For execution validation, a fresh uncached pointer vector-add was compared with
PyTorch's `a + b` reference and passed its `1e-5` maximum-error bound on the
assigned MI350X. FlyDSL emitted ISA naming target
`amdgcn-amd-amdhsa-unknown-gfx950`, with `global_load_dword` for both inputs,
`v_add_f32_e32`, and `global_store_dword` for the output.

The image contains ROCm 7.2, so a build on a machine physically lacking all SDK
files could not be performed. Disabling package discovery, checking the actual
build, and inspecting ELF metadata establish the dependency removal available
in this environment. A HIP runtime remains required only when ROCm GPU work is
actually requested. CUDA/NVVM and a dual-backend wheel remain outside this
bounded change.
