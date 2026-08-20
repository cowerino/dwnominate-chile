/**
 * @file dwnominate.cpp
 * @brief Implementacion de la clase DWNominate.
 */

#include "dwnominate.hpp"
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <cmath>
#include <algorithm>
#include <limits>
#include <chrono>
#include <set>

#ifdef _OPENMP
#include <omp.h>
#endif

// Instrumentacion de tiempo por fase
static double g_wintTimeMs = 0.0;
static double g_sigmasTimeMs = 0.0;
static double g_rcTimeMs = 0.0;
static double g_legTimeMs = 0.0;

// CONSTRUCTOR E INICIALIZACION
DWNominate::DWNominate(const DWNominateConfig &config, const DWNominateInput &input)
    : config_(config),
      votes_(input.votes),
      currentLogLikelihood_(0.0),
      lastTotalVotes_(0),
      lastClassificationAfter_(0)
{
    // call init_zdf
    initializeCDF();

    // WEIGHT(1:(NS+1)) = WEIGHTSIN
    int ns = config_.numDimensions;
    weights_ = input.initialWeights;
    if (weights_.size() == 0)
    {
        // Valores por defecto si no se proporcionan
        weights_.resize(ns + 1);
        weights_.setOnes();
        weights_(ns) = 4.925; // Beta por defecto
    }
    // WEIGHT(1)=1.000 (peso dimension 1 siempre es 1)
    weights_(0) = 1.0;

    // Cargar metadata de congresos
    loadCongressMetadata(input);

    // Cargar roll calls
    loadRollCalls(input);

    // Cargar legisladores
    loadLegislators(input);

    // Inicializar matrices de estado
    int numLegislators = static_cast<int>(legislatorCoords_.rows());
    int numRollCalls = static_cast<int>(rollCallMidpoints_.rows());

    // XBIGLOG: Log-likelihood por legislador (antes/despues)
    legislatorLogLikelihood_ = Eigen::MatrixXd::Zero(numLegislators, 2);

    // KBIGLOG: Conteos por legislador
    legislatorVoteCounts_ = Eigen::MatrixXi::Zero(numLegislators, 4);

    // XVAR: Varianzas por legislador unico
    int maxUniqueId = 0;
    for (int id : legislatorUniqueId_)
    {
        maxUniqueId = std::max(maxUniqueId, id);
    }
    legislatorVariances_ = Eigen::MatrixXd::Zero(maxUniqueId + 1, 6);

    // Polaridad de cortes por roll call
    rollCallPolarity_.resize(numRollCalls);

    log("DWNominate inicializado");
    log("  Dimensiones: " + std::to_string(ns));
    log("  Congresos: " + std::to_string(config_.firstCongress) +
        " - " + std::to_string(config_.lastCongress));
    log("  Roll calls: " + std::to_string(numRollCalls));
    log("  Legisladores: " + std::to_string(numLegislators));
}

// Inicializa la tabla CDF.
void DWNominate::initializeCDF()
{
    // NormalCDF se inicializa en su constructor con los mismos
    // parametros que init_zdf: NDEVIT=50001, XDEVIT=10000.0
    // La tabla ZDF se precomputa automaticamente.
}

// Carga metadata de congresos y calcula offsets.
void DWNominate::loadCongressMetadata(const DWNominateInput &input)
{
    int numCongresses = config_.lastCongress - config_.firstCongress + 1;
    congressInfo_.resize(numCongresses);

    int legislatorOffset = 0;
    int rollCallOffset = 0;

    for (int i = 0; i < numCongresses; ++i)
    {
        int congressIndex = config_.firstCongress + i;
        CongressInfo &info = congressInfo_[i];

        info.index = congressIndex;

        // Obtener numLegislators y numRollCalls de la metadata
        if (congressIndex < static_cast<int>(input.congressMetadata.size()))
        {
            info.numLegislators = input.congressMetadata[congressIndex].first;
            info.numRollCalls = input.congressMetadata[congressIndex].second;
        }
        else
        {
            info.numLegislators = 0;
            info.numRollCalls = 0;
        }

        // Offsets (equivalen a KTOTP, KTOTQ acumulados)
        info.legislatorOffset = legislatorOffset;
        info.rollCallOffset = rollCallOffset;

        legislatorOffset += info.numLegislators;
        rollCallOffset += info.numRollCalls;
    }
}

// Carga roll calls y determina validez.
void DWNominate::loadRollCalls(const DWNominateInput &input)
{
    // Copiar roll call congress
    rollCallCongress_ = input.rollCallCongress;

    // Copiar midpoints y spreads
    rollCallMidpoints_ = input.rollCallMidpoints;
    rollCallSpreads_ = input.rollCallSpreads;

    // Determinar validez de cada roll call
    int numRollCalls = static_cast<int>(rollCallCongress_.size());
    validRollCalls_.resize(numRollCalls);

    for (int i = 0; i < numRollCalls; ++i)
    {
        // Contar votos Si y No
        int kyes = 0;
        int kno = 0;

        size_t numLeg = votes_.getNumLegislators();
        for (size_t leg = 0; leg < numLeg; ++leg)
        {
            if (!votes_.isMissing(leg, i))
            {
                if (votes_.getVote(leg, i))
                {
                    kyes++;
                }
                else
                {
                    kno++;
                }
            }
        }

        // Calcular margen
        int krctot = kyes + kno;
        int krcmin = std::min(kyes, kno);
        double xmarg = (krctot > 0) ? static_cast<double>(krcmin) / krctot : 0.0;

        // Verificar si spread es ~0 (indica roll call NA de R cuando fixRollCalls=true)
        bool hasNonZeroSpread = false;
        for (int d = 0; d < config_.numDimensions; ++d)
        {
            if (std::abs(rollCallSpreads_(i, d)) > 1e-10)
            {
                hasNonZeroSpread = true;
                break;
            }
        }

        // Nota: RCBAD=.TRUE. significa roll call VALIDO en Fortran
        // Roll call es válido si: margen >= threshold Y spread no es cero
        validRollCalls_[i] = (xmarg >= config_.marginThreshold) && hasNonZeroSpread;
    }
}

// Carga legisladores y construye mapas de presencia.
void DWNominate::loadLegislators(const DWNominateInput &input)
{
    // Copiar datos basicos
    legislatorCongress_ = input.legislatorCongress;
    legislatorUniqueId_ = input.legislatorUniqueId;
    legislatorCoords_ = input.legislatorCoords;

    // Construir mapa de presencia (reemplaza LWHERE/KWHERE)
    int maxUniqueId = 0;
    for (int id : legislatorUniqueId_)
    {
        maxUniqueId = std::max(maxUniqueId, id);
    }
    legislatorPresence_.resize(maxUniqueId + 1);

    // Obtener dimensiones
    int numLegislators = static_cast<int>(legislatorUniqueId_.size());
    int numRollCalls = static_cast<int>(rollCallCongress_.size());

    // DETECCION DE PRESENCIA BASADA EN VOTOS
    // Para cada legislador, detectar en qué periodos tiene votos no-missing
    for (int i = 0; i < numLegislators; ++i)
    {
        int uniqueId = legislatorUniqueId_[i];

        // Inicializar si es la primera vez que vemos este ID
        if (legislatorPresence_[uniqueId].uniqueId < 0)
        {
            legislatorPresence_[uniqueId].uniqueId = uniqueId;
        }

        // Set para rastrear periodos en que participa este legislador
        std::set<int> periodsWithVotes;

        // Recorrer todos los roll calls para encontrar votos del legislador
        for (int j = 0; j < numRollCalls; ++j)
        {
            // Si el legislador tiene un voto no-missing en este roll call
            if (!votes_.isMissing(static_cast<size_t>(i), static_cast<size_t>(j)))
            {
                // Agregar el periodo de este roll call
                int period = rollCallCongress_[j];
                periodsWithVotes.insert(period);
            }
        }

        // Agregar todos los periodos detectados al mapa de presencia
        for (int period : periodsWithVotes)
        {
            // El dataIndex es el índice del legislador en el array de datos
            // (mismo para todos los periodos ya que comparten coordenadas base)
            legislatorPresence_[uniqueId].congressToDataIndex[period] = i;
        }
    }

    // Log de diagnóstico
    int totalPresence = 0;
    int multiPeriodCount = 0;
    for (int uid = 0; uid <= maxUniqueId; ++uid)
    {
        if (legislatorPresence_[uid].uniqueId >= 0)
        {
            int numPeriods = static_cast<int>(legislatorPresence_[uid].congressToDataIndex.size());
            totalPresence += numPeriods;
            if (numPeriods > 1)
            {
                multiPeriodCount++;
            }
        }
    }
    log("  Presencia detectada: " + std::to_string(totalPresence) +
        " entradas, " + std::to_string(multiPeriodCount) +
        " legisladores con multiples periodos");
}

