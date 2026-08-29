/**
 * @file main_cli.cpp
 * @brief Ejecutable CLI para DW-NOMINATE C++.
 *
 * Uso:
 *   dwnominate [opciones]
 *
 * Opciones:
 *   --input-dir=<path>     Directorio de votaciones (default: input_R)
 *   --output-dir=<path>    Directorio de salida CSV (default: output_cpp)
 *   --wnominate=<path>     Archivo de coordenadas iniciales WNOMINATE
 *   --bill-params=<path>   Archivo de parámetros de bill iniciales
 *   --model=<0|1|2|3>      Modelo temporal: 0=const, 1=linear, 2=quad, 3=cubic (default: 1)
 *   --iterations=<n>       Número de iteraciones (default: 4)
 *   --periods=<n>          Número de períodos (default: auto-detectar)
 *   --dimensions=<n>       Número de dimensiones espaciales (default: 2)
 *   --beta=<value>         Parámetro beta inicial (default: 5.9539)
 *   --w2=<value>           Peso de dimensión 2 inicial (default: 0.3463)
 *   --legacy-round-starts  Cuantiza las coordenadas iniciales a 3 decimales
 *   --verbose              Mostrar progreso detallado
 *   --help                 Mostrar ayuda
 *
 * Ejemplo:
 *   dwnominate --model=1 --iterations=10 --verbose
 *   dwnominate --input-dir=datos --output-dir=resultados --periods=5
 */

#include "dwnominate.hpp"
#include "csv_loader.hpp"

#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <string>
#include <vector>
#include <map>
#include <filesystem>
#include <chrono>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace fs = std::filesystem;

struct OptimizerPrecisionSettings
{
    double relativeXTolerance;
    double relativeFTolerance;
    double constraintTolerance;
    int scalarMaxEvaluations;
    int rollCallMaxEvaluations;
    int legislatorMaxEvaluations;
};

OptimizerPrecisionSettings precisionSettings(const std::string &profile)
{
    if (profile == "relaxed")
    {
        return {1e-5, 1e-7, 1e-8, 60, 150, 250};
    }
    if (profile == "standard")
    {
        return {1e-8, 1e-10, 1e-10, 120, 400, 600};
    }
    if (profile == "strict")
    {
        return {1e-10, 1e-12, 1e-12, 360, 1200, 1800};
    }
    if (profile == "ultra")
    {
        return {1e-12, 1e-14, 1e-13, 720, 2400, 3600};
    }
    throw std::invalid_argument(
        "perfil de precision desconocido: " + profile +
        " (use relaxed, standard, strict o ultra)");
}

// Configuración CLI
struct CLIConfig
{
    std::string inputDir = "input_R";
    std::string outputDir = "output_cpp";
    std::string wnominatePath = "output_wnominate/wnominate_coordinates.csv";
    std::string seedPerPeriodPath = ""; // Si vacío, usa solo wnominatePath (default per-leg)
    std::string billParamsPath = "";    // Si vacío, no cargar
    int temporalModel = 1;              // 0=const, 1=linear, 2=quad, 3=cubic
    int iterations = 4;
    int firstIteration = 1;
    int periods = 0; // 0 = auto-detectar
    int dimensions = 2;
    double beta = 5.9539;
    double w2 = 0.3463;
    bool verbose = false;
    bool showHelp = false;
    bool exportCorrected = true; // Exportar con corrección de polaridad
    bool exportOptimizerTrace = true;
    bool legacyRoundStarts = false;
    bool fortranReplication = false;
    bool evaluateOnly = false;
    bool fixGlobalParams = false;
    bool fixRollCalls = false;
    bool fixLegislators = false;
    std::string optimizerPrecision = "standard";
    std::string blockSolver = "cobyla";
    std::string scalarSearch = "local";
    std::string likelihoodEvaluator = "continuous";
    std::string billStart = "canonical-zero";
    std::string d2Identification = "none";
    double w2UpperBound = 1.0;
    double betaUpperBound = 20.0;
    bool solverFallbackToCobyla = true;
    bool adaptiveTolerances = false;
    int scalarMaxEvaluations = 0;
    int rollCallMaxEvaluations = 0;
    int legislatorMaxEvaluations = 0;
    int threads = 1;
    int minimumIterations = 4;
    double convergenceAbsoluteTolerance = 0.0;
    double convergenceRelativeTolerance = 0.0;
    int convergencePatience = 2;
};

