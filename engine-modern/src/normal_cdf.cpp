#include "normal_cdf.hpp"
#include <cmath>
#include <algorithm>

namespace
{
constexpr double sqrtTwo = 1.4142135623730950488016887242097;
constexpr double logSqrtTwoPi = 0.91893853320467274178032973640562;
}

NormalCDFMode parseNormalCDFMode(const std::string &value)
{
    if (value == "continuous")
        return NormalCDFMode::Continuous;
    if (value == "interpolated")
        return NormalCDFMode::InterpolatedTable;
    if (value == "legacy-nearest")
        return NormalCDFMode::LegacyNearestTable;
    throw std::invalid_argument(
        "likelihood evaluator desconocido: " + value +
        " (use continuous, interpolated o legacy-nearest)");
}

const char *normalCDFModeName(NormalCDFMode mode)
{
    switch (mode)
    {
    case NormalCDFMode::Continuous:
        return "continuous";
    case NormalCDFMode::InterpolatedTable:
        return "interpolated";
    case NormalCDFMode::LegacyNearestTable:
        return "legacy-nearest";
    }
    return "unknown";
}

NormalCDF::NormalCDF(NormalCDFMode mode)
    : table_(TABLE_ROWS * 4, 0.0), tableSize_(2 * NDEVIT - 1), resolution_(XDEVIT),
      minZ_(0.0), maxZ_(0.0), mode_(mode)
{
    initializeTable();

    // Guardar min/max valores z para la verificación de límites
    minZ_ = table_[0];                    // Primer valor z (más negativo)
    maxZ_ = table_[(tableSize_ - 1) * 4]; // Último valor z (más positivo)
}

double NormalCDF::nearest(double z, int column) const
{
    const size_t centre = NDEVIT - 1;
    size_t offset = static_cast<size_t>(
        std::floor(std::abs(z) * resolution_ + 0.5));
    offset = std::min(offset, NDEVIT - 2);
    const size_t row = z >= 0.0 ? centre + offset : centre - offset;
    return table_[row * 4 + static_cast<size_t>(column)];
}

double NormalCDF::continuousLogCdf(double z)
{
    if (z < -10.0)
    {
        // Mills-series evaluation of log Phi(z).  Factoring the leading
        // phi(z)/(-z) term avoids underflow for beta sensitivity runs well
        // beyond the historical +/-5 table.
        const double inverseSquare = 1.0 / (z * z);
        const double correction =
            1.0 - inverseSquare + 3.0 * inverseSquare * inverseSquare -
            15.0 * inverseSquare * inverseSquare * inverseSquare +
            105.0 * inverseSquare * inverseSquare * inverseSquare * inverseSquare;
        return -0.5 * z * z - std::log(-z) - logSqrtTwoPi +
               std::log(correction);
    }
    if (z > 0.0)
    {
        const double upperTail = 0.5 * std::erfc(z / sqrtTwo);
        return std::log1p(-upperTail);
    }
    return std::log(0.5 * std::erfc(-z / sqrtTwo));
}

double NormalCDF::continuousGaussOverCdf(double z, double logCdf)
{
    constexpr double sqrtTwoPi =
        2.506628274631000502415765284811;
    // Deliberately omit 1/sqrt(2*pi), matching the historical derivative
    // representation used by the block code.
    return continuousPdfOverCdf(z, logCdf) * sqrtTwoPi;
}

double NormalCDF::continuousPdfOverCdf(double z, double logCdf)
{
    if (z < -10.0)
    {
        // Exact derivative of the executed Mills-series log-CDF above. This
        // matters for KKT diagnostics: objective and gradient must describe
        // the same numerical function, even in the far tail.
        const double q = 1.0 / (z * z);
        const double correction =
            1.0 - q + 3.0 * q * q - 15.0 * q * q * q +
            105.0 * q * q * q * q;
        const double derivativeCorrection =
            -1.0 + 6.0 * q - 45.0 * q * q + 420.0 * q * q * q;
        const double dqDz = -2.0 / (z * z * z);
        return -z - 1.0 / z + derivativeCorrection * dqDz / correction;
    }
    return std::exp(-0.5 * z * z - logSqrtTwoPi - logCdf);
}