// METODO PRINCIPAL run()
// Ejecuta el algoritmo completo.
DWNominateResult DWNominate::run()
{
    DWNominateResult result;
    int ns = config_.numDimensions;

    // Reset timers
    g_wintTimeMs = 0.0;
    g_sigmasTimeMs = 0.0;
    g_rcTimeMs = 0.0;
    g_legTimeMs = 0.0;
    optimizerTrace_.clear();

    auto iterStart = std::chrono::high_resolution_clock::now();

#ifdef _OPENMP
    omp_set_dynamic(0);
    omp_set_num_threads(std::max(1, config_.numThreads));
#endif

    // Bucle principal IHAPPY
    for (int ihappy = config_.firstIteration; ihappy <= config_.lastIteration; ++ihappy)
    {
        log("=== Iteracion global " + std::to_string(ihappy) + " ===");

        // Fase de pesos dimensionales (WINT)
        if (ns >= 2)
        {
            if (config_.fixGlobalParams)
            {
                log("[VALIDACION] W2 fijo en " + std::to_string(weights_(1)) + " (no re-estimado)");
            }
            else
            {
                log("Estimando pesos dimensionales...");
                auto phaseStart = std::chrono::high_resolution_clock::now();
                executeWeightPhase(ihappy);
                auto phaseEnd = std::chrono::high_resolution_clock::now();
                g_wintTimeMs += std::chrono::duration<double, std::milli>(phaseEnd - phaseStart).count();
            }
        }

        // Fase de beta (SIGMAS)
        if (config_.fixGlobalParams)
        {
            log("[VALIDACION] Beta fijo en " + std::to_string(weights_(2)) + " (no re-estimado)");
        }
        else
        {
            log("Estimando beta...");
            auto phaseStart = std::chrono::high_resolution_clock::now();
            executeBetaPhase(ihappy);
            auto phaseEnd = std::chrono::high_resolution_clock::now();
            g_sigmasTimeMs += std::chrono::duration<double, std::milli>(phaseEnd - phaseStart).count();
        }

        // Fase de roll calls
        if (config_.fixRollCalls)
        {
            log("[VALIDACION] Roll calls fijos (cutting planes no re-estimados)");
        }
        else
        {
            log("Estimando vectores de roll calls...");
            auto phaseStart = std::chrono::high_resolution_clock::now();
            executeRollCallPhase(ihappy);
            auto phaseEnd = std::chrono::high_resolution_clock::now();
            g_rcTimeMs += std::chrono::duration<double, std::milli>(phaseEnd - phaseStart).count();
        }

        // PLOG despues de roll calls
        currentLogLikelihood_ = computeLogLikelihood();

        // Fase de legisladores
        if (config_.fixLegislators)
        {
            log("[VALIDACION] Coordenadas de legisladores fijas (solo PLOG, sin optimizacion)");
        }
        else
        {
            log("Estimando coordenadas de legisladores...");
            auto phaseStart = std::chrono::high_resolution_clock::now();
            executeLegislatorPhase(ihappy);
            auto phaseEnd = std::chrono::high_resolution_clock::now();
            g_legTimeMs += std::chrono::duration<double, std::milli>(phaseEnd - phaseStart).count();
        }

        // PLOG despues de legisladores
        currentLogLikelihood_ = computeLogLikelihood();

        result.totalIterations = ihappy;
        result.convergenceTrace.push_back({
            ihappy,
            currentLogLikelihood_,
            ns >= 2 ? weights_(1) : 1.0,
            weights_(weights_.size() - 1)});

        // Reporte de tiempos por iteración
        auto iterNow = std::chrono::high_resolution_clock::now();
        double elapsedSec = std::chrono::duration<double>(iterNow - iterStart).count();
        std::cout << "[TIMING iter " << ihappy << "] "
                  << "WINT=" << (g_wintTimeMs / 1000.0) << "s, "
                  << "SIGMAS=" << (g_sigmasTimeMs / 1000.0) << "s, "
                  << "RC=" << (g_rcTimeMs / 1000.0) << "s, "
                  << "LEG=" << (g_legTimeMs / 1000.0) << "s, "
                  << "LL=" << currentLogLikelihood_ << ", "
                  << "Total=" << elapsedSec << "s\n";
    }
    // Fin bucle 9999

    // Reporte final de tiempos
    std::cout << "\n========== RESUMEN DE TIEMPOS ==========\n";
    std::cout << "  WINT (pesos):      " << (g_wintTimeMs / 1000.0) << " segundos\n";
    std::cout << "  SIGMAS (beta):     " << (g_sigmasTimeMs / 1000.0) << " segundos\n";
    std::cout << "  RC (roll calls):   " << (g_rcTimeMs / 1000.0) << " segundos\n";
    std::cout << "  LEG (legisladores):" << (g_legTimeMs / 1000.0) << " segundos\n";
    double totalTime = (g_wintTimeMs + g_sigmasTimeMs + g_rcTimeMs + g_legTimeMs) / 1000.0;
    std::cout << "  TOTAL FASES:       " << totalTime << " segundos\n";
    std::cout << "==========================================\n\n";

    // Preparar resultados
    result.legislatorCoords = legislatorCoords_;
    result.rollCallMidpoints = rollCallMidpoints_;
    result.rollCallSpreads = rollCallSpreads_;
    result.weights = weights_;
    result.finalLogLikelihood = currentLogLikelihood_;
    result.finalStats = globalStats_;
    result.optimizerTrace = optimizerTrace_;

    // Asignar estadisticas de clasificacion (correccion bug reporte)
    result.totalValidVotes = lastTotalVotes_;
    result.classificationAfter = lastClassificationAfter_;

    // Recopilar estadisticas por legislador
    int numLegislators = static_cast<int>(legislatorCoords_.rows());
    result.legislatorStats.resize(numLegislators);

    for (int i = 0; i < numLegislators; ++i)
    {
        LegislatorStats &stats = result.legislatorStats[i];

        stats.logLikelihoodBefore = legislatorLogLikelihood_(i, 0);
        stats.logLikelihoodAfter = legislatorLogLikelihood_(i, 1);
        stats.voteCountBefore = legislatorVoteCounts_(i, 0);
        stats.voteCountAfter = legislatorVoteCounts_(i, 1);
        stats.yesCountBefore = legislatorVoteCounts_(i, 2);
        stats.yesCountAfter = legislatorVoteCounts_(i, 3);

        // GMP = exp(LL / N)
        if (stats.voteCountBefore > 0)
        {
            stats.gmpBefore = std::exp(stats.logLikelihoodBefore /
                                       stats.voteCountBefore);
        }
        if (stats.voteCountAfter > 0)
        {
            stats.gmpAfter = std::exp(stats.logLikelihoodAfter /
                                      stats.voteCountAfter);
        }

        // Varianzas (si NS=2)
        if (ns == 2)
        {
            int uniqueId = legislatorUniqueId_[i];
            double tt = (legislatorCoords_.cols() > ns)
                            ? legislatorCoords_(i, ns)
                            : 0.0;

            // VARX1=XVAR(ID1(I),1)+TT*TT*XVAR(ID1(I),2)+2.0*TT*XVAR(ID1(I),3)
            stats.varianceX1 = legislatorVariances_(uniqueId, 0) + tt * tt * legislatorVariances_(uniqueId, 1) + 2.0 * tt * legislatorVariances_(uniqueId, 2);

            // VARX2=XVAR(ID1(I),4)+TT*TT*XVAR(ID1(I),5)+2.0*TT*XVAR(ID1(I),6)
            stats.varianceX2 = legislatorVariances_(uniqueId, 3) + tt * tt * legislatorVariances_(uniqueId, 4) + 2.0 * tt * legislatorVariances_(uniqueId, 5);

            stats.stdDevX1 = std::sqrt(std::abs(stats.varianceX1));
            stats.stdDevX2 = std::sqrt(std::abs(stats.varianceX2));
        }
    }

    // SOPORTE MULTI-PERIODO
    // Copiar coeficientes temporales al resultado
    result.temporalCoefficients = temporalCoefficients_;

    // Construir lista de IDs unicos de legisladores procesados
    result.legislatorUniqueIds.clear();
    for (const auto &pair : temporalCoefficients_)
    {
        result.legislatorUniqueIds.push_back(pair.first);
    }
    std::sort(result.legislatorUniqueIds.begin(), result.legislatorUniqueIds.end());

    // Guardar configuracion del modelo para reconstruccion
    result.numPeriods = config_.lastCongress - config_.firstCongress + 1;
    result.temporalModel = config_.temporalModel;
    result.numDimensions = ns;

    return result;
}

