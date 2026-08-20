#include "csv_loader.hpp"

#include <cmath>
#include <iostream>
#include <limits>

namespace
{
bool approximatelyEqual(double lhs, double rhs)
{
    return std::abs(lhs - rhs) <= 1e-15;
}
}

int main()
{
    using dwnominate_input::roundLegacyStartCoordinate;

    struct Case
    {
        double input;
        double expected;
    };

    const Case cases[] = {
        {0.12349, 0.123},
        {0.12351, 0.124},
        {-0.12349, -0.123},
        {-0.12351, -0.124},
        {0.0, 0.0},
        {1.0, 1.0},
    };

    for (const auto &testCase : cases)
    {
        const double actual = roundLegacyStartCoordinate(testCase.input);
        if (!approximatelyEqual(actual, testCase.expected))
        {
            std::cerr << "legacy rounding mismatch: input=" << testCase.input
                      << ", expected=" << testCase.expected
                      << ", actual=" << actual << "\n";
            return 1;
        }
    }

    const double nan = std::numeric_limits<double>::quiet_NaN();
    if (!std::isnan(roundLegacyStartCoordinate(nan)))
    {
        std::cerr << "legacy rounding did not preserve NaN\n";
        return 1;
    }

    return 0;
}
