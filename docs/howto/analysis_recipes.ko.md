# How-to: 그림이 인쇄하는 숫자를 계산하기

괄호 아래의 P값, 모서리의 Pearson r, 범례의 AUC, 곡선 옆의 EC50 — 이것은 **결과**이고, fig-atlas는 그것을 계산하지 않습니다. 분석 스크립트가 계산합니다. scipy, R, statsmodels, 연구가 이미 쓰는 무엇이든. 그림은 스크립트가 넘긴 값을 그릴 뿐입니다([결정 0007](../decisions/0007-renderers-draw-results-they-do-not-compute.md)).

이유는 결벽이 아닙니다. 검정은 설계에 달려 있습니다. 어떤 값들이 짝이고, 어느 개체가 대조군이며, 어떤 공변량이 있고, 어떤 값이 결측인지. 그 지식은 분석 스크립트에 있지, 잘 정돈된 표를 받는 렌더러에 있지 않습니다. 그래서 렌더러는 그리고, 스크립트가 결정합니다.

## 1. 모든 레시피가 공유하는 다섯 단계

| 단계 | 쓰는 것 | 도착하는 곳 |
|---|---|---|
| 계산 | 분석 스크립트에서 검정·적합·모형 | `analysis/<domain>/<category>/<project>_analysis.py` |
| 컬럼 쓰기 | `df["p_value"] = ...` | 패널이 그리는 표 |
| 표 등록 | `stats.record(table, name="paired_t", title="...")` | `outputs/publish/<project>/figure_NN_statistics/paired_t.csv` |
| 컬럼 이름 붙이기 | config의 `pvalue_col: p_value` | 패널의 `plots.<name>` 블록 |
| 범례에 설명 달기 | `claims.record("star_rule", ...)` | FigureSpec의 `{star_rule}` |

config 블록이 컬럼을 가리키고, 렌더러는 그것을 읽기만 합니다:

```yaml
plots:
  before_after:
    pvalue_col: "p_value"                                        # 분석 스크립트가 쓴 컬럼
    sig_thresholds: [[0.001, "***"], [0.01, "**"], [0.05, "*"]]  # P -> 기호, 임계값 오름차순
```

범례 문장은 같은 임계값으로 만들어지므로 별표와 어긋날 수 없습니다:

```python
from fig_atlas import claims

thresholds = cfg["plots"]["before_after"]["sig_thresholds"]
rule = "paired t-test, two-sided (" + ", ".join(f"{sym}P < {thr:g}" for thr, sym in thresholds) + ")"
claims.record("star_rule", rule, source=f"{__file__} (paired t-test on before/after)")
```

## 2. 전후 비교: 짝지은 검정

개체마다 한 행, 두 컬럼(before, after). 짝짓기는 설계이므로 렌더러가 아니라 여기 있습니다:

```python
import pandas as pd
from scipy.stats import ttest_rel, wilcoxon
from fig_atlas import stats

wide = load_pairs()                                     # subject, before, after
p = ttest_rel(wide["after"], wide["before"]).pvalue      # Student's paired t-test
# p = wilcoxon(wide["after"], wide["before"]).pvalue     # 차이가 정규분포가 아니면 Wilcoxon signed-rank

long = wide.melt(id_vars="subject", var_name="condition", value_name="value")
long["p_value"] = p                                     # 렌더러가 이 컬럼을 그린다

stats.record(pd.DataFrame({"test": ["paired t"], "n": [len(wide)], "p": [p]}),
             name="paired_t", title="Before vs after (two-sided paired t-test)")
```

R에서는 같은 단계가 한 줄이고, 표를 써 두면 스크립트가 읽습니다:

```r
p <- t.test(d$after, d$before, paired = TRUE)$p.value
write.csv(data.frame(test = "paired t", n = nrow(d), p = p), "paired_t.csv", row.names = FALSE)
```

## 3. 세 집단 이상: 사후 비교

먼저 전체 검정, 다음은 패널이 실제로 괄호로 묶는 비교들. 그리는 비교만 행이 필요합니다:

```python
import pandas as pd
from scipy.stats import tukey_hsd
from fig_atlas import stats

groups = [df.loc[df["group"] == g, "value"].to_numpy() for g in order]
res = tukey_hsd(*groups)                                # family-wise 보정이 Tukey 안에 있다
rows = [{"group_a": order[i], "group_b": order[j], "p_adj": float(res.pvalue[i, j])}
        for i in range(len(order)) for j in range(i + 1, len(order))]
comparisons = pd.DataFrame(rows)
stats.record(comparisons, name="posthoc", title="Tukey HSD, all pairwise comparisons")
```

대조군 하나와 비교할 때는 `scipy.stats.dunnett`(또는 `statsmodels.stats.multicomp`)을 쓰고, 괄호가 잇는 비교 옆에 나온 `p_adj`를 씁니다. R의 `emmeans::contrast(..., adjust = "tukey")`가 같은 표를 줍니다.

## 4. 두 변수: 상관과 회귀

r과 P는 인쇄되고, 직선은 그려집니다. 둘 다 여기 같은 적합에서 나오므로 숫자와 선이 어긋나지 않습니다:

```python
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from fig_atlas import stats

df = load_xy()                                           # 항목마다 한 행: x, y, group
r, p = pearsonr(df["x"], df["y"])                        # 순위라면 spearmanr
df["r"], df["p_value"] = r, p                            # r_col / p_col이 읽는다

stats.record(pd.DataFrame({"r": [r], "p": [p], "n": [len(df)]}),
             name="correlation", title="Pearson correlation")
```

config가 두 컬럼을 가리킵니다(`group_scatter`가 모서리에 그립니다):

