/**
 * @file csv_loader.cpp
 * @brief Implementación del cargador de datos CSV para DW-NOMINATE.
 */

#include "csv_loader.hpp"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <stdexcept>
#include <cmath>

// Constructor
CSVLoader::CSVLoader(const std::string &inputDir, const std::string &outputDir)
    : inputDir_(inputDir), outputDir_(outputDir)
{
}

// Utilidades de parsing CSV
std::vector<std::string> CSVLoader::splitCSVLine(const std::string &line)
{
    std::vector<std::string> result;
    std::string current;
    bool inQuotes = false;

    for (size_t i = 0; i < line.size(); ++i)
    {
        char c = line[i];
        if (c == '"')
        {
            inQuotes = !inQuotes;
        }
        else if (c == ',' && !inQuotes)
        {
            result.push_back(current);
            current.clear();
        }
        else
        {
            current += c;
        }
    }
    result.push_back(current);
    return result;
}

double CSVLoader::parseDouble(const std::string &str, double defaultVal)
{
    if (isNA(str) || str.empty())
    {
        return defaultVal;
    }
    try
    {
        return std::stod(str);
    }
    catch (...)
    {
        return defaultVal;
    }
}

int CSVLoader::parseInt(const std::string &str, int defaultVal)
{
    if (isNA(str) || str.empty())
    {
        return defaultVal;
    }
    try
    {
        return std::stoi(str);
    }
    catch (...)
    {
        return defaultVal;
    }
}

bool CSVLoader::isNA(const std::string &str)
{
    std::string s = str;
    // Trim whitespace
    s.erase(0, s.find_first_not_of(" \t\r\n"));
    s.erase(s.find_last_not_of(" \t\r\n") + 1);

    return s == "NA" || s == "na" || s == "N/A" || s == "NaN" || s == "nan" || s.empty();
}

// Carga de metadata de legisladores
void CSVLoader::loadLegislatorMetadata()
{
    std::string path = inputDir_ + "/legislator_metadata.csv";
    std::ifstream file(path);
    if (!file.is_open())
    {
        throw std::runtime_error("No se puede abrir: " + path);
    }

    std::string line;
    // Leer header
    std::getline(file, line);
    // Esperado: legislator_id,id,nombres,partido,region,distrito

    while (std::getline(file, line))
    {
        if (line.empty())
            continue;

        auto fields = splitCSVLine(line);
        if (fields.size() < 5)
            continue;

        LegislatorInfo info;
        info.id = parseInt(fields[0]);
        info.name = fields.size() > 2 ? fields[2] : "";
        info.party = fields.size() > 3 ? fields[3] : "";
        info.region = fields.size() > 4 ? fields[4] : "";
        info.district = fields.size() > 5 ? fields[5] : "";

        if (info.id > 0)
        {
            legislatorInfo_[info.id] = info;
        }
    }
}

// Carga de votos de un período
PeriodData CSVLoader::loadPeriodVotes(int periodNum)
{
    PeriodData data;
    data.periodIndex = periodNum - 1; // 0-based

    std::string path = inputDir_ + "/votes_matrix_p" + std::to_string(periodNum) + ".csv";
    std::ifstream file(path);
    if (!file.is_open())
    {
        throw std::runtime_error("No se puede abrir: " + path);
    }

    std::string line;
    bool isHeader = true;

    while (std::getline(file, line))
    {
        if (line.empty())
            continue;

        auto fields = splitCSVLine(line);

        if (isHeader)
        {
            // Primera fila es header: primera columna es ID legislador,
            // resto son IDs de votaciones
            data.numRollCalls = static_cast<int>(fields.size()) - 1;
            isHeader = false;
            continue;
        }

        // Primera columna es ID del legislador
        int legId = parseInt(fields[0]);
        if (legId < 0)
            continue;

        data.legislatorIds.push_back(legId);

        // Resto son votos
        std::vector<int> legVotes;
        for (size_t j = 1; j < fields.size(); ++j)
        {
            if (isNA(fields[j]))
            {
                legVotes.push_back(-1); // Missing
            }
            else
            {
                int vote = parseInt(fields[j], -1);
                legVotes.push_back(vote);
            }
        }
        data.votes.push_back(legVotes);
    }

    return data;
}

