#include "cutting_plane.hpp"

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
    // El orden de entrada mezcla deliberadamente votos Si/No respecto de x1.
    // Los ausentes deben permanecer en la nube geometrica sin ser clasificados.
    Eigen::MatrixXd coordinates(12, 2);
    coordinates << -0.90, 0.80,
        -0.75, -0.70,
        -0.60, 0.65,
        -0.40, -0.55,
        -0.20, 0.45,
        0.00, -0.40,
        0.20, 0.35,
        0.40, -0.25,
        0.60, 0.20,
        0.75, -0.15,
        0.90, 0.10,
        0.05, 0.90;

    const std::vector<int> votes{
        VoteCode::YES,
        VoteCode::NO,
        VoteCode::YES,
        VoteCode::NO,
        VoteCode::MISSING,
        VoteCode::NO,
        VoteCode::YES,
        VoteCode::NO,
        VoteCode::YES,
        VoteCode::NO,
        VoteCode::YES,
        VoteCode::MISSING};

    Eigen::VectorXd normal(2);
    normal << 1.0, 0.0;
    const RollCallClassification reference =
        classifyRollCall(coordinates, normal, votes, true);

    if (reference.totalClassified != 10)
    {
        return fail("CUTPLANE counted missing votes as classified");
    }
    if (reference.legislatorErrors[4] != 0 ||
        reference.legislatorErrors[11] != 0)
    {
        return fail("CUTPLANE assigned an error to a missing vote");
    }

    // La clasificacion debe ser invariante al permutar conjuntamente filas y
    // votos. Esto detecta el antiguo desacople por ordenar solo voteCodes.
    const std::vector<int> permutation{7, 2, 10, 0, 5, 11, 3, 8, 1, 9, 4, 6};
    Eigen::MatrixXd permutedCoordinates(12, 2);
    std::vector<int> permutedVotes(12);
    for (int i = 0; i < 12; ++i)
    {
        permutedCoordinates.row(i) = coordinates.row(permutation[i]);
        permutedVotes[i] = votes[permutation[i]];
    }

    Eigen::VectorXd permutedNormal(2);
    permutedNormal << 1.0, 0.0;
    const RollCallClassification permuted =
        classifyRollCall(permutedCoordinates, permutedNormal, permutedVotes, true);

    if (permuted.totalClassified != reference.totalClassified ||
        permuted.totalErrors != reference.totalErrors)
    {
        return fail("CUTPLANE changed aggregate classification after aligned row permutation");
    }

    std::vector<int> restoredErrors(12, 0);
    for (int i = 0; i < 12; ++i)
    {
        restoredErrors[permutation[i]] = permuted.legislatorErrors[i];
    }
    if (restoredErrors != reference.legislatorErrors)
    {
        return fail("CUTPLANE changed legislator errors after aligned row permutation");
    }

    // Empates producidos por el redondeo legado deben resolverse de forma
    // determinista conservando el indice original.
    const std::vector<double> tiedValues{0.2, -0.1, 0.2, -0.1};
    const std::vector<size_t> tiedOrder = argsort(tiedValues);
    const std::vector<size_t> expectedOrder{1, 3, 0, 2};
    if (tiedOrder != expectedOrder)
    {
        return fail("argsort did not resolve equal projections deterministically");
    }

    return 0;
}
