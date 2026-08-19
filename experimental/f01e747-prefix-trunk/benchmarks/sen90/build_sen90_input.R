# Tier 1 fidelity gate: convert canonical sen90 (90th US Senate) into the QV
# C++ DW-NOMINATE input format, and produce the published W-NOMINATE reference.
#
# Recoding mirrors the Chilean rule (extract_multi_period.py:71-77):
#   yea (1,2,3) -> 1 ; nay (4,5,6) -> 6 ; missing/present/notInLegis (0,7,8,9,NA) -> 9
suppressMessages(library(wnominate))
set.seed(42)
outdir <- "."
data(sen90)

V <- sen90$votes                          # 102 x 596, raw cast codes
recode <- function(x) {
  out <- ifelse(x %in% c(1,2,3), 1L,
         ifelse(x %in% c(4,5,6), 6L, 9L)) # everything else (0,7,8,9,NA) -> missing
  out[is.na(out)] <- 9L
  out
}
M <- apply(V, c(1,2), recode)
ids <- sen90$legis.data$icpsrLegis
rownames(M) <- ids
colnames(M) <- seq_len(ncol(M))           # rollcall ids 1..596

# votes_matrix_p1.csv : first col = legislator id, header = rollcall ids
df <- data.frame(M, check.names = FALSE)
write.csv(df, file.path(outdir, "votes_matrix_p1.csv"), row.names = TRUE)

# Canonical published W-NOMINATE reference (polarity per the package vignette)
wn <- wnominate(sen90, polarity = c(2, 5), dims = 2, minvotes = 20)
ref <- data.frame(
  legislator_id = ids,
  coord1D = wn$legislators$coord1D,
  coord2D = wn$legislators$coord2D,
  party   = sen90$legis.data$party,
  name    = rownames(sen90$legis.data),
  stringsAsFactors = FALSE
)
write.csv(ref, file.path(outdir, "wnom_reference.csv"), row.names = FALSE)

# Seed A: the W-NOMINATE coords themselves (stability test)
seedA <- data.frame(coord1D = ref$coord1D, coord2D = ref$coord2D,
                    legislator_id = ids, legislator_name = ref$name, party = ref$party,
                    stringsAsFactors = FALSE)
write.csv(seedA, file.path(outdir, "wnominate_coordinates.csv"), row.names = FALSE)

# Seed B: perturbed start (estimate-not-regurgitate test)
seedB <- seedA
seedB$coord1D <- pmax(-0.99, pmin(0.99, seedA$coord1D + rnorm(nrow(seedA), 0, 0.30)))
seedB$coord2D <- pmax(-0.99, pmin(0.99, seedA$coord2D + rnorm(nrow(seedA), 0, 0.30)))
write.csv(seedB, file.path(outdir, "wnominate_coordinates_perturbed.csv"), row.names = FALSE)

# legislator metadata (party for polarity anchor)
meta <- data.frame(legislator_id = ids, party = sen90$legis.data$party,
                   name = rownames(sen90$legis.data), stringsAsFactors = FALSE)
write.csv(meta, file.path(outdir, "legislator_metadata.csv"), row.names = FALSE)

cat("WROTE: votes_matrix_p1.csv (", nrow(M), "x", ncol(M), "), wnom_reference.csv,",
    "wnominate_coordinates.csv (+perturbed), legislator_metadata.csv\n")
cat("wnom classification (correct%):",
    round(100 * (sum(wn$legislators$correctYea, na.rm=TRUE) + sum(wn$legislators$correctNay, na.rm=TRUE)) /
          (sum(wn$legislators$correctYea, wn$legislators$wrongYea, wn$legislators$correctNay, wn$legislators$wrongNay, na.rm=TRUE)), 2), "\n")
