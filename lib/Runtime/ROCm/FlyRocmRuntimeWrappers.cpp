//===- FlyRocmRuntimeWrappers.cpp - ROCm runtime with module caching ------===//
//
// Derived from LLVM Project: mlir/lib/ExecutionEngine/RocmRuntimeWrappers.cpp
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// Thin ROCm runtime wrappers for MLIR ExecutionEngine JIT.
//
//===----------------------------------------------------------------------===//

#include <cassert>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <dlfcn.h>
#include <type_traits>
#include <vector>

#include "mlir/ExecutionEngine/CRunnerUtils.h"

// Keep the JIT runtime buildable with LLVM/MLIR alone.  HIP's public handle
// types are opaque pointers and the handful of scalar ABI constants used here
// are stable runtime ABI, so no vendor development headers are needed.
using hipError_t = int;
using hipModule_t = void *;
using hipFunction_t = void *;
using hipStream_t = void *;
using hipEvent_t = void *;
using hipDeviceptr_t = void *;

struct HipLaunchAttribute {
  int id;
  char alignmentPadding[4];
  union {
    char pad[64];
    unsigned clusterDim[3];
  } value;
};

struct HipLaunchConfig {
  unsigned gridDimX, gridDimY, gridDimZ;
  unsigned blockDimX, blockDimY, blockDimZ;
  unsigned sharedMemBytes;
  hipStream_t hStream;
  HipLaunchAttribute *attrs;
  unsigned numAttrs;
};

static_assert(sizeof(HipLaunchAttribute) == 72);
static_assert(offsetof(HipLaunchConfig, hStream) == 32);
static_assert(sizeof(HipLaunchConfig) == 56);

static void *getHipRuntime() {
  static void *handle = [] {
    constexpr const char *sonames[] = {"libamdhip64.so", "libamdhip64.so.7",
                                       "libamdhip64.so.6", "libamdhip64.so.5"};
    for (const char *soname : sonames)
      if (void *library = dlopen(soname, RTLD_LAZY | RTLD_LOCAL))
        return library;
    return static_cast<void *>(nullptr);
  }();
  return handle;
}

template <typename Function> static Function getHipSymbol(const char *name) {
  void *runtime = getHipRuntime();
  return runtime ? reinterpret_cast<Function>(dlsym(runtime, name)) : nullptr;
}

template <typename Function, typename... Args>
static hipError_t callHip(const char *name, Args... args) {
  static_assert(std::is_pointer_v<Function>);
  auto function = getHipSymbol<Function>(name);
  if (!function) {
    const char *error = dlerror();
    fprintf(stderr, "FlyDSL could not resolve HIP runtime symbol '%s': %s\n", name,
            error ? error : "libamdhip64 is not installed");
    return 999; // hipErrorUnknown
  }
  return function(args...);
}

#define HIP_CALL(name, ...) callHip<decltype(&name)>(#name, __VA_ARGS__)

// Function declarations provide types for dynamic calls without introducing
// link-time references to libamdhip64.
extern "C" {
hipError_t hipModuleLoadData(hipModule_t *, const void *);
hipError_t hipModuleUnload(hipModule_t);
hipError_t hipModuleGetFunction(hipFunction_t *, hipModule_t, const char *);
hipError_t hipModuleLaunchKernel(hipFunction_t, unsigned, unsigned, unsigned, unsigned, unsigned,
                                 unsigned, unsigned, hipStream_t, void **, void **);
hipError_t hipStreamCreate(hipStream_t *);
hipError_t hipStreamDestroy(hipStream_t);
hipError_t hipStreamSynchronize(hipStream_t);
hipError_t hipStreamWaitEvent(hipStream_t, hipEvent_t, unsigned);
hipError_t hipEventCreateWithFlags(hipEvent_t *, unsigned);
hipError_t hipEventDestroy(hipEvent_t);
hipError_t hipEventSynchronize(hipEvent_t);
hipError_t hipEventRecord(hipEvent_t, hipStream_t);
hipError_t hipMalloc(void **, size_t);
hipError_t hipFree(void *);
hipError_t hipMemcpyAsync(void *, const void *, size_t, int, hipStream_t);
hipError_t hipMemsetD32Async(hipDeviceptr_t, int, size_t, hipStream_t);
hipError_t hipMemsetD16Async(hipDeviceptr_t, int, size_t, hipStream_t);
hipError_t hipHostRegister(void *, size_t, unsigned);
hipError_t hipHostUnregister(void *);
hipError_t hipSetDevice(int);
hipError_t hipHostGetDevicePointer(void **, void *, unsigned);
}

