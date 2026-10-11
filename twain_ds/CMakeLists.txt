cmake_minimum_required(VERSION 3.21)

project(NospeVirtualScanner LANGUAGES CXX)

add_library(NospeVirtualScanner SHARED
    src/NospeVirtualScanner.cpp
)

target_compile_features(NospeVirtualScanner PRIVATE cxx_std_17)
target_compile_definitions(NospeVirtualScanner PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

set_target_properties(NospeVirtualScanner PROPERTIES
    OUTPUT_NAME "NospeVirtualScanner"
    SUFFIX ".ds"
)

if (MSVC)
    target_compile_options(NospeVirtualScanner PRIVATE /W4 /permissive-)
endif()

if (WIN32)
    target_link_libraries(NospeVirtualScanner PRIVATE gdiplus)
endif()
