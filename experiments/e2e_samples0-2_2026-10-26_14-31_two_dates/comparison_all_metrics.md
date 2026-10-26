## F1 by category, mean ± std over 3 runs (seeds 42, 43, 44)

| Split | A-MEM | T-MEM one date | T-MEM two dates |
|---|---|---|---|
| Overall | **0.3905 ± 0.0025** | 0.3817 ± 0.0038 | 0.3879 ± 0.0045 |
| Cat 1 multi-hop | **0.2788 ± 0.0060** | 0.2774 ± 0.0143 | 0.2770 ± 0.0141 |
| Cat 2 temporal | 0.4399 ± 0.0086 | 0.4591 ± 0.0137 | **0.4976 ± 0.0185** |
| Cat 3 open-domain | 0.0914 ± 0.0061 | **0.1151 ± 0.0250** | 0.1047 ± 0.0201 |
| Cat 4 single-hop | **0.3726 ± 0.0102** | 0.3644 ± 0.0066 | 0.3650 ± 0.0079 |
| Cat 5 adversarial | **0.5127 ± 0.0202** | 0.4694 ± 0.0163 | 0.4667 ± 0.0202 |

## All metrics, overall, mean ± std

| Metric | A-MEM | T-MEM one date | T-MEM two dates |
|---|---|---|---|
| f1 | **0.3905 ± 0.0025** | 0.3817 ± 0.0038 | 0.3879 ± 0.0045 |
| exact_match | **0.1583 ± 0.0061** | 0.1455 ± 0.0071 | 0.1496 ± 0.0023 |
| rougeL_f | **0.3910 ± 0.0026** | 0.3859 ± 0.0037 | 0.3891 ± 0.0062 |
| bleu1 | **0.3353 ± 0.0024** | 0.3222 ± 0.0051 | 0.3238 ± 0.0031 |
| meteor | **0.2985 ± 0.0050** | 0.2887 ± 0.0081 | 0.2944 ± 0.0087 |
| bert_f1 | **0.9111 ± 0.0001** | 0.9098 ± 0.0004 | 0.9101 ± 0.0009 |
| sbert_similarity | **0.5391 ± 0.0023** | 0.5327 ± 0.0043 | 0.5288 ± 0.0079 |

## Per-run overall F1

| Config | seed 42 | seed 43 | seed 44 | Range |
|---|---|---|---|---|
| A-MEM | 0.3881 | 0.3901 | 0.3932 | 0.0051 |
| T-MEM one date | 0.3847 | 0.3774 | 0.3831 | 0.0073 |
| T-MEM two dates | 0.3834 | 0.3923 | 0.3878 | 0.0089 |

## T-MEM two dates minus A-MEM

| Split | seed 42 | seed 43 | seed 44 | Mean Δ | Seeds where B > A |
|---|---|---|---|---|---|
| Overall | -0.0047 | +0.0022 | -0.0054 | -0.0026 | 1/3 |
| Cat 1 multi-hop | -0.0038 | +0.0179 | -0.0193 | -0.0017 | 1/3 |
| Cat 2 temporal | +0.0782 | +0.0370 | +0.0581 | +0.0578 | 3/3 |
| Cat 3 open-domain | +0.0008 | -0.0042 | +0.0434 | +0.0133 | 2/3 |
| Cat 4 single-hop | -0.0282 | -0.0002 | +0.0058 | -0.0075 | 1/3 |
| Cat 5 adversarial | -0.0311 | -0.0305 | -0.0762 | -0.0459 | 0/3 |

Question-level F1 averaged over runs: 126 better, 138 worse, 233 same; sign-test p = 0.50

## T-MEM two dates minus T-MEM one date

| Split | seed 42 | seed 43 | seed 44 | Mean Δ | Seeds where B > A |
|---|---|---|---|---|---|
| Overall | -0.0013 | +0.0150 | +0.0047 | +0.0061 | 2/3 |
| Cat 1 multi-hop | -0.0184 | +0.0312 | -0.0138 | -0.0003 | 1/3 |
| Cat 2 temporal | +0.0642 | +0.0035 | +0.0478 | +0.0385 | 3/3 |
| Cat 3 open-domain | +0.0038 | -0.0506 | +0.0155 | -0.0104 | 2/3 |
| Cat 4 single-hop | -0.0093 | +0.0111 | +0.0002 | +0.0007 | 2/3 |
| Cat 5 adversarial | -0.0292 | +0.0327 | -0.0116 | -0.0027 | 1/3 |

Question-level F1 averaged over runs: 127 better, 109 worse, 261 same; sign-test p = 0.27
