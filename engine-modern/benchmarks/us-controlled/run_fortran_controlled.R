#!/usr/bin/env Rscript

# Controlled Fortran run. It reconstructs the five rollcall objects from the
# committed CSV matrices and gives dwnominate exactly the same float32 seed CSV
# consumed by C++. No W-NOMINATE or repository estimate is recalculated here.

suppressMessages({
  library(dwnominate)
  library(pscl)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3) {
  stop("usage: run_fortran_controlled.R <us-benchmark-dir> <common-seed.csv> <output-dir>")
}

benchmark_dir <- normalizePath(args[[1]], mustWork = TRUE)
seed_path <- normalizePath(args[[2]], mustWork = TRUE)
output_dir <- args[[3]]
if (dir.exists(output_dir)) {
  stop("output directory already exists: ", output_dir)
}
dir.create(output_dir, recursive = TRUE)

published <- read.csv(file.path(benchmark_dir, "voteview_published.csv"),
                      stringsAsFactors = FALSE)
party_label <- function(code) {
  ifelse(code == 100, "D", ifelse(code == 200, "R", "I"))
}

rollcalls <- lapply(1:5, function(period) {
  matrix_path <- file.path(
    benchmark_dir, "cpp_input", sprintf("votes_matrix_p%d.csv", period)
  )
  votes <- read.csv(matrix_path, row.names = 1, check.names = FALSE)
  row_ids <- as.integer(row.names(votes))
  period_members <- published[published$period == period, ]
  matches <- match(period_members$legislator_id, row_ids)
  if (anyNA(matches)) stop("period roster is not contained in vote matrix: ", period)
  votes <- as.matrix(votes[matches, , drop = FALSE])
  storage.mode(votes) <- "integer"
  row.names(votes) <- as.character(period_members$legislator_id)

  legislator_data <- data.frame(
    icpsr = as.integer(period_members$legislator_id),
    party = party_label(period_members$party_code),
    stringsAsFactors = FALSE,
    row.names = row.names(votes)
  )
  rollcall(
    votes,
    yea = 1,
    nay = 6,
    missing = 9,
    notInLegis = 0,
    legis.names = row.names(votes),
    vote.names = colnames(votes),
    legis.data = legislator_data,
    desc = paste0("S", 110 + period)
  )
})

seed <- read.csv(seed_path, stringsAsFactors = FALSE)
required <- c("legislator_id", "coord1D", "coord2D")
if (!all(required %in% names(seed))) stop("common seed has missing columns")
if (anyDuplicated(seed$legislator_id)) stop("common seed has duplicated legislators")
if (any(!is.finite(seed$coord1D)) || any(!is.finite(seed$coord2D))) {
  stop("common seed contains non-finite coordinates")
}

controlled_start <- list(
  dimensions = 2,
  legislators = data.frame(
    icpsr = as.integer(seed$legislator_id),
    coord1D = as.numeric(seed$coord1D),
    coord2D = as.numeric(seed$coord2D)
  )
)
class(controlled_start) <- "controlled_start"

# dwnominate's wrapper sets IHAPPY=c(1,niter+1). niter=4 therefore gives five
# effective WINT-SIGMAS-RC-LEG cycles, matching C++ --iterations=5.
result <- dwnominate(
  rollcalls,
  id = "icpsr",
  start = controlled_start,
  dims = 2,
  model = 1,
  niter = 4,
  beta = 5.9539,
  w = 0.3463
)

write.csv(result$legislators,
          file.path(output_dir, "fortran_coordinates_controlled.csv"),
          row.names = FALSE)
write.csv(result$rollcalls,
          file.path(output_dir, "fortran_bill_parameters_controlled.csv"),
          row.names = FALSE)
write.csv(
  data.frame(
    parameter = c("w1", "w2", "beta", "wrapper_niter", "effective_cycles",
                  "reported_legislator_loglikelihood_sum"),
    value = c(result$weights[[1]], result$weights[[2]], result$beta, 4, 5,
              sum(result$legislators$loglikelihood, na.rm = TRUE))
  ),
  file.path(output_dir, "fortran_summary_controlled.csv"),
  row.names = FALSE
)
saveRDS(result, file.path(output_dir, "fortran_result_controlled.rds"))