// Parsing de argumentos CLI
void printHelp(const char *programName)
{
    std::cout << "DW-NOMINATE C++ - Implementación optimizada\n\n";
    std::cout << "Uso: " << programName << " [opciones]\n\n";
    std::cout << "Opciones:\n";
    std::cout << "  --input-dir=<path>     Directorio de votaciones (default: input_R)\n";
    std::cout << "  --output-dir=<path>    Directorio de salida CSV (default: output_cpp)\n";
    std::cout << "  --wnominate=<path>     Coordenadas iniciales WNOMINATE per-legislador\n";
    std::cout << "                         (default: output_wnominate/wnominate_coordinates.csv)\n";
    std::cout << "  --seed-per-period=<p>  CSV adicional per-(leg,periodo) (override por fila apilada)\n";
    std::cout << "                         columnas: legislator_id,period,coord1D,coord2D (period 1-based)\n";
    std::cout << "                         Override prioritario sobre --wnominate; opcional.\n";
    std::cout << "  --bill-params=<path>   Parámetros de bill iniciales (opcional)\n";
    std::cout << "  --model=<0|1|2|3>      Modelo temporal (default: 1)\n";
    std::cout << "                         0=constante, 1=lineal, 2=cuadrático, 3=cúbico\n";
    std::cout << "  --iterations=<n>       Número de iteraciones (default: 4)\n";
    std::cout << "  --first-iteration=<n>  Índice global del primer ciclo (default: 1)\n";
    std::cout << "                         úselo al continuar un estado recargado\n";
    std::cout << "  --min-iterations=<n>   Mínimo antes de evaluar convergencia (default: 4)\n";
    std::cout << "  --convergence-abs=<x>  Umbral absoluto de mejora de LL (0 desactiva)\n";
    std::cout << "  --convergence-rel=<x>  Umbral relativo de mejora de LL (0 desactiva)\n";
    std::cout << "  --convergence-patience=<n> Ciclos consecutivos requeridos (default: 2)\n";
    std::cout << "  --periods=<n>          Número de períodos (default: auto-detectar)\n";
    std::cout << "  --dimensions=<n>       Dimensiones espaciales (default: 2)\n";
    std::cout << "  --beta=<value>         Parámetro beta inicial (default: 5.9539)\n";
    std::cout << "  --w2=<value>           Peso dimensión 2 inicial (default: 0.3463)\n";
    std::cout << "  --legacy-round-starts  Cuantizar coordenadas iniciales a 3 decimales\n";
    std::cout << "                         como los archivos del Fortran standalone\n";
    std::cout << "  --fortran-replication  Replica el procedimiento canónico y cambia sólo\n";
    std::cout << "                         sus búsquedas ad hoc por NLopt (sin cotas W2/beta)\n";
    std::cout << "  --evaluate-only        Evaluar el estado cargado sin optimizar ningun bloque\n";
    std::cout << "  --fix-global-params    Fijar W2 y beta; optimizar los demas bloques\n";
    std::cout << "  --fix-roll-calls       Fijar midpoint/spread cargados\n";
    std::cout << "  --fix-legislators      Fijar coeficientes temporales cargados\n";
    std::cout << "  --optimizer-precision=<perfil>\n";
    std::cout << "                         relaxed|standard|strict|ultra (default: standard)\n";
    std::cout << "  --block-solver=<modo>  cobyla|slsqp|hybrid (default: cobyla)\n";
    std::cout << "                         hybrid usa COBYLA y SLSQP en el ciclo final\n";
    std::cout << "  --scalar-search=<modo> local|global (default: local)\n";
    std::cout << "                         local conserva el alcance SIGMAS/WINT del Fortran\n";
    std::cout << "  --likelihood=<modo>    continuous|interpolated|legacy-nearest\n";
    std::cout << "                         (default científico: continuous)\n";
    std::cout << "  --bill-start=<modo>    canonical-zero|legacy-0.3\n";
    std::cout << "                         (default: canonical-zero)\n";
    std::cout << "  --w2-upper=<x>         Cota de identificación de W2 (default: 1)\n";
    std::cout << "  --d2-identification=<modo> none|maximal-feasible (default: none)\n";
    std::cout << "                         maximal-feasible fija la escala sin cambiar el ajuste\n";
    std::cout << "  --beta-upper=<x>       Cota de sensibilidad de beta (default: 20)\n";
    std::cout << "  --adaptive-tolerances  Presupuesto relajado al inicio y completo al final\n";
    std::cout << "  --scalar-maxeval=<n>   Override del presupuesto para W2 y beta\n";
    std::cout << "  --rollcall-maxeval=<n> Override del presupuesto por votacion\n";
    std::cout << "  --legislator-maxeval=<n> Override del presupuesto por legislador\n";
    std::cout << "  --threads=<n>          Bloques independientes en paralelo si hay OpenMP\n";
    std::cout << "  --no-solver-fallback   No usar COBYLA si SLSQP falla o empeora LL\n";
    std::cout << "  --verbose              Mostrar progreso detallado\n";
    std::cout << "  --no-corrected         No exportar archivos con polaridad corregida\n";
    std::cout << "  --no-optimizer-trace   Omitir el CSV de bloques (util en corridas largas)\n";
    std::cout << "  --help                 Mostrar esta ayuda\n\n";
    std::cout << "Ejemplos:\n";
    std::cout << "  " << programName << " --model=1 --iterations=10 --verbose\n";
    std::cout << "  " << programName << " --input-dir=datos --periods=5\n";
    std::cout << "  " << programName << " --model=0 --iterations=4\n";
    std::cout << "  " << programName << " --model=0 --legacy-round-starts\n";
}

std::string getArgValue(const std::string &arg, const std::string &prefix)
{
    if (arg.find(prefix) == 0)
    {
        return arg.substr(prefix.length());
    }
    return "";
}

