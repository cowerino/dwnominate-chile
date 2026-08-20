#ifndef OPTIMIZE_LEGISLATORS_HPP
#define OPTIMIZE_LEGISLATORS_HPP

#include "legislator_derivatives.hpp"
#include "normal_cdf.hpp"
#include "optimizer_options.hpp"

#include <Eigen/Dense>
#include <vector>

struct LegislatorOptimizerConfig
{
    int maxEvaluations = 600;
    double relativeXTolerance = 1e-8;
    double relativeFTolerance = 1e-10;
    double constraintTolerance = 1e-10;
    double interceptInitialStep = 0.05;
    double temporalInitialStep = 0.02;
    double initialInteriorRadius = 0.75;
    double eigenThreshold = 1e-8;
    BlockOptimizerAlgorithm algorithm = BlockOptimizerAlgorithm::Cobyla;
    bool fallbackToCobyla = true;
};

struct LegislatorOptimizationResult
{
    TemporalCoefficients coefficients;

    double logLikelihood0 = 0.0;
    double logLikelihood1 = 0.0;
    double logLikelihood2 = 0.0;
    double logLikelihood3 = 0.0;
    int totalVotes = 0;

    Eigen::MatrixXd covariance0;
    Eigen::MatrixXd covariance1;
    Eigen::MatrixXd covariance2;
    Eigen::MatrixXd covariance3;
    Eigen::MatrixXd dervish;
    Eigen::MatrixXd periodCoordinates;

    int objectiveEvaluations = 0;
    int optimizerStatus = 0;
    bool converged = false;
    double initialLogLikelihood = 0.0;
    BlockOptimizerAlgorithm algorithmUsed = BlockOptimizerAlgorithm::Cobyla;
    bool fallbackUsed = false;
    double elapsedMilliseconds = 0.0;

    explicit LegislatorOptimizationResult(int dimensions)
        : coefficients(dimensions),
          covariance0(Eigen::MatrixXd::Zero(dimensions, dimensions)),
          covariance1(Eigen::MatrixXd::Zero(2 * dimensions, 2 * dimensions)),
          covariance2(Eigen::MatrixXd::Zero(3 * dimensions, 3 * dimensions)),
          covariance3(Eigen::MatrixXd::Zero(4 * dimensions, 4 * dimensions)),
          dervish(Eigen::MatrixXd::Zero(4, dimensions))
    {
    }
};

LegislatorOptimizationResult optimizeLegislator(
    int legislatorIndex,
    const LegislatorPeriodInfo &periodInfo,
    const Eigen::MatrixXd &legislatorDataCoords,
    const Eigen::MatrixXd &rollCallMidpoints,
    const Eigen::MatrixXd &rollCallSpreads,
    const VoteMatrix &votes,
    const std::vector<bool> &validRollCalls,
    const Eigen::VectorXd &weights,
    const NormalCDF &normalCDF,
    TemporalModel maxModel,
    int firstPeriod,
    int lastPeriod,
    const LegislatorOptimizerConfig &config = LegislatorOptimizerConfig());

#endif