// Construir lista unificada de legisladores
void CSVLoader::buildUnifiedLegislatorList()
{
    // Bugfix 2026-04-23: only include legislators with at least one non-missing
    // vote across all periods. Previously, rows that appeared in the vote matrix
    // with every cell coded 9 or -1 ("phantoms") would still enter legislatorIds_
    // and receive fallback starting coords (csv_loader.cpp fallback block), which
    // then biased centerPointCloud (cutting_plane.cpp). Empirically, this caused
    // 0.611-unit self-drift for identical real-legislator vote data.
    std::set<int> activeIds;
    std::set<int> allIdsSeen;
    for (const auto &period : periodData_)
    {
        for (size_t i = 0; i < period.legislatorIds.size(); ++i)
        {
            int id = period.legislatorIds[i];
            allIdsSeen.insert(id);
            if (activeIds.count(id))
            {
                continue;
            }
            const auto &row = period.votes[i];
            for (int v : row)
            {
                if (v != -1 && v != 9)
                {
                    activeIds.insert(id);
                    break;
                }
            }
        }
    }

    // Convertir a vector ordenado
    legislatorIds_.clear();
    legislatorIds_.assign(activeIds.begin(), activeIds.end());
    std::sort(legislatorIds_.begin(), legislatorIds_.end());

    if (allIdsSeen.size() > legislatorIds_.size())
    {
        std::cout << "  Legisladores filtrados (sin votos no-missing en ningun periodo): "
                  << (allIdsSeen.size() - legislatorIds_.size())
                  << " de " << allIdsSeen.size() << " totales\n";
    }

    // Construir mapeo de ID a índice
    legislatorIdToIndex_.clear();
    for (size_t i = 0; i < legislatorIds_.size(); ++i)
    {
        legislatorIdToIndex_[legislatorIds_[i]] = static_cast<int>(i);
    }
}

// Obtener offset de roll calls para un período
int CSVLoader::getRollCallOffset(int period) const
{
    int offset = 0;
    for (int p = 0; p < period && p < static_cast<int>(rollCallsPerPeriod_.size()); ++p)
    {
        offset += rollCallsPerPeriod_[p];
    }
    return offset;
}

// Carga de coordenadas W-NOMINATE
std::map<int, WNominateCoords> CSVLoader::loadWNominateCoordinates(const std::string &path)
{
    std::map<int, WNominateCoords> result;

    std::ifstream file(path);
    if (!file.is_open())
    {
        throw std::runtime_error("No se puede abrir archivo W-NOMINATE: " + path);
    }

    std::string line;
    bool isHeader = true;

    while (std::getline(file, line))
    {
        if (line.empty())
            continue;

        auto fields = splitCSVLine(line);

        if (isHeader)
        {
            // Esperado: "coord1D","coord2D","legislator_id","legislator_name","party"
            isHeader = false;
            continue;
        }

        if (fields.size() < 3)
            continue;

        WNominateCoords coords;
        coords.coord1D = parseDouble(fields[0]);
        coords.coord2D = parseDouble(fields[1]);
        coords.legislatorId = parseInt(fields[2]);
        if (fields.size() > 3)
            coords.name = fields[3];
        if (fields.size() > 4)
            coords.party = fields[4];

        if (coords.legislatorId > 0)
        {
            result[coords.legislatorId] = coords;
        }
    }

    std::cout << "  W-NOMINATE: Cargadas " << result.size()
              << " coordenadas iniciales desde " << path << std::endl;

    return result;
}

// Carga per-(legislator, period). Formato: legislator_id,period,coord1D,coord2D.
// Period es 1-based. Se ignora cualquier columna extra.
std::map<std::pair<int, int>, std::pair<double, double>>
CSVLoader::loadWNominateCoordinatesPerPeriod(const std::string &path)
{
    std::map<std::pair<int, int>, std::pair<double, double>> result;

    std::ifstream file(path);
    if (!file.is_open())
    {
        throw std::runtime_error("No se puede abrir archivo W-NOMINATE per-period: " + path);
    }

    std::string line;
    bool isHeader = true;
    while (std::getline(file, line))
    {
        if (line.empty())
            continue;
        auto fields = splitCSVLine(line);
        if (isHeader)
        {
            isHeader = false;
            continue;
        }
        if (fields.size() < 4)
            continue;
        int legId = parseInt(fields[0]);
        int period1 = parseInt(fields[1]);
        double c1 = parseDouble(fields[2]);
        double c2 = parseDouble(fields[3]);
        if (legId > 0 && period1 > 0)
        {
            result[{legId, period1}] = {c1, c2};
        }
    }

    std::cout << "  W-NOMINATE per-period: Cargadas " << result.size()
              << " coordenadas (leg, periodo) desde " << path << std::endl;

    return result;
}