CLIConfig parseArguments(int argc, char *argv[])
{
    CLIConfig config;

    for (int i = 1; i < argc; ++i)
    {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h")
        {
            config.showHelp = true;
        }
        else if (arg == "--verbose" || arg == "-v")
        {
            config.verbose = true;
        }
        else if (arg == "--no-corrected")
        {
            config.exportCorrected = false;
        }
        else if (arg == "--no-optimizer-trace")
        {
            config.exportOptimizerTrace = false;
        }
        else if (arg == "--legacy-round-starts")
        {
            config.legacyRoundStarts = true;
        }
        else if (arg == "--fortran-replication")
        {
            config.fortranReplication = true;
        }
        else if (arg == "--evaluate-only")
        {
            config.evaluateOnly = true;
        }
        else if (arg == "--fix-global-params")
        {
            config.fixGlobalParams = true;
        }
        else if (arg == "--fix-roll-calls")
        {
            config.fixRollCalls = true;
        }
        else if (arg == "--fix-legislators")
        {
            config.fixLegislators = true;
        }
        else if (arg == "--adaptive-tolerances")
        {
            config.adaptiveTolerances = true;
        }
        else if (arg == "--no-solver-fallback")
        {
            config.solverFallbackToCobyla = false;
        }
        else if (arg.find("--input-dir=") == 0)
        {
            config.inputDir = getArgValue(arg, "--input-dir=");
        }
        else if (arg.find("--output-dir=") == 0)
        {
            config.outputDir = getArgValue(arg, "--output-dir=");
        }
        else if (arg.find("--wnominate=") == 0)
        {
            config.wnominatePath = getArgValue(arg, "--wnominate=");
        }
        else if (arg.find("--seed-per-period=") == 0)
        {
            config.seedPerPeriodPath = getArgValue(arg, "--seed-per-period=");
        }
        else if (arg.find("--bill-params=") == 0)
        {
            config.billParamsPath = getArgValue(arg, "--bill-params=");
        }
        else if (arg.find("--model=") == 0)
        {
            config.temporalModel = std::stoi(getArgValue(arg, "--model="));
        }
        else if (arg.find("--iterations=") == 0)
        {
            config.iterations = std::stoi(getArgValue(arg, "--iterations="));
        }
        else if (arg.find("--first-iteration=") == 0)
        {
            config.firstIteration =
                std::stoi(getArgValue(arg, "--first-iteration="));
        }
        else if (arg.find("--min-iterations=") == 0)
        {
            config.minimumIterations = std::stoi(getArgValue(arg, "--min-iterations="));
        }
        else if (arg.find("--convergence-abs=") == 0)
        {
            config.convergenceAbsoluteTolerance = std::stod(getArgValue(arg, "--convergence-abs="));
        }
        else if (arg.find("--convergence-rel=") == 0)
        {
            config.convergenceRelativeTolerance = std::stod(getArgValue(arg, "--convergence-rel="));
        }
        else if (arg.find("--convergence-patience=") == 0)
        {
            config.convergencePatience = std::stoi(getArgValue(arg, "--convergence-patience="));
        }
        else if (arg.find("--periods=") == 0)
        {
            config.periods = std::stoi(getArgValue(arg, "--periods="));
        }
        else if (arg.find("--dimensions=") == 0)
        {
            config.dimensions = std::stoi(getArgValue(arg, "--dimensions="));
        }
        else if (arg.find("--beta=") == 0)
        {
            config.beta = std::stod(getArgValue(arg, "--beta="));
        }
        else if (arg.find("--w2=") == 0)
        {
            config.w2 = std::stod(getArgValue(arg, "--w2="));
        }
        else if (arg.find("--optimizer-precision=") == 0)
        {
            config.optimizerPrecision =
                getArgValue(arg, "--optimizer-precision=");
        }
        else if (arg.find("--block-solver=") == 0)
        {
            config.blockSolver = getArgValue(arg, "--block-solver=");
        }
        else if (arg.find("--scalar-search=") == 0)
        {
            config.scalarSearch = getArgValue(arg, "--scalar-search=");
        }
        else if (arg.find("--likelihood=") == 0)
        {
            config.likelihoodEvaluator = getArgValue(arg, "--likelihood=");
        }
        else if (arg.find("--bill-start=") == 0)
        {
            config.billStart = getArgValue(arg, "--bill-start=");
        }
        else if (arg.find("--w2-upper=") == 0)
        {
            config.w2UpperBound = std::stod(getArgValue(arg, "--w2-upper="));
        }
        else if (arg.find("--d2-identification=") == 0)
        {
            config.d2Identification = getArgValue(arg, "--d2-identification=");
        }
        else if (arg.find("--beta-upper=") == 0)
        {
            config.betaUpperBound = std::stod(getArgValue(arg, "--beta-upper="));
        }
        else if (arg.find("--scalar-maxeval=") == 0)
        {
            config.scalarMaxEvaluations =
                std::stoi(getArgValue(arg, "--scalar-maxeval="));
        }
        else if (arg.find("--rollcall-maxeval=") == 0)
        {
            config.rollCallMaxEvaluations =
                std::stoi(getArgValue(arg, "--rollcall-maxeval="));
        }
        else if (arg.find("--legislator-maxeval=") == 0)
        {
            config.legislatorMaxEvaluations =
                std::stoi(getArgValue(arg, "--legislator-maxeval="));
        }
        else if (arg.find("--threads=") == 0)
        {
            config.threads = std::stoi(getArgValue(arg, "--threads="));
        }
        else
        {
            std::cerr << "Advertencia: argumento desconocido: " << arg << "\n";
        }
    }

    // Este preset define el brazo de aislamiento causal: datos, arranque,
    // orden de bloques, PLOG y restricciones del Fortran; cambia únicamente
    // las búsquedas ad hoc por optimizadores derivativo-libres de NLopt.
    if (config.fortranReplication)
    {
        config.blockSolver = "cobyla";
        config.scalarSearch = "local";
        config.likelihoodEvaluator = "legacy-nearest";
        config.billStart = "canonical-zero";
        config.d2Identification = "none";
        config.adaptiveTolerances = false;
    }

    // Validacion temprana para que un perfil mal escrito no inicie la carga.
    static_cast<void>(precisionSettings(config.optimizerPrecision));
    static_cast<void>(parseBlockSolverMode(config.blockSolver));
    static_cast<void>(parseNormalCDFMode(config.likelihoodEvaluator));
    if (config.scalarSearch != "local" && config.scalarSearch != "global")
    {
        throw std::invalid_argument(
            "scalar search desconocido: " + config.scalarSearch +
            " (use local o global)");
    }
    if (config.billStart != "canonical-zero" && config.billStart != "legacy-0.3")
    {
        throw std::invalid_argument(
            "bill start desconocido: " + config.billStart +
            " (use canonical-zero o legacy-0.3)");
    }
    if (config.d2Identification != "none" &&
        config.d2Identification != "maximal-feasible")
    {
        throw std::invalid_argument(
            "identificacion D2 desconocida: " + config.d2Identification +
            " (use none o maximal-feasible)");
    }
    if (config.likelihoodEvaluator != "continuous" &&
        config.blockSolver != "cobyla")
    {
        throw std::invalid_argument(
            "SLSQP requiere --likelihood=continuous: los modos tabulados "
            "solo admiten el solver derivativo-libre cobyla");
    }
    if (config.threads < 1 || config.scalarMaxEvaluations < 0 ||
        config.rollCallMaxEvaluations < 0 ||
        config.legislatorMaxEvaluations < 0 || config.iterations < 1 ||
        config.firstIteration < 1 ||
        config.minimumIterations < 1 ||
        config.convergenceAbsoluteTolerance < 0.0 ||
        config.convergenceRelativeTolerance < 0.0 ||
        config.convergencePatience < 1 ||
        (!config.fortranReplication &&
         (config.w2UpperBound <= 0.01 || config.betaUpperBound <= 0.05 ||
          config.w2 <= 0.0 || config.w2 > config.w2UpperBound ||
          config.beta <= 0.0 || config.beta > config.betaUpperBound)))
    {
        throw std::invalid_argument(
            "configuracion numerica invalida: iteraciones/paciencia deben ser "
            "positivas y las tolerancias deben ser no negativas");
    }
    return config;
}

