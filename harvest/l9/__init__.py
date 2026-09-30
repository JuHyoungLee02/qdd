"""L9 diverse data generator (docs/superpowers/specs/2026-09-30-l9-diverse-datagen-design.md, stage 1: one arm)."""

# seed ranges per split (disjoint from every L8 range): pilots 900000-999999 (gate G1, their successes may train),
# production 1000000-1999999, held-out evaluation 2000000-2099999
SEEDS = {"train": range(900000, 2000000), "l9_eval": range(2000000, 2100000)}
