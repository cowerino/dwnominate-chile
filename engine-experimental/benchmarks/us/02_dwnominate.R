# Canonical DW-NOMINATE (McCarty's Fortran via the wmay dwnominate package)
# on the 3-congress US Senate island. This is our "oracle" run on clean data.
suppressMessages({library(dwnominate); library(pscl)})
rcs <- readRDS("data/rollcall_list.rds")
cat("Running dwnominate on", length(rcs), "sessions...\n")
res <- dwnominate(rcs, id = "icpsr", dims = 2, polarity = NULL)  # sign fixed later via Procrustes
cat("\n== dwnominate result structure ==\n"); print(names(res))
cat("\n== legislators columns ==\n"); print(colnames(res$legislators))
cat("\n== head ==\n"); print(head(res$legislators, 6))
cat("\n== rows per session ==\n"); print(table(res$legislators$session))
saveRDS(res, "data/dwnominate_result.rds")
write.csv(res$legislators, "fortran_dwnom.csv", row.names = FALSE)
cat("\nWROTE fortran_dwnom.csv + data/dwnominate_result.rds\n")
