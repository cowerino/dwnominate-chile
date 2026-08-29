cmake_minimum_required(VERSION 3.15)
project(nominate_cmodule)

# Forzar modo Release por defecto
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Buscar dependencias
find_package(OpenMP REQUIRED)
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(NLOPT nlopt)
endif()
find_package(BLAS)

# The canonical Fortran computes the CUTPLANE SEARCH SVDs with LAPACK's DGESDD
# (DW-NOMINATE-wmay.f lines 3319 and 3333). The matched configuration therefore
# routes this engine's CUTPLANE SVDs through the same routine, and it takes
# precedence over the Eigen/LAPACKE route below. Every matched-arm comparison
# published from this package (the three-engine vintage under results/ and the
# optimizer-isolation protocol) was produced with this configuration; the
# LAPACKE route below reproduces the earlier engine-lineage likelihoods only.
option(USE_SYSTEM_DGESDD
       "Use the system LAPACK DGESDD used by wmay/dwnominate SEARCH (matched configuration)" ON)
set(SYSTEM_LAPACK_LIBRARY "" CACHE FILEPATH
    "Explicit LAPACK library for the DGESDD route")
set(SYSTEM_BLAS_LIBRARY "" CACHE FILEPATH
    "Explicit BLAS library for the DGESDD route")

# REQ-005 Stage 2: locally-built reference netlib LAPACK 3.12.1.
# Routes Eigen's SVD through LAPACKE_dgesvd via EIGEN_USE_LAPACKE.
# See external/lapack-3.12.1/ for the source build.
#
# 2026-08-20: the SVD backend is now an EXPLICIT switch, not an implicit
# consequence of a static library happening to exist on disk. Rung L3 of the
# tolerance ladder (findings/FINDING-tolerance-rungs-2026-08-17.md) measures
# Eigen JacobiSVD against LAPACKE_dgesvd at +780.75 nats on one config and
# -433.63 on another, and it is the ONLY rung that moves a reported parameter.
# A quantity that large must be selectable and recorded, not inferred from a
# file test. This route reproduces the earlier engine-lineage likelihoods
# (statics, tolerance-ladder findings); it is NOT the matched configuration,
# which is USE_SYSTEM_DGESDD above and takes precedence.
option(USE_REF_LAPACK "Route Eigen's SVD through LAPACKE_dgesvd (engine-lineage configuration)" ON)
set(REF_LAPACK_ROOT ${CMAKE_SOURCE_DIR}/external/lapack-3.12.1/build)
if(USE_SYSTEM_DGESDD)
    if(SYSTEM_LAPACK_LIBRARY AND SYSTEM_BLAS_LIBRARY)
        set(DWNOM_SYSTEM_LINEAR_ALGEBRA
            ${SYSTEM_LAPACK_LIBRARY} ${SYSTEM_BLAS_LIBRARY})
    elseif(EXISTS ${REF_LAPACK_ROOT}/lib/liblapack.a AND EXISTS ${REF_LAPACK_ROOT}/lib/libblas.a)
        # The vendored reference netlib build serves the DGESDD route too:
        # deterministic, no CPU dispatch, the same library the matched arms link.
        set(DWNOM_SYSTEM_LINEAR_ALGEBRA
            ${REF_LAPACK_ROOT}/lib/liblapack.a
            ${REF_LAPACK_ROOT}/lib/libblas.a)
    else()
        message(FATAL_ERROR
            "USE_SYSTEM_DGESDD is ON (the matched configuration) but no LAPACK/BLAS was found.\n"
            "  Either build external/lapack-3.12.1 per external/README-DEPENDENCIES.md, or pass\n"
            "  -DSYSTEM_LAPACK_LIBRARY= and -DSYSTEM_BLAS_LIBRARY= explicitly.\n"
            "  There is deliberately no silent fallback: the SVD route moves dynamic-panel\n"
            "  optima by hundreds of nats. To build the Eigen/LAPACKE engine-lineage\n"
            "  configuration instead, configure with -DUSE_SYSTEM_DGESDD=OFF.")
    endif()
    set(REF_LAPACK_FOUND FALSE)
    message(STATUS "CUTPLANE SEARCH: system LAPACK DGESDD")
