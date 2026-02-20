# GNSS-SDR (OpenCL): Host-Misuse Case Study – kernel_name handling in clFFT + off-by-one buffer index in OpenCL acquisition

## Scope / What this artifact contains
This artifact documents a GNSS-SDR OpenCL-related host-side issue investigation and the resulting fixes. It is written to be reproducible by third parties:
- how the issue was observed and narrowed down,
- how it can be reproduced (including optional debugger evidence),
- what was changed (patch),
- which tools were used,
- and how to validate the fixed build.

All evidence files (patch + logs) are intended to be stored under:
`~/projects/opencl-host-misuse-study/artifacts/GNSS-SDR/`

## Environment assumptions
- OS: Linux (Ubuntu-like).
- GNSS-SDR built from source with Ninja/CMake (out-of-tree build directory `build/`).
- OpenCL is available. The documented run used the NVIDIA OpenCL ICD (reported as “Using platform: NVIDIA CUDA” and device “NVIDIA GeForce RTX 5050”).
- The configuration file `gps_ibyte_opencl_acq.conf` exists either:
  - in the repo: `repo/gnss-sdr/conf/local/gps_ibyte_opencl_acq.conf`, and/or
  - installed system-wide: `/usr/local/share/gnss-sdr/conf/local/gps_ibyte_opencl_acq.conf`.

Important: `gnss-sdr --config_file=...` validates that the file exists. Relative paths are resolved relative to the current working directory.

## Summary of the observed problems
Two independent host-side problems were addressed:

### (A) Off-by-one / inconsistent buffer indexing in OpenCL acquisition
File: `src/algorithms/acquisition/gnuradio_blocks/pcps_opencl_acquisition_cc.cc`

In `pcps_opencl_acquisition_cc::acquisition_core_opencl()`, the code used `d_well_count` as an index into `d_in_buffer[]` and then incremented it, but later in the same function still accessed `d_in_buffer[d_well_count]`. This made the indexing inconsistent and could access the next (or an invalid) dwell buffer.

This manifested as a segmentation fault observed under debugger tooling, with a backtrace pointing into `libvolk` when `volk_32fc_magnitude_squared_32f(...)` was called.

Fix: Snapshot the current dwell index once at function entry and consistently use that snapshot for all accesses.

Evidence (fixed code location):
- `pcps_opencl_acquisition_cc.cc`, around lines 428–463 (example line numbers from `nl -ba`):
  - `const uint32_t well = d_well_count;`
  - use `d_in_buffer[well]` consistently
  - increment `d_well_count++` after staging the input

### (B) Incorrect `kernel_name` handling in clFFT kernel string generator
File: `src/algorithms/libs/opencl/fft_kernelstring.cc`

The code allocated `kernel_name` manually and then used `snprintf(...)` with an incorrect size expression (`sizeof(pointer)` pattern). This is a classic “sizeof(pointer) used as buffer size” host-side defect pattern that is relevant for an OpenCL host-misuse taxonomy.

Fix: Replace the manual allocation + snprintf usage with `strdup(kernelName.c_str())`.

Evidence (fixed code locations):
- `fft_kernelstring.cc` around `createLocalMemfftKernelString(...)` (example: line ~893)
- `fft_kernelstring.cc` around `createGlobalFFTKernelString(...)` (example: line ~1144)

## Tools used during investigation
- `grep`, `nl`, `sed`, `perl`: locate and patch relevant code sections.
- `strace -f -e openat,access`: verify where kernel sources (e.g., `math_kernel.cl`) are searched for.
- `oclgrind`: OpenCL simulator/tooling used to run GNSS-SDR in a tool-instrumented environment.
- `gdb`: capture a deterministic backtrace of the crash.
- `ninja`: rebuild and install.

Notes:
- `oclgrind --log ...` may produce an empty file if it does not emit warnings before a crash. Capturing stdout/stderr via `tee` is recommended.
- `gdb` may ask about debuginfod. Use `set debuginfod enabled off` or answer `n` for reproducibility/offline usage.

## Reproduction guide

### 1) Build and install GNSS-SDR (baseline)
From the GNSS-SDR repo root:
```bash
cd ~/projects/opencl-host-misuse-study/repo/gnss-sdr
ninja -C build
sudo ninja -C build install