int detectNumPeriods(const std::string &inputDir)
{
    int maxPeriod = 0;

    try
    {
        for (const auto &entry : fs::directory_iterator(inputDir))
        {
            std::string filename = entry.path().filename().string();

            // Buscar archivos votes_matrix_p<N>.csv
            if (filename.find("votes_matrix_p") == 0 && filename.find(".csv") != std::string::npos)
            {
                // Extraer número del nombre
                size_t start = std::string("votes_matrix_p").length();
                size_t end = filename.find(".csv");
                if (end > start)
                {
                    std::string numStr = filename.substr(start, end - start);
                    try
                    {
                        int period = std::stoi(numStr);
                        maxPeriod = std::max(maxPeriod, period);
                    }
                    catch (...)
                    {
                        // Ignorar archivos con nombres inválidos
                    }
                }
            }
        }
        if (maxPeriod == 0 && fs::exists(fs::path(inputDir) / "votes_matrix.csv"))
        {
            maxPeriod = 1;
        }
    }
    catch (const fs::filesystem_error &e)
    {
        std::cerr << "Error al leer directorio " << inputDir << ": " << e.what() << "\n";
        return 0;
    }

    return maxPeriod;
}

void exportCoordinatesAllPeriods(const std::string &path,
                                 const DWNominateResult &result,
                                 int numPeriods)
{
    std::ofstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Error: No se puede crear " << path << std::endl;
        return;
    }

    if (!result.hasTemporalCoefficients())
    {
        std::cerr << "Error: No hay coeficientes temporales disponibles.\n";
        return;
    }

    file << std::fixed << std::setprecision(17);
    file << "legislator_id,period,coord1D,coord2D,effective_model\n";

    int exported = 0;
    for (int period = 1; period <= numPeriods; ++period)
    {
        for (int legId : result.legislatorUniqueIds)
        {
            Eigen::VectorXd coords = result.getCoordinatesAtPeriod(legId, period);
            if (coords.size() >= 2)
            {
                int effModel = result.getEffectiveTemporalOrder(legId);
                file << legId << "," << period << ","
                     << coords(0) << "," << coords(1) << ","
                     << effModel << "\n";
                exported++;
            }
        }
    }

    std::cout << "Exportado: " << path << " (" << exported << " registros)\n";
}

void exportCoordinatesAllPeriodsCorrected(const std::string &path,
                                          const DWNominateResult &result,
                                          int numPeriods)
{
    std::ofstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Error: No se puede crear " << path << std::endl;
        return;
    }

    if (!result.hasTemporalCoefficients())
    {
        std::cerr << "Error: No hay coeficientes temporales disponibles.\n";
        return;
    }

    file << std::fixed << std::setprecision(17);
    file << "legislator_id,period,coord1D,coord2D,effective_model\n";

    int exported = 0;
    for (int period = 1; period <= numPeriods; ++period)
    {
        for (int legId : result.legislatorUniqueIds)
        {
            if (!result.servedInPeriod(legId, period))
            {
                continue;
            }
            Eigen::VectorXd coords = result.getCoordinatesAtPeriod(legId, period);
            if (coords.size() >= 2)
            {
                int effModel = result.getEffectiveTemporalOrder(legId);
                // Corrección de polaridad: multiplicar por -1
                file << legId << "," << period << ","
                     << (-coords(0)) << "," << (-coords(1)) << ","
                     << effModel << "\n";
                exported++;
            }
        }
    }

    std::cout << "Exportado (polaridad corregida): " << path << " (" << exported << " registros)\n";
}

void exportTemporalCoefficients(const std::string &path,
                                const DWNominateResult &result)
{
    std::ofstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Error: No se puede crear " << path << std::endl;
        return;
    }

    file << std::fixed << std::setprecision(17);
    file << "legislator_id,served_periods,effective_model,"
            "beta0_dim1,beta0_dim2,beta1_dim1,beta1_dim2,"
            "beta2_dim1,beta2_dim2,beta3_dim1,beta3_dim2,"
            "intercept_radius\n";

    int exported = 0;
    for (int legId : result.legislatorUniqueIds)
    {
        const auto coefficientIt = result.temporalCoefficients.find(legId);
        const auto periodsIt = result.servedPeriods.find(legId);
        if (coefficientIt == result.temporalCoefficients.end() ||
            periodsIt == result.servedPeriods.end())
        {
            continue;
        }

        const Eigen::MatrixXd &beta = coefficientIt->second;
        if (beta.rows() < 4 || beta.cols() < 2)
        {
            continue;
        }
        const double interceptRadius = beta.row(0).head(2).norm();
        file << legId << "," << periodsIt->second.size() << ","
             << result.getEffectiveTemporalOrder(legId);
        for (int term = 0; term < 4; ++term)
        {
            file << "," << beta(term, 0) << "," << beta(term, 1);
        }
        file << "," << interceptRadius << "\n";
        ++exported;
    }

    std::cout << "Exportado: " << path << " (" << exported
              << " legisladores)\n";
}

void exportBillParameters(const std::string &path,
                          const DWNominateResult &result,
                          int numRollCalls)
{
    std::ofstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Error: No se puede crear " << path << std::endl;
        return;
    }

    file << std::fixed << std::setprecision(17);
    file << "rollcall_id,midpoint1D,midpoint2D,spread1D,spread2D\n";

    for (int i = 0; i < numRollCalls; ++i)
    {
        file << i << ","
             << result.rollCallMidpoints(i, 0) << ","
             << (result.rollCallMidpoints.cols() > 1 ? result.rollCallMidpoints(i, 1) : 0.0) << ","
             << result.rollCallSpreads(i, 0) << ","
             << (result.rollCallSpreads.cols() > 1 ? result.rollCallSpreads(i, 1) : 0.0) << "\n";
    }

    std::cout << "Exportado: " << path << " (" << numRollCalls << " roll calls)\n";
}

