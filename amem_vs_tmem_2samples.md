# A-MEM vs T-MEM Comparison

- A-MEM file: `robust`
- T-MEM file: `tmem_robust`
- Dataset: `/Users/rajanyadav/Desktop/Projects/A-mem/data/locomo10.json` vs `/Users/rajanyadav/Desktop/Projects/A-mem/data/locomo10.json`
- Total questions: `304` vs `304`
- T-MEM temporal config: `alpha=0.7`, `lambda=0.1`, `decay_only=True`

## Question-Level F1 Summary

- Matched questions: `304`
- T-MEM better F1: `57`
- A-MEM better F1: `95`
- Ties: `152`

### Overall

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.1480 | 0.0822 | -0.0658 |
| f1 | 0.3613 | 0.2768 | -0.0845 |
| rougeL_f | 0.3689 | 0.2798 | -0.0891 |
| bleu1 | 0.3144 | 0.2340 | -0.0804 |
| bert_f1 | 0.9074 | 0.8962 | -0.0112 |
| meteor | 0.2868 | 0.2190 | -0.0678 |
| sbert_similarity | 0.5153 | 0.4275 | -0.0877 |

### Category 1

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.0233 | 0.0233 | +0.0000 |
| f1 | 0.1978 | 0.1609 | -0.0370 |
| rougeL_f | 0.1749 | 0.1431 | -0.0318 |
| bleu1 | 0.1529 | 0.1149 | -0.0380 |
| bert_f1 | 0.8746 | 0.8684 | -0.0062 |
| meteor | 0.0814 | 0.0847 | +0.0033 |
| sbert_similarity | 0.3936 | 0.3421 | -0.0515 |

### Category 2

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.1111 | 0.0317 | -0.0794 |
| f1 | 0.4455 | 0.3579 | -0.0875 |
| rougeL_f | 0.4537 | 0.3571 | -0.0966 |
| bleu1 | 0.3795 | 0.2904 | -0.0891 |
| bert_f1 | 0.9211 | 0.9113 | -0.0098 |
| meteor | 0.2769 | 0.1873 | -0.0896 |
| sbert_similarity | 0.6950 | 0.5924 | -0.1027 |

### Category 3

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.0000 | 0.0000 | +0.0000 |
| f1 | 0.1107 | 0.0923 | -0.0184 |
| rougeL_f | 0.1138 | 0.1154 | +0.0016 |
| bleu1 | 0.0952 | 0.1148 | +0.0196 |
| bert_f1 | 0.8761 | 0.8721 | -0.0040 |
| meteor | 0.0794 | 0.0839 | +0.0046 |
| sbert_similarity | 0.4331 | 0.4366 | +0.0035 |

### Category 4

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.0877 | 0.0351 | -0.0526 |
| f1 | 0.3203 | 0.2340 | -0.0863 |
| rougeL_f | 0.3446 | 0.2471 | -0.0974 |
| bleu1 | 0.2622 | 0.1835 | -0.0787 |
| bert_f1 | 0.8999 | 0.8877 | -0.0122 |
| meteor | 0.2843 | 0.2165 | -0.0678 |
| sbert_similarity | 0.4682 | 0.3747 | -0.0934 |

### Category 5

| Metric | A-MEM | T-MEM | Delta (T-A) |
| --- | ---: | ---: | ---: |
| exact_match | 0.3803 | 0.2535 | -0.1268 |
| f1 | 0.4974 | 0.3778 | -0.1196 |
| rougeL_f | 0.4969 | 0.3764 | -0.1205 |
| bleu1 | 0.4784 | 0.3588 | -0.1195 |
| bert_f1 | 0.9328 | 0.9177 | -0.0151 |
| meteor | 0.4620 | 0.3572 | -0.1047 |
| sbert_similarity | 0.5201 | 0.4161 | -0.1040 |

