# Tier 2 data acquisition: 3 contiguous US Senates (113,114,115) from VoteView.
# Downloads per-congress votes + member files, builds vote matrices, constructs
# pscl rollcall objects for the canonical wmay dwnominate Fortran, and writes
# the QV C++ input (votes_matrix_pN.csv + seed + metadata) on a GLOBAL roster.
suppressMessages({library(wnominate); library(pscl)})
set.seed(42)
congs <- c(111, 112, 113, 114, 115)
base  <- "https://voteview.com/static/data/out"
dir.create("data", showWarnings = FALSE)

dl <- function(kind, c) {
  f <- sprintf("data/S%d_%s.csv", c, kind)
  if (!file.exists(f)) download.file(sprintf("%s/%s/S%d_%s.csv", base, kind, c, kind), f, quiet = TRUE, mode = "wb")
  read.csv(f, stringsAsFactors = FALSE)
}

votes <- lapply(congs, function(c) dl("votes", c))
membs <- lapply(congs, function(c) dl("members", c))
names(votes) <- names(membs) <- as.character(congs)

cat("== votes file columns ==\n"); print(colnames(votes[[1]]))
for (i in seq_along(congs)) {
  v <- votes[[i]]; m <- membs[[i]]
  m <- m[m$chamber == "Senate", ]
  cat(sprintf("S%d: %d vote-records, %d senators (members file), %d roll calls\n",
              congs[i], nrow(v), nrow(m), length(unique(v$rollnumber))))
}

# Build per-congress cast-code matrix (rows=icpsr senators, cols=rollnumber)
build_mat <- function(v, m) {
  sen <- m[m$chamber == "Senate", ]
  v <- v[v$icpsr %in% sen$icpsr, ]                  # senators only (drop president)
  rolls <- sort(unique(v$rollnumber)); ids <- sort(unique(v$icpsr))
  M <- matrix(0L, length(ids), length(rolls), dimnames = list(ids, rolls))
  M[cbind(match(v$icpsr, ids), match(v$rollnumber, rolls))] <- as.integer(v$cast_code)
  M
}
mats <- Map(build_mat, votes, membs)
for (i in seq_along(congs)) cat(sprintf("S%d matrix: %d x %d\n", congs[i], nrow(mats[[i]]), ncol(mats[[i]])))

# pscl rollcall objects for dwnominate (codes mirror voteview cast_code).
# legis.data MUST carry an id + party (dwnominate/wnominate cbind against it).
party_lbl <- function(pc) ifelse(pc == 100, "D", ifelse(pc == 200, "R", "I"))
rcs <- lapply(seq_along(congs), function(i) {
  M <- mats[[i]]; m <- membs[[i]]; m <- m[m$chamber == "Senate", ]
  ld <- data.frame(icpsr = as.integer(rownames(M)),
                   party = party_lbl(m$party_code[match(as.integer(rownames(M)), m$icpsr)]),
                   stringsAsFactors = FALSE, row.names = rownames(M))
  rollcall(M, yea = 1:3, nay = 4:6, missing = 7:9, notInLegis = 0,
           legis.names = rownames(M), vote.names = colnames(M),
           legis.data = ld, desc = paste0("S", congs[i]))
})
names(rcs) <- as.character(congs)
saveRDS(rcs, "data/rollcall_list.rds")
saveRDS(membs, "data/members_list.rds")

# ---- QV C++ inputs: GLOBAL roster (union of icpsr across congresses) ----
global_ids <- sort(unique(unlist(lapply(mats, rownames))))
cat(sprintf("\nGlobal roster (union): %d unique senators across %d congresses\n",
            length(global_ids), length(congs)))
recode <- function(x) {  # preserve matrix shape + dimnames (ifelse strips them)
  v <- ifelse(x %in% 1:3, 1L, ifelse(x %in% 4:6, 6L, 9L)); v[is.na(v)] <- 9L
  matrix(v, nrow = nrow(x), ncol = ncol(x), dimnames = dimnames(x))
}

dir.create("cpp_input", showWarnings = FALSE)
for (i in seq_along(congs)) {
  M <- mats[[i]]; R <- recode(M)
  full <- matrix(9L, length(global_ids), ncol(M), dimnames = list(global_ids, colnames(M)))
  full[rownames(R), ] <- R                          # absent senators -> all 9 (missing)
  df <- data.frame(full, check.names = FALSE)
  # quote = FALSE: rownames are character ids, and write.csv quotes character.
  # The Fortran harness reads the id field list-directed into an INTEGER, so a
  # quoted "10808" aborts the whole matrix load (same defect class as the seed).
  write.csv(df, sprintf("cpp_input/votes_matrix_p%d.csv", i), row.names = TRUE,
            quote = FALSE)
}