// El cargador espera session,ID,midpoint1D,midpoint2D,spread1D,spread2D en un archivo
// llamado dwnominate_bill_parameters.csv, mientras que la exportacion historica escribe
// un rollcall_id plano en cpp_bill_parameters.csv. Sin este segundo archivo un estado
// exportado no se puede volver a cargar con --bill-params sin re-etiquetar las filas a
// mano, que es lo que hace stage_bills() dentro de tests/test_dynamic_roundtrip.py.
void exportBillParametersReloadable(const std::string &path,
                                    const DWNominateResult &result,
                                    const std::vector<int> &rollCallCongress)
{
    std::ofstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Error: No se puede crear " << path << std::endl;
        return;
    }

    file << std::fixed << std::setprecision(17);
    file << "session,ID,midpoint1D,midpoint2D,spread1D,spread2D\n";

    const int numRollCalls = static_cast<int>(rollCallCongress.size());
    int localId = 0;
    int previousPeriod = -1;

    for (int i = 0; i < numRollCalls; ++i)
    {
        const int period = rollCallCongress[i];
        localId = (period == previousPeriod) ? localId + 1 : 1;
        previousPeriod = period;

        file << (period + 1) << ","
             << localId << ","
             << result.rollCallMidpoints(i, 0) << ","
             << (result.rollCallMidpoints.cols() > 1 ? result.rollCallMidpoints(i, 1) : 0.0) << ","
             << result.rollCallSpreads(i, 0) << ","
             << (result.rollCallSpreads.cols() > 1 ? result.rollCallSpreads(i, 1) : 0.0) << "\n";
    }

    std::cout << "Exportado: " << path << " (" << numRollCalls << " roll calls, recargable)\n";
}

void exportSummary(const std::string &path,
                   const DWNominateResult &result,
                   const CLIConfig &config,
                   double elapsedSeconds)
{
    std::ofstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Error: No se puede crear " << path << std::endl;
        return;
    }

    file << "parameter,value\n";
    file << "log_likelihood," << std::fixed << std::setprecision(12) << result.finalLogLikelihood << "\n";
    file << "iterations," << result.totalIterations << "\n";
    file << "first_iteration," << config.firstIteration << "\n";
    file << "converged," << (result.converged ? 1 : 0) << "\n";
    file << "final_ll_improvement," << result.finalLogLikelihoodImprovement << "\n";
    file << "convergence_absolute_tolerance," << config.convergenceAbsoluteTolerance << "\n";
    file << "convergence_relative_tolerance," << config.convergenceRelativeTolerance << "\n";
    file << "convergence_patience," << config.convergencePatience << "\n";
    file << "valid_votes," << result.totalValidVotes << "\n";
    file << "correct_classifications," << result.classificationAfter << "\n";
    double classPct = result.totalValidVotes > 0 ? (100.0 * result.classificationAfter / result.totalValidVotes) : 0.0;
    file << "classification_pct," << std::setprecision(4) << classPct << "\n";
    file << "w1," << std::setprecision(17) << result.weights(0) << "\n";
    file << "w2," << result.weights(1) << "\n";
    file << "beta," << result.weights(2) << "\n";
    file << "temporal_model," << config.temporalModel << "\n";
    file << "dimensions," << config.dimensions << "\n";
    file << "periods," << config.periods << "\n";
    file << "optimizer_precision," << config.optimizerPrecision << "\n";
    file << "block_solver," << config.blockSolver << "\n";
    file << "scalar_search," << config.scalarSearch << "\n";
    file << "likelihood_evaluator," << config.likelihoodEvaluator << "\n";
    file << "bill_start," << config.billStart << "\n";
    file << "fortran_replication," << (config.fortranReplication ? 1 : 0) << "\n";
    file << "w2_upper_bound,";
    if (config.fortranReplication)
        file << "none\n";
    else
        file << config.w2UpperBound << "\n";
    file << "d2_identification," << config.d2Identification << "\n";
    file << "d2_scale_factor," << result.secondDimensionScaleFactor << "\n";
    file << "raw_w2_before_identification," << result.rawSecondDimensionWeight << "\n";
    file << "beta_upper_bound,";
    if (config.fortranReplication)
        file << "none\n";
    else
        file << config.betaUpperBound << "\n";
    file << "evaluate_only," << (config.evaluateOnly ? 1 : 0) << "\n";
    file << "fix_global_params," <<
                (config.evaluateOnly || config.fixGlobalParams ? 1 : 0) << "\n";
    file << "fix_roll_calls," <<
                (config.evaluateOnly || config.fixRollCalls ? 1 : 0) << "\n";
    file << "fix_legislators," <<
                (config.evaluateOnly || config.fixLegislators ? 1 : 0) << "\n";
    file << "adaptive_tolerances," << (config.adaptiveTolerances ? 1 : 0) << "\n";
    file << "threads," << config.threads << "\n";
    file << "optimizer_trace_exported," <<
                (config.exportOptimizerTrace ? 1 : 0) << "\n";
    file << "elapsed_seconds," << std::setprecision(2) << elapsedSeconds << "\n";

    std::cout << "Exportado: " << path << "\n";
}

