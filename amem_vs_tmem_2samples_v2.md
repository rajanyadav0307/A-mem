# A-MEM vs T-MEM Comparison

- A-MEM file: `robust`
- T-MEM file: `tmem_robust`
- Dataset: `/Users/rajanyadav/Desktop/Projects/A-mem/data/locomo10.json` vs `/Users/rajanyadav/Desktop/Projects/A-mem/data/locomo10.json`
- Total questions: `304` vs `304`
- T-MEM temporal config: `alpha=0.9`, `lambda=0.1`, `decay_only=True`

## Question-Level F1 Summary

- Matched questions: `304`
- T-MEM better F1: `58`
- A-MEM better F1: `58`
- Ties: `188`

### Overall

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.1480 | 0.1480 | +0.0000 |
| f1 | 0.3613 | 0.3686 | +0.0072 |
| rougeL_f | 0.3689 | 0.3742 | +0.0053 |
| bleu1 | 0.3144 | 0.3164 | +0.0021 |
| bert_f1 | 0.9074 | 0.9069 | -0.0005 |
| meteor | 0.2868 | 0.2830 | -0.0038 |
| sbert_similarity | 0.5153 | 0.5217 | +0.0064 |

### Category 1

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.0233 | 0.0233 | +0.0000 |
| f1 | 0.1978 | 0.1920 | -0.0059 |
| rougeL_f | 0.1749 | 0.1875 | +0.0126 |
| bleu1 | 0.1529 | 0.1498 | -0.0030 |
| bert_f1 | 0.8746 | 0.8731 | -0.0015 |
| meteor | 0.0814 | 0.0735 | -0.0079 |
| sbert_similarity | 0.3936 | 0.4050 | +0.0114 |

### Category 2

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.1111 | 0.0635 | -0.0476 |
| f1 | 0.4455 | 0.4610 | +0.0155 |
| rougeL_f | 0.4537 | 0.4627 | +0.0090 |
| bleu1 | 0.3795 | 0.3737 | -0.0058 |
| bert_f1 | 0.9211 | 0.9196 | -0.0015 |
| meteor | 0.2769 | 0.2453 | -0.0316 |
| sbert_similarity | 0.6950 | 0.7001 | +0.0050 |

### Category 3

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.0000 | 0.0000 | +0.0000 |
| f1 | 0.1107 | 0.1073 | -0.0035 |
| rougeL_f | 0.1138 | 0.1218 | +0.0080 |
| bleu1 | 0.0952 | 0.1127 | +0.0175 |
| bert_f1 | 0.8761 | 0.8725 | -0.0036 |
| meteor | 0.0794 | 0.0965 | +0.0172 |
| sbert_similarity | 0.4331 | 0.4215 | -0.0116 |

### Category 4

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.0877 | 0.0614 | -0.0263 |
| f1 | 0.3203 | 0.3130 | -0.0073 |
| rougeL_f | 0.3446 | 0.3273 | -0.0173 |
| bleu1 | 0.2622 | 0.2440 | -0.0182 |
| bert_f1 | 0.8999 | 0.8968 | -0.0031 |
| meteor | 0.2843 | 0.2699 | -0.0144 |
| sbert_similarity | 0.4682 | 0.4538 | -0.0144 |

### Category 5

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.3803 | 0.4648 | +0.0845 |
| f1 | 0.4974 | 0.5305 | +0.0330 |
| rougeL_f | 0.4969 | 0.5305 | +0.0336 |
| bleu1 | 0.4784 | 0.5201 | +0.0418 |
| bert_f1 | 0.9328 | 0.9387 | +0.0058 |
| meteor | 0.4620 | 0.4985 | +0.0365 |
| sbert_similarity | 0.5201 | 0.5614 | +0.0414 |

