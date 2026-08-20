#ifndef ROLLCALL_OPTIMIZER_HPP
#define ROLLCALL_OPTIMIZER_HPP

#include "rollcall_derivatives.hpp"
#include "optimizer_options.hpp"
#include <Eigen/Dense>

/**
 * Configuration for the constrained roll-call maximum-likelihood problem.
 *
 * NLopt/COBYLA or SLSQP replaces the hand-written RCINT2 grid and line
 * searches. The constraint is expressed directly as
 * ||midpoint||^2 - 1 <= 0.
 */
struct RollCallOptimizerConfig
{
    int maxEvaluations = 400;
    double relativeXTolerance = 1e-8;
    double relativeFTolerance = 1e-10;
    double constraintTolerance = 1e-10;
    double midpointInitialStep = 0.05;
    double spreadInitialStep = 0.05;
    BlockOptimizerAlgorithm algorithm = BlockOptimizerAlgorithm::Cobyla;
    bool fallbackToCobyla = true;
};

struct RollCallOptimizationResult
{
    Eigen::VectorXd midpoint;
    Eigen::VectorXd spread;

    double logLikelihood = 0.0;
    double geometricMeanProb = 0.0;
    double initialGMP = 0.0;
    double initialLogLikelihood = 0.0;

    int totalIterations = 0; // objective evaluations performed by NLopt
    int spreadIterations = 0; // retained for output compatibility
    int midpointIterations = 0; // retained for output compatibility
    bool converged = false;
    int optimizerStatus = 0;
    BlockOptimizerAlgorithm algorithmUsed = BlockOptimizerAlgorithm::Cobyla;
    bool fallbackUsed = false;
    double elapsedMilliseconds = 0.0;

    int totalVotes = 0;
    int correctClassified = 0;

    RollCallOptimizationResult() = default;

    explicit RollCallOptimizationResult(int numDimensions)
        : midpoint(Eigen::VectorXd::Zero(numDimensions)),
          spread(Eigen::VectorXd::Zero(numDimensions))
    {
    }

    double getAccuracy() const
    {
        return totalVotes > 0
                   ? static_cast<double>(correctClassified) /
                         static_cast<double>(totalVotes)
                   : 0.0;
    }

    double getImprovement() const { return geometricMeanProb - initialGMP; }
};

RollCallOptimizationResult optimizeRollCall(
    const Eigen::MatrixXd &legislatorCoords,
    int rollCallIndex,
    const Eigen::VectorXd &initialMidpoint,
    const Eigen::VectorXd &initialSpread,
    const VoteMatrix &votes,
    const Eigen::VectorXd &weights,
    const NormalCDF &normalCDF,
    const RollCallOptimizerConfig &config = RollCallOptimizerConfig());

RollCallOptimizationResult optimizeRollCall(
    const Eigen::MatrixXd &legislatorCoords,
    int rollCallIndex,
    const RollCallParameters &initialParams,
    const VoteMatrix &votes,
    const Eigen::VectorXd &weights,
    const NormalCDF &normalCDF,
    const RollCallOptimizerConfig &config = RollCallOptimizerConfig());

#endif