// Carga principal: construir DWNominateInput (wrapper simple)
DWNominateInput CSVLoader::loadInput(int numPeriods)
{
    return buildDWNominateInput(numPeriods, nullptr);
}

// Carga con configuración de inicialización específica
DWNominateInput CSVLoader::loadInput(int numPeriods, const InitializationConfig &initConfig)
{
    return buildDWNominateInput(numPeriods, &initConfig);
}

// Implementación interna: construir DWNominateInput
DWNominateInput CSVLoader::buildDWNominateInput(int numPeriods, const InitializationConfig *initConfig)
{
    // 1. Cargar metadata de legisladores
    loadLegislatorMetadata();

    // 2. Cargar datos de votaciones de cada período
    periodData_.clear();
    rollCallsPerPeriod_.clear();
    for (int p = 1; p <= numPeriods; ++p)
    {
        PeriodData pd = loadPeriodVotes(p);
        periodData_.push_back(pd);
        rollCallsPerPeriod_.push_back(pd.numRollCalls);
    }

    // 3. Construir lista unificada de legisladores
    buildUnifiedLegislatorList();

    // 4. Construir layout XDATA APILADO (stacked), una fila por (periodo, legislador-activo).
    //
    // Finding C fix (2026-05-24): el motor (CongressInfo::legislatorOffset,
    // LegislatorPresence::congressToDataIndex, reconstructLegislatorCoords y el
    // direccionamiento legislatorOffset+localLeg del optimizador de roll calls)
    // YA asume un layout apilado estilo Fortran: una fila distinta por cada
    // aparicion (legislador, congreso). El loader previo construia almacenamiento
    // por legislador UNICO, lo que (a) hacia que el offset por periodo se saliera
    // de rango en los periodos 2+ y (b) colapsaba las coordenadas por periodo a
    // una sola fila. Aqui construimos el layout apilado que el resto del motor
    // espera; ningun optimizador ni la matematica cambian.
    //
    // Una fila apilada existe para (periodo p, legislador) si el legislador emitio
    // >=1 voto no-missing en p. Dentro de cada periodo las filas se ordenan por id
    // unico ascendente, de modo que un run de un solo periodo reproduce exactamente
    // el comportamiento anterior (Tier 1 no regresiona).
    struct StackedRow
    {
        int period;       // congreso 0-based
        int legId;        // id unico del legislador
        int periodVoteRow; // indice de fila en periodData_[period].votes
    };
    std::vector<StackedRow> stackedRows;
    std::vector<int> perPeriodCount(numPeriods, 0);

    // Mapa por periodo: legId -> indice de fila en el CSV de ese periodo.
    std::vector<std::map<int, int>> periodLegIdxMaps(numPeriods);
    for (int p = 0; p < numPeriods; ++p)
    {
        const auto &pd = periodData_[p];
        for (size_t i = 0; i < pd.legislatorIds.size(); ++i)
        {
            periodLegIdxMaps[p][pd.legislatorIds[i]] = static_cast<int>(i);
        }
    }

    for (int p = 0; p < numPeriods; ++p)
    {
        const auto &pd = periodData_[p];
        const auto &idxMap = periodLegIdxMaps[p];
        // legislatorIds_ ya esta ordenado ascendente (buildUnifiedLegislatorList).
        for (int legId : legislatorIds_)
        {
            auto it = idxMap.find(legId);
            if (it == idxMap.end())
            {
                continue; // no aparece en el CSV de este periodo
            }
            int voteRow = it->second;
            // Activo en este periodo: >=1 voto no-missing (1=Si, 0/6=No; -1/9=missing).
            bool active = false;
            for (int v : pd.votes[voteRow])
            {
                if (v != -1 && v != 9)
                {
                    active = true;
                    break;
                }
            }
            if (!active)
            {
                continue;
            }
            stackedRows.push_back({p, legId, voteRow});
            perPeriodCount[p]++;
        }
    }

    int totalLegislators = static_cast<int>(stackedRows.size()); // = filas apiladas (S)
    int totalUniqueLegislators = static_cast<int>(legislatorIds_.size());
    int totalRollCalls = 0;
    for (int rc : rollCallsPerPeriod_)
    {
        totalRollCalls += rc;
    }

    // 5. Construir DWNominateInput
    DWNominateInput input(totalLegislators, totalRollCalls);

    // 5.1 Pesos iniciales: [W1=1.0, W2, Beta]
    // Si hay configuración, usar valores especificados; sino, usar defaults
    input.initialWeights.resize(3); // NS=2 + 1
    input.initialWeights(0) = 1.0;  // W1 siempre es 1.0
    if (initConfig)
    {
        input.initialWeights(1) = initConfig->w2;   // Peso dimension 2
        input.initialWeights(2) = initConfig->beta; // Beta (sigma^2)
        std::cout << "  Pesos iniciales: W1=1.0, W2=" << initConfig->w2
                  << ", Beta=" << initConfig->beta << std::endl;
    }
    else
    {
        input.initialWeights(1) = 0.5;
        input.initialWeights(2) = 4.925;
    }

    // 5.2 Coordenadas iniciales de legisladores
    input.legislatorCoords = Eigen::MatrixXd::Zero(totalLegislators, 2);

    // Si hay configuración con coordenadas externas, cargarlas
    std::map<int, WNominateCoords> wnomCoords;
    std::map<std::pair<int, int>, std::pair<double, double>> wnomCoordsPP;
    bool useWNominate = initConfig && initConfig->useWNominateStart &&
                        !initConfig->wnominatePath.empty();
    bool useSeedPP = initConfig && initConfig->useSeedPerPeriod &&
                     !initConfig->seedPerPeriodPath.empty();

    if (useWNominate)
    {
        wnomCoords = loadWNominateCoordinates(initConfig->wnominatePath);
    }
    if (useSeedPP)
    {
        wnomCoordsPP = loadWNominateCoordinatesPerPeriod(initConfig->seedPerPeriodPath);
    }

    // Asignar coordenadas semilla por fila apilada. Cuando useSeedPP esta activo,
    // cada fila (legId, period_0based) consulta la semilla per-(leg,period) usando
    // period_1based = period_0based + 1; si no hay entrada para esa tupla, cae al
    // valor per-legislador (si useWNominate esta activo) o al fallback determinista.
    // El default (sin useSeedPP) es el comportamiento original per-legislador,
    // por lo que Tier 1 (sen90) y Tier 2 (US linear 1-117) no regresionan.
    int coordsFromPP = 0;
    int coordsFromWNom = 0;
    int coordsFallback = 0;
    for (int r = 0; r < totalLegislators; ++r)
    {
        int legId = stackedRows[r].legId;
        int period0 = stackedRows[r].period; // 0-based
        bool applied = false;

        if (useSeedPP)
        {
            auto itPP = wnomCoordsPP.find({legId, period0 + 1});
            if (itPP != wnomCoordsPP.end())
            {
                input.legislatorCoords(r, 0) = itPP->second.first;
                input.legislatorCoords(r, 1) = itPP->second.second;
                coordsFromPP++;
                applied = true;
            }
        }

        if (!applied && useWNominate)
        {
            auto it = wnomCoords.find(legId);
            if (it != wnomCoords.end())
            {
                input.legislatorCoords(r, 0) = it->second.coord1D;
                input.legislatorCoords(r, 1) = it->second.coord2D;
                coordsFromWNom++;
                applied = true;
            }
        }

        if (!applied)
        {
            // Fallback: distribución uniforme simple basada en el índice único
            int uIdx = legislatorIdToIndex_.count(legId) ? legislatorIdToIndex_.at(legId) : 0;
            double frac = (totalUniqueLegislators > 0)
                              ? static_cast<double>(uIdx) / static_cast<double>(totalUniqueLegislators)
                              : 0.0;
            input.legislatorCoords(r, 0) = frac - 0.5;
            input.legislatorCoords(r, 1) = (uIdx % 2 == 0 ? 0.1 : -0.1) * frac;
            coordsFallback++;
        }
    }

    if (useSeedPP || useWNominate)
    {
        std::cout << "  Coordenadas aplicadas: " << coordsFromPP << " per-(leg,periodo), "
                  << coordsFromWNom << " per-legislador, " << coordsFallback << " fallback\n";
    }

    // 5.3 Midpoints y spreads iniciales de roll calls
    input.rollCallMidpoints = Eigen::MatrixXd::Zero(totalRollCalls, 2);
    input.rollCallSpreads = Eigen::MatrixXd::Constant(totalRollCalls, 2, 0.3);

    // 5.3.1 NUEVO: Si tenemos parámetros de referencia de R, usarlos como inicialización
    // Esto replica el flujo del Fortran donde ZMID viene pre-calculado
    auto rBillParams = loadReferenceBillParams();
    if (!rBillParams.empty())
    {
        int paramsLoaded = 0;
        for (const auto &bp : rBillParams)
        {
            int period = bp.session - 1;
            if (period < 0 || period >= numPeriods)
                continue;

            int rcOffset = getRollCallOffset(period);
            int globalIdx = rcOffset + (bp.billId - 1);

            if (globalIdx >= 0 && globalIdx < totalRollCalls && bp.isValid)
            {
                input.rollCallMidpoints(globalIdx, 0) = bp.midpoint1D;
                input.rollCallMidpoints(globalIdx, 1) = bp.midpoint2D;
                input.rollCallSpreads(globalIdx, 0) = bp.spread1D;
                input.rollCallSpreads(globalIdx, 1) = bp.spread2D;
                paramsLoaded++;
            }
        }

        if (paramsLoaded > 0)
        {
            std::cout << "  Bill params inicializados desde R: " << paramsLoaded << "/" << totalRollCalls << "\n";
        }
    }

    // 5.4 Votos y congresos (layout apilado)
    input.rollCallCongress.resize(totalRollCalls);
    input.legislatorCongress.resize(totalLegislators);
    input.legislatorUniqueId.resize(totalLegislators);

    // Offset de roll calls por periodo + asignacion congreso->roll call.
    std::vector<int> periodRcOffset(numPeriods, 0);
    {
        int off = 0;
        for (int period = 0; period < numPeriods; ++period)
        {
            periodRcOffset[period] = off;
            for (int j = 0; j < periodData_[period].numRollCalls; ++j)
            {
                input.rollCallCongress[off + j] = period;
            }
            off += periodData_[period].numRollCalls;
        }
    }

    // Metadata por fila apilada: id unico + congreso (periodo) de la fila.
    for (int r = 0; r < totalLegislators; ++r)
    {
        input.legislatorUniqueId[r] = stackedRows[r].legId;
        input.legislatorCongress[r] = stackedRows[r].period;
    }

    // 5.5 Construir matriz de votos apilada.
    // Cada fila apilada lleva votos NO-missing solo en los roll calls de SU periodo;
    // todas las demas columnas quedan missing. Asi cada voto (legislador, periodo)
    // aparece exactamente una vez y la likelihood global usa la coordenada de ese
    // periodo (tras la reconstruccion polinomial) para ese voto.
    for (int r = 0; r < totalLegislators; ++r)
    {
        int p = stackedRows[r].period;
        int voteRow = stackedRows[r].periodVoteRow;
        const auto &pd = periodData_[p];
        int off = periodRcOffset[p];

        for (int globalRcIdx = 0; globalRcIdx < totalRollCalls; ++globalRcIdx)
        {
            if (input.rollCallCongress[globalRcIdx] == p)
            {
                int localRc = globalRcIdx - off;
                int vote = pd.votes[voteRow][localRc];
                // Codificación: 1=Sí, 0/6=No, 9=Missing/Abstención, -1=NA
                if (vote == -1 || vote == 9)
                {
                    input.votes.setVote(r, globalRcIdx, false, true);
                }
                else
                {
                    input.votes.setVote(r, globalRcIdx, vote == 1, false);
                }
            }
            else
            {
                // Roll call de otro periodo: missing para esta fila apilada.
                input.votes.setVote(r, globalRcIdx, false, true);
            }
        }
    }

    // 5.6 Metadata de congresos.
    // numLegislators por periodo = numero de FILAS APILADAS de ese periodo
    // (legisladores activos en p). Esto alimenta legislatorOffset en
    // loadCongressMetadata y debe coincidir con la particion de filas apiladas.
    input.congressMetadata.clear();
    for (int period = 0; period < numPeriods; ++period)
    {
        input.congressMetadata.push_back({perPeriodCount[period], periodData_[period].numRollCalls});
    }

    return input;
}

