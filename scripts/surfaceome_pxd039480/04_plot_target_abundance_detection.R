#!/usr/bin/env Rscript

# Plot per-protein abundance distributions and detection frequency for key targets.
#
# This script uses the extracted TSV from scripts/surfaceome_pxd039480/03_extract_targets_from_pxd039480.py
# and creates a 2-panel figure:
# 1) Main panel: box + jitter of log2(iTop3) (or log2(Top3)) across replicates.
# 2) Side panel: detection frequency heatmap (% detected) by protein x sample class.

args <- commandArgs(trailingOnly = TRUE)

input_tsv <- if (length(args) >= 1) args[[1]] else "results/surfaceome_pxd039480/targets_pxd039480_proteinGroups_cleaned.tsv"
output_png <- if (length(args) >= 2) args[[2]] else "results/surfaceome_pxd039480/target_abundance_detection_itop3.png"
metric_pref <- if (length(args) >= 3) args[[3]] else "iTop3"   # allowed: iTop3 or Top3

if (!file.exists(input_tsv)) {
  stop(sprintf("Input TSV not found: %s", input_tsv))
}

dir.create(dirname(output_png), recursive = TRUE, showWarnings = FALSE)

# Read table exactly as-is. keep names and avoid factor conversion.
df <- read.delim(input_tsv, sep = "\t", check.names = FALSE, stringsAsFactors = FALSE)

# Core proteins tracked across datasets.
targets <- c("MYMX", "MYMK", "MYOD1", "MYOG")

df$matched_targets <- ifelse(is.na(df$matched_targets), "", df$matched_targets)
df$GN <- ifelse(is.na(df$GN), "", df$GN)

# Keep rows that mention one of our targets.
has_target <- function(row_text) {
  any(targets %in% unlist(strsplit(row_text, ";", fixed = TRUE)))
}

keep <- vapply(df$matched_targets, has_target, logical(1)) | (df$GN %in% targets)
sub <- df[keep, , drop = FALSE]

if (nrow(sub) == 0) {
  stop("No target rows found in input TSV.")
}

# Decide whether to use iTop3 or Top3 columns.
metric_candidates <- if (metric_pref == "Top3") c("Top3 ", "iTop3 ") else c("iTop3 ", "Top3 ")
metric_prefix <- ""
metric_cols <- character(0)
for (prefix in metric_candidates) {
  cols <- grep(paste0("^", prefix), names(sub), value = TRUE)
  if (length(cols) > 0) {
    metric_prefix <- prefix
    metric_cols <- cols
    break
  }
}

if (length(metric_cols) == 0) {
  stop("No Top3/iTop3 columns found in input TSV.")
}

# Convert intensity text to numeric safely.
as_num <- function(x) {
  x <- trimws(as.character(x))
  x[x == ""] <- NA
  suppressWarnings(as.numeric(x))
}

# Pick one representative row per target gene.
# Rule: choose row with highest number of detected replicates (non-missing and >0),
# then highest mean log2 intensity among detected replicates.
pick_best_row <- function(gene) {
  idx <- which(vapply(sub$matched_targets, function(x) gene %in% unlist(strsplit(x, ";", fixed = TRUE)), logical(1)) |
                 sub$GN == gene)

  if (length(idx) == 0) {
    return(NA_integer_)
  }

  det_counts <- numeric(length(idx))
  means <- numeric(length(idx))

  for (i in seq_along(idx)) {
    vals <- as_num(unlist(sub[idx[i], metric_cols, drop = TRUE]))
    detected <- !is.na(vals) & vals > 0
    det_counts[i] <- sum(detected)
    means[i] <- if (any(detected)) mean(log2(vals[detected])) else -Inf
  }

  best_local <- which(det_counts == max(det_counts))
  if (length(best_local) > 1) {
    best_local <- best_local[which.max(means[best_local])]
  }
  idx[best_local[1]]
}

selected_idx <- vapply(targets, pick_best_row, integer(1))
selected <- sub[selected_idx[!is.na(selected_idx)], , drop = FALSE]

# If some proteins are missing, keep going but warn.
missing_targets <- setdiff(targets, selected$GN)
if (length(missing_targets) > 0) {
  message("Targets not found as GN in selected rows: ", paste(missing_targets, collapse = ", "))
}

# Build long replicate-level table.
long <- data.frame(
  protein = character(0),
  sample = character(0),
  sample_group = character(0),
  sample_class = character(0),
  intensity = numeric(0),
  detected = logical(0),
  stringsAsFactors = FALSE
)

# Sample class mapping.
# Note: fusion class assignments should be verified against study metadata.
sample_class_map <- c(
  # Controls
  MRC5 = "Control", Myo = "Control",
  # PDX
  PDXs16 = "PDX", PDXs29 = "PDX", PDXs35 = "PDX",
  # FP-RMS (working mapping)
  RH4 = "FP-RMS", Rh4 = "FP-RMS", Rh5 = "FP-RMS", Rh28 = "FP-RMS", Rh30 = "FP-RMS", RMS = "FP-RMS", Ruch3 = "FP-RMS",
  # FN-RMS (working mapping)
  RD = "FN-RMS", Rh18 = "FN-RMS", Rh36 = "FN-RMS", JR = "FN-RMS", TTC442 = "FN-RMS"
)

class_levels <- c("Control", "PDX", "FP-RMS", "FN-RMS", "Unknown")
protein_levels <- targets