elseif(USE_REF_LAPACK AND EXISTS ${REF_LAPACK_ROOT}/lib/liblapacke.a)
    set(REF_LAPACK_FOUND TRUE)
    message(STATUS "Reference LAPACK found at ${REF_LAPACK_ROOT} (EIGEN_USE_LAPACKE ON)")
elseif(NOT USE_REF_LAPACK)
    message(STATUS "USE_REF_LAPACK=OFF: Eigen's own JacobiSVD will be used")
else()
    # 2026-08-21: this branch used to be silent, and that silence is the single
    # most expensive defect in the reproduction package. USE_REF_LAPACK defaults
    # ON, so a user who has not built external/lapack-3.12.1 got a Jacobi binary
    # while believing they had built the published configuration -- and the
    # backend moves the likelihood by 2.4 to 31.8 nats, changing which engine
    # wins on 2 of 4 panels. It is never acceptable to resolve this quietly.
    message(WARNING
        "USE_REF_LAPACK is ON but ${REF_LAPACK_ROOT}/lib/liblapacke.a was NOT found.\n"
        "  Falling back to Eigen's own JacobiSVD. THIS IS NEITHER PUBLISHED CONFIGURATION.\n"
        "  The engine-lineage likelihoods were produced with LAPACKE; the two backends differ by\n"
        "  2.4 to 31.8 nats on the panels in the paper and disagree about which engine wins\n"
        "  on 2 of 4 of them. The backend actually used is recorded as 'svd_backend' in\n"
        "  every cpp_summary.csv -- check it before comparing any likelihood.\n"
        "  To build the published configuration, see external/README-DEPENDENCIES.md.\n"
        "  To silence this deliberately, configure with -DUSE_REF_LAPACK=OFF.")
endif()

# Eigen is MANDATORY and is not part of a normal system install here; the
# reproduction package shipped without it, so the failure mode was a wall of
# 'Eigen/Dense: No such file' rather than one actionable line.
if(NOT EXISTS ${CMAKE_SOURCE_DIR}/Eigen/Dense
   AND NOT EXISTS ${CMAKE_SOURCE_DIR}/Eigen/Eigen/Dense)
    message(FATAL_ERROR
        "Eigen headers not found at ${CMAKE_SOURCE_DIR}/Eigen.\n"
        "  Eigen is a required, header-only dependency. Obtain Eigen 3.4.0 and place its\n"
        "  headers so that ${CMAKE_SOURCE_DIR}/Eigen/Dense resolves.\n"
        "  See external/README-DEPENDENCIES.md for the exact pinned version and layout.")
endif()

# REQ-005 Stage 2b: locally-built OpenBLAS 0.3.33 (BLAS + LAPACK + LAPACKE bundled,
# with optimized assembly kernels). Toggle via -DUSE_OPENBLAS=ON at cmake time.
# When ON, replaces REF_LAPACK linkage. See external/OpenBLAS-0.3.33/ for source build.
option(USE_OPENBLAS "Link against locally-built OpenBLAS instead of reference netlib LAPACK" OFF)
set(OPENBLAS_ROOT ${CMAKE_SOURCE_DIR}/external/OpenBLAS-0.3.33/build)
if(USE_OPENBLAS AND EXISTS ${OPENBLAS_ROOT}/lib/libopenblas.a)
    set(OPENBLAS_FOUND TRUE)
    set(REF_LAPACK_FOUND FALSE)  # mutually exclusive
    message(STATUS "OpenBLAS found at ${OPENBLAS_ROOT} (will replace reference LAPACK)")
endif()

