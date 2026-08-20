#include "feasibility.hpp"

#include <Eigen/Dense>

#include <cmath>
#include <iostream>

namespace
{
int fail(const char *message)
{
    std::cerr << message << '\n';
    return 1;
}
}

int main()
{
    constexpr double tolerance = 1e-10;
    Eigen::VectorXd accepted(2);
    UnitBallFeasibilityAudit audit;

    Eigen::Vector2d feasible(0.6, 0.8);
    if (!acceptUnitBallReturn(feasible, tolerance, accepted, audit) ||
        audit.correctionApplied || (accepted - feasible).norm() != 0.0)
    {
        return fail("a feasible point was altered or rejected");
    }

    Eigen::Vector2d numericalResidual(1.0 + 2e-11, 0.0);
    if (!acceptUnitBallReturn(
            numericalResidual, tolerance, accepted, audit) ||
        !audit.correctionApplied || std::abs(accepted.norm() - 1.0) > 1e-15)
    {
        return fail("an in-tolerance residual was not snapped to the boundary");
    }

    Eigen::Vector2d infeasible(1.001, 0.0);
    accepted = Eigen::Vector2d(0.25, 0.25);
    const Eigen::VectorXd before = accepted;
    if (acceptUnitBallReturn(infeasible, tolerance, accepted, audit) ||
        audit.feasibleWithinTolerance || (accepted - before).norm() != 0.0)
    {
        return fail("a materially infeasible solver return was rescued");
    }

    double bounded = 0.0;
    BoundFeasibilityAudit boundAudit;
    if (!acceptBoundReturn(
            2.0 + 5e-13, 0.01, 2.0, 1e-12, bounded, boundAudit) ||
        bounded != 2.0 || !boundAudit.correctionApplied)
    {
        return fail("an in-tolerance bound residual was not corrected");
    }
    if (acceptBoundReturn(
            2.001, 0.01, 2.0, 1e-12, bounded, boundAudit))
    {
        return fail("a materially out-of-bounds scalar return was accepted");
    }
    return 0;
}