// FASE DE PESOS (WINT)
/**
 * Esta fase solo se ejecuta si NS >= 2.
 * Optimiza WEIGHT(2:NS) manteniendo WEIGHT(1)=1.0.
 */
void DWNominate::executeWeightPhase(int iteration)
{
    int ns = config_.numDimensions;

    // Verificacion de seguridad (ya se verifica en run(), pero doble check)
    if (ns < 2)
    {
        return;
    }

    // Construir vector de parametros de roll calls
    std::vector<RollCallParameters> rollCallParams = buildRollCallParams();

    // Crear contexto de likelihood
    // LikelihoodContext toma weights_ por referencia, permitiendo que
    // optimizeWeight2 modifique weights_ directamente
    LikelihoodContext context(
        legislatorCoords_,
        rollCallParams,
        votes_,
        weights_,
        normalCDF_,
        validRollCalls_);

    // Configuracion del problema escalar acotado para W2.
    WeightOptimizerConfig config = wintConfig();
    if (!config_.scalarLocalTrustRegion)
    {
        config.localRadius = 0.0;
    }
    config.verbose = config_.verbose;
    config.relativeXTolerance = config_.optimizerRelativeXTolerance;
    config.relativeFTolerance = config_.optimizerRelativeFTolerance;
    config.maxEvaluations = config_.scalarMaxEvaluations;
    if (config_.adaptiveOptimizerSchedule &&
        iteration < config_.lastIteration)
    {
        const bool early = iteration <=
            config_.firstIteration +
                (config_.lastIteration - config_.firstIteration) / 2;
        config.relativeXTolerance = std::max(
            config.relativeXTolerance, early ? 1e-4 : 1e-6);
        config.relativeFTolerance = std::max(
            config.relativeFTolerance, early ? 1e-6 : 1e-8);
        config.maxEvaluations = std::max(
            20,
            static_cast<int>(std::ceil(
                static_cast<double>(config.maxEvaluations) *
                (early ? 0.25 : 0.5))));
    }

    // Ejecutar optimizacion
    WeightOptimizationResult result = optimizeWeight2(context, config);

    // weights_ ya fue modificado in-place por optimizeWeight2 a traves del context
    // Actualizar log-likelihood actual
    currentLogLikelihood_ = result.logLikelihood;

    if (config_.verbose)
    {
        log("  [WINT] W2: " + std::to_string(result.initialValue) +
            " -> " + std::to_string(result.value) +
            ", LL: " + std::to_string(result.logLikelihood) +
            ", iters: " + std::to_string(result.iterations));
    }
}

// FASE DE BETA (SIGMAS)

/**
 * Ejecuta fase de optimizacion de beta (SIGMAS).
 * Optimiza WEIGHT(NS+1) = beta mediante NLopt/BOBYQA.
 */
void DWNominate::executeBetaPhase(int iteration)
{
    // Construir vector de parametros de roll calls
    std::vector<RollCallParameters> rollCallParams = buildRollCallParams();

    // Crear contexto de likelihood
    // LikelihoodContext toma weights_ por referencia, permitiendo que
    // optimizeBeta modifique weights_ directamente
    LikelihoodContext context(
        legislatorCoords_,
        rollCallParams,
        votes_,
        weights_,
        normalCDF_,
        validRollCalls_);

    // Configuracion del problema escalar acotado para beta.
    BetaOptimizerConfig config = sigmasConfig();
    if (!config_.scalarLocalTrustRegion)
    {
        config.localRadius = 0.0;
    }
    config.verbose = config_.verbose;
    config.relativeXTolerance = config_.optimizerRelativeXTolerance;
    config.relativeFTolerance = config_.optimizerRelativeFTolerance;
    config.maxEvaluations = config_.scalarMaxEvaluations;
    if (config_.adaptiveOptimizerSchedule &&
        iteration < config_.lastIteration)
    {
        const bool early = iteration <=
            config_.firstIteration +
                (config_.lastIteration - config_.firstIteration) / 2;
        config.relativeXTolerance = std::max(
            config.relativeXTolerance, early ? 1e-4 : 1e-6);
        config.relativeFTolerance = std::max(
            config.relativeFTolerance, early ? 1e-6 : 1e-8);
        config.maxEvaluations = std::max(
            20,
            static_cast<int>(std::ceil(
                static_cast<double>(config.maxEvaluations) *
                (early ? 0.25 : 0.5))));
    }

    // Ejecutar optimizacion
    BetaOptimizationResult result = optimizeBeta(context, config);

    // weights_ ya fue modificado in-place por optimizeBeta a traves del context
    // Actualizar log-likelihood actual
    currentLogLikelihood_ = result.logLikelihood;

    if (config_.verbose)
    {
        log("  [SIGMAS] Beta: " + std::to_string(result.initialValue) +
            " -> " + std::to_string(result.value) +
            ", LL: " + std::to_string(result.logLikelihood) +
            ", iters: " + std::to_string(result.iterations));
    }
}

// FASE DE ROLL CALLS
RollCallOptimizerConfig DWNominate::makeRollCallOptimizerConfig(
    int iteration) const
{
    RollCallOptimizerConfig output;
    output.relativeXTolerance = config_.optimizerRelativeXTolerance;
    output.relativeFTolerance = config_.optimizerRelativeFTolerance;
    output.constraintTolerance = config_.optimizerConstraintTolerance;
    output.maxEvaluations = config_.rollCallMaxEvaluations;
    output.algorithm = resolveBlockAlgorithm(
        config_.blockSolverMode, iteration, config_.lastIteration);
    output.fallbackToCobyla = config_.solverFallbackToCobyla;

    if (!config_.adaptiveOptimizerSchedule ||
        iteration >= config_.lastIteration)
    {
        return output;
    }

    const bool early = iteration <=
        config_.firstIteration +
            (config_.lastIteration - config_.firstIteration) / 2;
    output.relativeXTolerance = std::max(
        output.relativeXTolerance, early ? 1e-4 : 1e-6);
    output.relativeFTolerance = std::max(
        output.relativeFTolerance, early ? 1e-6 : 1e-8);
    output.constraintTolerance = std::max(
        output.constraintTolerance, early ? 1e-7 : 1e-9);
    output.maxEvaluations = std::max(
        30,
        static_cast<int>(std::ceil(
            static_cast<double>(output.maxEvaluations) *
            (early ? 0.25 : 0.5))));
    return output;
}