// DW-NOMINATE only identifies the products w_k * distance_k.  Consequently,
// multiplying every second-dimension coordinate, midpoint and spread by c and
// dividing w2 by c leaves every utility, probability and likelihood exactly
// unchanged.  "maximal-feasible" chooses the unique representative that
// expands D2 until a constrained legislator intercept or roll-call midpoint
// touches the unit circle.  This is a gauge choice, not a z-score
// normalization and not another optimization step.
double applySecondDimensionIdentification(DWNominateResult &result,
                                          const std::string &mode)
{
    if (mode == "none" || result.numDimensions < 2 || result.weights.size() < 3)
    {
        result.secondDimensionScaleFactor = 1.0;
        result.rawSecondDimensionWeight =
            result.weights.size() > 1 ? result.weights(1) : 0.0;
        return 1.0;
    }
    if (mode != "maximal-feasible")
    {
        throw std::invalid_argument(
            "identificacion D2 desconocida: " + mode +
            " (use none o maximal-feasible)");
    }

    double maximumScale = std::numeric_limits<double>::infinity();
    auto includeCircleConstraint = [&maximumScale](double first, double second)
    {
        if (std::abs(second) <= 1e-15)
        {
            return;
        }
        const double remaining = std::max(0.0, 1.0 - first * first);
        maximumScale = std::min(
            maximumScale, std::sqrt(remaining / (second * second)));
    };

    if (!result.temporalCoefficients.empty())
    {
        for (const auto &[id, coefficients] : result.temporalCoefficients)
        {
            (void)id;
            if (coefficients.rows() > 0 && coefficients.cols() > 1)
            {
                includeCircleConstraint(coefficients(0, 0), coefficients(0, 1));
            }
        }
    }
    else if (result.legislatorCoords.cols() > 1)
    {
        for (Eigen::Index row = 0; row < result.legislatorCoords.rows(); ++row)
        {
            includeCircleConstraint(
                result.legislatorCoords(row, 0), result.legislatorCoords(row, 1));
        }
    }
    if (result.rollCallMidpoints.cols() > 1)
    {
        for (Eigen::Index row = 0; row < result.rollCallMidpoints.rows(); ++row)
        {
            includeCircleConstraint(
                result.rollCallMidpoints(row, 0), result.rollCallMidpoints(row, 1));
        }
    }

    // Feasible estimated states imply maximumScale >= 1.  Clamp tiny solver
    // tolerance excursions, and leave a degenerate all-zero D2 untouched.
    const double scale = std::isfinite(maximumScale)
                             ? std::max(1.0, maximumScale)
                             : 1.0;
    result.rawSecondDimensionWeight = result.weights(1);
    result.secondDimensionScaleFactor = scale;
    result.weights(1) /= scale;
    if (result.legislatorCoords.cols() > 1)
    {
        result.legislatorCoords.col(1) *= scale;
    }
    if (result.rollCallMidpoints.cols() > 1)
    {
        result.rollCallMidpoints.col(1) *= scale;
        result.rollCallSpreads.col(1) *= scale;
    }
    for (auto &[id, coefficients] : result.temporalCoefficients)
    {
        (void)id;
        if (coefficients.cols() > 1)
        {
            coefficients.col(1) *= scale;
        }
    }
    for (LegislatorStats &stats : result.legislatorStats)
    {
        stats.varianceX2 *= scale * scale;
        stats.stdDevX2 *= scale;
    }
    return scale;
}

void exportConvergenceTrace(const std::string &path,
                            const DWNominateResult &result)
{
    std::ofstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Error: No se puede crear " << path << std::endl;
        return;
    }

    file << "iteration,log_likelihood,w2,beta,delta_log_likelihood\n";
    file << std::fixed << std::setprecision(12);
    double previous = 0.0;
    bool first = true;
    for (const auto &entry : result.convergenceTrace)
    {
        const double delta = first ? 0.0 : entry.logLikelihood - previous;
        file << entry.iteration << ","
             << entry.logLikelihood << ","
             << entry.weight2 << ","
             << entry.beta << ","
             << delta << "\n";
        previous = entry.logLikelihood;
        first = false;
    }

    std::cout << "Exportado: " << path << "\n";
}

void exportOptimizerTrace(const std::string &path,
                          const DWNominateResult &result)
{
    std::ofstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Error: No se puede crear " << path << std::endl;
        return;
    }

    file << "iteration,block,item_index,algorithm,fallback_used,"
            "objective_evaluations,status,initial_log_likelihood,"
            "final_log_likelihood,improvement,elapsed_milliseconds,"
            "attempted,accepted,raw_return_feasible,numerical_correction_applied,"
            "constraint_tolerance,raw_constraint_violation,"
            "feasibility_correction_norm,infeasible_objective_evaluations,"
            "max_objective_constraint_violation\n";
    file << std::fixed << std::setprecision(12);
    for (const auto &entry : result.optimizerTrace)
    {
        file << entry.iteration << ","
             << entry.block << ","
             << entry.itemIndex << ","
             << entry.algorithm << ","
             << (entry.fallbackUsed ? 1 : 0) << ","
             << entry.objectiveEvaluations << ","
             << entry.optimizerStatus << ","
             << entry.initialLogLikelihood << ","
             << entry.finalLogLikelihood << ","
             << entry.improvement << ","
             << entry.elapsedMilliseconds << ","
             << (entry.attempted ? 1 : 0) << ","
             << (entry.accepted ? 1 : 0) << ","
             << (entry.rawReturnFeasible ? 1 : 0) << ","
             << (entry.numericalCorrectionApplied ? 1 : 0) << ","
             << entry.constraintTolerance << ","
             << entry.rawConstraintViolation << ","
             << entry.feasibilityCorrectionNorm << ","
             << entry.infeasibleObjectiveEvaluations << ","
             << entry.maxObjectiveConstraintViolation << "\n";
    }
    std::cout << "Exportado: " << path << "\n";
}

