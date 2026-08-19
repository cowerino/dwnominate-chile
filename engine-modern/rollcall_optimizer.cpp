#include "rollcall_optimizer.hpp"

#include <nlopt.hpp>

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace
{
struct RollCallObjective
{
    const Eigen::MatrixXd &legislatorCoords;
    int rollCallIndex;
    const VoteMatrix &votes;
    const Eigen::VectorXd &weights;
    const NormalCDF &normalCDF;
    int dimensions;
    int evaluations = 0;

    static double evaluate(
        const std::vector<double> &parameters,
        std::vector<double> &gradient,
        void *opaque)
    {
        // COBYLA is derivative-free. An accidental gradient request is made
        // explicit rather than silently supplying an inconsistent derivative.
        if (!gradient.empty())
        {
            std::fill(gradient.begin(), gradient.end(), 0.0);
        }

        auto &self = *static_cast<RollCallObjective *>(opaque);
        ++self.evaluations;

        Eigen::Map<const Eigen::VectorXd> midpoint(
            parameters.data(), self.dimensions);
        Eigen::Map<const Eigen::VectorXd> spread(
            parameters.data() + self.dimensions, self.dimensions);

        const auto result = computeRollCallDerivatives(
            self.legislatorCoords,
            self.rollCallIndex,
            midpoint,
            spread,
            self.votes,
            self.weights,
            self.normalCDF);

        return result.logLikelihood;
    }
};

struct UnitBallConstraint
{
    int dimensions;

    static double evaluate(
        const std::vector<double> &parameters,
        std::vector<double> &gradient,
        void *opaque)
    {
        const auto &self = *static_cast<UnitBallConstraint *>(opaque);
        double squaredNorm = 0.0;
        for (int k = 0; k < self.dimensions; ++k)
        {
            squaredNorm += parameters[static_cast<std::size_t>(k)] *
                           parameters[static_cast<std::size_t>(k)];
        }

        if (!gradient.empty())
        {
            std::fill(gradient.begin(), gradient.end(), 0.0);
            for (int k = 0; k < self.dimensions; ++k)
            {
                gradient[static_cast<std::size_t>(k)] =
                    2.0 * parameters[static_cast<std::size_t>(k)];
            }
        }
        return squaredNorm - 1.0;
    }
};

Eigen::VectorXd projectToUnitBall(const Eigen::VectorXd &value)
{
    const double norm = value.norm();
    if (norm <= 1.0 || norm == 0.0)
    {
        return value;
    }
    return value / norm;
}

bool isSuccessful(nlopt::result status)
{
    return static_cast<int>(status) > 0;
}
} // namespace

RollCallOptimizationResult optimizeRollCall(
    const Eigen::MatrixXd &legislatorCoords,
    int rollCallIndex,
    const Eigen::VectorXd &initialMidpoint,
    const Eigen::VectorXd &initialSpread,
    const VoteMatrix &votes,
    const Eigen::VectorXd &weights,
    const NormalCDF &normalCDF,
    const RollCallOptimizerConfig &config)
{
    const int dimensions = static_cast<int>(initialMidpoint.size());
    if (dimensions <= 0 || initialSpread.size() != dimensions)
    {
        throw std::invalid_argument("invalid roll-call parameter dimensions");
    }
    if (legislatorCoords.cols() != dimensions || weights.size() != dimensions + 1)
    {
        throw std::invalid_argument("roll-call data dimensions do not agree");
    }

    RollCallOptimizationResult output(dimensions);
    output.midpoint = projectToUnitBall(initialMidpoint);
    output.spread = initialSpread;

    const auto initial = computeRollCallDerivatives(
        legislatorCoords,
        rollCallIndex,
        output.midpoint,
        output.spread,
        votes,
        weights,
        normalCDF);
    output.initialGMP = initial.geometricMeanProb;
    output.totalVotes = initial.totalVotes;

    if (initial.totalVotes == 0)
    {
        return output;
    }

    std::vector<double> parameters(static_cast<std::size_t>(2 * dimensions));
    for (int k = 0; k < dimensions; ++k)
    {
        parameters[static_cast<std::size_t>(k)] = output.midpoint(k);
        parameters[static_cast<std::size_t>(dimensions + k)] = output.spread(k);
    }

    RollCallObjective objective{
        legislatorCoords,
        rollCallIndex,
        votes,
        weights,
        normalCDF,
        dimensions};
    UnitBallConstraint constraint{dimensions};

    nlopt::opt optimizer(
        nlopt::LN_COBYLA,
        static_cast<unsigned int>(parameters.size()));
    optimizer.set_max_objective(&RollCallObjective::evaluate, &objective);
    optimizer.add_inequality_constraint(
        &UnitBallConstraint::evaluate,
        &constraint,
        config.constraintTolerance);
    optimizer.set_maxeval(config.maxEvaluations);
    optimizer.set_xtol_rel(config.relativeXTolerance);
    optimizer.set_ftol_rel(config.relativeFTolerance);

    std::vector<double> initialStep(parameters.size(), config.spreadInitialStep);
    for (int k = 0; k < dimensions; ++k)
    {
        initialStep[static_cast<std::size_t>(k)] = config.midpointInitialStep;
    }
    optimizer.set_initial_step(initialStep);

    double optimum = initial.logLikelihood;
    nlopt::result status = nlopt::FAILURE;
    try
    {
        status = optimizer.optimize(parameters, optimum);
    }
    catch (const nlopt::roundoff_limited &)
    {
        status = nlopt::ROUNDOFF_LIMITED;
    }
    catch (const nlopt::forced_stop &)
    {
        status = nlopt::FORCED_STOP;
    }

    for (int k = 0; k < dimensions; ++k)
    {
        output.midpoint(k) = parameters[static_cast<std::size_t>(k)];
        output.spread(k) = parameters[static_cast<std::size_t>(dimensions + k)];
    }

    // Defend against a solver feasibility tolerance or accumulated roundoff.
    // This is not an optimizer step: it enforces the model's declared domain.
    output.midpoint = projectToUnitBall(output.midpoint);

    const auto final = computeRollCallDerivatives(
        legislatorCoords,
        rollCallIndex,
        output.midpoint,
        output.spread,
        votes,
        weights,
        normalCDF);

    output.logLikelihood = final.logLikelihood;
    output.geometricMeanProb = final.geometricMeanProb;
    output.correctClassified = final.correctClassified;
    output.totalVotes = final.totalVotes;
    output.totalIterations = objective.evaluations;
    output.spreadIterations = objective.evaluations;
    output.midpointIterations = objective.evaluations;
    output.optimizerStatus = static_cast<int>(status);
    output.converged = isSuccessful(status) || status == nlopt::ROUNDOFF_LIMITED;

    return output;
}

RollCallOptimizationResult optimizeRollCall(
    const Eigen::MatrixXd &legislatorCoords,
    int rollCallIndex,
    const RollCallParameters &initialParams,
    const VoteMatrix &votes,
    const Eigen::VectorXd &weights,
    const NormalCDF &normalCDF,
    const RollCallOptimizerConfig &config)
{
    return optimizeRollCall(
        legislatorCoords,
        rollCallIndex,
        initialParams.midpoint,
        initialParams.spread,
        votes,
        weights,
        normalCDF,
        config);
}
