import random
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NCSS_DATA = PROJECT_ROOT / "91-王泽宇-2025.dta"

KNOWLEDGE_SOURCE_COLUMNS = [
    ("a3_0_1", "纸媒书籍/杂志"),
    ("a3_0_2", "电视/广播"),
    ("a3_0_3", "网络/社交媒体单向科普"),
    ("a3_0_4", "网络/社交媒体互动交流"),
    ("a3_0_5", "综合/专科医院线下就诊"),
    ("a3_0_6", "基层卫生服务机构"),
    ("a3_0_7", "父母等长辈"),
    ("a3_0_8", "老师等长辈"),
    ("a3_0_9", "朋友/同学等同辈"),
    ("a3_0_10", "其他"),
    ("a3_0_11", "不会主动获取"),
]

SEX_EDUCATION_FORM_COLUMNS = [
    ("a1_3_1", "大型讲座"),
    ("a1_3_2", "小班教师灌输式授课"),
    ("a1_3_3", "小班教师互动式授课"),
    ("a1_3_4", "参与式同伴教育"),
    ("a1_3_5", "其他"),
]

CASUAL_PARTNER_COLUMNS = [
    ("c6_2_1", "曾经的男/女朋友"),
    ("c6_2_2", "老师"),
    ("c6_2_3", "同辈非亲属"),
    ("c6_2_4", "同辈亲属"),
    ("c6_2_5", "长辈非亲属"),
    ("c6_2_6", "长辈亲属"),
    ("c6_2_7", "网友"),
    ("c6_2_8", "有偿性服务提供者"),
    ("c6_2_9", "陌生人"),
    ("c6_2_10", "其他"),
]

CONTRACEPTION_COLUMNS = [
    ("c14_0_1", "没有采用避孕措施"),
    ("c14_0_2", "口服避孕药"),
    ("c14_0_3", "紧急避孕药"),
    ("c14_0_4", "男用安全套/避孕套"),
    ("c14_0_5", "女用安全套/避孕套"),
    ("c14_0_6", "体外排精"),
    ("c14_0_7", "安全期"),
    ("c14_0_8", "避孕针"),
    ("c14_0_9", "阴道避孕环"),
    ("c14_0_10", "宫内节育器/上环"),
    ("c14_0_11", "女性绝育"),
    ("c14_0_12", "男性绝育"),
    ("c14_0_13", "杀精剂"),
    ("c14_0_14", "皮下埋植剂"),
    ("c14_0_15", "其他"),
]

NO_CONTRACEPTION_REASON_COLUMNS = [
    ("c14_1_1", "认为偶尔不避孕不会怀孕"),
    ("c14_1_2", "一时冲动"),
    ("c14_1_3", "对方不想使用/拒绝使用"),
    ("c14_1_4", "缺少避孕知识"),
    ("c14_1_5", "认为没有必要"),
    ("c14_1_6", "获取不方便"),
    ("c14_1_7", "使用麻烦/不会使用"),
    ("c14_1_8", "经济/价格因素"),
    ("c14_1_9", "担心副作用"),
    ("c14_1_10", "避孕效果不好"),
    ("c14_1_11", "影响性体验"),
    ("c14_1_12", "想要怀孕"),
    ("c14_1_13", "同性性行为不需要"),
    ("c14_1_14", "其他"),
]

STI_COLUMNS = [
    ("c20_0_1", "淋病"),
    ("c20_0_2", "梅毒"),
    ("c20_0_3", "衣原体感染相关疾病"),
    ("c20_0_4", "生殖器疱疹"),
    ("c20_0_5", "HPV感染/尖锐湿疣"),
    ("c20_0_6", "软下疳"),
    ("c20_0_7", "滴虫病"),
    ("c20_0_8", "乙型肝炎"),
    ("c20_0_9", "非淋菌性尿道炎"),
    ("c20_0_10", "艾滋病"),
]


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
        text = value.strip()
        if text in {"否", "无", "没有", "从未有过"}:
            return False
        if text.startswith("没有") or text.startswith("从未"):
            return False
        return ("是" in text) or ("有过" in text) or ("选择了" in text)
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


def _value_text(row, col: str, default: str = "未知") -> str:
    if col not in row.index or pd.isna(row[col]):
        return default
    return str(row[col])


def _selected_labels(row, columns, default: str = "无") -> str:
    labels = [label for col, label in columns if col in row.index and _yes(row[col])]
    return "、".join(labels) if labels else default


def _social_hours_text(row) -> str:
    partner_hours = _to_number(row.get("b3_7_1", 0))
    peer_hours = _to_number(row.get("b3_7_2", 0))
    return f"与伴侣社交娱乐约{partner_hours:g}小时；独处或与非伴侣社交娱乐约{peer_hours:g}小时"


def _binary_text(value) -> str:
    return "是" if _yes(value) else "否"


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
                    "sex_education_forms": _selected_labels(row, SEX_EDUCATION_FORM_COLUMNS),
                    "knowledge_sources": _selected_labels(row, KNOWLEDGE_SOURCE_COLUMNS),
                    "relationship_status": _value_text(row, "b3"),
                    "wants_partner": _value_text(row, "b3_1"),
                    "past_partner_count": _value_text(row, "b3_5", default="未知"),
                    "daily_social_hours": _social_hours_text(row),
                    "porn_exposure_frequency": _value_text(row, "c2"),
                    "has_insertive_sex": _binary_text(row.get("c5", 0)),
                    "casual_sex_experience": _binary_text(row.get("c6", 0)),
                    "casual_sex_partner_count": _value_text(row, "c6_1", default="0"),
                    "casual_sex_partner_types": _selected_labels(row, CASUAL_PARTNER_COLUMNS),
                    "sex_frequency_last_year": _value_text(row, "c11", default="无或未知"),
                    "recent_contraception_methods": _selected_labels(row, CONTRACEPTION_COLUMNS),
                    "contraception_decision_maker": _value_text(row, "c15"),
                    "no_contraception_reasons": _selected_labels(row, NO_CONTRACEPTION_REASON_COLUMNS),
                    "sti_history": _selected_labels(row, STI_COLUMNS),
                    "hiv_diagnosis_last_year": _binary_text(row.get("c20_0_10", 0)),
                    "hiv_treatment_after_diagnosis": _value_text(row, "c20_10", default="不适用或未知"),
                }
            )

        return records


def generate_student_profiles_from_ncss(n: int, data_path: Optional[str] = None) -> List[Dict]:
    return NCSSProfileSampler(data_path=data_path).sample(n)
