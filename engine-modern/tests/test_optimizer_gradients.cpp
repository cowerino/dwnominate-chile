#include "legislator_derivatives.hpp"
#include "rollcall_derivatives.hpp"

#include <Eigen/Dense>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <vector>

namespace
{
constexpr double inverseSqrtTwoPi =
    0.39894228040143267793994605993438;

int fail(const char *label, const Eigen::VectorXd &analytic,
         const Eigen::VectorXd &numeric)
{
    std::cerr << label << " gradient mismatch\n"
              << "analytic: " << analytic.transpose() << "\n"
              << "numeric:  " << numeric.transpose() << "\n";
    return 1;
}

bool closeGradient(const Eigen::VectorXd &analytic,
                   const Eigen::VectorXd &numeric)
{
    const double scale = std::max(1.0, numeric.norm());
    return (analytic - numeric).norm() / scale < 3e-3;
}
} // namespace

int main()
{
    NormalCDF normal;
    Eigen::VectorXd weights(3);
    weights << 1.0, 0.65, 3.7;
    const double conversion = -2.0 * weights(2) * inverseSqrtTwoPi;
    constexpr double step = 2e-5;

    Eigen::MatrixXd coordinates(10, 2);
    coordinates << -0.90, -0.25,
        -0.72, 0.18,
        -0.51, -0.31,
        -0.26, 0.42,
        -0.05, -0.18,
        0.16, 0.33,
        0.37, -0.38,
        0.58, 0.25,
        0.77, -0.12,
        0.93, 0.19;
    VoteMatrix rollVotes(10, 1);
    for (int i = 0; i < 10; ++i)
    {
        rollVotes.setVote(
            static_cast<std::size_t>(i), 0,
            coordinates(i, 0) + 0.35 * coordinates(i, 1) > 0.03);
    }
    Eigen::VectorXd midpoint(2);
    midpoint << 0.08, -0.12;
    Eigen::VectorXd spread(2);
    spread << -0.43, 0.17;

    const auto rc = computeRollCallDerivatives(
        coordinates, 0, midpoint, spread, rollVotes, weights, normal);
    Eigen::VectorXd rcAnalytic(4);
    rcAnalytic.head(2) = conversion * rc.midpointDerivatives;
    rcAnalytic.tail(2) = conversion * rc.spreadDerivatives;
    Eigen::VectorXd rcNumeric(4);
    for (int p = 0; p < 4; ++p)
    {
        Eigen::VectorXd plusMid = midpoint;
        Eigen::VectorXd minusMid = midpoint;
        Eigen::VectorXd plusSpread = spread;
        Eigen::VectorXd minusSpread = spread;
        if (p < 2)
        {
            plusMid(p) += step;
            minusMid(p) -= step;
        }
        else
        {
            plusSpread(p - 2) += step;
            minusSpread(p - 2) -= step;
        }
        const double plus = computeRollCallDerivatives(
                                coordinates, 0, plusMid, plusSpread,
                                rollVotes, weights, normal)
                                .logLikelihood;
        const double minus = computeRollCallDerivatives(
                                 coordinates, 0, minusMid, minusSpread,
                                 rollVotes, weights, normal)
                                 .logLikelihood;
        rcNumeric(p) = (plus - minus) / (2.0 * step);
    }
    if (!closeGradient(rcAnalytic, rcNumeric))
    {
        return fail("roll-call", rcAnalytic, rcNumeric);
    }

    Eigen::MatrixXd initialLegislator(1, 2);
    initialLegislator << 0.14, -0.21;
    Eigen::MatrixXd billMidpoints(6, 2);
    billMidpoints << -0.61, 0.08,
        -0.35, -0.17,
        -0.08, 0.22,
        0.21, -0.13,
        0.47, 0.15,
        0.72, -0.06;
    Eigen::MatrixXd billSpreads(6, 2);
    billSpreads << -0.42, 0.12,
        -0.38, -0.08,
        -0.46, 0.09,
        -0.41, -0.11,
        -0.44, 0.07,
        -0.39, -0.05;
    VoteMatrix legislatorVotes(1, 6);
    legislatorVotes.setVote(0, 0, false);
    legislatorVotes.setVote(0, 1, false);
    legislatorVotes.setVote(0, 2, true);
    legislatorVotes.setVote(0, 3, true);
    legislatorVotes.setVote(0, 4, true);
    legislatorVotes.setVote(0, 5, true);
    LegislatorPeriodInfo periodInfo(1);
    periodInfo.markServed(0, 0, 6);
    TimeTrends trends(1);
    TemporalCoefficients coefficients(2);
    coefficients(0, 0) = initialLegislator(0, 0);
    coefficients(0, 1) = initialLegislator(0, 1);
    const std::vector<bool> valid(6, true);

    const auto leg = computeLegislatorDerivatives(
        0, periodInfo, trends, coefficients, billMidpoints, billSpreads,
        legislatorVotes, valid, weights, normal, TemporalModel::Constant, 0, 0);
    const Eigen::VectorXd legAnalytic = conversion * leg.derivatives0;
    Eigen::VectorXd legNumeric(2);
    for (int p = 0; p < 2; ++p)
    {
        TemporalCoefficients plus = coefficients;
        TemporalCoefficients minus = coefficients;
        plus(0, p) += step;
        minus(0, p) -= step;
        const double plusValue = computeLegislatorDerivatives(
                                     0, periodInfo, trends, plus, billMidpoints,
                                     billSpreads, legislatorVotes, valid, weights,
                                     normal, TemporalModel::Constant, 0, 0)
                                     .logLikelihood;
        const double minusValue = computeLegislatorDerivatives(
                                      0, periodInfo, trends, minus, billMidpoints,
                                      billSpreads, legislatorVotes, valid, weights,
                                      normal, TemporalModel::Constant, 0, 0)
                                      .logLikelihood;
        legNumeric(p) = (plusValue - minusValue) / (2.0 * step);
    }
    if (!closeGradient(legAnalytic, legNumeric))
    {
        return fail("legislator", legAnalytic, legNumeric);
    }

    // Dynamic five-period check. The active parameter order used by SLSQP is
    // [beta0_dim1, beta0_dim2, beta1_dim1, beta1_dim2]. This independently
    // verifies the chain rule through the linear Legendre time term.
    constexpr int periods = 5;
    constexpr int billsPerPeriod = 3;
    constexpr int totalBills = periods * billsPerPeriod;
    LegislatorPeriodInfo dynamicPeriodInfo(periods);
    TimeTrends dynamicTrends(periods);
    VoteMatrix dynamicVotes(periods, totalBills);
    Eigen::MatrixXd dynamicMidpoints(totalBills, 2);
    Eigen::MatrixXd dynamicSpreads(totalBills, 2);
    const std::vector<bool> dynamicValid(totalBills, true);

    for (int period = 0; period < periods; ++period)
    {
        dynamicPeriodInfo.markServed(period, period, billsPerPeriod);
        const double t = -1.0 + 0.5 * static_cast<double>(period);
        dynamicTrends.setPeriod(period, t);
        for (int bill = 0; bill < billsPerPeriod; ++bill)
        {
            const int globalBill = period * billsPerPeriod + bill;
            dynamicMidpoints(globalBill, 0) =
                -0.52 + 0.075 * static_cast<double>(globalBill);
            dynamicMidpoints(globalBill, 1) =
                0.18 * std::sin(0.7 * static_cast<double>(globalBill));
            dynamicSpreads(globalBill, 0) =
                -0.38 + 0.025 * static_cast<double>(bill);
            dynamicSpreads(globalBill, 1) =
                (globalBill % 2 == 0) ? -0.09 : 0.11;
            dynamicVotes.setVote(
                static_cast<std::size_t>(period),
                static_cast<std::size_t>(globalBill),
                (period + bill) % 2 == 0);
        }
    }

    TemporalCoefficients linearCoefficients(2);
    linearCoefficients(0, 0) = 0.12;
    linearCoefficients(0, 1) = -0.18;
    linearCoefficients(1, 0) = 0.15;
    linearCoefficients(1, 1) = 0.09;

    const auto dynamic = computeLegislatorDerivatives(
        0,
        dynamicPeriodInfo,
        dynamicTrends,
        linearCoefficients,
        dynamicMidpoints,
        dynamicSpreads,
        dynamicVotes,
        dynamicValid,
        weights,
        normal,
        TemporalModel::Linear,
        0,
        periods - 1);
    const Eigen::VectorXd dynamicAnalytic =
        conversion * dynamic.getDerivativesForModel(TemporalModel::Linear);
    Eigen::VectorXd dynamicNumeric(4);
    for (int parameter = 0; parameter < 4; ++parameter)
    {
        const int term = parameter / 2;
        const int dimension = parameter % 2;
        TemporalCoefficients plus = linearCoefficients;
        TemporalCoefficients minus = linearCoefficients;
        plus(term, dimension) += step;
        minus(term, dimension) -= step;
        const double plusValue = computeLegislatorDerivatives(
                                     0,
                                     dynamicPeriodInfo,
                                     dynamicTrends,
                                     plus,
                                     dynamicMidpoints,
                                     dynamicSpreads,
                                     dynamicVotes,
                                     dynamicValid,
                                     weights,
                                     normal,
                                     TemporalModel::Linear,
                                     0,
                                     periods - 1)
                                     .logLikelihood;
        const double minusValue = computeLegislatorDerivatives(
                                      0,
                                      dynamicPeriodInfo,
                                      dynamicTrends,
                                      minus,
                                      dynamicMidpoints,
                                      dynamicSpreads,
                                      dynamicVotes,
                                      dynamicValid,
                                      weights,
                                      normal,
                                      TemporalModel::Linear,
                                      0,
                                      periods - 1)
                                      .logLikelihood;
        dynamicNumeric(parameter) =
            (plusValue - minusValue) / (2.0 * step);
    }
    if (!closeGradient(dynamicAnalytic, dynamicNumeric))
    {
        return fail("dynamic legislator", dynamicAnalytic, dynamicNumeric);
    }

    return 0;
}
