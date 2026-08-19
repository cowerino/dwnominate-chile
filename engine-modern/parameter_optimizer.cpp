#include "parameter_optimizer.hpp"

#include <nlopt.hpp>

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace
{
struct ScalarObjective
{
    LikelihoodContext &context;
    int parameterIndex;
    int evaluations = 0;

    static double evaluate(
        const std::vector<double> &x,
        std::vector<double> &gradient,
        void *opaque)
    {
        if (!gradient.empty())
        {
            std::fill(gradient.begin(), gradient.end(), 0.0);
        }

        auto &self = *static_cast<ScalarObjective *>(opaque);
        ++self.evaluations;
        self.context.weights(self.parameterIndex) = x.front();

        return computeLogLikelihoodParallel(
                   self.context.legislatorCoords,
                   self.context.rollCallParams,
                   self.context.votes,
                   self.context.weights,
                   self.context.normalCDF,
                   self.context.validRollCalls)
            .logLikelihood;
    }
};
} // namespace

ParameterOptimizationResult optimizeParameter(
    LikelihoodContext &context,
    int paramIndex,
    const ScalarOptimizerConfig &config)
{
    if (paramIndex < 0 || paramIndex >= context.weights.size())
    {
        throw std::out_of_range("global parameter index is out of range");
    }
    if (!(config.lowerBound < config.upperBound))
    {
        throw std::invalid_argument("invalid scalar optimizer bounds");
    }

    ParameterOptimizationResult output;
    output.initialValue = context.weights(paramIndex);
    output.initialValue = std::clamp(
        output.initialValue,
        config.lowerBound,
        config.upperBound);
    context.weights(paramIndex) = output.initialValue;

    output.initialLL = computeLogLikelihoodParallel(
                           context.legislatorCoords,
                           context.rollCallParams,
                           context.votes,
                           context.weights,
                           context.normalCDF,
                           context.validRollCalls)
                           .logLikelihood;

    ScalarObjective objective{context, paramIndex};
    nlopt::opt optimizer(nlopt::LN_BOBYQA, 1U);
    optimizer.set_max_objective(&ScalarObjective::evaluate, &objective);
    optimizer.set_lower_bounds(std::vector<double>{config.lowerBound});
    optimizer.set_upper_bounds(std::vector<double>{config.upperBound});
    optimizer.set_initial_step(std::vector<double>{config.initialStep});
    optimizer.set_xtol_rel(config.relativeXTolerance);
    optimizer.set_ftol_rel(config.relativeFTolerance);
    optimizer.set_maxeval(config.maxEvaluations);

    std::vector<double> x{output.initialValue};
    double optimum = output.initialLL;
    nlopt::result status = nlopt::FAILURE;
    try
    {
        status = optimizer.optimize(x, optimum);
    }
    catch (const nlopt::roundoff_limited &)
    {
        status = nlopt::ROUNDOFF_LIMITED;
    }
    catch (const nlopt::forced_stop &)
    {
        status = nlopt::FORCED_STOP;
    }

    output.value = std::clamp(x.front(), config.lowerBound, config.upperBound);
    context.weights(paramIndex) = output.value;
    output.logLikelihood = computeLogLikelihoodParallel(
                               context.legislatorCoords,
                               context.rollCallParams,
                               context.votes,
                               context.weights,
                               context.normalCDF,
                               context.validRollCalls)
                               .logLikelihood;
    output.iterations = objective.evaluations;
    output.optimizerStatus = static_cast<int>(status);
    output.converged = static_cast<int>(status) > 0 ||
                       status == nlopt::ROUNDOFF_LIMITED;
    output.direction = (output.value > output.initialValue) -
                       (output.value < output.initialValue);
    return output;
}

BetaOptimizationResult optimizeBeta(
    LikelihoodContext &context,
    const BetaOptimizerConfig &config)
{
    const int betaIndex = static_cast<int>(context.weights.size()) - 1;
    return optimizeParameter(context, betaIndex, config);
}

WeightOptimizationResult optimizeWeight2(
    LikelihoodContext &context,
    const WeightOptimizerConfig &config)
{
    const int dimensions = static_cast<int>(context.weights.size()) - 1;
    if (dimensions < 2)
    {
        throw std::invalid_argument("weight 2 requires at least two dimensions");
    }
    return optimizeParameter(context, 1, config);
}
