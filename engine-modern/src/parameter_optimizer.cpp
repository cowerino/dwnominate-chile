#include "parameter_optimizer.hpp"
#include "feasibility.hpp"

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
    if ((!std::isfinite(config.lowerBound) ||
         !std::isfinite(config.upperBound)) &&
        !(config.localRadius > 0.0 && std::isfinite(config.localRadius)))
    {
        throw std::invalid_argument(
            "unbounded scalar search requires a finite local radius");
    }

    ParameterOptimizationResult output;
    output.initialValue = context.weights(paramIndex);
    output.initialValue = std::clamp(
        output.initialValue,
        config.lowerBound,
        config.upperBound);
    context.weights(paramIndex) = output.initialValue;

    double effectiveLower = config.lowerBound;
    double effectiveUpper = config.upperBound;
    if (config.localRadius > 0.0)
    {
        effectiveLower = std::max(
            effectiveLower, output.initialValue - config.localRadius);
        effectiveUpper = std::min(
            effectiveUpper, output.initialValue + config.localRadius);
    }
    if (!std::isfinite(effectiveLower) ||
        !std::isfinite(effectiveUpper) ||
        !(effectiveLower < effectiveUpper))
    {
        throw std::invalid_argument("NLopt scalar box must be finite");
    }

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
    optimizer.set_lower_bounds(std::vector<double>{effectiveLower});
    optimizer.set_upper_bounds(std::vector<double>{effectiveUpper});
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

    BoundFeasibilityAudit feasibility;
    double acceptedValue = output.initialValue;
    output.rawReturnFeasible = acceptBoundReturn(
        x.front(),
        effectiveLower,
        effectiveUpper,
        config.feasibilityTolerance,
        acceptedValue,
        feasibility);
    output.rawConstraintViolation = feasibility.constraintViolation;
    output.feasibilityCorrection = feasibility.correction;
    output.numericalCorrectionApplied = feasibility.correctionApplied;

    context.weights(paramIndex) = acceptedValue;
    output.logLikelihood = output.rawReturnFeasible
                               ? computeLogLikelihoodParallel(
                                     context.legislatorCoords,
                                     context.rollCallParams,
                                     context.votes,
                                     context.weights,
                                     context.normalCDF,
                                     context.validRollCalls)
                                     .logLikelihood
                               : output.initialLL;
    // A failed or roundoff-limited local solve must never make the outer
    // alternating trajectory worse. Keep the pre-solve state as the accepted
    // point unless NLopt returns a finite non-decreasing objective.
    const bool acceptableStatus = static_cast<int>(status) > 0 ||
                                  status == nlopt::ROUNDOFF_LIMITED;
    const bool objectiveDidNotDecrease =
        std::isfinite(output.logLikelihood) &&
        output.logLikelihood + config.acceptanceTolerance >= output.initialLL;
    const bool objectiveIsFlat =
        std::isfinite(output.logLikelihood) &&
        std::abs(output.logLikelihood - output.initialLL) <=
            config.acceptanceTolerance;
    output.accepted = output.rawReturnFeasible && acceptableStatus &&
                      objectiveDidNotDecrease;
    if (!output.accepted)
    {
        output.value = output.initialValue;
        context.weights(paramIndex) = output.initialValue;
        output.logLikelihood = output.initialLL;
    }
    else
    {
        // BOBYQA is free to return any point in a constant box. The canonical
        // first WINT/SIGMAS calls see precisely such a box because bill
        // midpoint and spread are both zero. A numerically flat solve must not
        // create an arbitrary trajectory or change the identification gauge.
        output.value = objectiveIsFlat ? output.initialValue : acceptedValue;
        context.weights(paramIndex) = output.value;
        if (objectiveIsFlat)
            output.logLikelihood = output.initialLL;
    }
    output.iterations = objective.evaluations;
    output.optimizerStatus = static_cast<int>(status);
    output.converged = output.accepted;
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
