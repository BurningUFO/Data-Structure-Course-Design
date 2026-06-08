"""
成员 B：模糊查询模块

本模块用于处理：

- 名称片段匹配
- 标签匹配
- 关键字匹配
- 描述补充召回
- 错字容忍和跳字缩写召回
- 多关键词覆盖排序

当前实现继续保持轻量，但补强了名称、标签、关键词、描述的权重，
并补充了同义词归一化、拼音首字母、编辑距离、标点归一化和跳字缩写支持，
便于第九至第十周场所查询和美食推荐直接复用。

后续如有需要，可继续扩展：
- Trie 前缀匹配
- 更完整的拼音字典
- 更完整的同义词词典
"""

from __future__ import annotations

import re
from typing import Any


Record = dict[str, Any]
MatchDetail = dict[str, Any]

DIRECT_QUERY_TERM_BONUS = 6

TERM_EQUIVALENT_GROUPS = (
    ("洗手间", "卫生间", "厕所", "公厕", "wc", "restroom", "toilet", "washroom", "lavatory", "xsj"),
    ("食堂", "餐厅", "餐饮", "catering", "st"),
    ("便利店", "超市", "商店", "shopping", "bld"),
    ("图书馆", "tsg", "library"),
    ("阅览室", "自习室", "自习", "yls", "zxs"),
    ("教学楼", "教室楼", "教室", "上课", "jxl"),
    ("宿舍", "寝室", "公寓", "学生公寓", "ss"),
    ("体育场", "操场", "运动场", "体育馆", "tyc"),
    ("校门", "大门", "入口", "xm"),
    ("广场", "中心广场", "square", "gc"),
    ("停车", "停车场", "车库", "parking", "tc"),
    ("咖啡", "coffee", "kf"),
    ("未名湖", "湖", "wml"),
)

SEPARATOR_PATTERN = re.compile(r"[\s,，。.;；:：、/\\|_\-+()（）\[\]【】{}<>《》\"'`~!！?？@#$%^&*=]+")
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
MAX_PINYIN_VARIANT_COUNT = 24

PINYIN_SYLLABLES = {
    "北": "bei",
    "京": "jing",
    "大": "da",
    "学": "xue",
    "校": "xiao",
    "园": "yuan",
    "区": "qu",
    "图": "tu",
    "书": "shu",
    "馆": "guan",
    "未": "wei",
    "名": "ming",
    "湖": "hu",
    "洗": "xi",
    "手": "shou",
    "间": "jian",
    "卫": "wei",
    "生": "sheng",
    "厕": "ce",
    "所": "suo",
    "公": "gong",
    "食": "shi",
    "堂": "tang",
    "餐": "can",
    "厅": "ting",
    "饮": "yin",
    "便": "bian",
    "利": "li",
    "店": "dian",
    "超": "chao",
    "市": "shi",
    "商": "shang",
    "教": "jiao",
    "楼": "lou",
    "室": "shi",
    "上": "shang",
    "课": "ke",
    "宿": "su",
    "舍": "she",
    "寝": "qin",
    "寓": "yu",
    "体": "ti",
    "育": "yu",
    "场": "chang",
    "操": "cao",
    "运": "yun",
    "动": "dong",
    "门": "men",
    "入": "ru",
    "口": "kou",
    "广": "guang",
    "中": "zhong",
    "心": "xin",
    "停": "ting",
    "车": "che",
    "库": "ku",
    "咖": "ka",
    "啡": "fei",
    "阅": "yue",
    "览": "lan",
    "自": "zi",
    "习": "xi",
    "热": "re",
    "水": "shui",
    "房": "fang",
    "服": "fu",
    "务": "wu",
    "台": "tai",
    "活": "huo",
    "休": "xiu",
    "闲": "xian",
    "办": "ban",
    "理": "li",
    "报": "bao",
    "修": "xiu",
    "卡": "ka",
    "借": "jie",
    "读": "du",
    "习": "xi",
    "习": "xi",
    "百": "bai",
    "周": "zhou",
    "年": "nian",
    "纪": "ji",
    "念": "nian",
    "广": "guang",
    "五": "wu",
    "四": "si",
    "农": "nong",
    "燕": "yan",
    "南": "nan",
    "东": "dong",
    "西": "xi",
    "北": "bei",
    "清": "qing",
    "华": "hua",
    "武": "wu",
    "汉": "han",
    "复": "fu",
    "旦": "dan",
    "同": "tong",
    "济": "ji",
    "苏": "su",
    "州": "zhou",
    "山": "shan",
    "厦": "xia",
    "门": "men",
    "浙": "zhe",
    "江": "jiang",
}