LegislatorOptimizerConfig DWNominate::makeLegislatorOptimizerConfig(
    int iteration) const
{
    LegislatorOptimizerConfig output;
    output.relativeXTolerance = config_.optimizerRelativeXTolerance;
    output.relativeFTolerance = config_.optimizerRelativeFTolerance;
    output.constraintTolerance = config_.optimizerConstraintTolerance;
    output.maxEvaluations = config_.legislatorMaxEvaluations;
    output.algorithm = resolveBlockAlgorithm(
        config_.blockSolverMode, iteration, config_.lastIteration);
    output.fallbackToCobyla = config_.solverFallbackToCobyla;

    if (!config_.adaptiveOptimizerSchedule ||
        iteration >= config_.lastIteration)
    {
        return output;
    }

    const bool early = iteration <=
        config_.firstIteration +
            (config_.lastIteration - config_.firstIteration) / 2;
    output.relativeXTolerance = std::max(
        output.relativeXTolerance, early ? 1e-4 : 1e-6);
    output.relativeFTolerance = std::max(
        output.relativeFTolerance, early ? 1e-6 : 1e-8);
    output.constraintTolerance = std::max(
        output.constraintTolerance, early ? 1e-7 : 1e-9);
    output.maxEvaluations = std::max(
        40,
        static_cast<int>(std::ceil(
            static_cast<double>(output.maxEvaluations) *
            (early ? 0.25 : 0.5))));
    return output;
}

void DWNominate::executeRollCallPhase(int iteration)
{
    int classificationBefore = 0; // LASSB4
    int classificationAfter = 0;  // LASSAF
    int totalVotes = 0;           // LATOT

    // Estructura para trabajo paralelo
    struct RollCallWork
    {
        int congressIndex;
        int rollCallLocalIndex;
        int globalRollCallIndex;
        int legislatorOffset;
    };

    // Construir lista de trabajos (aplanar loop anidado)
    std::vector<RollCallWork> workList;
    for (const CongressInfo &congress : congressInfo_)
    {
        int congressIndex = congress.index;

        // Verificar que el congreso esta en el rango
        if (congressIndex < config_.firstCongress ||
            congressIndex > config_.lastCongress)
        {
            continue;
        }

        int legislatorOffset = congress.legislatorOffset;
        int rollCallOffset = congress.rollCallOffset;
        int numRollCalls = congress.numRollCalls;

        for (int j = 0; j < numRollCalls; ++j)
        {
            int globalRollCallIndex = rollCallOffset + j;
            if (globalRollCallIndex >= static_cast<int>(validRollCalls_.size()))
            {
                continue;
            }
            workList.push_back({congressIndex, j, globalRollCallIndex, legislatorOffset});
        }
    }

    const int numWork = static_cast<int>(workList.size());
    std::vector<BlockOptimizationTraceEntry> phaseTrace(
        static_cast<std::size_t>(numWork));

// Procesar roll calls en paralelo con OpenMP
#ifdef _OPENMP
#pragma omp parallel for if(config_.numThreads > 1) num_threads(config_.numThreads) schedule(static) reduction(+ : totalVotes, classificationBefore, classificationAfter)
#endif
    for (int w = 0; w < numWork; ++w)
    {
        const RollCallWork &work = workList[w];
        int localTotalVotes = 0;
        int localClassBefore = 0;
        int localClassAfter = 0;

        processRollCallParallel(
            work.congressIndex,
            work.rollCallLocalIndex,
            work.globalRollCallIndex,
            iteration,
            work.legislatorOffset,
            localClassBefore,
            localClassAfter,
            localTotalVotes,
            phaseTrace[static_cast<std::size_t>(w)]);

        totalVotes += localTotalVotes;
        classificationBefore += localClassBefore;
        classificationAfter += localClassAfter;
    }

    for (const auto &entry : phaseTrace)
    {
        if (!entry.block.empty())
        {
            optimizerTrace_.push_back(entry);
        }
    }

    // Guardar estadisticas en miembros de clase para uso posterior
    lastTotalVotes_ = totalVotes;
    lastClassificationAfter_ = classificationAfter;

    // Calcular estadisticas
    if (totalVotes > 0)
    {
        double yclass = static_cast<double>(classificationAfter) / totalVotes;
        log("  Clasificacion: " + std::to_string(classificationAfter) +
            "/" + std::to_string(totalVotes) +
            " (" + std::to_string(yclass * 100.0) + "%)");
    }
}

// Procesa un roll call individual.
void DWNominate::processRollCall(
    int congressIndex,
    int rollCallLocalIndex,
    int globalRollCallIndex,
    int iteration,
    int legislatorOffset,
    int &classificationBefore,
    int &classificationAfter,
    int &totalVotes)
{
    int ns = config_.numDimensions;

    // Preparar datos del roll call
    Eigen::MatrixXd coords;
    std::vector<int> voteCodes;
    std::vector<int> sortedIndices;
    int kyes = 0;
    int kno = 0;

    int numVoters = prepareRollCallData(
        congressIndex,
        rollCallLocalIndex,
        legislatorOffset,
        coords,
        voteCodes,
        sortedIndices,
        kyes,
        kno);

    if (numVoters == 0)
    {
        return;
    }

    // Verificar margen
    if (!isRollCallValid(kyes, kno))
    {
        for (int k = 0; k < ns; ++k)
        {
            rollCallMidpoints_(globalRollCallIndex, k) = 0.0;
            rollCallSpreads_(globalRollCallIndex, k) = 0.0;
        }
        return;
    }

    // Normalizar midpoint a esfera unitaria
    Eigen::VectorXd midpoint = rollCallMidpoints_.row(globalRollCallIndex).transpose();
    normalizeToUnitSphere(midpoint);
    rollCallMidpoints_.row(globalRollCallIndex) = midpoint.transpose();

    // Variables temporales para el roll call actual
    // Fortran: OLDZ, OLDD
    Eigen::VectorXd oldz = rollCallMidpoints_.row(globalRollCallIndex).transpose();
    Eigen::VectorXd oldd = rollCallSpreads_.row(globalRollCallIndex).transpose();
    CuttingPolarity polarity;

    // Obtener clasificacion inicial
    if (ns == 1)
    {
        // NS=1: Usar JAN11PT
        std::vector<double> projections(numVoters);
        std::vector<int> sortedVoteCodes(numVoters);
        for (int i = 0; i < numVoters; ++i)
        {
            projections[i] = coords(sortedIndices[i], 0);
            sortedVoteCodes[i] = voteCodes[sortedIndices[i]];
        }

        double cuttingPoint = 0.0;
        double spread = 0.5;
        double accuracy1 = 0.0;
        double accuracy2 = 0.0;

        applyJan11pt(numVoters, projections, sortedVoteCodes,
                     cuttingPoint, spread, polarity,
                     accuracy1, accuracy2);

        // Primera iteracion: actualizar OLDZ, OLDD desde resultados
        if (iteration == config_.firstIteration)
        {
            // Normalizar punto de corte a [-1, 1]
            if (std::abs(cuttingPoint) > 1.0)
            {
                cuttingPoint = cuttingPoint / std::abs(cuttingPoint);
            }
            oldz(0) = cuttingPoint;
            oldd(0) = spread;
        }
    }
    else
    {
        // NS>1: Usar CUTPLANE
        // IMPORTANTE: Solo inicializar desde CUTPLANE en la primera iteracion
        // En Fortran: IF(IHAPPY.EQ.1) - solo primera iteracion global
        // En iteraciones posteriores, CUTPLANE solo actualiza polarity,
        // pero OLDZ/OLDD se mantienen de la iteracion anterior

        // Verificar si ya tenemos valores inicializados (de R o anterior)
        bool hasPreloadedValues = oldz.squaredNorm() > 1e-10;

        applyCutplane(numVoters, coords, voteCodes, oldz, oldd, polarity);

        // Solo actualizar midpoint/spread desde CUTPLANE en primera iteracion
        // Y SOLO si no había valores pre-cargados (e.g., de R)
        if (iteration != config_.firstIteration || hasPreloadedValues)
        {
            // Restaurar valores previos - CUTPLANE solo sirvio para polarity
            oldz = rollCallMidpoints_.row(globalRollCallIndex).transpose();
            oldd = rollCallSpreads_.row(globalRollCallIndex).transpose();
        }
    }

    // Guardar polaridad
    rollCallPolarity_[globalRollCallIndex] = polarity;

    // PROLLC2 + RCINT2: Optimizar parametros del roll call
    // Configuracion del optimizador de roll calls
    RollCallOptimizerConfig rcConfig =
        makeRollCallOptimizerConfig(iteration);

    // Ejecutar optimizacion
    // Fortran: CALL RCINT2(...)
    RollCallOptimizationResult rcResult = optimizeRollCall(
        legislatorCoords_,
        globalRollCallIndex,
        oldz,
        oldd,
        votes_,
        weights_,
        normalCDF_,
        rcConfig);

    // Actualizar parametros optimizados en el estado interno
    rollCallMidpoints_.row(globalRollCallIndex) = rcResult.midpoint.transpose();
    rollCallSpreads_.row(globalRollCallIndex) = rcResult.spread.transpose();

    // Actualizar contadores de clasificacion
    totalVotes += rcResult.totalVotes;
    classificationBefore += rcResult.totalVotes; // Aproximacion para antes
    classificationAfter += rcResult.correctClassified;
}