#define HIP_REPORT_IF_ERROR(expr)                                                                  \
  [](hipError_t result) {                                                                          \
    if (!result)                                                                                   \
      return;                                                                                      \
    using GetErrorName = const char *(*)(hipError_t);                                              \
    auto getErrorName = getHipSymbol<GetErrorName>("hipGetErrorName");                            \
    const char *name = getErrorName ? getErrorName(result) : nullptr;                              \
    if (!name)                                                                                     \
      name = "<unknown>";                                                                          \
    fprintf(stderr, "'%s' failed with '%s'\n", #expr, name);                                       \
  }(expr)

thread_local static int32_t defaultDevice = 0;

extern "C" hipModule_t mgpuModuleLoad(void *data, size_t /*gpuBlobSize*/) {
  hipModule_t module = nullptr;
  HIP_REPORT_IF_ERROR(HIP_CALL(hipModuleLoadData, &module, data));
  return module;
}

extern "C" hipModule_t mgpuModuleLoadJIT(void *data, int optLevel) {
  (void)data;
  (void)optLevel;
  assert(false && "This function is not available in HIP.");
  return nullptr;
}

extern "C" void mgpuModuleUnload(hipModule_t module) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipModuleUnload, module));
}

extern "C" hipFunction_t mgpuModuleGetFunction(hipModule_t module, const char *name) {
  hipFunction_t function = nullptr;
  HIP_REPORT_IF_ERROR(HIP_CALL(hipModuleGetFunction, &function, module, name));
  return function;
}

extern "C" void mgpuLaunchKernel(hipFunction_t function, intptr_t gridX, intptr_t gridY,
                                 intptr_t gridZ, intptr_t blockX, intptr_t blockY, intptr_t blockZ,
                                 int32_t smem, hipStream_t stream, void **params, void **extra,
                                 size_t /*paramsCount*/) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipModuleLaunchKernel, function, gridX, gridY, gridZ, blockX, blockY,
                               blockZ, smem, stream, params, extra));
}

extern "C" void mgpuLaunchClusterKernel(hipFunction_t function, intptr_t clusterX,
                                        intptr_t clusterY, intptr_t clusterZ, intptr_t gridX,
                                        intptr_t gridY, intptr_t gridZ, intptr_t blockX,
                                        intptr_t blockY, intptr_t blockZ, int32_t smem,
                                        hipStream_t stream, void **params, void **extra,
                                        size_t /*paramsCount*/) {
  // Resolve hipDrvLaunchKernelEx at runtime via dlsym so that the same
  // shared library works across HIP versions (required for wheel builds).
  // Mirrors Triton's approach: triton/third_party/amd/backend/driver.c.
  using LaunchKernelExFn = hipError_t (*)(const HipLaunchConfig *, hipFunction_t, void **, void **);
  static auto launchKernelEx = getHipSymbol<LaunchKernelExFn>("hipDrvLaunchKernelEx");

  if (launchKernelEx) {
    HipLaunchAttribute attrs[1]{};
    // hipLaunchAttributeClusterDimension == 4, hardcoded to avoid a
    // compile-time dependency on HIP headers that define the enum value.
    attrs[0].id = 4;
    auto *clusterDims = attrs[0].value.clusterDim;
    clusterDims[0] = static_cast<unsigned>(clusterX);
    clusterDims[1] = static_cast<unsigned>(clusterY);
    clusterDims[2] = static_cast<unsigned>(clusterZ);

    HipLaunchConfig config{};
    config.gridDimX = static_cast<unsigned>(gridX);
    config.gridDimY = static_cast<unsigned>(gridY);
    config.gridDimZ = static_cast<unsigned>(gridZ);
    config.blockDimX = static_cast<unsigned>(blockX);
    config.blockDimY = static_cast<unsigned>(blockY);
    config.blockDimZ = static_cast<unsigned>(blockZ);
    config.sharedMemBytes = static_cast<unsigned>(smem);
    config.hStream = stream;
    config.attrs = attrs;
    config.numAttrs = 1;

    HIP_REPORT_IF_ERROR(launchKernelEx(&config, function, params, extra));
  } else {
    if ((clusterX > 1) || (clusterY > 1) || (clusterZ > 1)) {
      fprintf(stderr,
              "[mgpuLaunchClusterKernel] cluster=(%ld,%ld,%ld) requested but "
              "hipDrvLaunchKernelEx is unavailable; "
              "falling back to hipModuleLaunchKernel.\n",
              static_cast<long>(clusterX), static_cast<long>(clusterY),
              static_cast<long>(clusterZ));
    }
    HIP_REPORT_IF_ERROR(HIP_CALL(hipModuleLaunchKernel, function, gridX, gridY, gridZ, blockX,
                                 blockY, blockZ, smem, stream, params, extra));
  }
}

extern "C" hipStream_t mgpuStreamCreate() {
  hipStream_t stream = nullptr;
  HIP_REPORT_IF_ERROR(HIP_CALL(hipStreamCreate, &stream));
  return stream;
}

extern "C" void mgpuStreamDestroy(hipStream_t stream) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipStreamDestroy, stream));
}

extern "C" void mgpuStreamSynchronize(hipStream_t stream) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipStreamSynchronize, stream));
}

extern "C" void mgpuStreamWaitEvent(hipStream_t stream, hipEvent_t event) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipStreamWaitEvent, stream, event, /*flags=*/0));
}

extern "C" hipEvent_t mgpuEventCreate() {
  hipEvent_t event = nullptr;
  HIP_REPORT_IF_ERROR(HIP_CALL(hipEventCreateWithFlags, &event, /*hipEventDisableTiming=*/2));
  return event;
}