for (i in seq_len(nrow(selected))) {
  gene <- selected$GN[i]
  vals <- as_num(unlist(selected[i, metric_cols, drop = TRUE]))
  samp <- sub(paste0("^", metric_prefix), "", metric_cols)
  grp <- sub("_[0-9]+$", "", samp)

  cls <- ifelse(grp %in% names(sample_class_map), sample_class_map[grp], "Unknown")
  detected <- !is.na(vals) & vals > 0

  long <- rbind(
    long,
    data.frame(
      protein = gene,
      sample = samp,
      sample_group = grp,
      sample_class = cls,
      intensity = vals,
      detected = detected,
      stringsAsFactors = FALSE
    )
  )
}

# Prepare factors for stable plotting order.
long$protein <- factor(long$protein, levels = protein_levels)
long$sample_class <- factor(long$sample_class, levels = class_levels)

# For abundance panel: use log2 intensity only for detected values.
long$log2_intensity <- ifelse(long$detected, log2(long$intensity), NA_real_)

# Detection frequency matrix: protein x class.
freq <- aggregate(detected ~ protein + sample_class, data = long, FUN = function(x) 100 * mean(x))

# Convert to full matrix with explicit missing cells.
freq_mat <- matrix(NA_real_, nrow = length(protein_levels), ncol = length(class_levels),
                   dimnames = list(protein_levels, class_levels))
for (i in seq_len(nrow(freq))) {
  p <- as.character(freq$protein[i])
  c <- as.character(freq$sample_class[i])
  freq_mat[p, c] <- freq$detected[i]
}

# Colors by sample class.
class_cols <- c("Control" = "#4E79A7", "PDX" = "#E15759", "FP-RMS" = "#59A14F", "FN-RMS" = "#F28E2B", "Unknown" = "#9D9D9D")
pt_cols <- class_cols[as.character(long$sample_class)]

png(output_png, width = 1800, height = 900, res = 140)
layout(matrix(c(1, 2), nrow = 1), widths = c(3.4, 1.6))

# --- Main panel: box + jitter ---
# Extra right margin is reserved for the legend to avoid overlap with points.
par(mar = c(9, 5, 4, 6))

plot_data <- split(long$log2_intensity, long$protein)
boxplot(plot_data,
        outline = FALSE,
        col = "#F2F2F2",
        border = "#6E6E6E",
        ylab = paste0("log2(", trimws(metric_prefix), ")"),
        xlab = "",
        main = "Protein abundance across replicates",
        xaxt = "n",  # draw x-axis labels only once (custom axis call below)
        names = rep("", length(plot_data)),
        xlim = c(0.5, length(protein_levels) + 0.8))

# Add jittered points by sample class.
x_pos <- as.numeric(long$protein)
jitter_x <- jitter(x_pos, amount = 0.18)
points(jitter_x, long$log2_intensity, pch = 16, col = adjustcolor(pt_cols, alpha.f = 0.8), cex = 1.05)

axis(1, at = seq_along(protein_levels), labels = protein_levels, las = 1)
legend("topright",
       inset = c(-0.13, 0),
       xpd = NA,
       legend = names(class_cols),
       col = class_cols,
       pch = 16,
       bty = "n",
       cex = 0.9)

mtext("Missing/zero intensities are treated as not detected and excluded from y-values", side = 1, line = 7.8, cex = 0.8)

# --- Side panel: detection frequency heatmap ---
par(mar = c(9, 4, 4, 4))

# image() starts at bottom-left, so reverse row order for top-to-bottom labels.
mat_plot <- freq_mat[rev(rownames(freq_mat)), , drop = FALSE]

# Detection color scale.
pal <- colorRampPalette(c("#FFFFFF", "#7A1E1E"))(100)

image(
  x = seq_len(ncol(mat_plot)),
  y = seq_len(nrow(mat_plot)),
  z = t(mat_plot),
  col = pal,
  xaxt = "n",
  yaxt = "n",
  xlab = "",
  ylab = "",
  main = "Detection frequency (%)",
  zlim = c(0, 100)
)

axis(1, at = seq_len(ncol(mat_plot)), labels = colnames(mat_plot), las = 2, cex.axis = 0.9)
axis(2, at = seq_len(nrow(mat_plot)), labels = rownames(mat_plot), las = 2, cex.axis = 0.9)

# Overlay numeric percentages.
for (i in seq_len(nrow(mat_plot))) {
  for (j in seq_len(ncol(mat_plot))) {
    v <- mat_plot[i, j]
    if (!is.na(v)) {
      text(j, i, labels = sprintf("%.0f", v), cex = 0.75, col = ifelse(v > 60, "white", "black"))
    }
  }
}

# Colorbar (simple manual legend).
usr <- par("usr")
x0 <- usr[2] + 0.35
x1 <- usr[2] + 0.6
y0 <- usr[3]
y1 <- usr[4]
ys <- seq(y0, y1, length.out = 100)
for (k in seq_len(99)) {
  rect(x0, ys[k], x1, ys[k + 1], col = pal[k], border = NA, xpd = NA)
}
text(x1 + 0.08, y0, "0", xpd = NA, cex = 0.8, adj = c(0, 0.5))
text(x1 + 0.08, y1, "100", xpd = NA, cex = 0.8, adj = c(0, 0.5))
text(x1 + 0.08, (y0 + y1) / 2, "%", xpd = NA, srt = 90, cex = 0.9)

# Save a long-format table for downstream stats/replots.
out_long <- sub("\\.png$", "_long.tsv", output_png)
write.table(long, file = out_long, sep = "\t", quote = FALSE, row.names = FALSE)

dev.off()

message("Plot written: ", output_png)
message("Long-format table: ", out_long)
message("Metric used: ", trimws(metric_prefix))