/**
 * Procesa un roll call individual (version thread-safe para OpenMP).
 * Escribe resultados en variables locales y en filas independientes de matrices.
 */
void DWNominate::processRollCallParallel(
    int congressIndex,
    int rollCallLocalIndex,
    int globalRollCallIndex,
    int iteration,
    int legislatorOffset,
    int &localClassificationBefore,
    int &localClassificationAfter,
    int &localTotalVotes,
    BlockOptimizationTraceEntry &trace)
{
    int ns = config_.numDimensions;
    localTotalVotes = 0;
    localClassificationBefore = 0;
    localClassificationAfter = 0;
    trace.iteration = iteration;
    trace.block = "rollcall";
    trace.itemIndex = globalRollCallIndex;

    // Preparar datos del roll call (thread-safe: solo lecturas)
    Eigen::MatrixXd coords;
    std::vector<int> voteCodes;
    std::vector<int> sortedIndices;
    int kyes = 0;
    int kno = 0;

    int numVoters = prepareRollCallData(
        congressIndex,
        rollCallLocalIndex,
        legislatorOffset,
        coords,
        voteCodes,
        sortedIndices,
        kyes,
        kno);

    if (numVoters == 0)
    {
        return;
    }

    // Verificar margen
    if (!isRollCallValid(kyes, kno))
    {
        for (int k = 0; k < ns; ++k)
        {
            rollCallMidpoints_(globalRollCallIndex, k) = 0.0;
            rollCallSpreads_(globalRollCallIndex, k) = 0.0;
        }
        return;
    }

    // Leer y hacer factible el midpoint actual antes de cualquier evaluación.
    // Esto corresponde al control previo de ZMID del llamador Fortran.
    Eigen::VectorXd midpoint = rollCallMidpoints_.row(globalRollCallIndex).transpose();
    normalizeToUnitSphere(midpoint);

    // Variables temporales para el roll call actual
    Eigen::VectorXd oldz = midpoint;
    Eigen::VectorXd oldd = rollCallSpreads_.row(globalRollCallIndex).transpose();
    CuttingPolarity polarity;

    // Obtener clasificacion inicial
    if (ns == 1)
    {
        // NS=1: Usar JAN11PT
        std::vector<double> projections(numVoters);
        std::vector<int> sortedVoteCodes(numVoters);
        for (int i = 0; i < numVoters; ++i)
        {
            projections[i] = coords(sortedIndices[i], 0);
            sortedVoteCodes[i] = voteCodes[sortedIndices[i]];
        }

        double cuttingPoint = 0.0;
        double spread = 0.5;
        double accuracy1 = 0.0;
        double accuracy2 = 0.0;

        applyJan11pt(numVoters, projections, sortedVoteCodes,
                     cuttingPoint, spread, polarity,
                     accuracy1, accuracy2);

        // Primera iteracion: actualizar OLDZ, OLDD desde resultados
        if (iteration == config_.firstIteration)
        {
            if (std::abs(cuttingPoint) > 1.0)
            {
                cuttingPoint = cuttingPoint / std::abs(cuttingPoint);
            }
            oldz(0) = cuttingPoint;
            oldd(0) = spread;
        }
    }
    else
    {
        // NS>1: Usar CUTPLANE
        // IMPORTANTE: Solo inicializar desde CUTPLANE en la primera iteracion
        // En Fortran: IF(IHAPPY.EQ.1) - solo primera iteracion global

        // Verificar si ya tenemos valores inicializados (de R o anterior)
        bool hasPreloadedValues = oldz.squaredNorm() > 1e-10;

        applyCutplane(numVoters, coords, voteCodes, oldz, oldd, polarity);

        // Solo actualizar midpoint/spread desde CUTPLANE en primera iteracion
        // Y SOLO si no había valores pre-cargados (e.g., de R)
        if (iteration != config_.firstIteration || hasPreloadedValues)
        {
            // Restaurar valores previos - CUTPLANE solo sirvio para polarity
            oldz = midpoint;
            oldd = rollCallSpreads_.row(globalRollCallIndex).transpose();
        }
    }

    // Guardar polaridad (thread-safe: cada thread escribe en indice diferente)
    rollCallPolarity_[globalRollCallIndex] = polarity;

    // Configuracion del optimizador
    RollCallOptimizerConfig rcConfig =
        makeRollCallOptimizerConfig(iteration);

    // Ejecutar optimizacion (thread-safe: solo lee datos compartidos)
    RollCallOptimizationResult rcResult = optimizeRollCall(
        legislatorCoords_,
        globalRollCallIndex,
        oldz,
        oldd,
        votes_,
        weights_,
        normalCDF_,
        rcConfig);

    // Actualizar parametros (thread-safe: cada thread escribe en fila diferente)
    rollCallMidpoints_.row(globalRollCallIndex) = rcResult.midpoint.transpose();
    rollCallSpreads_.row(globalRollCallIndex) = rcResult.spread.transpose();

    // Retornar contadores locales para reduccion
    localTotalVotes = rcResult.totalVotes;
    localClassificationBefore = rcResult.totalVotes;
    localClassificationAfter = rcResult.correctClassified;
    trace.objectiveEvaluations = rcResult.totalIterations;
    trace.optimizerStatus = rcResult.optimizerStatus;
    trace.initialLogLikelihood = rcResult.initialLogLikelihood;
    trace.finalLogLikelihood = rcResult.logLikelihood;
    trace.improvement =
        rcResult.logLikelihood - rcResult.initialLogLikelihood;
    trace.elapsedMilliseconds = rcResult.elapsedMilliseconds;
    trace.algorithm = toString(rcResult.algorithmUsed);
    trace.fallbackUsed = rcResult.fallbackUsed;
}

