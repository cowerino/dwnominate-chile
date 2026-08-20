#ifndef OPTIMIZER_OPTIONS_HPP
#define OPTIMIZER_OPTIONS_HPP

#include <stdexcept>
#include <string>

enum class BlockOptimizerAlgorithm
{
    Cobyla,
    Slsqp
};

enum class BlockSolverMode
{
    Cobyla,
    Slsqp,
    Hybrid
};

inline const char *toString(BlockOptimizerAlgorithm algorithm)
{
    return algorithm == BlockOptimizerAlgorithm::Slsqp ? "slsqp" : "cobyla";
}

inline const char *toString(BlockSolverMode mode)
{
    switch (mode)
    {
    case BlockSolverMode::Cobyla:
        return "cobyla";
    case BlockSolverMode::Slsqp:
        return "slsqp";
    case BlockSolverMode::Hybrid:
        return "hybrid";
    }
    return "cobyla";
}

inline BlockSolverMode parseBlockSolverMode(const std::string &value)
{
    if (value == "cobyla")
    {
        return BlockSolverMode::Cobyla;
    }
    if (value == "slsqp")
    {
        return BlockSolverMode::Slsqp;
    }
    if (value == "hybrid")
    {
        return BlockSolverMode::Hybrid;
    }
    throw std::invalid_argument(
        "block solver desconocido: " + value +
        " (use cobyla, slsqp o hybrid)");
}

inline BlockOptimizerAlgorithm resolveBlockAlgorithm(
    BlockSolverMode mode,
    int iteration,
    int finalIteration)
{
    if (mode == BlockSolverMode::Slsqp ||
        (mode == BlockSolverMode::Hybrid && iteration >= finalIteration))
    {
        return BlockOptimizerAlgorithm::Slsqp;
    }
    return BlockOptimizerAlgorithm::Cobyla;
}

#endif