# Incluir directorios
include_directories(
    ${CMAKE_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/Eigen
    ${NLOPT_INCLUDE_DIRS}
)
if(REF_LAPACK_FOUND)
    include_directories(${REF_LAPACK_ROOT}/include)
endif()
if(OPENBLAS_FOUND)
    # OpenBLAS bundles netlib LAPACK headers in its source tree
    include_directories(
        ${OPENBLAS_ROOT}
        ${OPENBLAS_ROOT}/generated
        ${CMAKE_SOURCE_DIR}/external/OpenBLAS-0.3.33/lapack-netlib/LAPACKE/include
    )
endif()

# Fuentes compartidas
set(CORE_SOURCES
    src/dwnominate.cpp
    src/csv_loader.cpp
    src/likelihood.cpp
    src/normal_cdf.cpp
    src/cutting_plane.cpp
    src/cutting_point.cpp
    src/grid_optimizer.cpp
    src/rollcall_optimizer.cpp
    src/rollcall_derivatives.cpp
    src/optimize_legislators.cpp
    src/legislator_derivatives.cpp
    src/simple_ols.cpp
)

# EJECUTABLE PRINCIPAL: dwnominate
add_executable(dwnominate src/main_cli.cpp ${CORE_SOURCES})

target_link_libraries(dwnominate 
    ${NLOPT_LIBRARIES}
    OpenMP::OpenMP_CXX
)
target_link_directories(dwnominate PRIVATE ${NLOPT_LIBRARY_DIRS})
target_compile_definitions(dwnominate PRIVATE USE_OPENMP)
# Keep the negative-control arithmetic comparable with engine-modern and the
# Fortran reference. Fast-math changes likelihood summation and boundary
# behavior in a non-convex fixed-cycle procedure; -march=native also makes the
# receipt machine-specific. Release optimization is already supplied by CMake.
# (Until 2026-08-29 this line carried -march=native -ffast-math, which the
# matched protocol forbids; the isolation builds never used them.)
target_compile_options(dwnominate PRIVATE -O3 -DNDEBUG)

if(USE_SYSTEM_DGESDD)
    target_link_libraries(dwnominate ${DWNOM_SYSTEM_LINEAR_ALGEBRA} gfortran quadmath)
    target_compile_definitions(dwnominate PRIVATE DWNOM_USE_FORTRAN_DGESDD)
endif()

if(BLAS_FOUND)
    target_link_libraries(dwnominate ${BLAS_LIBRARIES})
    target_compile_definitions(dwnominate PRIVATE EIGEN_USE_BLAS)
endif()

if(REF_LAPACK_FOUND)
    # Link order matters: lapacke -> lapack -> blas -> gfortran runtime
    target_link_libraries(dwnominate
        ${REF_LAPACK_ROOT}/lib/liblapacke.a
        ${REF_LAPACK_ROOT}/lib/liblapack.a
        ${REF_LAPACK_ROOT}/lib/libblas.a
        gfortran
        quadmath
    )
    target_compile_definitions(dwnominate PRIVATE EIGEN_USE_LAPACKE EIGEN_USE_BLAS)
endif()

if(OPENBLAS_FOUND)
    # OpenBLAS provides BLAS + LAPACK + LAPACKE in a single static archive
    target_link_libraries(dwnominate
        ${OPENBLAS_ROOT}/lib/libopenblas.a
        gfortran
        quadmath
    )
    target_compile_definitions(dwnominate PRIVATE EIGEN_USE_LAPACKE EIGEN_USE_BLAS)
endif()

# VALIDADOR CSV: test_validate_csv (optional - only if source exists)
if(EXISTS "${CMAKE_SOURCE_DIR}/tests/test_validate_csv.cpp")
    add_executable(test_validate_csv tests/test_validate_csv.cpp)
    target_compile_options(test_validate_csv PRIVATE -O3 -DNDEBUG)
endif()

# Mensajes de estado
message(STATUS "NLopt: ${NLOPT_LIBRARIES}")
message(STATUS "OpenMP: ${OpenMP_CXX_VERSION}")
if(BLAS_FOUND)
    message(STATUS "BLAS: ${BLAS_LIBRARIES}")
endif()