// Prepara datos para un roll call.
int DWNominate::prepareRollCallData(
    int congressIndex,
    int rollCallLocalIndex,
    int legislatorOffset,
    Eigen::MatrixXd &coords,
    std::vector<int> &voteCodes,
    std::vector<int> &sortedIndices,
    int &yesCount,
    int &noCount)
{
    int ns = config_.numDimensions;
    yesCount = 0;
    noCount = 0;

    // Encontrar el congreso en congressInfo_
    const CongressInfo *congressPtr = nullptr;
    for (const auto &c : congressInfo_)
    {
        if (c.index == congressIndex)
        {
            congressPtr = &c;
            break;
        }
    }

    if (!congressPtr)
    {
        return 0;
    }

    int numLegislatorsInCongress = congressPtr->numLegislators;
    int globalRollCall = congressPtr->rollCallOffset + rollCallLocalIndex;

    if (numLegislatorsInCongress <= 0 || legislatorOffset < 0 ||
        legislatorOffset + numLegislatorsInCongress > legislatorCoords_.rows() ||
        legislatorOffset + numLegislatorsInCongress >
            static_cast<int>(votes_.getNumLegislators()) ||
        globalRollCall < 0 ||
        globalRollCall >= static_cast<int>(votes_.getNumRollCalls()))
    {
        return 0;
    }

    // CUTPLANE del Fortran recibe los NPC legisladores, incluidos los ausentes.
    // Los ausentes no cuentan para el margen ni para los errores, pero sus puntos
    // se proyectan sobre el plano y participan en la geometria de SEARCH.
    const int numLegislators = numLegislatorsInCongress;
    coords.resize(numLegislators, ns);
    voteCodes.assign(numLegislators, VoteCode::MISSING);
    std::vector<double> projections(numLegislators);

    for (int i = 0; i < numLegislators; ++i)
    {
        const int globalLeg = legislatorOffset + i;

        for (int k = 0; k < ns; ++k)
        {
            coords(i, k) = legislatorCoords_(globalLeg, k);
        }

        // LDATA: 1=Si, 6=No, 0/9=ausente. Mantener cada codigo alineado
        // con la misma fila de coords; CUTPLANE ordena ambas cosas internamente.
        if (!votes_.isMissing(globalLeg, globalRollCall))
        {
            if (votes_.getVote(globalLeg, globalRollCall))
            {
                voteCodes[i] = VoteCode::YES;
                ++yesCount;
            }
            else
            {
                voteCodes[i] = VoteCode::NO;
                ++noCount;
            }
        }

        projections[i] = coords(i, 0); // Primera dimension para ordenar
    }

    // Fortran skips the roll-call phase entirely when KRCTOT=0. Returning zero
    // here preserves the initialized bill parameters instead of treating an
    // all-missing column as a failed-margin roll call and overwriting it.
    if (yesCount + noCount == 0)
    {
        return 0;
    }

    // Ordenar por primera dimension
    std::vector<size_t> rawIndices = argsort(projections);
    sortedIndices.resize(rawIndices.size());
    for (size_t i = 0; i < rawIndices.size(); ++i)
    {
        sortedIndices[i] = static_cast<int>(rawIndices[i]);
    }

    return numLegislators;
}

// Aplica JAN11PT para NS=1.
void DWNominate::applyJan11pt(
    int /*numVoters*/,
    const std::vector<double> &projections,
    const std::vector<int> &voteCodes,
    double &cuttingPoint,
    double &spread,
    CuttingPolarity &polarity,
    double &accuracy1,
    double &accuracy2)
{
    // Probar ambas polaridades
    CuttingPolarity pol1(VoteCode::YES, VoteCode::NO);
    CuttingPolarity pol2(VoteCode::NO, VoteCode::YES);

    // Usar findCuttingPoint1DFixedPolarity de cutting_point.hpp
    CuttingPointResult result1 = findCuttingPoint1DFixedPolarity(
        projections, voteCodes, pol1);
    CuttingPointResult result2 = findCuttingPoint1DFixedPolarity(
        projections, voteCodes, pol2);

    accuracy1 = result1.counts.accuracy() * 100.0;
    accuracy2 = result2.counts.accuracy() * 100.0;

    // Seleccionar la mejor polaridad
    if (accuracy1 >= accuracy2)
    {
        polarity = pol1;
        cuttingPoint = result1.cuttingPoint;
        spread = 0.5; // Valor por defecto
    }
    else
    {
        polarity = pol2;
        cuttingPoint = result2.cuttingPoint;
        spread = -0.5;
    }
}

// Aplica CUTPLANE para NS>1.
void DWNominate::applyCutplane(
    int /*numVoters*/,
    const Eigen::MatrixXd &coords,
    const std::vector<int> &voteCodes,
    Eigen::VectorXd &midpoint,
    Eigen::VectorXd &spread,
    CuttingPolarity &polarity)
{
    int ns = config_.numDimensions;

    // Vector normal inicial
    Eigen::VectorXd normalVector = Eigen::VectorXd::Zero(ns);
    normalVector(0) = 1.0;

    // Llamar a classifyRollCall de cutting_plane.hpp
    bool searchEnabled = true; // IFIXX=1
    RollCallClassification result = classifyRollCall(
        coords, normalVector, voteCodes, searchEnabled);

    // Ajustar orientacion del vector normal
    Eigen::VectorXd zvec = normalVector;
    double ws = result.cuttingPoint;

    if (zvec(0) < 0.0)
    {
        zvec = -zvec;
        ws = -ws;
        polarity = CuttingPolarity(result.polarity.highSideVote,
                                   result.polarity.lowSideVote);
    }
    else
    {
        polarity = result.polarity;
    }

    // Calcular midpoint
    for (int k = 0; k < ns; ++k)
    {
        midpoint(k) = ws * zvec(k);
    }
    // El Fortran proyecta OLDZ inmediatamente después de regresar de CUTPLANE.
    // La restricción pertenece al llamador, no a la subrutina CUTPLANE.
    normalizeToUnitSphere(midpoint);

    // Calcular spread
    for (int k = 0; k < ns; ++k)
    {
        if (polarity.lowSideVote == VoteCode::YES)
        {
            spread(k) = 0.5 * zvec(k);
        }
        else
        {
            spread(k) = -0.5 * zvec(k);
        }
    }
}