extern "C" void mgpuEventDestroy(hipEvent_t event) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipEventDestroy, event));
}

extern "C" void mgpuEventSynchronize(hipEvent_t event) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipEventSynchronize, event));
}

extern "C" void mgpuEventRecord(hipEvent_t event, hipStream_t stream) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipEventRecord, event, stream));
}

extern "C" void *mgpuMemAlloc(uint64_t sizeBytes, hipStream_t /*stream*/, bool /*isHostShared*/) {
  void *ptr = nullptr;
  HIP_REPORT_IF_ERROR(HIP_CALL(hipMalloc, &ptr, sizeBytes));
  return ptr;
}

extern "C" void mgpuMemFree(void *ptr, hipStream_t /*stream*/) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipFree, ptr));
}

extern "C" void mgpuMemcpy(void *dst, void *src, size_t sizeBytes, hipStream_t stream) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipMemcpyAsync, dst, src, sizeBytes, /*hipMemcpyDefault=*/4, stream));
}

extern "C" void mgpuMemset32(void *dst, int value, size_t count, hipStream_t stream) {
  HIP_REPORT_IF_ERROR(
      HIP_CALL(hipMemsetD32Async, reinterpret_cast<hipDeviceptr_t>(dst), value, count, stream));
}

extern "C" void mgpuMemset16(void *dst, int shortValue, size_t count, hipStream_t stream) {
  HIP_REPORT_IF_ERROR(
      HIP_CALL(hipMemsetD16Async, reinterpret_cast<hipDeviceptr_t>(dst), shortValue, count, stream));
}

extern "C" void mgpuMemHostRegister(void *ptr, uint64_t sizeBytes) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipHostRegister, ptr, sizeBytes, /*flags=*/0));
}

extern "C" void mgpuMemHostRegisterMemRef(int64_t rank, StridedMemRefType<char, 1> *descriptor,
                                          int64_t elementSizeBytes) {
  int64_t *sizes = descriptor->sizes;
  int64_t *strides = sizes + rank;

  std::vector<int64_t> denseStrides(static_cast<size_t>(rank));
  if (rank > 0) {
    denseStrides[static_cast<size_t>(rank - 1)] = sizes[rank - 1];
    for (int64_t i = rank - 2; i >= 0; --i)
      denseStrides[static_cast<size_t>(i)] = sizes[i] * denseStrides[static_cast<size_t>(i + 1)];
  }
  auto sizeBytes = (rank > 0 ? denseStrides[0] : 1) * elementSizeBytes;

  for (int64_t i = 0; i < rank - 1; ++i)
    denseStrides[static_cast<size_t>(i)] = denseStrides[static_cast<size_t>(i + 1)];
  if (rank > 0)
    denseStrides[static_cast<size_t>(rank - 1)] = 1;

  for (int64_t i = 0; i < rank; ++i)
    assert(strides[i] == denseStrides[static_cast<size_t>(i)]);

  auto ptr = descriptor->data + descriptor->offset * elementSizeBytes;
  mgpuMemHostRegister(ptr, sizeBytes);
}

extern "C" void mgpuMemHostUnregister(void *ptr) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipHostUnregister, ptr));
}

extern "C" void mgpuMemHostUnregisterMemRef(int64_t /*rank*/,
                                            StridedMemRefType<char, 1> *descriptor,
                                            int64_t elementSizeBytes) {
  auto ptr = descriptor->data + descriptor->offset * elementSizeBytes;
  mgpuMemHostUnregister(ptr);
}

template <typename T> static void mgpuMemGetDevicePointer(T *hostPtr, T **devicePtr) {
  HIP_REPORT_IF_ERROR(HIP_CALL(hipSetDevice, defaultDevice));
  HIP_REPORT_IF_ERROR(HIP_CALL(hipHostGetDevicePointer, (void **)devicePtr, hostPtr, /*flags=*/0));
}

extern "C" StridedMemRefType<float, 1> mgpuMemGetDeviceMemRef1dFloat(float * /*allocated*/,
                                                                     float *aligned, int64_t offset,
                                                                     int64_t size, int64_t stride) {
  float *devicePtr = nullptr;
  mgpuMemGetDevicePointer(aligned, &devicePtr);
  return {devicePtr, devicePtr, offset, {size}, {stride}};
}

extern "C" StridedMemRefType<int32_t, 1> mgpuMemGetDeviceMemRef1dInt32(int32_t * /*allocated*/,
                                                                       int32_t *aligned,
                                                                       int64_t offset, int64_t size,
                                                                       int64_t stride) {
  int32_t *devicePtr = nullptr;
  mgpuMemGetDevicePointer(aligned, &devicePtr);
  return {devicePtr, devicePtr, offset, {size}, {stride}};
}

extern "C" void mgpuSetDefaultDevice(int32_t device) {
  defaultDevice = device;
  HIP_REPORT_IF_ERROR(HIP_CALL(hipSetDevice, device));
}