// Carga de coordenadas de referencia (output de R)
std::vector<ReferenceCoordinates> CSVLoader::loadReferenceCoordinates()
{
    std::vector<ReferenceCoordinates> result;

    if (outputDir_.empty())
    {
        return result;
    }

    // Usar versión corregida con polaridad alineada a convención estándar
    // La versión sin corrección tiene signos arbitrarios que dependen de la inicialización
    std::string path = outputDir_ + "/dwnominate_coordinates_all_periods_corrected.csv";
    std::ifstream file(path);

    // Si no existe la versión corregida, intentar con la original
    if (!file.is_open())
    {
        path = outputDir_ + "/dwnominate_coordinates_all_periods.csv";
        file.open(path);
    }
    if (!file.is_open())
    {
        std::cerr << "Advertencia: No se puede abrir " << path << std::endl;
        return result;
    }

    std::string line;
    bool isHeader = true;

    while (std::getline(file, line))
    {
        if (line.empty())
            continue;

        auto fields = splitCSVLine(line);

        if (isHeader)
        {
            isHeader = false;
            continue;
        }

        // Esperado: period,legislator,party,name,coord1D,coord2D,se1D,se2D,var1D,var2D,
        //           loglikelihood,numVotes,numErrors,GMP,...
        if (fields.size() < 14)
            continue;

        ReferenceCoordinates rc;
        rc.period = parseInt(fields[0]);
        rc.legislatorId = parseInt(fields[1]);
        rc.party = fields[2];
        rc.coord1D = parseDouble(fields[4]);
        rc.coord2D = parseDouble(fields[5]);
        rc.se1D = parseDouble(fields[6]);
        rc.se2D = parseDouble(fields[7]);
        rc.logLikelihood = parseDouble(fields[10]);
        rc.numVotes = parseInt(fields[11]);
        rc.numErrors = parseInt(fields[12]);
        rc.gmp = parseDouble(fields[13]);

        result.push_back(rc);
    }

    return result;
}