// FASE DE LEGISLADORES
void DWNominate::executeLegislatorPhase(int iteration)
{
    // PASO 1: Recolectar legisladores válidos (secuencial)
    // 1. Pre-inicializar temporalCoefficients_ (std::map no es thread-safe)
    // 2. Crear un vector para iterar con OpenMP (requiere random access)

    std::vector<int> validLegislatorIds;
    validLegislatorIds.reserve(legislatorPresence_.size());

    for (int uniqueId = 0; uniqueId < static_cast<int>(legislatorPresence_.size());
         ++uniqueId)
    {
        const LegislatorPresence &presence = legislatorPresence_[uniqueId];

        // Verificar si este legislador tiene presencia en algun congreso
        if (presence.uniqueId < 0)
        {
            continue;
        }

        // Contar congresos en el rango
        int congressCount = 0;
        for (const auto &pair : presence.congressToDataIndex)
        {
            int congress = pair.first;
            if (congress >= config_.firstCongress &&
                congress <= config_.lastCongress)
            {
                congressCount++;
            }
        }

        if (congressCount == 0)
        {
            continue;
        }

        validLegislatorIds.push_back(uniqueId);

        // Pre-inicializar entrada en temporalCoefficients_ para evitar
        // reallocaciones concurrentes en std::map (no es thread-safe)
        temporalCoefficients_[uniqueId] = Eigen::MatrixXd();
    }

    const int numValidLegislators = static_cast<int>(validLegislatorIds.size());
    std::vector<BlockOptimizationTraceEntry> phaseTrace(
        static_cast<std::size_t>(numValidLegislators));

    // PASO 2: Procesar legisladores en paralelo
    // Cada legislador es independiente:
    // - Lee de: legislatorCoords_, rollCallMidpoints_, rollCallSpreads_,
    //           votes_, validRollCalls_, weights_, normalCDF_
    // - Escribe a posiciones únicas en: legislatorCoords_,
    //           temporalCoefficients_, legislatorVariances_,
    //           legislatorLogLikelihood_, legislatorVoteCounts_

#ifdef _OPENMP
#pragma omp parallel for if(config_.numThreads > 1) num_threads(config_.numThreads) schedule(static)
#endif
    for (int i = 0; i < numValidLegislators; ++i)
    {
        int uniqueId = validLegislatorIds[i];
        const LegislatorPresence &presence = legislatorPresence_[uniqueId];

        // Procesar legislador (cada uno escribe a posiciones únicas)
        phaseTrace[static_cast<std::size_t>(i)] =
            processLegislator(uniqueId, presence, iteration);
    }
    // Fin loop paralelo

    for (const auto &entry : phaseTrace)
    {
        optimizerTrace_.push_back(entry);
    }

    log("  Legisladores unicos procesados: " + std::to_string(numValidLegislators));
}

// Procesa un legislador unico.
BlockOptimizationTraceEntry DWNominate::processLegislator(
    int uniqueId,
    const LegislatorPresence &presence,
    int iteration)
{
    int ns = config_.numDimensions;

    // Construir LegislatorPeriodInfo desde presence
    LegislatorPeriodInfo periodInfo = buildLegislatorPeriodInfo(uniqueId, presence);

    // Determinar modelo temporal basado en numero de congresos
    int congressCount = presence.getNumCongresses();
    TemporalModel maxModel = TemporalModel::Constant;
    if (config_.temporalModel >= 1 && congressCount >= 5)
    {
        maxModel = TemporalModel::Linear;
    }
    if (config_.temporalModel >= 2 && congressCount >= 6)
    {
        maxModel = TemporalModel::Quadratic;
    }
    if (config_.temporalModel >= 3 && congressCount >= 7)
    {
        maxModel = TemporalModel::Cubic;
    }

    // El solver de bloque maximiza conjuntamente los coeficientes activos y
    // declara la restricción del intercepto como desigualdad no lineal.
    LegislatorOptimizerConfig legConfig =
        makeLegislatorOptimizerConfig(iteration);

    // Ejecutar optimizacion
    LegislatorOptimizationResult legResult = optimizeLegislator(
        uniqueId,
        periodInfo,
        legislatorCoords_,
        rollCallMidpoints_,
        rollCallSpreads_,
        votes_,
        validRollCalls_,
        weights_,
        normalCDF_,
        maxModel,
        config_.firstCongress,
        config_.lastCongress,
        legConfig);

    // Reconstruir coordenadas en legislatorCoords_ desde coeficientes optimizados
    reconstructLegislatorCoords(presence, legResult.coefficients);

    // Guardar coeficientes temporales para reconstruccion posterior por periodo.
    //
    // REQ-003 fix (2026-06-01): zero out Legendre coefficients ABOVE the active
    // temporal model. The optimizer-loop in optimize_legislators.cpp only
    // touches coefficient slots 0..maxModel; for model<3 the higher-order
    // slots retain whatever value computeInitialBetasForDimension produced
    // from the initial OLS (which fits up to cubic when kk >= 7). That value
    // is then summed by getCoordinatesAtPeriod (dwnominate.hpp:305) and
    // reconstructLegislatorCoords during output evaluation, producing a
    // cubic/quadratic distortion the model never optimized for.
    //
    // Mirrors Fortran PROX legacy_2004_DW-NOMINATE.FOR:1592-1622 exactly:
    // NMODEL=2 sums XBETA(1,2,3) only; XBETA(4,*) (cubic) is unused.
    Eigen::MatrixXd betaToStore = legResult.coefficients.beta;
    for (int k = 0; k < ns; ++k)
    {
        if (config_.temporalModel < 1) betaToStore(1, k) = 0.0; // β₁ unused at model=0
        if (config_.temporalModel < 2) betaToStore(2, k) = 0.0; // β₂ unused at model<2
        if (config_.temporalModel < 3) betaToStore(3, k) = 0.0; // β₃ unused at model<3
    }
    temporalCoefficients_.at(uniqueId) = betaToStore;

    // Actualizar varianzas

    if (config_.temporalModel == 0 || congressCount < 5)
    {
        // Modelo constante: XVAR(id, 1:6) desde OUTX0
        if (ns >= 1)
        {
            legislatorVariances_(uniqueId, 0) = legResult.covariance0(0, 0); // Var(X1)
        }
        if (ns >= 2)
        {
            legislatorVariances_(uniqueId, 3) = legResult.covariance0(1, 1); // Var(X2)
        }
        // Los terminos cruzados son 0 para modelo constante
        legislatorVariances_(uniqueId, 1) = 0.0;
        legislatorVariances_(uniqueId, 2) = 0.0;
        legislatorVariances_(uniqueId, 4) = 0.0;
        legislatorVariances_(uniqueId, 5) = 0.0;
    }
    else
    {
        // Modelo lineal o superior: XVAR desde OUTX1
        if (ns >= 1 && legResult.covariance1.rows() >= 2 * ns)
        {
            legislatorVariances_(uniqueId, 0) = legResult.covariance1(0, 0);
            legislatorVariances_(uniqueId, 1) = legResult.covariance1(ns, ns);
            legislatorVariances_(uniqueId, 2) = legResult.covariance1(0, ns);
        }
        if (ns >= 2 && legResult.covariance1.rows() >= 2 * ns)
        {
            legislatorVariances_(uniqueId, 3) = legResult.covariance1(1, 1);
            legislatorVariances_(uniqueId, 4) = legResult.covariance1(ns + 1, ns + 1);
            legislatorVariances_(uniqueId, 5) = legResult.covariance1(1, ns + 1);
        }
    }

    // Actualizar estadisticas por legislador
    for (const auto &pair : presence.congressToDataIndex)
    {
        int dataIndex = pair.second;
        if (dataIndex >= 0 && dataIndex < legislatorLogLikelihood_.rows())
        {
            legislatorLogLikelihood_(dataIndex, 0) = legResult.logLikelihood0;
            legislatorVoteCounts_(dataIndex, 0) = legResult.totalVotes;
        }
    }

    BlockOptimizationTraceEntry trace;
    trace.iteration = iteration;
    trace.block = "legislator";
    trace.itemIndex = uniqueId;
    trace.objectiveEvaluations = legResult.objectiveEvaluations;
    trace.optimizerStatus = legResult.optimizerStatus;
    trace.initialLogLikelihood = legResult.initialLogLikelihood;
    trace.finalLogLikelihood = legResult.logLikelihood0;
    trace.improvement =
        legResult.logLikelihood0 - legResult.initialLogLikelihood;
    trace.elapsedMilliseconds = legResult.elapsedMilliseconds;
    trace.algorithm = toString(legResult.algorithmUsed);
    trace.fallbackUsed = legResult.fallbackUsed;
    return trace;
}

