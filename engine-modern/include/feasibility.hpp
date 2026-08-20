#ifndef FEASIBILITY_HPP
#define FEASIBILITY_HPP

#include <Eigen/Dense>

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

/**
 * Diagnostics for a solver return subject to ||x||^2 <= 1.
 *
 * `constraintViolation` uses the exact constraint supplied to NLopt:
 * max(0, ||x||^2 - 1). A point is eligible for a numerical boundary snap only
 * when that violation is already no greater than the declared tolerance.
 */
struct UnitBallFeasibilityAudit
{
    double rawRadius = 0.0;
    double constraintViolation = 0.0;
    double correctionNorm = 0.0;
    bool finite = true;
    bool feasibleWithinTolerance = true;
    bool correctionApplied = false;
};

inline UnitBallFeasibilityAudit auditUnitBall(
    const Eigen::VectorXd &raw,
    double constraintTolerance)
{
    if (constraintTolerance < 0.0 || !std::isfinite(constraintTolerance))
    {
        throw std::invalid_argument("invalid unit-ball feasibility tolerance");
    }

    UnitBallFeasibilityAudit audit;
    audit.finite = raw.allFinite();
    if (!audit.finite)
    {
        audit.rawRadius = std::numeric_limits<double>::infinity();
        audit.constraintViolation = std::numeric_limits<double>::infinity();
        audit.feasibleWithinTolerance = false;
        return audit;
    }

    audit.rawRadius = raw.norm();
    audit.constraintViolation = std::max(0.0, raw.squaredNorm() - 1.0);
    audit.feasibleWithinTolerance =
        audit.constraintViolation <= constraintTolerance;
    return audit;
}

/**
 * Enforce the strict solver-return contract.
 *
 * Returns false and leaves `accepted` unchanged when the raw solver result is
 * outside tolerance. Otherwise it copies the raw point and removes only a
 * numerical residual above radius one.
 */
inline bool acceptUnitBallReturn(
    const Eigen::VectorXd &raw,
    double constraintTolerance,
    Eigen::VectorXd &accepted,
    UnitBallFeasibilityAudit &audit)
{
    audit = auditUnitBall(raw, constraintTolerance);
    if (!audit.feasibleWithinTolerance)
    {
        return false;
    }

    accepted = raw;
    if (audit.rawRadius > 1.0)
    {
        accepted /= audit.rawRadius;
        audit.correctionNorm = (raw - accepted).norm();
        audit.correctionApplied = true;
    }
    return true;
}

struct BoundFeasibilityAudit
{
    double rawValue = 0.0;
    double constraintViolation = 0.0;
    double correction = 0.0;
    bool finite = true;
    bool feasibleWithinTolerance = true;
    bool correctionApplied = false;
};

inline BoundFeasibilityAudit auditBounds(
    double raw,
    double lower,
    double upper,
    double tolerance)
{
    if (!(lower < upper) || tolerance < 0.0 ||
        !std::isfinite(tolerance))
    {
        throw std::invalid_argument("invalid bound feasibility contract");
    }

    BoundFeasibilityAudit audit;
    audit.rawValue = raw;
    audit.finite = std::isfinite(raw);
    if (!audit.finite)
    {
        audit.constraintViolation = std::numeric_limits<double>::infinity();
        audit.feasibleWithinTolerance = false;
        return audit;
    }
    audit.constraintViolation =
        std::max({0.0, lower - raw, raw - upper});
    audit.feasibleWithinTolerance = audit.constraintViolation <= tolerance;
    return audit;
}

inline bool acceptBoundReturn(
    double raw,
    double lower,
    double upper,
    double tolerance,
    double &accepted,
    BoundFeasibilityAudit &audit)
{
    audit = auditBounds(raw, lower, upper, tolerance);
    if (!audit.feasibleWithinTolerance)
    {
        return false;
    }
    accepted = std::clamp(raw, lower, upper);
    audit.correction = std::abs(raw - accepted);
    audit.correctionApplied = audit.correction > 0.0;
    return true;
}

#endif
