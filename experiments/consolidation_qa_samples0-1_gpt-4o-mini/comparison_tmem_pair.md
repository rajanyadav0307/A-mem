## F1 by category

| Split | n | T-MEM V2 | T-MEM V2 + C |
|---|---|---|---|
| Overall | 304 | 0.3689 | **0.3767** |
| Cat 1 multi-hop | 43 | 0.1757 | **0.2097** |
| Cat 2 temporal | 63 | **0.4813** | 0.4351 |
| Cat 3 open-domain | 13 | 0.1183 | **0.1413** |
| Cat 4 single-hop | 114 | 0.3038 | **0.3197** |
| Cat 5 adversarial | 71 | 0.5365 | **0.5605** |

## All metrics, overall

| Metric | T-MEM V2 | T-MEM V2 + C |
|---|---|---|
| f1 | 0.3689 | **0.3767** |
| exact_match | 0.1480 | **0.1513** |
| rougeL_f | **0.3805** | 0.3743 |
| bleu1 | 0.3265 | **0.3288** |
| meteor | **0.3015** | 0.2905 |
| bert_f1 | **0.9092** | 0.9088 |
| sbert_similarity | **0.5360** | 0.5291 |

## Question-level F1 vs T-MEM V2

| Run | Better | Worse | Same | Sign-test p |
|---|---|---|---|---|
| T-MEM V2 + C | 60 | 55 | 189 | 0.71 |