void NormalCDF::initializeTable()
{
    // Matrices temporales equivalentes a YY y CUMNML en Fortran
    std::vector<double> yy(NDEVIT);
    std::vector<double> cumnml(NDEVIT);

    for (size_t i = 0; i < NDEVIT; ++i)
    {
        yy[i] = static_cast<double>(i) / XDEVIT;

        double x = yy[i] / std::sqrt(2.0);
        double xx = std::erf(x); // std::erf() es equivalente a Fortran ERF()
        xx = xx / 2.0 + 0.5;
        cumnml[i] = xx;
    }

    const double twopi = 1.0 / std::sqrt(2.0 * PI);

    for (size_t i = 0; i < NDEVIT; ++i)
    {
        size_t fortranIndex = NDEVIT - 1 - i; // Mapea a Fortran NDEVIT+1-I con base 0

        // Columna 1 (índice 0): valor z (lado negativo)
        table_[i * 4 + 0] = yy[fortranIndex] * (-1.0);

        // Columna 2 (índice 1): valor CDF
        table_[i * 4 + 1] = 1.0 - cumnml[fortranIndex];

        // Columna 3 (índice 2): log(CDF)
        table_[i * 4 + 2] = std::log(table_[i * 4 + 1]);
    }

    // FORTRAN LOOP 902: Llenar el lado positivo de la tabla
    for (size_t i = 1; i < NDEVIT; ++i)
    { // Comienza en 1, no en 0 (Fortran comienza en 2)

        size_t rowIndex = i - 1 + NDEVIT;

        // Columna 1 (índice 0): valor z (lado positivo)
        table_[rowIndex * 4 + 0] = yy[i];

        // Columna 2 (índice 1): valor CDF
        table_[rowIndex * 4 + 1] = cumnml[i];

        // Columna 3 (índice 2): log(CDF)
        table_[rowIndex * 4 + 2] = std::log(table_[rowIndex * 4 + 1]);
    }

    // FORTRAN LOOP 903: Calcular la razón pdf/CDF (columna 4)
    for (size_t i = 0; i < tableSize_; ++i)
    {
        double z = table_[i * 4 + 0];
        double cdf = table_[i * 4 + 1];

        // pdf(z) = (1/sqrt(2*pi)) * exp(-z^2/2)
        // Columna 4 (índice 3): pdf(z) / CDF(z)
        table_[i * 4 + 3] = (twopi * std::exp((-z * z) / 2.0)) / cdf;
    }
}

double NormalCDF::interpolate(double z, int column) const
{
    // Manejar valores fuera de límites
    if (z <= minZ_)
    {
        return table_[0 * 4 + column];
    }
    if (z >= maxZ_)
    {
        return table_[(tableSize_ - 1) * 4 + column];
    }

    // OPTIMIZADO: Cálculo directo de índice O(1) en lugar de búsqueda lineal O(n)
    // La tabla tiene valores z desde minZ_ (-5.0) hasta maxZ_ (+5.0)
    // con espaciado de 1/resolution_ (0.0001)
    double indexFloat = (z - minZ_) * resolution_;
    size_t lowerIndex = static_cast<size_t>(indexFloat);

    // Asegurar que no excedemos los límites
    if (lowerIndex >= tableSize_ - 1)
    {
        lowerIndex = tableSize_ - 2;
    }
    size_t upperIndex = lowerIndex + 1;

    // Obtener los valores z y los valores de la columna objetivo
    double z_lower = table_[lowerIndex * 4 + 0];
    double z_upper = table_[upperIndex * 4 + 0];
    double value_lower = table_[lowerIndex * 4 + column];
    double value_upper = table_[upperIndex * 4 + column];

    // Interpolación lineal
    // Evitar división por cero
    if (std::abs(z_upper - z_lower) < 1e-10)
    {
        return value_lower;
    }

    double t = (z - z_lower) / (z_upper - z_lower);
    return value_lower + t * (value_upper - value_lower);
}

double NormalCDF::cdf(double z) const
{
    if (mode_ == NormalCDFMode::Continuous)
        return std::exp(continuousLogCdf(z));
    if (mode_ == NormalCDFMode::LegacyNearestTable)
        return nearest(z, 1);
    return interpolate(z, 1);
}

