Tested commit: <git rev-parse --short HEAD>
Local changes: added Linux CMake build + cas_harness.c; optional tool-compat patch (CL_sRGBA->CL_RGBA).
Tool result: oclgrind fails pre-patch at clCreateImage(image_format); passes post-patch.


# CAS-2D Analysis & Tooling

## Scope
Goal: Make CAS-2D (OpenCL path) buildable + runnable under oclgrind (--check-api) for host-API misuse screening.

Tested commit: <git rev-parse --short HEAD>
Local modifications (not upstream):
- Added Linux CMake build (custom CMakeLists.txt)
- Added harness: cas_harness.c (uses CAS_* API)
- Tool-compat patch (optional): CL_sRGBA -> CL_RGBA in CAS-2D-Lib/CASImpl.cpp

## Prerequisites (Ubuntu)
- cmake, gcc
- OpenCL ICD + headers: libOpenCL + clinfo
- oclgrind 21.10+

Suggested:
  sudo apt-get install cmake gcc oclgrind clinfo ocl-icd-opencl-dev opencl-headers

## Build (Linux, OpenCL-only)
cd repo/CAS-2D/build
rm -rf *
cmake ..
make

## Harness (triggers OpenCL path)
cd repo/CAS-2D
gcc -std=c99 -O0 -g -o cas_harness cas_harness.c \
  -L./build -I./CAS-2D-Lib/include -lCAS2D -lOpenCL

export LD_LIBRARY_PATH=./build:$LD_LIBRARY_PATH
./cas_harness

## Tool run (oclgrind)
oclgrind --version
oclgrind --check-api ./cas_harness

## Tool-compat patch (optional)
### Motivation
Oclgrind fails at clCreateImage with CL_INVALID_VALUE when using CL_sRGBA image format
(cl::ImageFormat(CL_sRGBA, CL_UNORM_INT8)).
This may be a tool limitation or a portability issue (missing runtime format support check/fallback).

### Apply patch
# recommended: generate patch via git diff or diff -u and apply with git apply/patch
sed -i 's/CL_sRGBA/CL_RGBA/' CAS-2D-Lib/CASImpl.cpp
cd build && make && cd ..
oclgrind --check-api ./cas_harness

### Revert patch
# prefer restoring from a backup instead of global sed-replace
# e.g. cp CASImpl.cpp.bak CASImpl.cpp
	
	
	
## Findings
- Observation: Under oclgrind (--check-api), CAS fails at clCreateImage with CL_INVALID_VALUE for image_format when using CL_sRGBA/CL_UNORM_INT8.
- Workaround (tool-compat): Replace CL_sRGBA with CL_RGBA; then oclgrind run completes.
- Interpretation: Likely tool limitation for sRGB image formats and/or missing capability check + fallback in the app.
- Caveat: CL_sRGBA -> CL_RGBA can change color semantics; proper fix would query supported formats (clGetSupportedImageFormats) and select a supported fallback.

