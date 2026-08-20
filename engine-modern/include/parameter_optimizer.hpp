#ifndef PARAMETER_OPTIMIZER_HPP
#define PARAMETER_OPTIMIZER_HPP

#include "likelihood.hpp"
#include "normal_cdf.hpp"

#include <Eigen/Dense>
#include <vector>

/**
 * Compatibility name retained for the orchestrator. The implementation no
 * longer performs a grid search: scalar parameters are optimized by NLopt's
 * bound-constrained BOBYQA implementation.
 */
struct ParameterOptimizationResult
{
    double value = 0.0;
    double logLikelihood = 0.0;
    int iterations = 0;
    double initialValue = 0.0;
    double initialLL = 0.0;
    bool converged = false;
    int direction = 0;
    int optimizerStatus = 0;
    bool accepted = false;
    bool rawReturnFeasible = false;
    bool numericalCorrectionApplied = false;
    double rawConstraintViolation = 0.0;
    double feasibilityCorrection = 0.0;
};

using BetaOptimizationResult = ParameterOptimizationResult;
using WeightOptimizationResult = ParameterOptimizationResult;

struct ScalarOptimizerConfig
{
    double lowerBound = 0.01;
    double upperBound = 20.0;
    // Radius around the value at the start of an outer iteration. A positive
    // value preserves the finite reach of Fortran's SIGMAS/WINT searches while
    // still using NLopt/BOBYQA inside that interval. Zero selects a global box.
    double localRadius = 0.0;
    double initialStep = 0.05;
    double relativeXTolerance = 1e-8;
    double relativeFTolerance = 1e-10;
    double feasibilityTolerance = 1e-12;
    double acceptanceTolerance = 1e-8;
    int maxEvaluations = 120;
    bool verbose = false; // retained for CLI compatibility
};

using BetaOptimizerConfig = ScalarOptimizerConfig;
using WeightOptimizerConfig = ScalarOptimizerConfig;

struct LikelihoodContext
{
    const Eigen::MatrixXd &legislatorCoords;
    const std::vector<RollCallParameters> &rollCallParams;
    const VoteMatrix &votes;
    Eigen::VectorXd &weights;
    const NormalCDF &normalCDF;
    const std::vector<bool> &validRollCalls;

    LikelihoodContext(
        const Eigen::MatrixXd &coords,
        const std::vector<RollCallParameters> &rcParams,
        const VoteMatrix &voteMatrix,
        Eigen::VectorXd &modelWeights,
        const NormalCDF &cdf,
        const std::vector<bool> &valid)
        : legislatorCoords(coords),
          rollCallParams(rcParams),
          votes(voteMatrix),
          weights(modelWeights),
          normalCDF(cdf),
          validRollCalls(valid)
    {
    }
};

ParameterOptimizationResult optimizeParameter(
    LikelihoodContext &context,
    int paramIndex,
    const ScalarOptimizerConfig &config);

BetaOptimizationResult optimizeBeta(
    LikelihoodContext &context,
    const BetaOptimizerConfig &config = BetaOptimizerConfig());

WeightOptimizationResult optimizeWeight2(
    LikelihoodContext &context,
    const WeightOptimizerConfig &config = WeightOptimizerConfig());

inline BetaOptimizerConfig sigmasConfig()
{
    BetaOptimizerConfig config;
    config.lowerBound = 0.05;
    config.upperBound = 20.0;
    // Fortran: accepted probe plus NINC=15 steps, each of size 0.1.
    config.localRadius = 1.6;
    config.initialStep = 0.1;
    return config;
}

inline WeightOptimizerConfig wintConfig()
{
    WeightOptimizerConfig config;
    // The sign of a dimensional weight is unidentified because the likelihood
    // contains w_k^2. A positive interval removes that redundant gauge.
    config.lowerBound = 0.01;
    config.upperBound = 2.0;
    // Fortran: accepted probe plus NINC=15 steps, each of size 0.01.
    config.localRadius = 0.16;
    config.initialStep = 0.01;
    return config;
}

#endif
