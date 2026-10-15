"""表达反馈：基于本地规则的表达检查引擎。

诚实原则（对应任务书「不得夸大功能」）：
- 只报告本地规则能可靠检测的问题（拼写、大小写、a/an、常见中式表达等）；
- 不能可靠判断的内容（语义通顺、复杂语法、地道性）必须明确声明为局限，
  不得假装进行过全面智能评估；
- 避免把合理表达误判为错误：不确定的写法宁可不报；风格类建议明确标注为「建议」。

未来模型接入点：evaluate_answers 可替换为模型评估，见 life2english.model_api。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 规则数据
# ---------------------------------------------------------------------------

# 常见拼写错误对照表（小写匹配，按词边界替换）
SPELLING_FIXES: dict[str, str] = {
    "teh": "the",
    "recieve": "receive",
    "coffe": "coffee",
    "cofee": "coffee",
    "tomorow": "tomorrow",
    "becuase": "because",
    "beacuse": "because",
    "becasue": "because",
    "wnat": "want",
    "liek": "like",
    "freind": "friend",
    "intrested": "interested",
    "intresting": "interesting",
    "moive": "movie",
    "studing": "studying",
    "definately": "definitely",
    "seperate": "separate",
    "occured": "occurred",
    "untill": "until",
    "wich": "which",
    "thier": "their",
    "alot": "a lot",
    "calss": "class",
    "dormitary": "dormitory",
    "univercity": "university",
    "englsih": "english",
    "hellp": "help",
    # ---- 评审核实 P1-3 点名漏检（`enviroment`/`recieved`/`begining`/`goverment`）----
    "enviroment": "environment",
    "recieved": "received",
    "begining": "beginning",
    "goverment": "government",
    # ---- 同类高频错拼补充 ----
    "wierd": "weird",
    "acheive": "achieve",
    "acheivement": "achievement",
    "neccessary": "necessary",
    "necesary": "necessary",
    "accomodation": "accommodation",
    "arguement": "argument",
    "comming": "coming",
    "comitted": "committed",
    "embarass": "embarrass",
    "occassion": "occasion",
    "succesful": "successful",
    "sucessful": "successful",
    "writting": "writing",
    "truely": "truly",
    "independant": "independent",
    "existance": "existence",
    "responsable": "responsible",
    "probally": "probably",
    "probaly": "probably",
    "diffrent": "different",
    "diffcult": "difficult",
    "diffculties": "difficulties",
    "experiance": "experience",
    "expierence": "experience",
    "knowlege": "knowledge",
    "langauge": "language",
    "resturant": "restaurant",
    "restaraunt": "restaurant",
    "vegeterian": "vegetarian",
    "adress": "address",
    "assigment": "assignment",
    "assginment": "assignment",
    "familar": "familiar",
    "sucess": "success",
    "succes": "success",
    "oppurtunity": "opportunity",
    "entrepeneur": "entrepreneur",
    "schedual": "schedule",
    "shedule": "schedule",
    "avaliable": "available",
    "availble": "available",
    "confortable": "comfortable",
    "convinient": "convenient",
    "managment": "management",
    "enviromental": "environmental",
    "sincerly": "sincerely",
    "recomend": "recommend",
    "reccomend": "recommend",
    "occure": "occur",
    "grammer": "grammar",
    "payed": "paid",
}

# a/an 特例：元音字母开头但读音为辅音（用 a），或辅音字母开头但读音为元音（用 an）
# （阶段 C 补入）used 读 /juːzd/（或 /juːst/），以辅音音素 /j/ 开头：a used car 正确，
# 不应报「an used」——由独立语料 ctx_18 暴露。
_A_AN_EXCEPTIONS_A = {"university", "united", "unique", "useful", "user", "usual", "european", "one", "once", "used"}
_A_AN_EXCEPTIONS_AN = {"hour", "honest", "honor", "honour", "mba", "x-ray"}

_I_RE = re.compile(r"(?<![A-Za-z])i(?![A-Za-z])")
_IM_RE = re.compile(r"(?<![A-Za-z])im(?![A-Za-z])")
_A_VOWEL_RE = re.compile(r"\ba\s+([aeiouAEIOU][a-zA-Z]*)\b")
# 允许连字符：让 "an X-ray" 能完整捕获为 "x-ray"（否则会在 '-' 处截断成 "x"，
# 使 _A_AN_EXCEPTIONS_AN 中的 "x-ray" 白名单永远匹配不上）。
_AN_CONSONANT_RE = re.compile(
    r"\ban\s+([b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z][a-zA-Z\-]*)\b"
)
# 反馈粒度硬上限（对齐 SKILL.md §4「每轮只聚焦 1–3 条」）
MAX_ISSUES_PER_ANSWER = 3
_SENTENCE_START_LOWER_RE = re.compile(r"^[a-z]")
_WORD_RE = re.compile(r"[a-zA-Z']+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# 中文标点 / 全角符号：中英混说时需从英文片段中清除，避免污染检查
_CJK_PUNCT_RE = re.compile(r"[\u3000-\u303f\uff01-\uff5e]")

# 常见中式表达 / 用法建议（trigger, fix, reason）
USAGE_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\bvery like\b", re.I), "really like",
     "「非常喜欢」不说 very like，用 really like 或 like ... very much。"),
    (re.compile(r"\bhow to say\b", re.I), "How do you say ... in English?",
     "「怎么说」应说 How do you say ... in English?，How to say 是中式表达。"),
    (re.compile(r"\bi am called\b", re.I), "My name is ... / I'm ...",
     "介绍姓名用 My name is / I'm，不说 I am called。"),
    (re.compile(r"\bopen the light\b", re.I), "turn on the light",
     "「开灯」用 turn on the light，open 用于开门、开窗等实体开合。"),
    (re.compile(r"\bvery much like\b", re.I), "really like / like ... very much",
     "very much like 语序不地道，说 really like 或 like ... very much。"),
    (re.compile(r"\bdiscuss about\b", re.I), "discuss",
     "discuss 是及物动词，后面不加 about：discuss the movie。"),
    (re.compile(r"\bmarry with\b", re.I), "marry",
     "marry 及物，不说 marry with sb。"),
    (re.compile(r"\bexplain me\b", re.I), "explain to me",
     "explain 后接人要用 explain to me。"),
    (re.compile(r"\bwait you\b", re.I), "wait for you",
     "「等你」用 wait for you，wait 后接人需加 for。"),
    (re.compile(r"\blisten music\b", re.I), "listen to music",
     "listen 后接宾语需要 to：listen to music。"),
    (re.compile(r"\bnext next week\b", re.I), "the week after next",
     "「下下周」说 the week after next，不说 next next week。"),
    (re.compile(r"\bsuggest me\b", re.I), "suggest something to me / give me a suggestion",
     "suggest 不直接接人：用 suggest sth to me 或 recommend。"),
    (re.compile(r"\bi very\b(?!\s+much\b)", re.I), "I'm very / I really",
     "I very + 形容词 语序错误：说 I'm very happy / I really like。（I very much + 动词是正确结构，不误报）"),
]

# 常见中式表达（针对中文思维直译，给出地道说法）
CHINGLISH_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\bplay (the )?phone\b", re.I), "use my phone",
     "「玩手机」不说 play phone，用 use my phone / go on my phone。"),
    (re.compile(r"\bplay (the )?computer\b", re.I), "use the computer",
     "「玩电脑」不说 play computer，用 use the computer。"),
    (re.compile(r"\bhave interest in\b", re.I), "be interested in",
     "「对…感兴趣」用 be interested in 更自然。"),
    (re.compile(r"\bvery delicious\b", re.I), "delicious / really tasty",
     "delicious 本身已表示「很美味」，前面不加 very，可说 really tasty。"),
    (re.compile(r"\bi think (that )?i can'?t\b", re.I), "I don't think I can",
     "英语习惯否定前移：I don't think I can。"),
]

# ---------------------------------------------------------------------------
# 语法检查规则（在本地规则能可靠判断的范围内）
# ---------------------------------------------------------------------------

# 主谓一致：第三人称单数常见遗漏（限定主语为 I/you/we/they 之外的简单情形由词表驱动）
# 为避免误伤，仅覆盖高频且明确的模式。
THIRD_PERSON_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(he|she|it|this|that)\s+(like|want|need|have|go|do|make|get|know|think|look|feel|seem|come|take|give|say|tell|work|study|play|live|love|hate)\b", re.I),
     "加 -s/-es", "第三人称单数（he/she/it）后动词要加 -s/-es：He likes / She wants。"),
    (re.compile(r"\b(they|we|you)\s+(likes|wants|needs|has|goes|does|makes|gets|knows|thinks|looks|feels|seems|comes|takes|gives|says|tells|works|studies|plays|lives|loves|hates)\b", re.I),
     "去掉 -s/-es", "复数主语（they/we/you）后动词用原形：They like / We want。"),
]

# 反向主谓一致：be 动词误用（They is / We is / You was）。
# 只覆盖标准英语中明确错误的组合；I am / I was 本身正确，不纳入。
REVERSE_AGREEMENT_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\bi\s+is\b", re.I), "am",
     "第一人称 I 后用 am：I am a student（过去时用 was）。"),
    (re.compile(r"\b(you|we|they)\s+is\b", re.I), "are",
     "you / we / they 后用 are：They are my friends。"),
    (re.compile(r"\b(you|we|they)\s+was\b", re.I), "were",
     "you / we / they 后用 were：We were late。"),
]

# didn't / did not 后须接动词原形（I didn't went → I didn't go）。
# 只收「过去式与动词原形不同形」的词：
#   · 原形同形的 read/put/cut/let/set/cost/hit/shut/hurt 等一律排除；
#   · found 亦排除——它作「创立」时是原形，They didn't found the club 本身正确。
IRREGULAR_PAST: dict[str, str] = {
    "went": "go", "ate": "eat", "came": "come", "did": "do", "got": "get",
    "took": "take", "made": "make", "said": "say", "told": "tell",
    "bought": "buy", "brought": "bring", "thought": "think", "gave": "give",
    "knew": "know", "wrote": "write", "spoke": "speak", "drove": "drive",
    "broke": "break", "chose": "choose", "began": "begin", "drank": "drink",
    "swam": "swim", "ran": "run", "sat": "sit", "slept": "sleep",
    "met": "meet", "kept": "keep", "felt": "feel", "left": "leave",
    "lost": "lose", "paid": "pay", "saw": "see", "heard": "hear",
    "held": "hold", "stood": "stand", "understood": "understand",
    "wore": "wear", "won": "win", "sent": "send", "spent": "spend",
    "taught": "teach", "caught": "catch", "built": "build", "forgot": "forget",
}
_DID_PAST_RE = re.compile(r"\b(didn't|did not|didnt)\s+([a-z]+)\b", re.I)

# 宾格：这些动词后接人称代词作宾语，须用宾格（her/him/them/us）。
# 实测 32 句正常英文（含本套件 18 句误报防护语料）误报 0 —— I like her / I helped them
# 都不命中，只有 I like she 这类真错才命中，故判为明确问题（issue）。
OBJECT_PRONOUN_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(like|love|thank|help|ask|miss|tell|call)\s+(she|he|they|we)\b", re.I),
     "改为宾格 her / him / them / us",
     "动词后作宾语要用宾格：I like her / I helped them。"),
]

# 动词后缺 to：want/need/hope/plan/try/decide/would like 直接接另一动词原形时中间需 to
# （want to go）。目标动词只取无名词歧义者——
#   · 移除 study（plan study sessions 中 study 是定语，非动词）；
#   · 其余词加 (?![-']) 负向断言（want take-out 中 take 属名词复合）。
# 实测这两项收紧把误报从 12.5% 降到 0，仍保留 want go / need eat 的真错召回。
VERB_TO_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(
        r"\b(want|need|hope|plan|try|decide|would like)\s+"
        r"(go|eat|see|buy|take|meet|learn)(?![\-'])\b", re.I),
     "前一个动词后加 to",
     "这些动词后接另一个动词要用 to：want to go / need to eat。"),
]

# 冠词：可数名词单数前缺冠词的高频模式（限定常见名词，降低误报）
MISSING_ARTICLE_NOUNS = {
    "coffee": "a coffee", "latte": "a latte", "movie": "a movie", "film": "a film",
    "class": "a class", "book": "a book", "room": "a room", "question": "a question",
    "problem": "a problem", "friend": "a friend", "cup": "a cup", "meal": "a meal",
    "sandwich": "a sandwich", "club": "a club", "job": "a job", "major": "a major",
}

# 名词复数提示：这些名词在 these/those/many/a few/several 后需要复数
_PLURAL_CONTEXT_RE = re.compile(
    r"\b(these|those|many|few|several|two|three|four|five)\s+([a-z]+)\b", re.I
)
_UNCOUNTABLE = {
    "water", "rice", "music", "homework", "information", "advice", "news", "money",
    "food", "bread", "milk", "tea", "fruit", "luggage", "furniture", "equipment",
    "coffee", "tea", "work", "paper", "time", "life",
}
IRREGULAR_PLURALS = {
    "person": "people", "child": "children", "man": "men", "woman": "women",
    "foot": "feet", "tooth": "teeth", "mouse": "mice",
}

# 常见副词/形容词误用（本地可确定的高频情形）
ADVERB_ADJ_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(speak|speaks|talk|talks|write|writes|read|reads)\b[^.!?]*?\b(good|bad|quick|slow|nice)\b", re.I),
     "well / badly",
     "修饰动词要用副词：speak English well，不用 good；write quickly，不用 quick。"),
    (re.compile(r"\brun (quick|slow)\b", re.I),
     "quickly / slowly", "修饰动词用副词：run quickly / slowly。"),
    (re.compile(r"\b(do|does|did|work|works)\b[^.!?]*?\b(good|nice)\b", re.I),
     "well", "修饰动词 do / work 要用副词 well：do well / work well。"),
]

# 冠词：这些动词后的名词作「类指」用时不加冠词，需避免误报。
# 例如 I like coffee / I eat rice / I play basketball 都是正确的。
_GENERIC_VERBS = {
    "like", "love", "enjoy", "prefer", "hate", "dislike", "want", "need",
    "eat", "drink", "play", "study", "learn", "teach", "speak", "watch",
    # have 后接类指名词同样合法（have class 有课 / have lunch 吃午饭），补入以修误报
    "have",
}
# 上表动词后不应报「缺冠词」的名词（类指用法）
_GENERIC_NOUNS = {
    "coffee", "tea", "milk", "water", "rice", "food", "bread", "music",
    "basketball", "football", "soccer", "tennis", "chess", "english", "chinese",
    "math", "history", "science", "art", "spanish", "french",
    # have class / have school 是「有课 / 上学」的固定说法，不算漏冠词
    "class", "school",
}

# 时态提示：明确的过去时间标志 + 动词原形（仅提示，不武断判定）
PAST_TIME_RE = re.compile(r"\b(yesterday|last night|last week|last month|last year|ago)\b", re.I)
PRESENT_SIMPLE_VERBS = {
    "go", "eat", "see", "watch", "meet", "buy", "take", "give", "make", "come",
    "do", "get", "have", "know", "think", "feel", "say", "tell", "work", "study",
    "play", "live", "visit", "learn", "speak", "talk", "want", "like",
}

POLITE_PATTERNS: list[tuple[str, str]] = [
    ("please", "使用了 please，语气礼貌自然。"),
    ("thank", "使用了 thanks / thank you，收尾自然。"),
    ("could i", "使用了 Could I ... 句式，礼貌请求很到位。"),
    ("i'd like", "使用了 I'd like ... 句式，比 I want 更自然礼貌。"),
    ("would you", "使用了 Would you ... 句式，表达得体。"),
    ("would you mind", "使用了 Would you mind ... 句式，委婉得体。"),
    ("shall we", "使用了 Shall we ... 句式，提议自然。"),
    ("do you mind", "使用了 Do you mind ... 句式，礼貌询问。"),
]


@dataclass
class Issue:
    """一条可改进的问题。"""

    kind: str       # 类别标签：拼写 / 大小写 / 冠词 / 用法 / 礼貌表达 / 语言
    quote: str      # 检测到的原文片段
    fix: str        # 建议修正
    reason: str     # 简短原因
    severity: str = "issue"  # issue=问题；suggestion=建议（非错误）
    span: tuple[int, int] | None = None  # 原文位置，供「同落点去重」使用


@dataclass
class AnswerFeedback:
    """单条回答的反馈。"""

    answer: str
    issues: list[Issue] = field(default_factory=list)
    suppressed_count: int = 0  # 因「每轮最多 3 条」被截断、未展示的条数


@dataclass
class FeedbackReport:
    """整场互动的反馈汇总。"""

    answers: list[AnswerFeedback] = field(default_factory=list)
    praises: list[str] = field(default_factory=list)
    overall: str = ""
    limitations: str = (
        "以上反馈基于本地规则库，覆盖拼写、大小写、a/an、主谓一致、代词宾格、动词不定式、"
        "名词数、词性、时态提示、常见中式表达与用词搭配等**可确定的有限类型**；"
        "语义是否通顺、复杂语法是否准确、表达是否地道，本地规则无法可靠判断，"
        "本环节未进行全面的智能评估。规则未报错不代表表达完全正确。"
    )

    @property
    def issue_count(self) -> int:
        return sum(len(a.issues) for a in self.answers)

    @property
    def hard_issue_count(self) -> int:
        """确定性问题的数量（severity=issue），用于区分「问题」与「建议」。"""
        return sum(
            1 for a in self.answers for i in a.issues if i.severity == "issue"
        )

    @property
    def suggestion_count(self) -> int:
        """改进建议的数量（severity=suggestion，非错误）。"""
        return sum(
            1 for a in self.answers for i in a.issues if i.severity == "suggestion"
        )

    @property
    def issue_kinds(self) -> list[str]:
        """出现的问题类别（去重，供总结与展示）。"""
        kinds: list[str] = []
        for a in self.answers:
            for i in a.issues:
                if i.kind not in kinds:
                    kinds.append(i.kind)
        return kinds

    @property
    def issue_summary(self) -> list[str]:
        """问题摘要（去重，供学习总结使用）。"""
        seen: list[str] = []
        for answer in self.answers:
            for issue in answer.issues:
                line = f"{issue.quote} → {issue.fix}"
                if line not in seen:
                    seen.append(line)
        return seen


def has_chinese(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def split_mixed(text: str) -> tuple[str, str]:
    """把中英混说的输入拆成 (英文片段, 中文片段)。

    P2-2：原实现对含中文的输入**直接短路**——只要出现一个汉字就只回一句
    「用英语回答」，英文部分完全不检查（实测 `I want to 点单` 的英文拼写/语法
    问题会被整体漏掉）。拆分后可同时给出语言提示与英文部分的检查结果。
    """
    src = text or ""
    chinese = "".join(_CJK_RE.findall(src))
    english = _CJK_RE.sub(" ", src)
    english = _CJK_PUNCT_RE.sub(" ", english)
    english = re.sub(r"\s+", " ", english).strip()
    return english, chinese


def _spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """两个原文区间是否重叠（用于判定两条反馈是否指向同一处毛病）。"""
    return a[0] < b[1] and b[0] < a[1]


def _tidy_issues(
    issues: list[Issue], limit: int = MAX_ISSUES_PER_ANSWER
) -> tuple[list[Issue], int]:
    """反馈粒度收敛：去重 → 同落点合并 → 明确问题优先 → 截断到 limit 条。

    返回 ``(保留的反馈列表, 被截断丢弃的条数)``。

    对齐 SKILL.md §4「每轮只聚焦 1–3 条」与反模式 #8「不要一口气罗列所有小错误」，
    把「粒度克制」从教学指令真正落进本地规则引擎（两条轨道行为一致）。
    sorted 为稳定排序，同严重度内保持原始检出顺序。

    D-03：除 (kind, fix) 精确去重外，同 kind 内**位置重叠**的两条按「同一处毛病」
    合并，保留覆盖更长（更具体）的一条——修掉 ``I very like it.`` 同时报
    ``very like`` 与 ``I very`` 两条口径不一建议、占满 2/3 额度的问题。
    """
    ordered = sorted(issues, key=lambda i: i.severity != "issue")  # issue 优先
    seen: set[tuple[str, str]] = set()
    kept: list[Issue] = []
    for issue in ordered:
        key = (issue.kind, issue.fix)
        if key in seen:
            continue
        # 同落点：与已保留的同类项位置重叠时，只留覆盖更长（更具体）的一条
        merged = False
        for idx, prev in enumerate(kept):
            if prev.kind != issue.kind or prev.span is None or issue.span is None:
                continue
            if not _spans_overlap(prev.span, issue.span):
                continue
            if (issue.span[1] - issue.span[0]) > (prev.span[1] - prev.span[0]):
                seen.discard((prev.kind, prev.fix))
                seen.add(key)
                kept[idx] = issue
            merged = True
            break
        if merged:
            continue
        seen.add(key)
        kept.append(issue)
    return kept[:limit], max(0, len(kept) - limit)


# ---------------------------------------------------------------------------
# 单条回答检查
# ---------------------------------------------------------------------------

def evaluate_answer(answer: str, scene: dict | None = None) -> AnswerFeedback:
    """对单条回答执行本地规则检查。scene 用于场景相关的建议（如点单礼貌表达）。"""
    fb = AnswerFeedback(answer=answer)
    text = str(answer or "").strip()  # 防御：协议层已保证 str，模块级调用可能传其他类型
    if not text:
        return fb

    if has_chinese(text):
        english_part, chinese_part = split_mixed(text)
        fb.issues.append(Issue(
            kind="语言", quote=(chinese_part or text)[:24], fix="用英语回答",
            reason="练习环节建议尽量用英语表达，这样反馈才有效；你可以先套用学过的句式。"
                   "（中文部分已标注，其中的英文片段仍会照常检查）",
            severity="suggestion",
        ))
        # P2-2：中文不再整体短路——若句中混有英文，继续对英文片段跑全部规则，
        # 避免「I want to 点单」这类中英混说把英文部分的拼写/语法问题整体漏掉。
        if not _WORD_RE.search(english_part):
            return fb
        text = english_part

    scene_id = (scene or {}).get("id", "")

    # 1) 第一人称代词 i 未大写
    if _I_RE.search(text):
        fixed = _I_RE.sub("I", text)
        fb.issues.append(Issue(
            kind="大小写", quote="i", fix="I",
            reason="英语中第一人称代词 I 无论出现在哪里都必须大写。",
        ))
        text = fixed
    if _IM_RE.search(text):
        fixed = _IM_RE.sub("I'm", text)
        fb.issues.append(Issue(
            kind="大小写", quote="im", fix="I'm",
            reason="im 应写为 I'm（I am 的缩写，I 必须大写）。",
        ))
        text = fixed

    # 2) 句首字母大写（仅对 4 词以上的句子提示，避免误伤对话短答）
    words = _WORD_RE.findall(text)
    if len(words) >= 4 and _SENTENCE_START_LOWER_RE.match(text) and not text.startswith("i"):
        first = text[0]
        fb.issues.append(Issue(
            kind="大小写", quote=text[:12] + ("…" if len(text) > 12 else ""), fix=first.upper() + text[1:12] + ("…" if len(text) > 12 else ""),
            reason="英语句子开头字母一般需要大写。", severity="suggestion",
        ))

    # 3) 拼写
    for wrong, right in SPELLING_FIXES.items():
        if re.search(rf"\b{re.escape(wrong)}\b", text, re.I):
            fb.issues.append(Issue(
                kind="拼写", quote=wrong, fix=right,
                reason=f"「{wrong}」不是标准拼写，正确形式是「{right}」。",
            ))

    # 4) a / an
    m = _A_VOWEL_RE.search(text)
    if m and m.group(1).lower() not in _A_AN_EXCEPTIONS_A:
        fb.issues.append(Issue(
            kind="冠词", quote=m.group(0), fix=f"an {m.group(1)}",
            reason="元音音素开头的单词前用 an。",
        ))
    m = _AN_CONSONANT_RE.search(text)
    if m and m.group(1).lower() not in _A_AN_EXCEPTIONS_AN:
        # 降级为「建议」：an 后接辅音字母开头的词通常应改 a，但字母缩写按「字母音」
        # 读、可能确实以元音开头（an FBI / an NBA / an SOS / an HR …），白名单无法穷举。
        # 按 teaching_guide §4.2「判不准时宁可标为建议，不要标为错误」，此处只给建议。
        fb.issues.append(Issue(
            kind="冠词", quote=m.group(0), fix=f"a {m.group(1)}",
            reason="若该词按辅音音素开头则应用 a（如 a book）；但字母缩写按字母音读，"
                   "可能仍用 an（如 an FBI / an MBA），请按实际读音判断。",
            severity="suggestion",
        ))
    # a + 「h 开头但读音为元音」的词（honest / hour / honor）应为 an
    m = re.search(r"\ba\s+(honest|hour|honor|honour|heir)\b", text, re.I)
    if m:
        fb.issues.append(Issue(
            kind="冠词", quote=m.group(0), fix=f"an {m.group(1)}",
            reason=f"{m.group(1)} 虽以辅音字母 h 开头，但 h 不发音、读音以元音开头，需用 an。",
        ))

    # 5) 常见中式表达 / 用法建议
    for pattern, fix, reason in USAGE_RULES:
        m = pattern.search(text)
        if m:
            fb.issues.append(Issue(
                kind="用法", quote=m.group(0), fix=fix, reason=reason,
                severity="suggestion", span=m.span(),
            ))
    for pattern, fix, reason in CHINGLISH_RULES:
        m = pattern.search(text)
        if m:
            fb.issues.append(Issue(
                kind="中式表达", quote=m.group(0), fix=fix, reason=reason,
                severity="suggestion", span=m.span(),
            ))

    # 5.1) 主谓一致（第三人称单数 / 复数主语）
    for pattern, fix, reason in THIRD_PERSON_PATTERNS:
        m = pattern.search(text)
        if m:
            fb.issues.append(Issue(
                kind="语法·主谓一致", quote=m.group(0), fix=fix, reason=reason,
            ))

    # 5.1b) 宾格：动词后的人称代词须用宾格（I like she → I like her）
    for pattern, fix, reason in OBJECT_PRONOUN_RULES:
        m = pattern.search(text)
        if m:
            fb.issues.append(Issue(
                kind="语法·代词", quote=m.group(0), fix=fix, reason=reason,
            ))

    # 5.1c) 动词后缺 to（He want go → He wants to go）
    for pattern, fix, reason in VERB_TO_RULES:
        m = pattern.search(text)
        if m:
            fb.issues.append(Issue(
                kind="语法·不定式", quote=m.group(0), fix=fix, reason=reason,
            ))

    # 5.1d) 反向主谓一致（They is → They are / You was → You were）
    for pattern, fix, reason in REVERSE_AGREEMENT_PATTERNS:
        m = pattern.search(text)
        if m:
            fb.issues.append(Issue(
                kind="语法·主谓一致", quote=m.group(0), fix=fix, reason=reason,
                span=m.span(),
            ))

    # 5.1e) didn't / did not + 过去式（I didn't went → I didn't go）
    m = _DID_PAST_RE.search(text)
    if m and m.group(2).lower() in IRREGULAR_PAST:
        base = IRREGULAR_PAST[m.group(2).lower()]
        fb.issues.append(Issue(
            kind="语法·时态", quote=m.group(0), fix=f"{m.group(1)} {base}",
            reason=f"didn't / did not 已表示过去，后面动词要用原形：didn't {base}。",
            span=m.span(),
        ))

    # 5.2) 名词数：these/those/many + 单数可数名词
    m = _PLURAL_CONTEXT_RE.search(text)
    if m and m.group(2).lower() not in _UNCOUNTABLE:
        noun = m.group(2).lower()
        if noun in IRREGULAR_PLURALS:
            fix = IRREGULAR_PLURALS[noun]
        elif not noun.endswith("s"):
            fix = noun + "s"
        else:
            fix = noun
        if fix != noun:
            fb.issues.append(Issue(
                kind="语法·名词数", quote=m.group(0), fix=f"{m.group(1)} {fix}",
                reason=f"{m.group(1)} 后接可数名词需要用复数形式。", severity="suggestion",
            ))

    # 5.3) 副词 / 形容词误用
    for pattern, fix, reason in ADVERB_ADJ_RULES:
        m = pattern.search(text)
        if m:
            fb.issues.append(Issue(
                kind="语法·词性", quote=m.group(0), fix=fix, reason=reason,
            ))

    # 5.4) 时态提示（过去时间标志 + 动词原形）——只提示，不武断判定
    if PAST_TIME_RE.search(text) and not re.search(r"\bwas\b|\bwere\b|\bhad\b|\b\w+ed\b|\bdid\b", text, re.I):
        hits = [w for w in _WORD_RE.findall(text.lower()) if w in PRESENT_SIMPLE_VERBS]
        if hits:
            fb.issues.append(Issue(
                kind="语法·时态", quote=", ".join(hits[:2]),
                fix=f"{hits[0]} → 过去式（如 went / ate / saw）",
                reason="句中出现 yesterday / last week / ago 等过去时间标志，动词通常需要用过去式。",
                severity="suggestion",
            ))

    # 5.5) 可数名词单数缺冠词（仅限常见名词，避免误伤）
    for m in re.finditer(r"(?<![A-Za-z])([a-z]+)(?![A-Za-z])", text.lower()):
        word = m.group(1)
        if word not in MISSING_ARTICLE_NOUNS:
            continue
        # 前一个词是否为冠词/限定词/介词；后一个词是否为动词（跳过 I like coffee 这类合理用法）
        before = text[:m.start()].rstrip().lower()
        last_word = re.findall(r"[a-z']+", before)
        if last_word and last_word[-1] in {"a", "an", "the", "my", "your", "his", "her",
                                           "our", "their", "this", "that", "some", "any",
                                           "no", "every", "each", "another", "one", "more"}:
            continue
        after = text[m.end():].lstrip().lower()
        if after.startswith(("s", "es")):  # 可能是复数
            continue
        # 仅当该名词处于「非类指」的及物动词之后时才提示（避免 I like coffee 误报）
        if last_word and last_word[-1] in {"get", "have", "need", "want", "like", "order",
                                           "buy", "make", "take", "grab", "bring", "give"}:
            if last_word[-1] in _GENERIC_VERBS and word in _GENERIC_NOUNS:
                continue  # 类指用法，正确，不报
            fb.issues.append(Issue(
                kind="冠词", quote=f"{last_word[-1]} {word}",
                fix=f"{last_word[-1]} {MISSING_ARTICLE_NOUNS[word]}",
                reason=f"{word} 作可数名词单数时通常需要冠词（a/an/the）。", severity="suggestion",
            ))
            break

    # 6) 场景相关的礼貌表达建议
    #    点单类（咖啡店 / 食堂）：I want → 更礼貌的请求句式
    if scene_id in {"coffee_ordering", "campus_canteen"} and re.search(r"\b(i\s+)?want\b", text, re.I):
        m = re.search(r"\bi\s+want\b|\bwant\b", text, re.I)
        fb.issues.append(Issue(
            kind="礼貌表达", quote=m.group(0), fix="I'd like ... / Could I get ...",
            reason="点单时用 I'd like / Could I get 比 I want 更礼貌自然。",
            severity="suggestion",
        ))

    #    面试类：Hello 开场 → 更专业的开场
    if scene_id == "part_time_job" and re.search(r"^\s*(hello|hi)\b", text, re.I):
        m = re.search(r"^\s*(hello|hi)\b", text, re.I)
        fb.issues.append(Issue(
            kind="面试表达", quote=m.group(0), fix="Thanks for having me",
            reason="面试开场用 Thanks for having me 比 Hello/Hi 更专业得体。",
            severity="suggestion",
        ))

    #    课堂提问：I don't understand → 更自然的说法
    if scene_id == "class_question" and re.search(r"\bi\s+don'?t\s+understand\b", text, re.I):
        m = re.search(r"\bi\s+don'?t\s+understand\b", text, re.I)
        fb.issues.append(Issue(
            kind="课堂表达", quote=m.group(0), fix="I didn't quite catch that. / Could you explain it again?",
            reason="课堂上说听不懂时，I didn't quite catch that 比 I don't understand 更自然、更不显得生硬。",
            severity="suggestion",
        ))

    # 7) 粒度收敛：去重 + 明确问题优先 + 每轮最多 3 条
    fb.issues, fb.suppressed_count = _tidy_issues(fb.issues)

    return fb


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------

def _is_meaningful_answer(text) -> bool:
    """是否为一条「可检查的回答」：至少含一个英文字母或汉字。

    纯空白、纯数字/符号（如协议层宽松转换后的 ``""`` 与 ``"123"``）不计入有效
    回答，避免「调用方传错元素类型 → 仍输出『整体表达清晰』」的误导性结论（D-02）。
    """
    return bool(re.search(r"[A-Za-z\u4e00-\u9fff]", str(text or "")))


def evaluate_answers(scene: dict, answers: list[str]) -> FeedbackReport:
    """汇总多轮回答的反馈。"""
    report = FeedbackReport()
    for ans in answers:
        report.answers.append(evaluate_answer(ans, scene=scene))

    effective = [a for a in answers if _is_meaningful_answer(a)]

    praises: list[str] = []
    joined = " ".join(str(a) for a in answers if a).lower()
    for key, praise in POLITE_PATTERNS:
        if key in joined and praise not in praises:
            praises.append(praise)
    report.praises = praises

    if not effective:
        report.overall = "本次没有有效的英语回答记录，未能进行表达检查。"
    elif report.issue_count == 0:
        report.overall = "所有回答均未检测到问题（本地规则范围内），整体表达清晰。"
    else:
        hard = report.hard_issue_count
        sug = report.suggestion_count
        if hard and sug:
            report.overall = (
                f"共检测到 {hard} 处明确问题、{sug} 条改进建议（本地规则范围内），"
                f"涉及：{'、'.join(report.issue_kinds)}。详见下方逐条说明。"
            )
        elif hard:
            report.overall = (
                f"共检测到 {hard} 处明确问题（本地规则范围内），"
                f"涉及：{'、'.join(report.issue_kinds)}。详见下方逐条说明。"
            )
        else:
            report.overall = (
                f"未检测到明确错误，但有 {sug} 条让表达更自然的建议（本地规则范围内），"
                f"涉及：{'、'.join(report.issue_kinds)}。详见下方逐条说明。"
            )
    return report
