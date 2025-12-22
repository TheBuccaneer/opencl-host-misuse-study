cmake_minimum_required(VERSION 3.10)
project(CAS2D_Linux)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# OpenCL-Backend aktivieren
add_compile_definitions(_USE_OPENCL_)

# OpenCL finden (Linux System-Pakete)
find_package(OpenCL REQUIRED)

# Quelldateien - NUR OpenCL, CUDA ausschließen
set(SOURCES
    "CAS-2D-Lib/CASImpl.cpp"
    "CAS-2D-Lib/CASLibWrapper.cpp"
    "CAS-2D-Lib/opencl_utils.cpp"
)

set(HEADERS
    "CAS-2D-Lib/CASImpl.hpp"
    "CAS-2D-Lib/include/CASLibWrapper.h"
)

# Library erstellen (.so statt .dll)
add_library(CAS2D SHARED ${SOURCES} ${HEADERS})

# Include Directories
target_include_directories(CAS2D PRIVATE ${OpenCL_INCLUDE_DIRS})
target_include_directories(CAS2D PUBLIC "CAS-2D-Lib")
target_include_directories(CAS2D PUBLIC "CAS-2D-Lib/include")

# Linken
target_link_libraries(CAS2D PRIVATE OpenCL::OpenCL)

# Optional: Für Debugging
target_compile_options(CAS2D PRIVATE -Wall -Wextra)

# Optional: Install target (für später)
install(TARGETS CAS2D 
        LIBRARY DESTINATION lib
        PUBLIC_HEADER DESTINATION include)