double NormalCDF::logCdf(double z) const
{
    if (mode_ == NormalCDFMode::Continuous)
        return continuousLogCdf(z);
    if (mode_ == NormalCDFMode::LegacyNearestTable)
        return nearest(z, 2);
    return interpolate(z, 2);
}

double NormalCDF::pdfOverCdf(double z) const
{
    if (mode_ == NormalCDFMode::Continuous)
    {
        const double logCdfValue = continuousLogCdf(z);
        return continuousPdfOverCdf(z, logCdfValue);
    }
    if (mode_ == NormalCDFMode::LegacyNearestTable)
        return nearest(z, 3);
    return interpolate(z, 3);
}

double NormalCDF::gaussOverCdf(double z) const
{
    // Fortran-compatible: ZGAUSS/ZDISTF where ZGAUSS = exp(-ZS²/2)
    // This is the Mills ratio without the 1/sqrt(2*pi) factor
    return logCdfAndMills(z).second;
}

std::pair<double, double> NormalCDF::logCdfAndMills(double z) const
{
    if (mode_ == NormalCDFMode::Continuous)
    {
        const double logCdfValue = continuousLogCdf(z);
        return {logCdfValue, continuousGaussOverCdf(z, logCdfValue)};
    }
    if (mode_ == NormalCDFMode::LegacyNearestTable)
    {
        const double logCdfValue = nearest(z, 2);
        const double cdfValue = std::max(nearest(z, 1), 1e-300);
        return {logCdfValue, std::exp(-0.5 * z * z) / cdfValue};
    }
    // OPTIMIZADO: Cálculo directo de índice O(1) + una sola búsqueda para ambos valores
    // Manejar valores fuera de límites
    if (z <= minZ_)
    {
        double logCdfVal = table_[0 * 4 + 2];
        double cdfVal = table_[0 * 4 + 1];
        if (cdfVal < 1e-300)
            cdfVal = 1e-300;
        double millsVal = std::exp(-z * z / 2.0) / cdfVal;
        return {logCdfVal, millsVal};
    }
    if (z >= maxZ_)
    {
        double logCdfVal = table_[(tableSize_ - 1) * 4 + 2];
        double cdfVal = table_[(tableSize_ - 1) * 4 + 1];
        if (cdfVal < 1e-300)
            cdfVal = 1e-300;
        double millsVal = std::exp(-z * z / 2.0) / cdfVal;
        return {logCdfVal, millsVal};
    }

    // OPTIMIZADO: Cálculo directo de índice O(1)
    double indexFloat = (z - minZ_) * resolution_;
    size_t lowerIndex = static_cast<size_t>(indexFloat);
    if (lowerIndex >= tableSize_ - 1)
    {
        lowerIndex = tableSize_ - 2;
    }
    size_t upperIndex = lowerIndex + 1;

    // Obtener los valores z
    double z_lower = table_[lowerIndex * 4 + 0];
    double z_upper = table_[upperIndex * 4 + 0];

    // Calcular factor de interpolación
    double t = 0.0;
    if (std::abs(z_upper - z_lower) >= 1e-10)
    {
        t = (z - z_lower) / (z_upper - z_lower);
    }

    // Interpolar logCdf (columna 2)
    double logCdf_lower = table_[lowerIndex * 4 + 2];
    double logCdf_upper = table_[upperIndex * 4 + 2];
    double logCdfVal = logCdf_lower + t * (logCdf_upper - logCdf_lower);

    // Interpolar CDF (columna 1) para calcular Mills ratio
    double cdf_lower = table_[lowerIndex * 4 + 1];
    double cdf_upper = table_[upperIndex * 4 + 1];
    double cdfVal = cdf_lower + t * (cdf_upper - cdf_lower);
    if (cdfVal < 1e-300)
        cdfVal = 1e-300;
    double millsVal = std::exp(-z * z / 2.0) / cdfVal;

    return {logCdfVal, millsVal};
}

double NormalCDF::getZ(size_t index) const
{
    if (index >= tableSize_)
    {
        throw std::out_of_range("Index out of range in NormalCDF table");
    }
    return table_[index * 4 + 0]; // Columna 1 en Fortran (índice 0 en C++)
}
