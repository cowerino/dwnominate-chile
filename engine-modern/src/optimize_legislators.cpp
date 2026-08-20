#include "optimize_legislators.hpp"
#include "feasibility.hpp"

#include <nlopt.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace
{
TimeTrends buildLegendreTimeTrends(int periods)
{
    TimeTrends trends(periods);
    const double increment = periods > 1
                                 ? 2.0 / static_cast<double>(periods - 1)
                                 : 0.0;
    for (int i = 0; i < periods; ++i)
    {
        const double t = -1.0 + static_cast<double>(i) * increment;
        trends.values(i, 0) = 1.0;
        trends.values(i, 1) = t;
        trends.values(i, 2) = (3.0 * t * t - 1.0) / 2.0;
        trends.values(i, 3) = (5.0 * t * t * t - 3.0 * t) / 2.0;
    }
    return trends;
}

TemporalModel effectiveModel(TemporalModel requested, int periods)
{
    if (periods < 5 || requested == TemporalModel::Constant)
    {
        return TemporalModel::Constant;
    }
    if (periods == 5 || requested == TemporalModel::Linear)
    {
        return TemporalModel::Linear;
    }
    if (periods == 6 || requested == TemporalModel::Quadratic)
    {
        return TemporalModel::Quadratic;
    }
    return TemporalModel::Cubic;
}

int numberOfTerms(TemporalModel model)
{
    return static_cast<int>(model) + 1;
}

Eigen::VectorXd projectToInterior(
    const Eigen::VectorXd &value,
    double interiorRadius)
{
    const double norm = value.norm();
    if (norm <= 1.0 || norm == 0.0)
    {
        return value;
    }
    return value * (interiorRadius / norm);
}

void copyParametersToCoefficients(
    const std::vector<double> &parameters,
    int terms,
    int dimensions,
    TemporalCoefficients &coefficients)
{
    coefficients.beta.setZero();
    for (int term = 0; term < terms; ++term)
    {
        for (int k = 0; k < dimensions; ++k)
        {
            const auto index = static_cast<std::size_t>(term * dimensions + k);
            coefficients(term, k) = parameters[index];
        }
    }
}

Eigen::MatrixXd invertInformation(
    const Eigen::MatrixXd &information,
    double threshold)
{
    if (information.rows() == 0)
    {
        return {};
    }

    Eigen::JacobiSVD<Eigen::MatrixXd> decomposition(
        information,
        Eigen::ComputeFullU | Eigen::ComputeFullV);
    if (decomposition.info() != Eigen::Success)
    {
        return Eigen::MatrixXd::Zero(information.rows(), information.cols());
    }

    Eigen::VectorXd inverseValues = decomposition.singularValues();
    for (Eigen::Index i = 0; i < inverseValues.size(); ++i)
    {
        inverseValues(i) = std::abs(inverseValues(i)) > threshold
                               ? 1.0 / inverseValues(i)
                               : 0.0;
    }
    const Eigen::MatrixXd leftVectors = decomposition.matrixU();
    const Eigen::MatrixXd rightVectors = decomposition.matrixV();
    const Eigen::MatrixXd inverseDiagonal = inverseValues.asDiagonal();
    return (rightVectors * inverseDiagonal * leftVectors.transpose()).eval();
}

struct LegislatorObjective
{
    int legislatorIndex;
    const LegislatorPeriodInfo &periodInfo;
    const TimeTrends &timeTrends;
    const Eigen::MatrixXd &rollCallMidpoints;
    const Eigen::MatrixXd &rollCallSpreads;
    const VoteMatrix &votes;
    const std::vector<bool> &validRollCalls;
    const Eigen::VectorXd &weights;
    const NormalCDF &normalCDF;
    TemporalModel model;
    int firstPeriod;
    int lastPeriod;
    int terms;
    int dimensions;
    double constraintTolerance;
    int evaluations = 0;
    int infeasibleEvaluations = 0;
    double maxConstraintViolation = 0.0;

    static double evaluate(
        const std::vector<double> &parameters,
        std::vector<double> &gradient,
        void *opaque)
    {
        auto &self = *static_cast<LegislatorObjective *>(opaque);
        ++self.evaluations;
        TemporalCoefficients coefficients(self.dimensions);
        copyParametersToCoefficients(
            parameters,
            self.terms,
            self.dimensions,
            coefficients);

        double interceptNormSquared = 0.0;
        for (int k = 0; k < self.dimensions; ++k)
        {
            interceptNormSquared +=
                parameters[static_cast<std::size_t>(k)] *
                parameters[static_cast<std::size_t>(k)];
        }
        const double violation =
            std::max(0.0, interceptNormSquared - 1.0);
        self.maxConstraintViolation =
            std::max(self.maxConstraintViolation, violation);
        if (violation > self.constraintTolerance)
        {
            ++self.infeasibleEvaluations;
        }

        const auto result = computeLegislatorDerivatives(
            self.legislatorIndex,
            self.periodInfo,
            self.timeTrends,
            coefficients,
            self.rollCallMidpoints,
            self.rollCallSpreads,
            self.votes,
            self.validRollCalls,
            self.weights,
            self.normalCDF,
            self.model,
            self.firstPeriod,
            self.lastPeriod);

        if (!gradient.empty())
        {
            constexpr double inverseSqrtTwoPi =
                0.39894228040143267793994605993438;
            const double scale =
                -2.0 * self.weights(self.dimensions) * inverseSqrtTwoPi;
            const Eigen::VectorXd historicalDirection =
                result.getDerivativesForModel(self.model);
            for (Eigen::Index i = 0; i < historicalDirection.size(); ++i)
            {
                gradient[static_cast<std::size_t>(i)] =
                    scale * historicalDirection(i);
            }
        }

        return result.logLikelihood;
    }
};

struct InterceptConstraint
{
    int dimensions;

    static double evaluate(
        const std::vector<double> &parameters,
        std::vector<double> &gradient,
        void *opaque)
    {
        const auto &self = *static_cast<InterceptConstraint *>(opaque);
        double normSquared = 0.0;
        for (int k = 0; k < self.dimensions; ++k)
        {
            normSquared += parameters[static_cast<std::size_t>(k)] *
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
        return normSquared - 1.0;
    }
};

void storeDervish(
    LegislatorOptimizationResult &output,
    const LegislatorDerivativesResult &derivatives)
{
    if (derivatives.totalVotes == 0)
    {
        return;
    }
    const double denominator = static_cast<double>(derivatives.totalVotes);
    output.dervish.row(0) = (derivatives.derivatives0 / denominator).transpose();
    output.dervish.row(1) = (derivatives.derivatives1 / denominator).transpose();
    output.dervish.row(2) = (derivatives.derivatives2 / denominator).transpose();
    output.dervish.row(3) = (derivatives.derivatives3 / denominator).transpose();
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
    const LegislatorOptimizerConfig &config)
{
    const auto started = std::chrono::steady_clock::now();
    const int dimensions = static_cast<int>(weights.size()) - 1;
    LegislatorOptimizationResult output(dimensions);

    std::vector<int> servedPeriods;
    for (int period = firstPeriod; period <= lastPeriod; ++period)
    {
        if (periodInfo.servedIn(period))
        {
            servedPeriods.push_back(period);
        }
    }
    if (servedPeriods.empty())
    {
        return output;
    }

    const int periods = static_cast<int>(servedPeriods.size());
    const TemporalModel model = effectiveModel(maxModel, periods);
    const int terms = numberOfTerms(model);
    const TimeTrends trends = buildLegendreTimeTrends(periods);

    TemporalCoefficients initialCoefficients(dimensions);
    for (int k = 0; k < dimensions; ++k)
    {
        Eigen::VectorXd observed(periods);
        for (int i = 0; i < periods; ++i)
        {
            const int dataIndex = periodInfo.dataIndices[servedPeriods[i]];
            observed(i) = legislatorDataCoords(dataIndex, k);
        }

        if (terms == 1)
        {
            initialCoefficients(0, k) = observed(0);
        }
        else
        {
            const Eigen::MatrixXd design = trends.values.leftCols(terms);
            const Eigen::VectorXd estimate =
                design.colPivHouseholderQr().solve(observed);
            for (int term = 0; term < terms; ++term)
            {
                initialCoefficients(term, k) = estimate(term);
            }
        }
    }

    initialCoefficients.beta.row(0) =
        projectToInterior(
            initialCoefficients.beta.row(0).transpose(),
            config.initialInteriorRadius)
            .transpose();

    std::vector<double> parameters(
        static_cast<std::size_t>(terms * dimensions),
        0.0);
    for (int term = 0; term < terms; ++term)
    {
        for (int k = 0; k < dimensions; ++k)
        {
            parameters[static_cast<std::size_t>(term * dimensions + k)] =
                initialCoefficients(term, k);
        }
    }

    LegislatorObjective objective{
        legislatorIndex,
        periodInfo,
        trends,
        rollCallMidpoints,
        rollCallSpreads,
        votes,
        validRollCalls,
        weights,
        normalCDF,
        model,
        firstPeriod,
        lastPeriod,
        terms,
        dimensions,
        config.constraintTolerance};
    InterceptConstraint constraint{dimensions};

    const std::vector<double> initialParameters = parameters;
    std::vector<double> noGradient;
    double optimum =
        LegislatorObjective::evaluate(parameters, noGradient, &objective);
    output.initialLogLikelihood = optimum;

    auto runSolver = [&](BlockOptimizerAlgorithm algorithm,
                         std::vector<double> &candidate,
                         double &candidateOptimum) {
        nlopt::opt optimizer(
            nloptAlgorithm(algorithm),
            static_cast<unsigned int>(candidate.size()));
        optimizer.set_max_objective(&LegislatorObjective::evaluate, &objective);
        optimizer.add_inequality_constraint(
            &InterceptConstraint::evaluate,
            &constraint,
            config.constraintTolerance);
        optimizer.set_maxeval(config.maxEvaluations);
        optimizer.set_xtol_rel(config.relativeXTolerance);
        optimizer.set_ftol_rel(config.relativeFTolerance);

        if (algorithm == BlockOptimizerAlgorithm::Cobyla)
        {
            std::vector<double> initialStep(
                candidate.size(), config.temporalInitialStep);
            for (int k = 0; k < dimensions; ++k)
            {
                initialStep[static_cast<std::size_t>(k)] =
                    config.interceptInitialStep;
            }
            optimizer.set_initial_step(initialStep);
        }

        nlopt::result status = nlopt::FAILURE;
        try
        {
            status = optimizer.optimize(candidate, candidateOptimum);
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

    BlockOptimizerAlgorithm algorithmUsed = config.algorithm;
    nlopt::result status = runSolver(algorithmUsed, parameters, optimum);

    UnitBallFeasibilityAudit returnAudit;
    TemporalCoefficients acceptedCoefficients = initialCoefficients;
    double acceptedLikelihood = output.initialLogLikelihood;

    auto auditSolverReturn = [&](nlopt::result currentStatus) {
        Eigen::VectorXd rawIntercept(dimensions);
        for (int k = 0; k < dimensions; ++k)
        {
            rawIntercept(k) = parameters[static_cast<std::size_t>(k)];
        }
        Eigen::VectorXd sanitizedIntercept(dimensions);
        if (!acceptUnitBallReturn(
                rawIntercept,
                config.constraintTolerance,
                sanitizedIntercept,
                returnAudit))
        {
            return false;
        }
        if (!std::all_of(
                parameters.begin(), parameters.end(),
                [](double value) { return std::isfinite(value); }))
        {
            return false;
        }

        TemporalCoefficients candidateCoefficients(dimensions);
        copyParametersToCoefficients(
            parameters, terms, dimensions, candidateCoefficients);
        candidateCoefficients.beta.row(0) = sanitizedIntercept.transpose();
        acceptedLikelihood = computeLegislatorDerivatives(
                                 legislatorIndex,
                                 periodInfo,
                                 trends,
                                 candidateCoefficients,
                                 rollCallMidpoints,
                                 rollCallSpreads,
                                 votes,
                                 validRollCalls,
                                 weights,
                                 normalCDF,
                                 model,
                                 firstPeriod,
                                 lastPeriod)
                                 .logLikelihood;
        const bool statusAcceptable =
            isSuccessful(currentStatus) ||
            currentStatus == nlopt::ROUNDOFF_LIMITED;
        const bool acceptable =
            statusAcceptable && std::isfinite(acceptedLikelihood) &&
            acceptedLikelihood + config.acceptanceTolerance >=
                output.initialLogLikelihood;
        if (acceptable)
        {
            acceptedCoefficients = candidateCoefficients;
        }
        return acceptable;
    };

    bool candidateAccepted = auditSolverReturn(status);
    if (!candidateAccepted &&
        config.algorithm == BlockOptimizerAlgorithm::Slsqp &&
        config.fallbackToCobyla)
    {
        parameters = initialParameters;
        optimum = output.initialLogLikelihood;
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

    // A materially infeasible or non-monotone return is rejected. The
    // previous feasible coefficients remain authoritative.
    const TemporalCoefficients &coefficients = acceptedCoefficients;

    const auto final = computeLegislatorDerivatives(
        legislatorIndex,
        periodInfo,
        trends,
        coefficients,
        rollCallMidpoints,
        rollCallSpreads,
        votes,
        validRollCalls,
        weights,
        normalCDF,
        model,
        firstPeriod,
        lastPeriod);

    output.coefficients = coefficients;
    output.logLikelihood0 = final.logLikelihood;
    output.logLikelihood1 = final.logLikelihood;
    output.logLikelihood2 = final.logLikelihood;
    output.logLikelihood3 = final.logLikelihood;
    output.totalVotes = final.totalVotes;
    output.periodCoordinates = final.periodCoordinates;
    output.objectiveEvaluations = objective.evaluations;
    output.optimizerStatus = static_cast<int>(status);
    output.algorithmUsed = algorithmUsed;
    output.converged = candidateAccepted;
    output.elapsedMilliseconds = std::chrono::duration<double, std::milli>(
                                     std::chrono::steady_clock::now() - started)
                                     .count();

    output.covariance0 = invertInformation(final.infoMatrix0, config.eigenThreshold);
    if (model >= TemporalModel::Linear)
    {
        output.covariance1 = invertInformation(final.infoMatrix1, config.eigenThreshold);
    }
    if (model >= TemporalModel::Quadratic)
    {
        output.covariance2 = invertInformation(final.infoMatrix2, config.eigenThreshold);
    }
    if (model >= TemporalModel::Cubic)
    {
        output.covariance3 = invertInformation(final.infoMatrix3, config.eigenThreshold);
    }
    storeDervish(output, final);
    return output;
}
