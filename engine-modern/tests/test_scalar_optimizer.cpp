#include "parameter_optimizer.hpp"

#include <Eigen/Dense>

#include <cmath>
#include <iostream>
#include <vector>

int main()
{
    Eigen::MatrixXd coordinates(6, 1);
    coordinates << -0.9, -0.6, -0.2, 0.2, 0.6, 0.9;

    VoteMatrix votes(6, 2);
    for (int i = 0; i < 6; ++i)
    {
        votes.setVote(static_cast<std::size_t>(i), 0, coordinates(i, 0) > -0.1);
        votes.setVote(static_cast<std::size_t>(i), 1, coordinates(i, 0) > 0.3);
    }

    std::vector<RollCallParameters> rollCalls;
    rollCalls.emplace_back(1);
    rollCalls.emplace_back(1);
    rollCalls[0].midpoint(0) = -0.1;
    rollCalls[0].spread(0) = -0.4;
    rollCalls[1].midpoint(0) = 0.3;
    rollCalls[1].spread(0) = -0.4;

    Eigen::VectorXd weights(2);
    weights << 1.0, 1.0;
    NormalCDF normal;
    const std::vector<bool> valid(2, true);
    LikelihoodContext context(
        coordinates,
        rollCalls,
        votes,
        weights,
        normal,
        valid);

    const double initialBeta = weights(1);
    const auto localConfig = sigmasConfig();
    const auto result = optimizeBeta(context, localConfig);
    if (!std::isfinite(result.logLikelihood))
    {
        std::cerr << "optimized likelihood is not finite\n";
        return 1;
    }
    if (result.value < 0.05 || result.value > 20.0)
    {
        std::cerr << "beta violated its identification bounds\n";
        return 1;
    }
    if (std::abs(result.value - initialBeta) > localConfig.localRadius + 1e-10)
    {
        std::cerr << "local scalar optimizer escaped its Fortran-reach box\n";
        return 1;
    }
    if (result.logLikelihood + 1e-8 < result.initialLL)
    {
        std::cerr << "scalar optimizer reduced the likelihood\n";
        return 1;
    }

    // The global mode remains available for explicit experiments and must
    // preserve the same monotonicity and identification guarantees.
    weights(1) = initialBeta;
    auto globalConfig = sigmasConfig();
    globalConfig.localRadius = 0.0;
    const auto globalResult = optimizeBeta(context, globalConfig);
    if (!std::isfinite(globalResult.logLikelihood) ||
        globalResult.value < globalConfig.lowerBound ||
        globalResult.value > globalConfig.upperBound ||
        globalResult.logLikelihood + 1e-8 < globalResult.initialLL)
    {
        std::cerr << "global scalar mode violated its contract\n";
        return 1;
    }
    return 0;
}
