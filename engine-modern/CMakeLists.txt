cmake_minimum_required(VERSION 3.24)

project(dwnominate_modern VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
include(CTest)

option(DWNOMINATE_FETCH_DEPENDENCIES
       "Download Eigen and NLopt when they are not installed" ON)
option(DWNOMINATE_ENABLE_OPENMP "Parallelize independent model blocks" OFF)
option(DWNOMINATE_ENABLE_REGRESSION_TESTS
       "Run the committed Chile and US numerical regression panels" OFF)

find_package(Eigen3 3.4 CONFIG QUIET)
if(NOT Eigen3_FOUND)
    if(NOT DWNOMINATE_FETCH_DEPENDENCIES)
        message(FATAL_ERROR "Eigen3 was not found")
    endif()
    set(EIGEN_BUILD_DOC OFF CACHE BOOL "" FORCE)
    set(BUILD_TESTING_SAVED ${BUILD_TESTING})
    set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
    FetchContent_Declare(
        eigen
        GIT_REPOSITORY https://gitlab.com/libeigen/eigen.git
        GIT_TAG 549bf8c75b6aae071cde2f28aa48f16ee3ae60b0
        GIT_SHALLOW FALSE
    )
    FetchContent_MakeAvailable(eigen)
    set(BUILD_TESTING ${BUILD_TESTING_SAVED} CACHE BOOL "" FORCE)
endif()

find_package(NLopt 2.10 CONFIG QUIET)
if(NOT NLopt_FOUND)
    if(NOT DWNOMINATE_FETCH_DEPENDENCIES)
        message(FATAL_ERROR "NLopt was not found")
    endif()
    set(NLOPT_CXX ON CACHE BOOL "" FORCE)
    set(NLOPT_PYTHON OFF CACHE BOOL "" FORCE)
    set(NLOPT_OCTAVE OFF CACHE BOOL "" FORCE)
    set(NLOPT_MATLAB OFF CACHE BOOL "" FORCE)
    set(NLOPT_GUILE OFF CACHE BOOL "" FORCE)
    set(NLOPT_SWIG OFF CACHE BOOL "" FORCE)
    set(NLOPT_TESTS OFF CACHE BOOL "" FORCE)
    FetchContent_Declare(
        nlopt
        GIT_REPOSITORY https://github.com/stevengj/nlopt.git
        GIT_TAG 88c424d4f458412787df96fcc95218acbca224fd
        GIT_SHALLOW FALSE
    )
    FetchContent_MakeAvailable(nlopt)
endif()

if(TARGET NLopt::nlopt)
    set(DWNOMINATE_NLOPT_TARGET NLopt::nlopt)
elseif(TARGET nlopt)
    set(DWNOMINATE_NLOPT_TARGET nlopt)
else()
    message(FATAL_ERROR "NLopt target was not created")
endif()

if(DWNOMINATE_ENABLE_OPENMP)
    find_package(OpenMP QUIET)
endif()

set(DWNOMINATE_CORE_SOURCES
    src/csv_loader.cpp
    src/cutting_plane.cpp
    src/cutting_point.cpp
    src/dwnominate.cpp
    src/parameter_optimizer.cpp
    src/legislator_derivatives.cpp
    src/likelihood.cpp
    src/normal_cdf.cpp
    src/optimize_legislators.cpp
    src/rollcall_derivatives.cpp
    src/rollcall_optimizer.cpp
)

add_library(dwnominate_core ${DWNOMINATE_CORE_SOURCES})
target_include_directories(dwnominate_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(dwnominate_core PUBLIC Eigen3::Eigen ${DWNOMINATE_NLOPT_TARGET})
target_compile_features(dwnominate_core PUBLIC cxx_std_20)

if(OpenMP_CXX_FOUND)
    target_link_libraries(dwnominate_core PUBLIC OpenMP::OpenMP_CXX)
endif()

if(MSVC)
    target_compile_options(dwnominate_core PRIVATE /W4 /permissive-)
else()
    target_compile_options(dwnominate_core PRIVATE
        -Wall -Wextra -Wpedantic -Wconversion -Wshadow
    )
endif()

# Deliberately no -ffast-math: probabilities near zero and active constraints
# require IEEE-consistent behavior for reproducible diagnostics.

add_executable(dwnominate_modern src/main_cli.cpp)
set_target_properties(dwnominate_modern PROPERTIES OUTPUT_NAME dwnominate-modern)
target_link_libraries(dwnominate_modern PRIVATE dwnominate_core)

if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_executable(test_unit_ball tests/test_unit_ball.cpp)
    target_link_libraries(test_unit_ball PRIVATE dwnominate_core)
    add_test(NAME unit_ball_constraints COMMAND test_unit_ball)

    add_executable(test_scalar_optimizer tests/test_scalar_optimizer.cpp)
    target_link_libraries(test_scalar_optimizer PRIVATE dwnominate_core)
    add_test(NAME scalar_optimizer COMMAND test_scalar_optimizer)

    add_executable(test_legacy_input_rounding tests/test_legacy_input_rounding.cpp)
    target_link_libraries(test_legacy_input_rounding PRIVATE dwnominate_core)
    add_test(NAME legacy_input_rounding COMMAND test_legacy_input_rounding)

    add_executable(test_cutplane_alignment tests/test_cutplane_alignment.cpp)
    target_link_libraries(test_cutplane_alignment PRIVATE dwnominate_core)
    add_test(NAME cutplane_alignment COMMAND test_cutplane_alignment)

    add_executable(test_optimizer_gradients tests/test_optimizer_gradients.cpp)
    target_link_libraries(test_optimizer_gradients PRIVATE dwnominate_core)
    add_test(NAME optimizer_gradients COMMAND test_optimizer_gradients)

    add_executable(test_feasibility_contract tests/test_feasibility_contract.cpp)
    target_link_libraries(test_feasibility_contract PRIVATE dwnominate_core)
    add_test(NAME feasibility_contract COMMAND test_feasibility_contract)

    add_test(
        NAME chile_static_alias_smoke
        COMMAND dwnominate_modern
            --input-dir=${CMAKE_CURRENT_SOURCE_DIR}/../data/chile-static/leg353
            --output-dir=${CMAKE_CURRENT_BINARY_DIR}/test-output/chile353
            --wnominate=${CMAKE_CURRENT_SOURCE_DIR}/../data/chile-static/leg353/wnominate_coordinates.csv
            --model=0 --iterations=1 --dimensions=2
            --block-solver=slsqp --scalar-search=local
    )
    set_tests_properties(chile_static_alias_smoke PROPERTIES TIMEOUT 60)

    add_test(
        NAME convergence_and_served_export
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_convergence_and_export.py
            $<TARGET_FILE:dwnominate_modern>
            ${CMAKE_CURRENT_SOURCE_DIR}/../data/chile-static/leg353
            ${CMAKE_CURRENT_BINARY_DIR}/test-output/convergence-chile353
    )
    set_tests_properties(convergence_and_served_export PROPERTIES TIMEOUT 120)

    add_test(
        NAME dynamic_state_roundtrip
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_dynamic_roundtrip.py
            $<TARGET_FILE:dwnominate_modern>
            ${CMAKE_CURRENT_SOURCE_DIR}/../engine-faithful/benchmarks/us/cpp_input
            ${CMAKE_CURRENT_BINARY_DIR}/test-output/dynamic-roundtrip
    )
    set_tests_properties(dynamic_state_roundtrip PROPERTIES TIMEOUT 180)

    if(DWNOMINATE_ENABLE_REGRESSION_TESTS)
        add_test(
            NAME reference_panels
            COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/tools/validate_reference_panels.py
                --binary=$<TARGET_FILE:dwnominate_modern>
                --repo-root=${CMAKE_CURRENT_SOURCE_DIR}/..
                --work-dir=${CMAKE_CURRENT_BINARY_DIR}/regression-output
        )
        set_tests_properties(reference_panels PROPERTIES TIMEOUT 300)
    endif()
endif()