PINYIN_SYLLABLES.update(
    {
        "一": "yi",
        "三": "san",
        "不": "bu",
        "与": "yu",
        "专": "zhuan",
        "为": "wei",
        "主": "zhu",
        "乐": ("le", "yue"),
        "二": "er",
        "于": "yu",
        "交": "jiao",
        "享": "xiang",
        "亭": "ting",
        "人": "ren",
        "代": "dai",
        "仪": "yi",
        "会": "hui",
        "伞": "san",
        "位": "wei",
        "住": "zhu",
        "作": "zuo",
        "供": "gong",
        "侧": "ce",
        "保": "bao",
        "信": "xin",
        "候": "hou",
        "值": "zhi",
        "健": "jian",
        "充": "chong",
        "全": "quan",
        "共": "gong",
        "关": "guan",
        "兹": "zi",
        "内": "nei",
        "准": "zhun",
        "出": "chu",
        "分": "fen",
        "切": "qie",
        "创": "chuang",
        "到": "dao",
        "功": "gong",
        "加": "jia",
        "助": "zhu",
        "勒": "le",
        "勤": "qin",
        "包": "bao",
        "化": "hua",
        "医": "yi",
        "卖": "mai",
        "卜": "bu",
        "印": "yin",
        "参": "can",
        "叉": "cha",
        "发": "fa",
        "叔": "shu",
        "取": "qu",
        "古": "gu",
        "只": "zhi",
        "可": "ke",
        "号": "hao",
        "各": "ge",
        "合": "he",
        "后": "hou",
        "向": "xiang",
        "吧": "ba",
        "告": "gao",
        "和": "he",
        "咨": "zi",
        "品": "pin",
        "售": "shou",
        "善": "shan",
        "喷": "pen",
        "器": "qi",
        "回": "hui",
        "国": "guo",
        "地": "di",
        "坐": "zuo",
        "型": "xing",
        "城": "cheng",
        "域": "yu",
        "塑": "su",
        "境": "jing",
        "处": "chu",
        "备": "bei",
        "外": "wai",
        "多": "duo",
        "媒": "mei",
        "子": "zi",
        "字": "zi",
        "安": "an",
        "实": "shi",
        "客": "ke",
        "家": "jia",
        "对": "dui",
        "导": "dao",
        "小": "xiao",
        "层": "ceng",
        "工": "gong",
        "己": "ji",
        "师": "shi",
        "干": "gan",
        "平": "ping",
        "幸": "xing",
        "床": "chuang",
        "府": "fu",
        "座": "zuo",
        "康": "kang",
        "廊": "lang",
        "建": "jian",
        "开": "kai",
        "引": "yin",
        "影": "ying",
        "径": "jing",
        "微": "wei",
        "德": "de",
        "快": "kuai",
        "怡": "yi",
        "总": "zong",
        "息": "xi",
        "成": "cheng",
        "或": "huo",
        "战": "zhan",
        "打": "da",
        "扶": "fu",
        "投": "tou",
        "拐": "guai",
        "拔": "ba",
        "拟": "ni",
        "择": "ze",
        "按": "an",
        "据": "ju",
        "接": "jie",
        "提": "ti",
        "插": "cha",
        "收": "shou",
        "数": "shu",
        "文": "wen",
        "料": "liao",
        "新": "xin",
        "方": "fang",
        "施": "shi",
        "旁": "pang",
        "配": "pei",
        "无": "wu",
        "星": "xing",
        "更": "geng",
        "最": "zui",
        "本": "ben",
        "术": "shu",
        "机": "ji",
        "材": "cai",
        "村": "cun",
        "杜": "du",
        "松": "song",
        "板": "ban",
        "析": "xi",
        "林": "lin",
        "架": "jia",
        "柜": "gui",
        "查": "cha",
        "标": "biao",
        "栏": "lan",
        "样": "yang",
        "案": "an",
        "桌": "zhuo",
        "档": "dang",
        "桩": "zhuang",
        "梯": "ti",
        "检": "jian",
        "椅": "yi",
        "步": "bu",
        "段": "duan",
        "民": "min",
        "汇": "hui",
        "池": "chi",
        "沙": "sha",
        "泉": "quan",
        "泊": "bo",
        "派": "pai",
        "流": "liu",
        "海": "hai",
        "消": "xiao",
        "淀": "dian",
        "源": "yuan",
        "点": "dian",
        "烘": "hong",
        "然": "ran",
        "片": "pian",
        "版": "ban",
        "牌": "pai",
        "物": "wu",
        "特": "te",
        "王": "wang",
        "环": "huan",
        "珍": "zhen",
        "班": "ban",
        "球": "qiu",
        "瑞": "rui",
        "用": "yong",
        "田": "tian",
        "由": "you",
        "电": "dian",
        "界": "jie",
        "略": "lue",
        "白": "bai",
        "的": "de",
        "盘": "pan",
        "目": "mu",
        "盲": "mang",
        "相": "xiang",
        "看": "kan",
        "真": "zhen",
        "短": "duan",
        "研": "yan",
        "硬": "ying",
        "碍": "ai",
        "社": "she",
        "票": "piao",
        "禁": "jin",
        "离": "li",
        "科": "ke",
        "究": "jiu",
        "空": "kong",
        "窗": "chuang",
        "立": "li",
        "站": "zhan",
        "端": "duan",
        "第": "di",
        "等": "deng",
        "筑": "zhu",
        "箱": "xiang",
        "篮": "lan",
        "籍": "ji",
        "类": "lei",
        "系": "xi",
        "索": "suo",
        "约": "yue",
        "线": "xian",
        "练": "lian",
        "组": "zu",
        "终": "zhong",
        "统": "tong",
        "综": "zong",
        "编": "bian",
        "网": "wang",
        "美": "mei",
        "考": "kao",
        "者": "zhe",
        "能": "neng",
        "至": "zhi",
        "航": "hang",
        "节": "jie",
        "营": "ying",
        "藏": "cang",
        "虚": "xu",
        "行": ("hang", "xing"),
        "衣": "yi",
        "观": "guan",
        "视": "shi",
        "角": "jiao",
        "讨": "tao",
        "套": "tao",
        "训": "xun",
        "议": "yi",
        "讲": "jiang",
        "论": "lun",
        "设": "she",
        "询": "xun",
        "调": ("tiao", "diao"),
        "购": "gou",
        "资": "zi",
        "赛": "sai",
        "走": "zou",
        "起": "qi",
        "足": "zu",
        "路": "lu",
        "身": "shen",
        "轻": "qing",
        "辅": "fu",
        "辆": "liang",
        "边": "bian",
        "达": "da",
        "过": "guo",
        "近": "jin",
        "还": "hai",
        "连": "lian",
        "适": "shi",
        "选": "xuan",
        "通": "tong",
        "速": "su",
        "道": "dao",
        "邱": "qiu",
        "邻": "lin",
        "部": "bu",
        "重": ("zhong", "chong"),
        "钮": "niu",
        "银": "yin",
        "铺": "pu",
        "防": "fang",
        "阶": "jie",
        "阿": "a",
        "附": "fu",
        "院": "yuan",
        "障": "zhang",
        "雨": "yu",
        "零": "ling",
        "青": "qing",
        "静": "jing",
        "面": "mian",
        "预": "yu",
        "题": "ti",
        "驳": "bo",
        "验": "yan",
        "骨": "gu",
        "鸟": "niao",
        "麦": "mai",
        "齐": "qi",
    }
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def normalize_match_text(value: Any) -> str:
    """归一化参与匹配的文本，忽略空白和常见标点。"""
    return SEPARATOR_PATTERN.sub("", normalize_text(value))


def build_term_aliases() -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for group in TERM_EQUIVALENT_GROUPS:
        normalized_group = [normalize_match_text(term) for term in group if normalize_match_text(term)]
        for term in normalized_group:
            aliases[term] = [candidate for candidate in normalized_group if candidate != term]
    return aliases


TERM_ALIASES = build_term_aliases()


def has_cjk(value: str) -> bool:
    return bool(CJK_PATTERN.search(value))


def get_pinyin_choices(char: str) -> tuple[str, ...]:
    syllable = PINYIN_SYLLABLES.get(char)
    if not syllable:
        return ()
    if isinstance(syllable, str):
        return (syllable,)
    return tuple(str(item) for item in syllable if str(item))


def combine_pinyin_options(option_groups: list[tuple[str, ...]]) -> list[str]:
    variants = [""]
    for choices in option_groups:
        if not choices:
            continue
        next_variants: list[str] = []
        for prefix in variants:
            for choice in choices:
                next_variants.append(f"{prefix}{choice}")
                if len(next_variants) >= MAX_PINYIN_VARIANT_COUNT:
                    break
            if len(next_variants) >= MAX_PINYIN_VARIANT_COUNT:
                break
        variants = next_variants
    return variants


def pinyin_variants(value: Any) -> list[str]:
    normalized = normalize_match_text(value)
    if not normalized or not has_cjk(normalized):
        return []

    syllable_options: list[tuple[str, ...]] = []
    initial_options: list[tuple[str, ...]] = []
    cjk_count = 0
    mapped_count = 0
    for char in normalized:
        if "\u4e00" <= char <= "\u9fff":
            cjk_count += 1
            choices = get_pinyin_choices(char)
            if not choices:
                continue
            mapped_count += 1
            syllable_options.append(choices)
            initial_options.append(tuple(unique_ordered([choice[0] for choice in choices])))
        elif char.isascii() and char.isalnum():
            syllable_options.append((char,))
            initial_options.append((char,))

    if not cjk_count or mapped_count < 2 or mapped_count / cjk_count < 0.75:
        return []

    return unique_ordered(
        [
            *combine_pinyin_options(syllable_options),
            *combine_pinyin_options(initial_options),
        ]
    )


def expand_match_value(value: Any) -> list[str]:
    normalized = normalize_match_text(value)
    if not normalized:
        return []
    return unique_ordered([normalized, *pinyin_variants(value)])


def expand_query_term(term: str) -> list[str]:
    normalized_term = normalize_match_text(term)
    if not normalized_term:
        return []

    ordered_terms: list[str] = [normalized_term]
    for candidate in TERM_ALIASES.get(normalized_term, []):
        if candidate not in ordered_terms:
            ordered_terms.append(candidate)
    return ordered_terms


def split_search_term_groups(keyword: str) -> list[list[str]]:
    """提取查询词组；每组内是同一用户词项的同义表达。"""
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return []

    compact_keyword = normalize_match_text(normalized_keyword)
    raw_parts = [
        normalize_match_text(part)
        for part in SEPARATOR_PATTERN.split(normalized_keyword)
        if normalize_match_text(part)
    ]
    meaningful_parts = [
        part
        for part in raw_parts
        if len(part) > 1
    ]

    base_terms: list[str] = []
    if compact_keyword and len(meaningful_parts) < 2:
        base_terms.append(compact_keyword)
    if meaningful_parts:
        base_terms.extend(part for part in meaningful_parts if part != compact_keyword)
    elif not compact_keyword:
        base_terms.extend(raw_parts)

    seen_groups: set[tuple[str, ...]] = set()
    term_groups: list[list[str]] = []
    for term in base_terms:
        expanded_terms = unique_ordered(expand_query_term(term))
        if not expanded_terms:
            continue
        group_key = tuple(expanded_terms)
        if group_key in seen_groups:
            continue
        seen_groups.add(group_key)
        term_groups.append(expanded_terms)

    return term_groups


def split_search_terms(keyword: str) -> list[str]:
    """兼容旧调用方：返回扁平化后的匹配词项。"""
    seen: set[str] = set()
    ordered_terms: list[str] = []
    for group in split_search_term_groups(keyword):
        for candidate in group:
            if candidate in seen:
                continue
            seen.add(candidate)
            ordered_terms.append(candidate)

    return ordered_terms


def unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def flatten_field_values(value: Any) -> list[Any]:
    """把列表、字典和字符串字段统一摊平成可匹配值。"""
    if value is None:
        return []
    if isinstance(value, dict):
        values: list[Any] = []
        for key, nested_value in value.items():
            values.append(key)
            values.extend(flatten_field_values(nested_value))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(flatten_field_values(item))
        return values
    return [value]


def score_collection(
    values: list[Any],
    term_groups: list[list[str]],
    *,
    exact_score: int,
    prefix_score: int,
    contains_score: int,
    subsequence_score: int,
    approximate_score: int,
) -> int:
    return score_collection_with_details(
        values,
        term_groups,
        exact_score=exact_score,
        prefix_score=prefix_score,
        contains_score=contains_score,
        subsequence_score=subsequence_score,
        approximate_score=approximate_score,
    )[0]


def score_collection_with_details(
    values: list[Any],
    term_groups: list[list[str]],
    *,
    exact_score: int,
    prefix_score: int,
    contains_score: int,
    subsequence_score: int,
    approximate_score: int,
) -> tuple[int, list[MatchDetail]]:
    """对一组字段值计算匹配得分。"""
    if not values or not term_groups:
        return 0, []

    normalized_values = unique_ordered(
        [
            candidate
            for value in values
            for candidate in expand_match_value(value)
        ]
    )
    if not normalized_values:
        return 0, []

    total_score = 0
    matched_group_count = 0
    details: list[MatchDetail] = []

    for group in term_groups:
        best_group_score = 0
        best_detail: MatchDetail | None = None
        direct_term = group[0] if group else ""
        for term_index, term in enumerate(group):
            for text in normalized_values:
                score, match_type = score_text_match(
                    term,
                    text,
                    exact_score=exact_score,
                    prefix_score=prefix_score,
                    contains_score=contains_score,
                    subsequence_score=subsequence_score,
                    approximate_score=approximate_score,
                )
                if score > 0 and term_index == 0 and term == direct_term:
                    score += DIRECT_QUERY_TERM_BONUS
                if score > best_group_score:
                    best_group_score = score
                    best_detail = {
                        "term": term,
                        "matched_text": text,
                        "match_type": match_type,
                        "score": score,
                    }

        if best_group_score > 0:
            matched_group_count += 1
            total_score += best_group_score
            if best_detail is not None:
                details.append(best_detail)

    if total_score and matched_group_count > 1:
        total_score += matched_group_count * 8

    return total_score, details


def score_text_match(
    term: str,
    text: str,
    *,
    exact_score: int,
    prefix_score: int,
    contains_score: int,
    subsequence_score: int,
    approximate_score: int,
) -> tuple[int, str]:
    """计算单个查询词与单个字段文本的匹配分。"""
    if not term or not text:
        return 0, ""
    if text == term:
        return exact_score, "exact"
    if text.startswith(term):
        return prefix_score, "prefix"
    if term in text:
        return contains_score, "contains"
    if is_ascii_word(term):
        return 0, ""
    if is_ordered_subsequence(term, text):
        return subsequence_score, "subsequence"
    approximate = approximate_match_score(term, text, approximate_score)
    return (approximate, "typo") if approximate > 0 else (0, "")


def is_ascii_word(value: str) -> bool:
    """英文查询词只做可靠匹配，避免 washroom 误召回 classroom。"""
    return value.isascii() and any(char.isalpha() for char in value)


def is_ordered_subsequence(term: str, text: str) -> bool:
    """支持“图馆”命中“图书馆”这类跳字缩写，短词保持保守。"""
    if len(term) < 2 or len(text) < len(term):
        return False
    if len(term) == 2 and len(text) > 4:
        return False

    position = 0
    for char in text:
        if position < len(term) and term[position] == char:
            position += 1
    if position != len(term):
        return False

    density = len(term) / len(text)
    return density >= 0.4 or len(term) >= 3


def approximate_match_score(term: str, text: str, base_score: int) -> int:
    """计算保守编辑距离近似匹配分，整字段命中优先于长文本窗口命中。"""
    if not term or not text:
        return 0

    max_distance = allowed_edit_distance(term)
    if max_distance <= 0:
        return 0

    if _bounded_levenshtein_distance(term, text, max_distance) <= max_distance:
        return base_score + 18

    term_length = len(term)
    min_window = max(1, term_length - max_distance)
    max_window = min(len(text), term_length + max_distance)
    for window_length in range(min_window, max_window + 1):
        for start in range(0, len(text) - window_length + 1):
            window = text[start : start + window_length]
            if _bounded_levenshtein_distance(term, window, max_distance) <= max_distance:
                return max(1, base_score - 10)

    return 0


def allowed_edit_distance(term: str) -> int:
    """按查询词长度给出最大允许编辑距离，避免短词误召回。"""
    length = len(term)
    if length <= 2:
        return 0
    if length <= 4:
        return 1
    if length <= 8:
        return 2
    return 3


def _bounded_levenshtein_distance(left: str, right: str, max_distance: int) -> int:
    """计算带上限的 Levenshtein 距离，超过上限时提前返回。"""
    if abs(len(left) - len(right)) > max_distance:
        return max_distance + 1

    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        row_min = current[0]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current[right_index - 1] + 1
            delete_cost = previous[right_index] + 1
            replace_cost = previous[right_index - 1] + (0 if left_char == right_char else 1)
            value = min(insert_cost, delete_cost, replace_cost)
            current.append(value)
            row_min = min(row_min, value)

        if row_min > max_distance:
            return max_distance + 1
        previous = current

    return previous[-1]


def calculate_match_score(record: Record, keyword: str) -> int:
    """
    计算单条记录对关键字的匹配分数。

    当前评分规则：
    - 名称：精确/前缀/包含匹配权重最高
    - keywords：强调业务关键词和设施词
    - tags：次高权重，适合“洗手间/便利店/轻食”类查询
    - description：补充召回，不抢占名称优先级

    当前额外支持：
    - 忽略常见空白和标点
    - 多关键词覆盖加权
    - 保守编辑距离错字召回
    - 有序跳字缩写召回
    """
    term_groups = split_search_term_groups(keyword)
    if not term_groups:
        return 0

    return calculate_match(record, keyword)["score"]


def calculate_match(record: Record, keyword: str) -> dict[str, Any]:
    """计算匹配总分和用于 UI 展示的解释信息。"""
    term_groups = split_search_term_groups(keyword)
    if not term_groups:
        return {"score": 0, "details": []}

    name_score, name_details = score_collection_with_details(
        flatten_field_values(record.get("name")),
        term_groups,
        exact_score=160,
        prefix_score=120,
        contains_score=90,
        subsequence_score=72,
        approximate_score=64,
    )
    keyword_score, keyword_details = score_collection_with_details(
        flatten_field_values(record.get("keywords")),
        term_groups,
        exact_score=85,
        prefix_score=68,
        contains_score=52,
        subsequence_score=42,
        approximate_score=36,
    )
    tag_score, tag_details = score_collection_with_details(
        flatten_field_values(record.get("tags")),
        term_groups,
        exact_score=70,
        prefix_score=56,
        contains_score=42,
        subsequence_score=34,
        approximate_score=30,
    )
    description_score, description_details = score_collection_with_details(
        flatten_field_values(record.get("description")),
        term_groups,
        exact_score=36,
        prefix_score=30,
        contains_score=24,
        subsequence_score=16,
        approximate_score=12,
    )

    total_score = name_score + keyword_score + tag_score + description_score

    matched_field_count = sum(
        1
        for score in (name_score, keyword_score, tag_score, description_score)
        if score > 0
    )
    if matched_field_count > 1:
        total_score += matched_field_count * 4

    details = []
    for field_name, field_label, field_details in (
        ("name", "名称", name_details),
        ("keywords", "关键词", keyword_details),
        ("tags", "标签", tag_details),
        ("description", "描述", description_details),
    ):
        for detail in field_details:
            details.append({
                **detail,
                "field": field_name,
                "field_label": field_label,
            })

    return {
        "score": total_score,
        "details": sorted(
            details,
            key=lambda item: int(item.get("score", 0)),
            reverse=True,
        )[:4],
    }


def fuzzy_search(records: list[Record], keyword: str) -> list[Record]:
    """
    对记录做模糊查询。

    返回结果会附加字段：
    - `_match_score`

    输出按匹配分数从高到低排序；
    如果分数相同，则按热度从高到低排序。
    """
    if not split_search_terms(keyword):
        return records[:]

    matched: list[Record] = []
    for record in records:
        match = calculate_match(record, keyword)
        score = int(match.get("score", 0))
        if score <= 0:
            continue

        copied = record.copy()
        copied["_match_score"] = score
        copied["_match_detail"] = match.get("details", [])
        matched.append(copied)

    # 当前结果规模通常不大，先用简单插入排序整理模糊匹配结果
    return sort_fuzzy_results(matched)


def sort_fuzzy_results(records: list[Record]) -> list[Record]:
    """
    对模糊查询结果做排序：
    1. 先按 _match_score 降序
    2. 再按 heat 降序
    3. 再按 rating 降序
    4. 最后按名称字典序升序，确保结果稳定
    """
    result = records[:]

    for i in range(1, len(result)):
        current = result[i]
        current_score = int(current.get("_match_score", 0))
        current_heat = float(current.get("heat", 0))
        current_rating = float(current.get("rating", 0))
        current_name = normalize_text(current.get("name"))
        j = i - 1

        while j >= 0:
            left_score = int(result[j].get("_match_score", 0))
            left_heat = float(result[j].get("heat", 0))
            left_rating = float(result[j].get("rating", 0))
            left_name = normalize_text(result[j].get("name"))

            should_move = False
            if left_score < current_score:
                should_move = True
            elif left_score == current_score and left_heat < current_heat:
                should_move = True
            elif left_score == current_score and left_heat == current_heat and left_rating < current_rating:
                should_move = True
            elif (
                left_score == current_score
                and left_heat == current_heat
                and left_rating == current_rating
                and left_name > current_name
            ):
                should_move = True

            if not should_move:
                break

            result[j + 1] = result[j]
            j -= 1

        result[j + 1] = current

    return result