# Seed coords: per-congress W-NOMINATE, each member seeded from the FIRST congress
# they served in, mapped to the global roster.
# (C++ uses one starting-coord file keyed by legislator_id.)
#
# Fitting rcs[[1]] alone and initialising the whole union roster at (0,0) left 61 of
# 168 members at exactly the origin, the one point that carries no information about
# which side of a cutting plane a member falls on.
#
# polarity = c(1,1) means "row 1 of THIS congress", and row 1 is a different senator
# in each congress, so fitting all five that way would orient each period against a
# different person. Use one anchor legislator present in every congress, resolved to
# its row index within each. Averaging the periods is not an option: the per-period
# frames are not mutually rotated, so a mean mixes frames and shrinks the
# configuration toward the origin, which is the defect being repaired. Taking one
# period keeps a single coherent frame.
present_all <- Reduce(intersect, lapply(mats, rownames))
party_of <- function(id) {
  for (i in seq_along(congs)) {
    m <- membs[[i]]; m <- m[m$chamber == "Senate", ]
    p <- m$party_code[match(as.integer(id), m$icpsr)]
    if (!is.na(p)) return(p)
  }
  NA
}
reps <- present_all[sapply(present_all, function(id) isTRUE(party_of(id) == 200))]
if (length(reps) == 0) stop("no Republican present in all congresses: no stable polarity anchor")
anchor <- sort(as.integer(reps))[1]
cat(sprintf("polarity anchor: icpsr %d, present in all %d congresses\n", anchor, length(congs)))

fits <- lapply(seq_along(congs), function(i) {
  a <- match(as.character(anchor), rownames(mats[[i]]))
  w <- wnominate(rcs[[i]], polarity = c(a, a), dims = 2, minvotes = 20, verbose = FALSE)
  stopifnot(nrow(w$legislators) == nrow(rcs[[i]]$votes))
  df <- data.frame(legislator_id = rownames(rcs[[i]]$votes),
                   coord1D = w$legislators$coord1D,
                   coord2D = w$legislators$coord2D,
                   stringsAsFactors = FALSE)
  df <- df[!is.na(df$coord1D) & !is.na(df$coord2D), ]
  cat(sprintf("S%d: %d of %d legislators fitted\n", congs[i], nrow(df), nrow(rcs[[i]]$votes)))
  df
})

# Sign alignment to period 1. The anchor fixes orientation in principle, but a
# dimension can still invert when the anchor sits near the origin on that axis.
# Check explicitly on the overlapping legislators and flip only on a negative
# correlation. Report every flip rather than doing it silently.
for (i in seq_along(fits)[-1]) {
  ref <- fits[[1]]; cur <- fits[[i]]
  common <- intersect(ref$legislator_id, cur$legislator_id)
  if (length(common) < 10) {
    cat(sprintf("S%d: only %d overlapping, no flip check\n", congs[i], length(common))); next
  }
  for (k in c("coord1D", "coord2D")) {
    r <- cor(ref[[k]][match(common, ref$legislator_id)], cur[[k]][match(common, cur$legislator_id)])
    if (!is.na(r) && r < 0) {
      cur[[k]] <- -cur[[k]]
      cat(sprintf("S%d %s: FLIPPED (r was %.4f on %d overlapping)\n", congs[i], k, r, length(common)))
    } else {
      cat(sprintf("S%d %s: kept (r = %.4f on %d overlapping)\n", congs[i], k, r, length(common)))
    }
  }
  fits[[i]] <- cur
}

# First served congress wins. Row order follows global_ids so the seed stays aligned
# row-for-row with cpp_input/votes_matrix_p*.csv; do not re-sort here.
seed <- data.frame(coord1D = 0.0, coord2D = 0.0, legislator_id = global_ids,
                   legislator_name = "", party = "", stringsAsFactors = FALSE)
seeded <- rep(FALSE, nrow(seed))
for (i in seq_along(fits)) {
  f <- fits[[i]]
  j <- match(f$legislator_id, seed$legislator_id)
  take <- !is.na(j) & !seeded[j]
  seed$coord1D[j[take]] <- f$coord1D[take]
  seed$coord2D[j[take]] <- f$coord2D[take]
  seeded[j[take]] <- TRUE
}
cat(sprintf("seeded %d of %d; still at origin: %d (no W-NOMINATE estimate in ANY congress)\n",
            sum(seeded), nrow(seed), sum(!seeded)))

# legislator_id must be written UNQUOTED. global_ids comes from matrix rownames and is
# therefore character; write.csv quotes character columns; and the Fortran harness reads
# that field list-directed into an INTEGER. The read fails on the first data row and no
# coordinate is applied at all, while the harness still prints that it loaded them.
seed$legislator_id <- as.integer(seed$legislator_id)
write.csv(seed, "cpp_input/wnominate_coordinates.csv", row.names = FALSE)

# Published VoteView DW-NOMINATE per (congress, icpsr) for the validity check
pub <- do.call(rbind, lapply(seq_along(congs), function(i) {
  m <- membs[[i]]; m <- m[m$chamber == "Senate", ]
  data.frame(period = i, congress = congs[i], legislator_id = m$icpsr,
             vv_dim1 = m$nominate_dim1, vv_dim2 = m$nominate_dim2,
             party_code = m$party_code, bioname = m$bioname, stringsAsFactors = FALSE)
}))
write.csv(pub, "voteview_published.csv", row.names = FALSE)
cat(sprintf("WROTE cpp_input/ (3 matrices + seed) and voteview_published.csv (%d rows)\n", nrow(pub)))
cat("Saved data/rollcall_list.rds for the dwnominate run.\n")