```yaml
plots:
  signal_vs_quality:
    r_col: "r"            # 상관계수 컬럼 (패널마다 한 값)
    p_col: "p_value"      # 그리고 그 P
```

신뢰띠·예측띠도 같습니다. 격자와 띠의 경계를 스크립트에서 계산하고 적합 표를 등록하면, 띠를 그리는 렌더러는 좌표를 받습니다. 렌더러가 다시 적합해서 어느 숫자를 인쇄할지 정하게 두지 마세요.

## 5. 분류기: ROC와 AUC

곡선은 순위 매기기의 결과이므로 계산합니다. 곡선 자체에는 추가 의존성이 필요 없습니다:

```python
import numpy as np
import pandas as pd
from fig_atlas import stats

def roc(labels, scores):
    order = np.argsort(-np.asarray(scores))
    y = np.asarray(labels, dtype=float)[order]
    tpr = np.cumsum(y) / y.sum()
    fpr = np.cumsum(1.0 - y) / (1.0 - y).sum()
    return np.r_[0.0, fpr], np.r_[0.0, tpr], float(np.trapezoid(np.r_[0.0, tpr], np.r_[0.0, fpr]))

fpr, tpr, auc = roc(labels, scores)                      # numpy 2: trapezoid, 그 전에는 np.trapz
curve = pd.DataFrame({"fpr": fpr, "tpr": tpr, "auc": auc})
stats.record(curve, name="roc", title="ROC curve, cases versus controls")
```

AUC의 신뢰구간은 bootstrap 또는 DeLong의 일입니다. 스크립트에서 2000번 재표본하거나 R의 `pROC::ci.auc`을 쓰고, 같은 표에 두 컬럼(`ci_low`, `ci_high`)으로 함께 넣습니다. "AUC 0.83 (0.76-0.89)"을 인쇄하는 렌더러는 세 값을 그 컬럼에서 읽습니다.

## 6. 용량 계열: 곡선 맞춤

모형은 과학적 선택(4PL, 3PL, Michaelis-Menten, 직선)이므로 스크립트에서 정하고, 그 모수를 곡선과 함께 보고합니다:

```python
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from fig_atlas import stats

def four_pl(x, bottom, top, log_ec50, hill):             # x = log10(dose)
    return bottom + (top - bottom) / (1.0 + 10.0 ** ((log_ec50 - x) * hill))

popt, cov = curve_fit(four_pl, np.log10(dose), response, p0=[response.min(), response.max(), np.median(np.log10(dose)), 1.0],
                      bounds=([-np.inf, -np.inf, -np.inf, 0.0], [np.inf, np.inf, np.inf, np.inf]))
curve = pd.DataFrame({"dose_log10": grid, "response_fit": four_pl(grid, *popt)})
params = pd.DataFrame({"parameter": ["bottom", "top", "log_ec50", "hill"], "estimate": popt})
stats.record(params, name="dose_response_fit", title="4PL fit (log10 EC50)")
```

맞춤 표가 그림으로 가고, 패널은 받은 모수를 인쇄합니다. EC50과 그 구간(`cov`에서 계산)까지요.

## 7. 개수: 분할표와 비율의 구간

비율에는 검정과 구간이 필요합니다. 둘 다 개수에서 계산하고, 그림은 막대와 구간을 수염으로 그립니다:

```python
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from fig_atlas import stats

table = pd.crosstab(df["group"], df["outcome"])          # 행: 집단, 열: 결과
chi2, p, dof, expected = chi2_contingency(table)
# 기대빈도가 작은 2x2 표라면 p = fisher_exact(table)[1]
summary = df.groupby(["group", "outcome"]).size().rename("count").reset_index()
summary["p_value"] = p
stats.record(pd.DataFrame({"chi2": [chi2], "dof": [dof], "p": [p]}),
             name="contingency", title="Chi-square test of independence")
```

비율의 95% 구간(Wilson — 작은 n과 0이나 1 근처에서 잘 동작합니다)은 몇 줄이고, 렌더러가 그리는 표에 들어갑니다:

```python
def wilson(k, n, z=1.959964):
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / d
    half = z * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / d
    return centre - half, centre + half

low, high = wilson(12, 40)                                # ci_low, ci_high 컬럼
```

## 8. 패키지가 여전히 하는 일

계산은 스크립트의 몫이고, 패키지는 표시와 기록을 맡습니다:

- **표시 계층**(`fig_atlas.stats`): `stars()`(P값 → 기호, 임계값은 config에서), `adjust()`(표시용 보정 P 열), `describe()`(패키지가 직접 돌리던 검정의 범례 문장), `record()`/`write()`(그림 옆 검정 표).
- **빌드**는 등록된 모든 표를 `figure_NN_statistics/`에 쓰고, 별·괄호를 그리는 그림에 표가 없으면 `verify`가 실패합니다. 그 표가 곧 출처입니다. 어떤 검정, 어떤 n, 어떤 P.
- **과도기 경로**: 몇몇 오래된 렌더러는 아직 `stat_test` 설정을 받아 `fig_atlas.stats`로 직접 비교를 돌립니다(마지막 하나가 omics의 `tf_expression_bars`). 그것들은 계속 동작하며 확장되지 않습니다. 새 그림은 위처럼 P값을 컬럼으로 넘깁니다.

아직 분석 스크립트가 없는 연구라면 정직한 길은 짧습니다. 그림을 만드는 스크립트에서 값을 계산하고, 컬럼을 쓰고, 표를 등록하세요. config나 제목에 손으로 적은 숫자는 `fa claims --check`가 잡으려는 바로 그것입니다.
