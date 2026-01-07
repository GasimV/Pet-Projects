cmake_minimum_required(VERSION 3.15)
project(proxima_qr)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/libs)
include_directories(${CMAKE_SOURCE_DIR}/libs/cpp-httplib)
include_directories(${CMAKE_SOURCE_DIR}/libs/json/include)
include_directories(${CMAKE_SOURCE_DIR}/libs/qrcodegen/cpp)
include_directories(${CMAKE_SOURCE_DIR}/libs/sqlite3)
include_directories(${CMAKE_SOURCE_DIR}/libs/stb)

# Source files
set(SOURCES
    src/main.cpp
    src/auth.cpp
    src/storage.cpp
    src/qr_generator.cpp
    src/templates.cpp
    src/utils.hpp
    libs/qrcodegen/cpp/qrcodegen.cpp
    libs/sqlite3/sqlite3.c
)

# Create executable
add_executable(proxima_qr ${SOURCES})

# Platform-specific settings
if(WIN32)
    target_link_libraries(proxima_qr ws2_32 wsock32)
else()
    target_link_libraries(proxima_qr pthread dl)
endif()

# Compiler flags
if(MSVC)
    target_compile_options(proxima_qr PRIVATE /W4)
else()
    target_compile_options(proxima_qr PRIVATE -Wall -Wextra)
endif()