// METODOS DE UTILIDAD
// Calcula log-likelihood global (PLOG).
double DWNominate::computeLogLikelihood()
{
    // Construir vector de parametros de roll call
    std::vector<RollCallParameters> rollCallParams;
    int numRollCalls = static_cast<int>(rollCallMidpoints_.rows());

    for (int i = 0; i < numRollCalls; ++i)
    {
        RollCallParameters params(config_.numDimensions);
        params.midpoint = rollCallMidpoints_.row(i).transpose();
        params.spread = rollCallSpreads_.row(i).transpose();
        rollCallParams.push_back(params);
    }

    // Llamar a computeLogLikelihood de likelihood.hpp (funcion global)
    LikelihoodResult result = ::computeLogLikelihood(
        legislatorCoords_,
        rollCallParams,
        votes_,
        weights_,
        normalCDF_,
        validRollCalls_);

    // Actualizar estadisticas globales
    globalStats_ = result.stats;

    // Actualizar estadisticas por legislador
    for (int i = 0; i < static_cast<int>(result.legislatorLL.size()); ++i)
    {
        legislatorLogLikelihood_(i, 1) = result.legislatorLL[i];
        legislatorVoteCounts_(i, 1) = result.legislatorVotes[i];
    }

    return result.logLikelihood;
}

// Normaliza un vector a la esfera unitaria.
void DWNominate::normalizeToUnitSphere(Eigen::VectorXd &point)
{
    double norm = point.norm();
    if (norm > 1.0)
    {
        point /= norm;
    }
}

// Verifica si un roll call es valido.
bool DWNominate::isRollCallValid(int yesCount, int noCount) const
{
    int total = yesCount + noCount;
    if (total == 0)
    {
        return false;
    }
    int minority = std::min(yesCount, noCount);
    double margin = static_cast<double>(minority) / total;
    return margin >= config_.marginThreshold;
}

// Log de progreso.
void DWNominate::log(const std::string &message) const
{
    if (config_.verbose)
    {
        std::cout << message << std::endl;
    }
}

// METODOS AUXILIARES DE INTEGRACION CON OPTIMIZADORES
/**
 * Construye vector de RollCallParameters desde estado interno.
 * @return Vector de parametros de roll calls
 */
std::vector<RollCallParameters> DWNominate::buildRollCallParams() const
{
    std::vector<RollCallParameters> params;
    int numRollCalls = static_cast<int>(rollCallMidpoints_.rows());
    int ns = config_.numDimensions;

    params.reserve(numRollCalls);
    for (int i = 0; i < numRollCalls; ++i)
    {
        RollCallParameters rc(ns);
        rc.midpoint = rollCallMidpoints_.row(i).transpose();
        rc.spread = rollCallSpreads_.row(i).transpose();
        params.push_back(rc);
    }

    return params;
}

/**
 * Construye LegislatorPeriodInfo para un legislador.
 * @param uniqueId ID unico del legislador
 * @param presence Informacion de presencia en congresos
 * @return Informacion de periodos para el optimizador
 */
LegislatorPeriodInfo DWNominate::buildLegislatorPeriodInfo(
    int /*uniqueId*/,
    const LegislatorPresence &presence) const
{
    // Determinar numero total de periodos
    int numPeriods = config_.lastCongress - config_.firstCongress + 1;
    LegislatorPeriodInfo info(numPeriods);

    // Poblar rollCallCounts para TODOS los periodos del rango, no solo los
    // servidos. computeLegislatorDerivatives acumula el offset global de roll
    // calls como sum(rollCallCounts[0..j-1]); si los periodos NO servidos
    // quedan en 0, el offset de un legislador que entra despues del primer
    // periodo apunta a columnas equivocadas (en el layout apilado, columnas
    // todas-missing -> 0 votos -> el legislador conserva su coordenada semilla).
    // Esto es direccionamiento/indexacion (hermano de Finding C), no matematica
    // del optimizador.
    for (const auto &cInfo : congressInfo_)
    {
        if (cInfo.index < config_.firstCongress || cInfo.index > config_.lastCongress)
        {
            continue;
        }
        int periodIndex = cInfo.index - config_.firstCongress;
        if (periodIndex >= 0 && periodIndex < static_cast<int>(info.rollCallCounts.size()))
        {
            info.rollCallCounts[periodIndex] = cInfo.numRollCalls;
        }
    }

    // Llenar informacion para cada congreso donde sirvio el legislador
    for (const auto &pair : presence.congressToDataIndex)
    {
        int congress = pair.first;
        int dataIndex = pair.second;

        // Verificar que el congreso esta en el rango
        if (congress < config_.firstCongress || congress > config_.lastCongress)
        {
            continue;
        }

        // Convertir congreso a indice de periodo (0-based relativo a firstCongress)
        int periodIndex = congress - config_.firstCongress;

        // Obtener numero de roll calls para este congreso
        int numRollCalls = 0;
        for (const auto &cInfo : congressInfo_)
        {
            if (cInfo.index == congress)
            {
                numRollCalls = cInfo.numRollCalls;
                break;
            }
        }

        // Marcar como servido
        info.markServed(periodIndex, dataIndex, numRollCalls);
    }

    return info;
}

/**
 * Reconstruye coordenadas de legislador desde coeficientes temporales.
 * @param presence Informacion de presencia
 * @param coefficients Coeficientes temporales optimizados
 */
void DWNominate::reconstructLegislatorCoords(
    const LegislatorPresence &presence,
    const TemporalCoefficients &coefficients)
{
    int ns = config_.numDimensions;

    // Obtener lista de periodos servidos
    std::vector<int> servedPeriods;
    for (const auto &pair : presence.congressToDataIndex)
    {
        int congress = pair.first;
        if (congress >= config_.firstCongress && congress <= config_.lastCongress)
        {
            servedPeriods.push_back(congress);
        }
    }

    int kk = static_cast<int>(servedPeriods.size());
    if (kk == 0)
    {
        return;
    }

    // Calcular incremento temporal (igual que en buildLegendreTimeTrends)
    double xinc = 0.0;
    if (kk > 1)
    {
        xinc = 2.0 / (static_cast<double>(kk) - 1.0);
    }

    // Reconstruir coordenadas para cada periodo
    int periodIdx = 0;
    for (int congress : servedPeriods)
    {
        int dataIndex = presence.getDataIndex(congress);
        if (dataIndex < 0)
        {
            periodIdx++;
            continue;
        }

        // Calcular tiempo normalizado t en [-1, 1]
        double xtime = -1.0 + static_cast<double>(periodIdx) * xinc;

        // Calcular polinomios de Legendre
        double p0 = 1.0;
        double p1 = xtime;
        double p2 = (3.0 * xtime * xtime - 1.0) / 2.0;
        double p3 = (5.0 * xtime * xtime * xtime - 3.0 * xtime) / 2.0;

        // Reconstruir coordenadas para cada dimension.
        //
        // REQ-003 fix (2026-06-01): respect config_.temporalModel — only sum
        // Legendre terms up to the active polynomial order. Without this gate,
        // the cubic OLS coefficient (computeInitialBetasForDimension fits all
        // 4 terms when kk >= 7) leaks into the output even in model=1 (linear)
        // and model=2 (quadratic) runs, where the optimization loop never
        // touches the cubic slot.
        //
        // Mirrors Fortran PROX legacy_2004_DW-NOMINATE.FOR:1592-1622 exactly:
        //   NMODEL=0 -> ATIME(KK,1)*XBETA(1,K)
        //   NMODEL=1 -> + ATIME(KK,2)*XBETA(2,K)
        //   NMODEL=2 -> + ATIME(KK,3)*XBETA(3,K)
        //   NMODEL=3 -> + ATIME(KK,4)*XBETA(4,K)
        for (int k = 0; k < ns; ++k)
        {
            double coord = coefficients(0, k) * p0;
            if (config_.temporalModel >= 1) coord += coefficients(1, k) * p1;
            if (config_.temporalModel >= 2) coord += coefficients(2, k) * p2;
            if (config_.temporalModel >= 3) coord += coefficients(3, k) * p3;
            legislatorCoords_(dataIndex, k) = coord;
        }

        periodIdx++;
    }
}
