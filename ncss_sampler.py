import random
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NCSS_DATA = PROJECT_ROOT / "91-王泽宇-2025.dta"


def _to_number(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _contains(value, keywords) -> bool:
    text = "" if pd.isna(value) else str(value)
    return any(keyword in text for keyword in keywords)


def _map_gender(value) -> str:
    if _contains(value, ["男"]):
        return "男"
    if _contains(value, ["女"]):
        return "女"
    if _to_number(value, None) == 1:
        return "男"
    return "女"


def _map_age(value) -> int:
    if pd.isna(value):
        return random.randint(18, 24)

    text = str(value)
    match = re.search(r"\d+", text)
    if match:
        age = int(match.group())
        if "以下" in text:
            return min(age, 15)
        if "以上" in text:
            return max(age, 30)
        return age

    code = _to_number(value, None)
    if code is not None:
        # 2025 coding: 4=18, 5=19, ..., 15=29, 16=30+
        if 4 <= code <= 15:
            return int(code + 14)
        if code == 16:
            return 30

    return random.randint(18, 24)


def _map_orientation(value) -> str:
    text = "" if pd.isna(value) else str(value)
    if "同性恋" in text:
        return "同性恋"
    if "双性恋" in text or "泛性恋" in text:
        return "双性恋"
    if "异性恋" in text:
        return "异性恋"
    return "其他/不确定"


def _yes(value) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return ("是" in value) or ("有过" in value) or ("选择了" in value)
    return _to_number(value) == 1


def _frequency_score(value) -> float:
    text = "" if pd.isna(value) else str(value)
    if "几乎每天" in text:
        return 5
    if "一周" in text:
        return 4
    if "一月" in text:
        return 3
    if "一年" in text:
        return 2
    if "超过一年" in text or "近些年没有" in text:
        return 1
    if "从未" in text or "没有" in text or "否" == text:
        return 0
    return _to_number(value)


def _tertile_label(value: float, low_cut: float, high_cut: float, labels) -> str:
    if value <= low_cut:
        return labels[0]
    if value <= high_cut:
        return labels[1]
    return labels[2]


class NCSSProfileSampler:
    """
    Build simulation profiles from NCSS-SRH respondent rows.

    Sampling whole rows preserves empirical joint distributions such as
    P(sexual_orientation, risk_behavior | sex, age, social_activity).
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = Path(data_path) if data_path else DEFAULT_NCSS_DATA
        if not self.data_path.exists():
            raise FileNotFoundError(f"NCSS data file not found: {self.data_path}")

        raw = pd.read_stata(self.data_path, convert_categoricals=True)
        self.profile_records = self._build_profile_records(raw)
        if not self.profile_records:
            raise ValueError(f"No usable profile rows found in {self.data_path}")

    def sample(self, n: int) -> List[Dict]:
        profiles = []
        for i in range(n):
            profile = dict(random.choice(self.profile_records))
            profile["name"] = f"Student_{i}"
            profiles.append(profile)
        return profiles

    def _build_profile_records(self, df: pd.DataFrame) -> List[Dict]:
        working = df.copy()

        social_total = pd.Series(0.0, index=working.index)
        if "b3_7_1" in working.columns:
            social_total += working["b3_7_1"].map(_to_number)
        if "b3_7_2" in working.columns:
            social_total += working["b3_7_2"].map(_to_number)

        social_low = social_total.quantile(0.33)
        social_high = social_total.quantile(0.67)

        sexual_experience = working.get("c5", pd.Series(False, index=working.index)).map(_yes)
        casual_sex = working.get("c6", pd.Series(False, index=working.index)).map(_yes)
        no_contraception = working.get("c14_0_1", pd.Series(0, index=working.index)).map(_yes)
        male_condom = working.get("c14_0_4", pd.Series(0, index=working.index)).map(_yes)
        female_condom = working.get("c14_0_5", pd.Series(0, index=working.index)).map(_yes)
        sex_frequency = working.get("c11", pd.Series(0, index=working.index)).map(_frequency_score)
        porn_frequency = working.get("c2", pd.Series(0, index=working.index)).map(_frequency_score)

        opportunity_score = (
            social_total.rank(pct=True).fillna(0)
            + sexual_experience.astype(int)
            + casual_sex.astype(int)
            + sex_frequency.rank(pct=True).fillna(0)
        )
        opp_low = opportunity_score.quantile(0.33)
        opp_high = opportunity_score.quantile(0.67)

        risk_score = (
            sexual_experience.astype(int)
            + casual_sex.astype(int) * 2
            + no_contraception.astype(int) * 2
            - (male_condom | female_condom).astype(int)
            + sex_frequency.rank(pct=True).fillna(0)
            + porn_frequency.rank(pct=True).fillna(0) * 0.5
        )
        risk_low = risk_score.quantile(0.33)
        risk_high = risk_score.quantile(0.67)

        records = []
        for idx, row in working.iterrows():
            if "sex" not in working.columns or "b1" not in working.columns:
                continue
            records.append(
                {
                    "age": _map_age(row["age"]) if "age" in working.columns else random.randint(18, 24),
                    "gender": _map_gender(row["sex"]),
                    "social_activity": _tertile_label(
                        social_total.loc[idx],
                        social_low,
                        social_high,
                        ["较低", "中等", "很高"],
                    ),
                    # NCSS has no self-rated attractiveness. This is an opportunity proxy
                    # built from social time and relationship/sexual experience variables.
                    "attractiveness": _tertile_label(
                        opportunity_score.loc[idx],
                        opp_low,
                        opp_high,
                        ["较低", "中等", "很高"],
                    ),
                    "sexual_orientation": _map_orientation(row["b1"]),
                    "risk_propensity": _tertile_label(
                        risk_score.loc[idx],
                        risk_low,
                        risk_high,
                        ["谨慎的", "普通的", "鲁莽的"],
                    ),
                }
            )

        return records


def generate_student_profiles_from_ncss(n: int, data_path: Optional[str] = None) -> List[Dict]:
    return NCSSProfileSampler(data_path=data_path).sample(n)
