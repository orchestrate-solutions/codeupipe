cmake_minimum_required(VERSION 3.20)
project(codeupipe_cpp CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_compile_options(-Wall -Wextra -Wpedantic)

# ---------------------------------------------------------------------------
# Header-only core
# ---------------------------------------------------------------------------
add_library(codeupipe_core INTERFACE)
target_include_directories(codeupipe_core INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(codeupipe_core INTERFACE cxx_std_20)

# ---------------------------------------------------------------------------
# Tests (Catch2, fetched at configure time; test-only dep)
# ---------------------------------------------------------------------------
option(CUP_BUILD_TESTS "Build codeupipe C++ tests" ON)
if(CUP_BUILD_TESTS)
  include(FetchContent)
  FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG        v3.5.3
  )
  FetchContent_MakeAvailable(Catch2)

  add_executable(cup_tests
    tests/test_payload.cpp
    tests/test_filter.cpp
    tests/test_pipeline.cpp
    tests/test_valve.cpp
    tests/test_contract.cpp
    tests/test_step_identity.cpp
    tests/test_tap.cpp
    tests/test_hook.cpp
    tests/test_state.cpp
    tests/test_invariants.cpp
  )
  target_link_libraries(cup_tests PRIVATE codeupipe_core Catch2::Catch2WithMain)

  enable_testing()
  include(CTest)
  add_test(NAME cup_tests COMMAND cup_tests)
endif()

# ---------------------------------------------------------------------------
# Bench
# ---------------------------------------------------------------------------
option(CUP_BUILD_BENCH "Build codeupipe C++ benchmarks" ON)
if(CUP_BUILD_BENCH)
  add_executable(cup_bench bench/bench_hop.cpp)
  target_link_libraries(cup_bench PRIVATE codeupipe_core)
  target_compile_options(cup_bench PRIVATE -O3)

  add_executable(cup_bench_raw bench/bench_raw.cpp)
  target_compile_options(cup_bench_raw PRIVATE -O3)
endif()

# ---------------------------------------------------------------------------
# Example
# ---------------------------------------------------------------------------
option(CUP_BUILD_EXAMPLES "Build codeupipe C++ examples" ON)
if(CUP_BUILD_EXAMPLES)
  add_executable(clean_validate_save examples/clean_validate_save/main.cpp)
  target_link_libraries(clean_validate_save PRIVATE codeupipe_core)
endif()