// Carga de parámetros de votaciones de referencia (output de R)
std::vector<ReferenceBillParams> CSVLoader::loadReferenceBillParams()
{
    std::vector<ReferenceBillParams> result;

    if (outputDir_.empty())
    {
        return result;
    }

    std::string path = outputDir_ + "/dwnominate_bill_parameters.csv";
    std::ifstream file(path);
    if (!file.is_open())
    {
        std::cerr << "Advertencia: No se puede abrir " << path << std::endl;
        return result;
    }

    std::string line;
    bool isHeader = true;

    while (std::getline(file, line))
    {
        if (line.empty())
            continue;

        auto fields = splitCSVLine(line);

        if (isHeader)
        {
            isHeader = false;
            continue;
        }

        // Esperado: session,ID,midpoint1D,midpoint2D,spread1D,spread2D
        if (fields.size() < 6)
            continue;

        ReferenceBillParams bp;
        bp.session = parseInt(fields[0]);
        bp.billId = parseInt(fields[1]);
        bp.isValid = !isNA(fields[2]) && !isNA(fields[3]) && !isNA(fields[4]) && !isNA(fields[5]);

        if (bp.isValid)
        {
            bp.midpoint1D = parseDouble(fields[2]);
            bp.midpoint2D = parseDouble(fields[3]);
            bp.spread1D = parseDouble(fields[4]);
            bp.spread2D = parseDouble(fields[5]);
        }

        result.push_back(bp);
    }

    return result;
}
