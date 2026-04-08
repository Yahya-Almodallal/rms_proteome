#!/usr/bin/env Rscript

# Plot PXD042840 target expression support across the 3 conditions.
#
# Important limitation:
# - Each condition is a single processed run, not a biological replicate set.
# - The y-values therefore reflect PSM-level abundance support, not replicate-level
#   protein abundance.

args <- commandArgs(trailingOnly = TRUE)

input_tsv <- if (length(args) >= 1) args[[1]] else "results/tmt_ccle_depmap/PXD042840_target_psm_quant.tsv"
output_png <- if (length(args) >= 2) args[[2]] else "results/tmt_ccle_depmap/PXD042840_expression_proxy.png"

if (!file.exists(input_tsv)) {
  stop(sprintf("Input TSV not found: %s", input_tsv))
}

dir.create(dirname(output_png), recursive = TRUE, showWarnings = FALSE)

df <- read.delim(input_tsv, sep = "\t", check.names = FALSE, stringsAsFactors = FALSE)

targets <- c("MYMK", "MYMX", "MYOD1", "MYOG")
conditions <- c("blank", "EV71", "EV71_PZH")
condition_cols <- c("blank" = "#4E79A7", "EV71" = "#E15759", "EV71_PZH" = "#59A14F")
condition_pch <- c("blank" = 16, "EV71" = 17, "EV71_PZH" = 15)

as_num <- function(x) {
  x <- trimws(as.character(x))
  x[x == ""] <- NA
  suppressWarnings(as.numeric(x))
}

df <- df[df$gene %in% targets & df$condition %in% conditions, , drop = FALSE]
df$gene <- factor(df$gene, levels = targets)
df$condition <- factor(df$condition, levels = conditions)
df$abundance_proxy_num <- as_num(df$abundance_proxy)
df$log2_abundance_proxy <- ifelse(!is.na(df$abundance_proxy_num) & df$abundance_proxy_num > 0,
                                  log2(df$abundance_proxy_num), NA_real_)

png(output_png, width = 1900, height = 980, res = 140)
layout(matrix(c(1, 2), nrow = 1), widths = c(3.3, 1.4))

par(mar = c(9.2, 5, 4.2, 7))

base_pos <- seq_along(targets)
offsets <- c(-0.22, 0, 0.22)
names(offsets) <- conditions

all_vals <- df$log2_abundance_proxy
y_lim <- range(all_vals, na.rm = TRUE)
plot(NA,
     xlim = c(0.5, length(targets) + 0.6),
     ylim = y_lim,
     xaxt = "n",
     xlab = "",
     ylab = "log2(abundance proxy)",
     main = "PXD042840 target expression support by condition")

axis(1, at = base_pos, labels = targets, las = 1)

for (cond in conditions) {
  sub <- df[df$condition == cond & !is.na(df$log2_abundance_proxy), , drop = FALSE]
  groups <- split(sub$log2_abundance_proxy, sub$gene)
  groups <- groups[targets]
  pos <- base_pos + offsets[cond]

  for (i in seq_along(groups)) {
    vals <- groups[[i]]
    if (length(vals) > 0) {
      boxplot(vals,
              at = pos[i],
              add = TRUE,
              boxwex = 0.18,
              outline = FALSE,
              xaxt = "n",
              yaxt = "n",
              col = adjustcolor(condition_cols[cond], alpha.f = 0.22),
              border = condition_cols[cond])
      points(jitter(rep(pos[i], length(vals)), amount = 0.04),
             vals,
             pch = condition_pch[cond],
             col = adjustcolor(condition_cols[cond], alpha.f = 0.9),
             cex = 1.05)
    }
  }
}

legend("topright",
       inset = c(-0.18, 0),
       xpd = NA,
       legend = conditions,
       col = condition_cols,
       pch = condition_pch,
       bty = "n",
       cex = 0.95)

mtext("Abundance proxy = PrecursorAbundance when present, else PSM (peptide-spectrum match) Intensity; single-run conditions, so boxes summarize PSMs not replicates", side = 1, line = 5.8, cex = 0.78, adj = 0.15)
mtext("blank = control RD cells; EV71 = EV-A71-infected RD cells; EV71_PZH = EV-A71-infected RD cells treated with PZH", side = 1, line = 6.9, cex = 0.78, adj = 0.15)

par(mar = c(9.2, 5, 4.2, 3))

count_df <- aggregate(peptide_id ~ gene + condition, data = df, FUN = length)
count_mat <- matrix(0, nrow = length(targets), ncol = length(conditions),
                    dimnames = list(targets, conditions))
for (i in seq_len(nrow(count_df))) {
  count_mat[as.character(count_df$gene[i]), as.character(count_df$condition[i])] <- count_df$peptide_id[i]
}

mat_plot <- count_mat[rev(rownames(count_mat)), , drop = FALSE]
pal <- colorRampPalette(c("#FFFFFF", "#163A63"))(100)

image(
  x = seq_len(ncol(mat_plot)),
  y = seq_len(nrow(mat_plot)),
  z = t(mat_plot),
  col = pal,
  xaxt = "n",
  yaxt = "n",
  xlab = "",
  ylab = "",
  main = "Linked PSM count",
  zlim = c(0, max(mat_plot))
)

axis(1, at = seq_len(ncol(mat_plot)), labels = colnames(mat_plot), las = 2, cex.axis = 0.9)
axis(2, at = seq_len(nrow(mat_plot)), labels = rownames(mat_plot), las = 2, cex.axis = 0.9)

for (i in seq_len(nrow(mat_plot))) {
  for (j in seq_len(ncol(mat_plot))) {
    text(j, i, labels = sprintf("%d", mat_plot[i, j]), cex = 0.85,
         col = ifelse(mat_plot[i, j] > max(mat_plot) * 0.45, "white", "black"))
  }
}

dev.off()

message("Plot written: ", output_png)