// Función principal
int main(int argc, char *argv[])
{
    // Parsear argumentos
    CLIConfig config = parseArguments(argc, argv);

    if (config.showHelp)
    {
        printHelp(argv[0]);
        return 0;
    }

    // Banner inicial
    std::cout << "============================================================\n";
    std::cout << "  DW-NOMINATE C++ CLI\n";
    std::cout << "============================================================\n\n";

    // Auto-detectar períodos si no se especificó
    if (config.periods == 0)
    {
        config.periods = detectNumPeriods(config.inputDir);
        if (config.periods == 0)
        {
            std::cerr << "ERROR: No se pudieron detectar archivos de votación en "
                      << config.inputDir << "\n";
            std::cerr << "       Especifique --periods=<n> o verifique el directorio.\n";
            return 1;
        }
        if (config.verbose)
        {
            std::cout << "Períodos auto-detectados: " << config.periods << "\n";
        }
    }

    // Crear directorio de salida si no existe
    try
    {
        fs::create_directories(config.outputDir);
    }
    catch (const fs::filesystem_error &e)
    {
        std::cerr << "ERROR: No se puede crear directorio de salida: " << e.what() << "\n";
        return 1;
    }

    // Mostrar configuración
    std::cout << "Configuracion:\n";
    std::cout << "  Input:      " << config.inputDir << "\n";
    std::cout << "  Output:     " << config.outputDir << "\n";
    std::cout << "  WNOMINATE:  " << config.wnominatePath << "\n";
    if (!config.seedPerPeriodPath.empty())
    {
        std::cout << "  SeedPP:     " << config.seedPerPeriodPath << "\n";
    }
    std::cout << "  Modelo:     " << config.temporalModel
              << (config.temporalModel == 0   ? " (constante)"
                  : config.temporalModel == 1 ? " (lineal)"
                  : config.temporalModel == 2 ? " (cuadratico)"
                                              : " (cubico)")
              << "\n";
    std::cout << "  Iteraciones:" << config.iterations << "\n";
    std::cout << "  Primer ciclo:" << config.firstIteration << "\n";
    std::cout << "  Periodos:   " << config.periods << "\n";
    std::cout << "  Dimensiones:" << config.dimensions << "\n";
    std::cout << "  Beta:       " << config.beta << "\n";
    std::cout << "  W2:         " << config.w2 << "\n\n";
    std::cout << "  Likelihood: " << config.likelihoodEvaluator << "\n";
    std::cout << "  Bill start: " << config.billStart << "\n";
    std::cout << "  Cotas:      ";
    if (config.fortranReplication)
        std::cout << "sin cotas globales W2/beta (cajas locales WINT/SIGMAS)\n";
    else
        std::cout << "W2<=" << config.w2UpperBound
                  << ", beta<=" << config.betaUpperBound << "\n";
    std::cout << "  Redondeo:   "
              << (config.legacyRoundStarts ? "3 decimales (legacy)" : "precision completa")
              << "\n";
    OptimizerPrecisionSettings optimizer =
        precisionSettings(config.optimizerPrecision);
    if (config.scalarMaxEvaluations > 0)
    {
        optimizer.scalarMaxEvaluations = config.scalarMaxEvaluations;
    }
    if (config.rollCallMaxEvaluations > 0)
    {
        optimizer.rollCallMaxEvaluations = config.rollCallMaxEvaluations;
    }
    if (config.legislatorMaxEvaluations > 0)
    {
        optimizer.legislatorMaxEvaluations = config.legislatorMaxEvaluations;
    }
    std::cout << "  NLopt:      " << config.optimizerPrecision
              << " (xtol=" << optimizer.relativeXTolerance
              << ", ftol=" << optimizer.relativeFTolerance << ")\n";
    std::cout << "  Maxeval:    scalar=" << optimizer.scalarMaxEvaluations
              << ", rollcall=" << optimizer.rollCallMaxEvaluations
              << ", legislador=" << optimizer.legislatorMaxEvaluations
              << "\n";
    std::cout << "  Solver:     " << config.blockSolver
              << (config.solverFallbackToCobyla ? " (fallback COBYLA)" : "")
              << "\n";
    std::cout << "  Escalares:  " << config.scalarSearch
              << (config.scalarSearch == "local"
                      ? " (caja SIGMAS/WINT)"
                      : " (caja global experimental)")
              << "\n";
    std::cout << "  Ident. D2:  " << config.d2Identification << "\n";
    std::cout << "  Réplica F:  " << (config.fortranReplication ? "sí" : "no") << "\n";
    std::cout << "  Modo:       "
              << (config.evaluateOnly ? "solo evaluacion" : "estimacion");
    if (!config.evaluateOnly &&
        (config.fixGlobalParams || config.fixRollCalls || config.fixLegislators))
    {
        std::cout << " (bloques fijados:"
                  << (config.fixGlobalParams ? " globales" : "")
                  << (config.fixRollCalls ? " votaciones" : "")
                  << (config.fixLegislators ? " legisladores" : "")
                  << ")";
    }
    std::cout << "\n";
    std::cout << "  Schedule:   "
              << (config.adaptiveTolerances ? "adaptativo" : "fijo") << "\n";
    std::cout << "  Threads:    " << config.threads;
#ifndef _OPENMP
    if (config.threads > 1)
    {
        std::cout << " (binario sin OpenMP: ejecucion serial)";
    }
#endif
    std::cout << "\n\n";

    // Iniciar cronómetro
    auto startTime = std::chrono::high_resolution_clock::now();

    // Cargar datos
    std::cout << "Cargando datos...\n";

    // Determinar directorio de referencia R basado en modelo temporal
    std::string refDir = "output_R_dwnominate_model" + std::to_string(config.temporalModel);
    if (!config.billParamsPath.empty())
    {
        fs::path billPath(config.billParamsPath);
        refDir = billPath.parent_path().string();
    }

    std::cout << "  Ref. R:     " << refDir << "\n";

    CSVLoader loader(config.inputDir, refDir);
    DWNominateInput input;

    // Configurar inicialización
    InitializationConfig initConfig;
    initConfig.beta = config.beta;
    initConfig.w2 = config.w2;
    initConfig.useWNominateStart = true;
    initConfig.wnominatePath = config.wnominatePath;
    initConfig.roundStartsToThreeDecimals = config.legacyRoundStarts;
    initConfig.initialRollCallSpread =
        config.billStart == "legacy-0.3" ? 0.3 : 0.0;
    if (!config.seedPerPeriodPath.empty())
    {
        initConfig.useSeedPerPeriod = true;
        initConfig.seedPerPeriodPath = config.seedPerPeriodPath;
    }

    try
    {
        input = loader.loadInput(config.periods, initConfig);
    }
    catch (const std::exception &e)
    {
        std::cerr << "ERROR cargando datos: " << e.what() << "\n";
        return 1;
    }

    std::cout << "  Legisladores: " << input.votes.getNumLegislators() << "\n";
    std::cout << "  Roll calls:   " << input.votes.getNumRollCalls() << "\n\n";

    // Configurar DW-NOMINATE
    DWNominateConfig dwConfig;
    dwConfig.numDimensions = config.dimensions;
    dwConfig.temporalModel = config.temporalModel;
    dwConfig.firstCongress = 0;
    dwConfig.lastCongress = config.periods - 1;
    dwConfig.firstIteration = config.firstIteration;
    dwConfig.lastIteration = config.firstIteration + config.iterations - 1;
    dwConfig.marginThreshold = 0.025;
    dwConfig.verbose = config.verbose;
    dwConfig.fixGlobalParams = config.evaluateOnly || config.fixGlobalParams;
    dwConfig.fixRollCalls = config.evaluateOnly || config.fixRollCalls;
    dwConfig.fixLegislators = config.evaluateOnly || config.fixLegislators;
    dwConfig.optimizerRelativeXTolerance = optimizer.relativeXTolerance;
    dwConfig.optimizerRelativeFTolerance = optimizer.relativeFTolerance;
    dwConfig.optimizerConstraintTolerance = optimizer.constraintTolerance;
    dwConfig.scalarMaxEvaluations = optimizer.scalarMaxEvaluations;
    dwConfig.rollCallMaxEvaluations = optimizer.rollCallMaxEvaluations;
    dwConfig.legislatorMaxEvaluations = optimizer.legislatorMaxEvaluations;
    dwConfig.scalarLocalTrustRegion = config.scalarSearch == "local";
    dwConfig.blockSolverMode = parseBlockSolverMode(config.blockSolver);
    dwConfig.solverFallbackToCobyla = config.solverFallbackToCobyla;
    dwConfig.adaptiveOptimizerSchedule = config.adaptiveTolerances;
    dwConfig.likelihoodMode = parseNormalCDFMode(config.likelihoodEvaluator);
    dwConfig.fortranReplicationMode = config.fortranReplication;
    dwConfig.weight2UpperBound = config.w2UpperBound;
    dwConfig.betaUpperBound = config.betaUpperBound;
    dwConfig.numThreads = config.threads;
    dwConfig.minimumIterations = std::min(config.minimumIterations, config.iterations);
    dwConfig.convergenceAbsoluteTolerance = config.convergenceAbsoluteTolerance;
    dwConfig.convergenceRelativeTolerance = config.convergenceRelativeTolerance;
    dwConfig.convergencePatience = config.convergencePatience;

    // Ejecutar algoritmo
    std::cout << "Ejecutando DW-NOMINATE...\n";
    if (config.verbose)
    {
        std::cout << "============================================================\n";
    }

    DWNominate nominate(dwConfig, input);
    DWNominateResult result;

    try
    {
        result = nominate.run();
        const double d2Scale =
            applySecondDimensionIdentification(result, config.d2Identification);
        if (d2Scale != 1.0)
        {
            std::cout << "Identificacion D2 maximal-feasible aplicada: c="
                      << std::setprecision(15) << d2Scale
                      << " (likelihood invariante)\n";
        }
    }
    catch (const std::exception &e)
    {
        std::cerr << "ERROR en ejecucion: " << e.what() << "\n";
        return 1;
    }

    // Calcular tiempo transcurrido
    auto endTime = std::chrono::high_resolution_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
    double elapsedSeconds = elapsed.count() / 1000.0;

    // Resumen
    if (config.verbose)
    {
        std::cout << "============================================================\n";
    }
    double classPctMain = result.totalValidVotes > 0 ? (100.0 * result.classificationAfter / result.totalValidVotes) : 0.0;
    std::cout << "\nResultados:\n";
    std::cout << "  Log-likelihood: " << std::fixed << std::setprecision(4) << result.finalLogLikelihood << "\n";
    std::cout << "  Iteraciones:    " << result.totalIterations << "\n";
    std::cout << "  Clasificacion:  " << result.classificationAfter << "/" << result.totalValidVotes
              << " (" << std::setprecision(2) << classPctMain << "%)\n";
    std::cout << "  W1=" << std::setprecision(4) << result.weights(0)
              << ", W2=" << result.weights(1)
              << ", Beta=" << result.weights(2) << "\n";
    std::cout << "  Tiempo: " << std::setprecision(1) << elapsedSeconds << "s\n\n";

    // Exportar resultados
    std::cout << "Exportando resultados...\n";

    if (!result.temporalCoefficients.empty())
    {
        exportCoordinatesAllPeriods(
            config.outputDir + "/cpp_coordinates_all_periods.csv",
            result, config.periods);

        if (config.exportCorrected)
        {
            exportCoordinatesAllPeriodsCorrected(
                config.outputDir + "/cpp_coordinates_all_periods_corrected.csv",
                result, config.periods);
        }

        exportTemporalCoefficients(
            config.outputDir + "/cpp_temporal_coefficients.csv",
            result);
    }
    else
    {
        std::cout << "Estado evaluado sin reexportar trayectorias "
                     "(coeficientes temporales fijos no reestimados).\n";
    }

    exportBillParameters(
        config.outputDir + "/cpp_bill_parameters.csv",
        result, input.votes.getNumRollCalls());

    exportBillParametersReloadable(
        config.outputDir + "/dwnominate_bill_parameters.csv",
        result, input.rollCallCongress);

    exportSummary(
        config.outputDir + "/cpp_summary.csv",
        result, config, elapsedSeconds);

    exportConvergenceTrace(
        config.outputDir + "/cpp_convergence_trace.csv",
        result);

    if (config.exportOptimizerTrace)
    {
        exportOptimizerTrace(
            config.outputDir + "/cpp_optimizer_trace.csv",
            result);
    }

    std::cout << "\nCompletado exitosamente.\n";

    return 0;
}
