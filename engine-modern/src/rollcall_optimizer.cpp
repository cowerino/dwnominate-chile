#include "rollcall_optimizer.hpp"
#include "feasibility.hpp"

#include <nlopt.hpp>

#include <algorithm>
#include <chrono>
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
    const std::vector<int> &observedLegislators;
    double constraintTolerance;
    RollCallDerivativesWorkBuffer workBuffer;
    int evaluations = 0;
    int infeasibleEvaluations = 0;
    double maxConstraintViolation = 0.0;

    RollCallObjective(
        const Eigen::MatrixXd &coords,
        int index,
        const VoteMatrix &voteMatrix,
        const Eigen::VectorXd &modelWeights,
        const NormalCDF &cdf,
        int modelDimensions,
        const std::vector<int> &observed,
        double feasibilityTolerance)
        : legislatorCoords(coords),
          rollCallIndex(index),
          votes(voteMatrix),
          weights(modelWeights),
          normalCDF(cdf),
          dimensions(modelDimensions),
          observedLegislators(observed),
          constraintTolerance(feasibilityTolerance)
    {
    }

    static double evaluate(
        const std::vector<double> &parameters,
        std::vector<double> &gradient,
        void *opaque)
    {
        auto &self = *static_cast<RollCallObjective *>(opaque);
        ++self.evaluations;

        Eigen::Map<const Eigen::VectorXd> midpoint(
            parameters.data(), self.dimensions);
        Eigen::Map<const Eigen::VectorXd> spread(
            parameters.data() + self.dimensions, self.dimensions);

        const double violation =
            std::max(0.0, midpoint.squaredNorm() - 1.0);
        self.maxConstraintViolation =
            std::max(self.maxConstraintViolation, violation);
        if (violation > self.constraintTolerance)
        {
            ++self.infeasibleEvaluations;
        }

        const auto result = computeRollCallDerivativesOptimized(
            self.legislatorCoords,
            self.rollCallIndex,
            midpoint,
            spread,
            self.votes,
            self.weights,
            self.normalCDF,
            self.workBuffer,
            self.observedLegislators);

        if (!gradient.empty())
        {
            // The historical PROLLC2 arrays are a negatively oriented,
            // unnormalised search direction. For the declared probit
            // log-likelihood, the exact analytic conversion is
            //   grad(L) = -2*beta/sqrt(2*pi) * PROLLC2_direction.
            // The table interpolation introduces only its documented 1e-4
            // approximation in z; test_optimizer_gradients checks this
            // conversion independently with central differences.
            constexpr double inverseSqrtTwoPi =
                0.39894228040143267793994605993438;
            const double scale =
                -2.0 * self.weights(self.dimensions) * inverseSqrtTwoPi;
            for (int k = 0; k < self.dimensions; ++k)
            {
                gradient[static_cast<std::size_t>(k)] =
                    scale * result.midpointDerivatives(k);
                gradient[static_cast<std::size_t>(self.dimensions + k)] =
                    scale * result.spreadDerivatives(k);
            }
        }

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

nlopt::algorithm nloptAlgorithm(BlockOptimizerAlgorithm algorithm)
{
    return algorithm == BlockOptimizerAlgorithm::Slsqp
               ? nlopt::LD_SLSQP
               : nlopt::LN_COBYLA;
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
    const auto started = std::chrono::steady_clock::now();
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
    output.initialLogLikelihood = initial.logLikelihood;
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

    std::vector<int> observedLegislators;
    observedLegislators.reserve(
        static_cast<std::size_t>(legislatorCoords.rows()));
    for (int i = 0; i < legislatorCoords.rows(); ++i)
    {
        if (!votes.isMissingUnsafe(i, rollCallIndex))
        {
            observedLegislators.push_back(i);
        }
    }

    RollCallObjective objective(
        legislatorCoords,
        rollCallIndex,
        votes,
        weights,
        normalCDF,
        dimensions,
        observedLegislators,
        config.constraintTolerance);
    UnitBallConstraint constraint{dimensions};

    const std::vector<double> initialParameters = parameters;
    auto runSolver = [&](BlockOptimizerAlgorithm algorithm,
                         std::vector<double> &candidate,
                         double &optimum) {
        nlopt::opt optimizer(
            nloptAlgorithm(algorithm),
            static_cast<unsigned int>(candidate.size()));
        optimizer.set_max_objective(&RollCallObjective::evaluate, &objective);
        optimizer.add_inequality_constraint(
            &UnitBallConstraint::evaluate,
            &constraint,
            config.constraintTolerance);
        optimizer.set_maxeval(config.maxEvaluations);
        optimizer.set_xtol_rel(config.relativeXTolerance);
        optimizer.set_ftol_rel(config.relativeFTolerance);

        if (algorithm == BlockOptimizerAlgorithm::Cobyla)
        {
            std::vector<double> initialStep(
                candidate.size(), config.spreadInitialStep);
            for (int k = 0; k < dimensions; ++k)
            {
                initialStep[static_cast<std::size_t>(k)] =
                    config.midpointInitialStep;
            }
            optimizer.set_initial_step(initialStep);
        }

        nlopt::result status = nlopt::FAILURE;
        try
        {
            status = optimizer.optimize(candidate, optimum);
        }
        catch (const nlopt::roundoff_limited &)
        {
            status = nlopt::ROUNDOFF_LIMITED;
        }
        catch (const nlopt::forced_stop &)
        {
            status = nlopt::FORCED_STOP;
        }
        catch (const std::exception &)
        {
            status = nlopt::FAILURE;
        }
        return status;
    };

    double optimum = initial.logLikelihood;
    BlockOptimizerAlgorithm algorithmUsed = config.algorithm;
    nlopt::result status = runSolver(algorithmUsed, parameters, optimum);

    UnitBallFeasibilityAudit returnAudit;
    Eigen::VectorXd acceptedMidpoint = output.midpoint;
    Eigen::VectorXd acceptedSpread = output.spread;
    double acceptedLikelihood = initial.logLikelihood;

    auto auditSolverReturn = [&](nlopt::result currentStatus) {
        Eigen::Map<const Eigen::VectorXd> rawMidpoint(
            parameters.data(), dimensions);
        Eigen::Map<const Eigen::VectorXd> rawSpread(
            parameters.data() + dimensions, dimensions);
        Eigen::VectorXd sanitizedMidpoint(dimensions);
        const bool feasible = acceptUnitBallReturn(
            rawMidpoint,
            config.constraintTolerance,
            sanitizedMidpoint,
            returnAudit);
        if (!feasible || !rawSpread.allFinite())
        {
            return false;
        }

        const auto evaluated = computeRollCallDerivativesOptimized(
            legislatorCoords,
            rollCallIndex,
            sanitizedMidpoint,
            rawSpread,
            votes,
            weights,
            normalCDF,
            objective.workBuffer,
            observedLegislators);
        acceptedMidpoint = sanitizedMidpoint;
        acceptedSpread = rawSpread;
        acceptedLikelihood = evaluated.logLikelihood;
        const bool statusAcceptable =
            isSuccessful(currentStatus) ||
            currentStatus == nlopt::ROUNDOFF_LIMITED;
        return statusAcceptable && std::isfinite(acceptedLikelihood) &&
               acceptedLikelihood + config.acceptanceTolerance >=
                   initial.logLikelihood;
    };

    bool candidateAccepted = auditSolverReturn(status);
    if (!candidateAccepted &&
        config.algorithm == BlockOptimizerAlgorithm::Slsqp &&
        config.fallbackToCobyla)
    {
        parameters = initialParameters;
        optimum = initial.logLikelihood;
        status = runSolver(
            BlockOptimizerAlgorithm::Cobyla, parameters, optimum);
        algorithmUsed = BlockOptimizerAlgorithm::Cobyla;
        output.fallbackUsed = true;
        candidateAccepted = auditSolverReturn(status);
    }

    output.accepted = candidateAccepted;
    output.rawReturnFeasible = returnAudit.feasibleWithinTolerance;
    output.numericalCorrectionApplied = returnAudit.correctionApplied;
    output.rawFinalRadius = returnAudit.rawRadius;
    output.rawConstraintViolation = returnAudit.constraintViolation;
    output.feasibilityCorrectionNorm = returnAudit.correctionNorm;
    output.infeasibleObjectiveEvaluations = objective.infeasibleEvaluations;
    output.maxObjectiveConstraintViolation = objective.maxConstraintViolation;

    if (candidateAccepted)
    {
        output.midpoint = acceptedMidpoint;
        output.spread = acceptedSpread;
    }
    // A materially infeasible or non-monotone return is rejected. There is no
    // projection rescue: output retains the feasible pre-solve state.

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
    output.algorithmUsed = algorithmUsed;
    output.converged = candidateAccepted;
    output.elapsedMilliseconds = std::chrono::duration<double, std::milli>(
                                     std::chrono::steady_clock::now() - started)
                                     .count();

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
