#include "optimize_legislators.hpp"
#include "rollcall_optimizer.hpp"

#include <Eigen/Dense>

#include <cmath>
#include <iostream>
#include <vector>

namespace
{
int fail(const char *message)
{
    std::cerr << message << '\n';
    return 1;
}
} // namespace

int main()
{
    NormalCDF normal;

    Eigen::MatrixXd coordinates(8, 2);
    coordinates << -0.90, -0.10,
        -0.70, 0.20,
        -0.40, -0.35,
        -0.10, 0.45,
        0.15, -0.30,
        0.45, 0.35,
        0.70, -0.15,
        0.90, 0.10;

    VoteMatrix rollCallVotes(8, 1);
    for (int i = 0; i < 8; ++i)
    {
        rollCallVotes.setVote(
            static_cast<std::size_t>(i),
            0,
            coordinates(i, 0) > 0.0);
    }

    Eigen::VectorXd weights(3);
    weights << 1.0, 0.5, 4.925;
    Eigen::VectorXd initialMidpoint(2);
    initialMidpoint << 2.0, -1.5;
    Eigen::VectorXd initialSpread(2);
    initialSpread << -0.50, 0.05;

    RollCallOptimizerConfig rollCallConfig;
    rollCallConfig.maxEvaluations = 250;
    rollCallConfig.algorithm = BlockOptimizerAlgorithm::Slsqp;
    rollCallConfig.fallbackToCobyla = false;
    const auto rollCall = optimizeRollCall(
        coordinates,
        0,
        initialMidpoint,
        initialSpread,
        rollCallVotes,
        weights,
        normal,
        rollCallConfig);

    if (!std::isfinite(rollCall.logLikelihood))
    {
        return fail("roll-call likelihood is not finite");
    }
    if (rollCall.midpoint.norm() > 1.0 + 1e-9)
    {
        return fail("roll-call midpoint escaped the unit ball");
    }
    if (!rollCall.accepted || !rollCall.rawReturnFeasible ||
        rollCall.rawConstraintViolation > rollCallConfig.constraintTolerance)
    {
        return fail("roll-call solver return violated the strict feasibility contract");
    }

    // Static, one-period legislator problem. The initial point is deliberately
    // infeasible; only the constant term may be active with one period.
    Eigen::MatrixXd initialLegislator(1, 2);
    initialLegislator << 1.8, 1.5;
    Eigen::MatrixXd midpoints(4, 2);
    midpoints << -0.55, 0.00,
        -0.15, 0.10,
        0.20, -0.10,
        0.60, 0.00;
    Eigen::MatrixXd spreads(4, 2);
    spreads << -0.40, 0.05,
        -0.35, 0.08,
        -0.40, -0.05,
        -0.45, 0.02;

    VoteMatrix legislatorVotes(1, 4);
    legislatorVotes.setVote(0, 0, false);
    legislatorVotes.setVote(0, 1, false);
    legislatorVotes.setVote(0, 2, true);
    legislatorVotes.setVote(0, 3, true);

    LegislatorPeriodInfo periodInfo(1);
    periodInfo.markServed(0, 0, 4);
    const std::vector<bool> valid(4, true);

    LegislatorOptimizerConfig legislatorConfig;
    legislatorConfig.maxEvaluations = 300;
    legislatorConfig.algorithm = BlockOptimizerAlgorithm::Slsqp;
    legislatorConfig.fallbackToCobyla = false;
    const auto legislator = optimizeLegislator(
        0,
        periodInfo,
        initialLegislator,
        midpoints,
        spreads,
        legislatorVotes,
        valid,
        weights,
        normal,
        TemporalModel::Cubic,
        0,
        0,
        legislatorConfig);

    const Eigen::VectorXd intercept =
        legislator.coefficients.beta.row(0).transpose();
    if (intercept.norm() > 1.0 + 1e-9)
    {
        return fail("one-period legislator escaped the unit ball");
    }
    if (legislator.coefficients.beta.bottomRows(3).norm() > 1e-12)
    {
        return fail("temporal coefficients were activated for one period");
    }
    if (legislator.totalVotes != 4)
    {
        return fail("unexpected legislator vote count");
    }
    if (!legislator.accepted || !legislator.rawReturnFeasible ||
        legislator.rawConstraintViolation >
            legislatorConfig.constraintTolerance)
    {
        return fail("legislator solver return violated the strict feasibility contract");
    }

    return 0;
}
