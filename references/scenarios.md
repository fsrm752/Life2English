# Life2English 场景模板库总览

本文件是 SKILL.md 引用的参考资料，用于让执行技能的 AI 快速了解可用场景与模板结构。
数据源：`scripts/data/scenarios.json`（模板与逻辑分离，新增场景只需改数据）。

当前 **8 个场景**，版本 1.2。每个模板含：情境、目标、实用表达、中文解释、例句、常见错误、互动任务、迁移练习、注意事项。

## 场景索引

| scene_id | 场景 | 难度 | 主题标签 | 触发示例 |
|---|---|---|---|---|
| `coffee_ordering` | 咖啡店点单 | 入门 | 日常服务、店员沟通、消费 | 我想在咖啡店点单 |
| `club_recruitment` | 社团招新与自我介绍 | 入门 | 校园、社交、介绍自己 | 我想练习社团招新自我介绍 |
| `movie_talk` | 与外国同学讨论电影 | 入门-进阶 | 社交、娱乐、讨论 | 我想和外国同学讨论电影 |
| `campus_life` | 介绍大学生活 | 入门 | 校园、介绍、日常 | 我想介绍我的大学生活 |
| `class_question` | 课堂提问与答疑 | 入门 | 校园、学习、课堂、师生沟通 | 我想练习在课堂上向老师提问 |
| `part_time_job` | 兼职面试与工作沟通 | 进阶 | 就业、面试、职场、实习 | 我想练习英文兼职面试 |
| `campus_canteen` | 食堂点餐与沟通 | 入门 | 日常服务、餐饮、消费、校园 | 我想练习在食堂点餐 |
| `dorm_life` | 宿舍生活与舍友沟通 | 入门 | 校园、社交、日常、住宿 | 我想练习和舍友用英语沟通 |

## 各场景详情

### 咖啡店点单（`coffee_ordering`）

- **情境**：在咖啡店用英语完成一次完整点单：打招呼、点单、说明杯型、结账致谢
- **学习目标**：学会在咖啡店用英语完成一次完整点单：打招呼、点单、说明杯型（堂食/外带）、结账致谢。
- **核心关键词**：咖啡店、咖啡厅、点单、点咖啡、点一杯、点杯、cafe、coffee
- **扩展关键词**：咖啡、拿铁、美式、卡布奇诺、饮品、喝点东西、菜单、奶茶
- **实用表达**：
  - `Hi, could I get a medium latte, please?` —— 你好，请给我一杯中杯拿铁。（点单最常用句式：Could I get ..., please?）
  - `For here, please. / To go, please.` —— 堂食，谢谢。/ 外带，谢谢。（店员常问 For here or to go?）
  - `Could you make it with oat milk?` —— 可以帮我换成燕麦奶吗？（特殊要求用 Could you ... 开头更礼貌）
  - `How much is it altogether?` —— 一共多少钱？（结账时的常用问法）
  - `Thanks, have a nice day!` —— 谢谢，祝你今天愉快！（结束对话的自然收尾）
- **情境互动**：对话对象「咖啡店店员」，4 轮，开场：Hi there, welcome to our café! What can I get for you today?
- **迁移练习**：奶茶店点单 (tea shop) —— 假设你在一家奶茶店，想点一杯少糖的珍珠奶茶并外带。请用本场景学过的句式（如 Could I get ... / To go, please）说一句话。
- **注意事项**：
  - Could I get ... 比 I want ... 更礼貌，点单场景优先使用
  - please 放在句尾能让语气更自然
- **常见错误**：
  - ❌ I want a coffee → ✅ Could I get a coffee, please?（点单用 request 句式更礼貌）
  - ❌ 说 For here 时才堂食；外带是 To go，别说成 Take away 之外的自造说法
  - ❌ What's the price? 也可，但结账更常说 How much is it altogether?
- **下一步建议**：下次可以尝试更复杂的定制要求：换奶（oat milk）、温度（extra hot）、加浓度（extra shot）。

### 社团招新与自我介绍（`club_recruitment`）

- **情境**：在社团招新中用英语介绍自己：姓名、专业、兴趣、加入理由
- **学习目标**：学会在社团招新中用英语完成自我介绍，并能说明自己的兴趣和加入理由。
- **核心关键词**：社团、招新、加入社团、社团面试、club、自我介绍
- **扩展关键词**：兴趣、面试、报名、学生会、部门、爱好、大学生社团
- **实用表达**：
  - `Hi, I'm Chen Lin. I'm a freshman majoring in computer science.` —— 你好，我是陈林，计算机专业大一学生。（自我介绍基本结构：姓名 + 年级 + 专业）
  - `I'm really into photography and editing videos.` —— 我非常喜欢摄影和剪辑视频。（be into ... 表示「喜欢、感兴趣」，口语中很常用）
  - `I'd love to join the club because I want to meet new friends.` —— 我很想加入这个社团，因为我想认识新朋友。（说加入理由时用 because 给出原因）
  - `I have some experience in event planning.` —— 我在活动策划方面有些经验。（experience in ... 用来展示相关经验）
  - `When do you usually have activities?` —— 你们一般什么时候有活动？（了解社团安排的自然问法）
- **情境互动**：对话对象「社团学长/学姐」，4 轮，开场：Hey! Welcome to our club's recruitment booth. Could you tell me a bit about yourself?
- **迁移练习**：课堂自我介绍 (first day of class) —— 开学第一节课，老师请你用英语向全班做自我介绍（姓名、专业、爱好）。请试一句。
- **注意事项**：
  - freshman 指大一学生，介绍年级时说 I'm a freshman 很自然
  - 避免中式表达 I am called ...，直接用 I'm ...
- **常见错误**：
  - ❌ I am called Tom → ✅ My name is Tom / I'm Tom（介绍姓名不用 I am called）
  - ❌ I very like music → ✅ I really like music（very 不直接修饰动词）
  - ❌ I join the club because I want. → 理由要说完：because I want to meet new people.
- **下一步建议**：可以练习更完整的自我介绍：家乡 + 专业 + 爱好 + 期待，控制在 4-6 句。

### 与外国同学讨论电影（`movie_talk`）

- **情境**：用英语和外国同学聊电影：最近看了什么、评价、互相推荐
- **学习目标**：学会用英语和外国同学聊电影：询问近况、表达喜好、说明理由、互相推荐。
- **核心关键词**：电影、movie、film、聊电影、讨论电影
- **扩展关键词**：影院、演员、剧情、导演、推荐、看片、电视剧、评分
- **实用表达**：
  - `Have you seen any good movies lately?` —— 你最近看了什么好电影吗？（lately 表示「最近」，用来开启话题很自然）
  - `What did you think of it?` —— 你觉得那部电影怎么样？（问对方评价的常用句）
  - `I really enjoyed the plot — it kept me guessing.` —— 我很喜欢剧情，一直让人猜不到走向。（评价电影可以从 plot / acting / music / ending 入手）
  - `The acting was amazing, but the ending felt a bit rushed.` —— 演技很棒，但结尾有点仓促。（用 but 表达「褒贬结合」更自然）
  - `If you like science fiction, I'd definitely recommend it.` —— 如果你喜欢科幻片，我强烈推荐这部。（推荐影片时先给出对方可能喜欢的类型）
- **情境互动**：对话对象「外国同学」，4 轮，开场：Hey! Good to see you. Have you seen any good movies lately?
- **迁移练习**：讨论电视剧 (TV series) —— 这次换你主动开启话题：向朋友推荐一部你最近在追的电视剧。请试一句。
- **注意事项**：
  - 评论电影常见维度：plot 剧情 / acting 演技 / visuals 画面 / soundtrack 配乐
- **常见错误**：
  - ❌ I very like this movie → ✅ I really like this movie
  - ❌ This movie is very interesting for me → ✅ I find this movie very interesting
  - ❌ 评价电影只会说 good/nice，可换成 gripping 扣人心弦 / moving 感人 / hilarious 好笑
- **下一步建议**：积累电影类型词汇：comedy 喜剧 / thriller 惊悚片 / documentary 纪录片 / animation 动画。

### 介绍大学生活（`campus_life`）

- **情境**：用英语向外国朋友介绍大学生活：校园、课程、日常安排、最喜欢的部分
- **学习目标**：学会用英语向外国朋友介绍大学生活：学校、专业、每天做什么、最喜欢什么。
- **核心关键词**：大学生活、校园生活、介绍大学、campus life、campus、我的大学
- **扩展关键词**：宿舍、课程、大一、新生、专业、食堂、图书馆、室友
- **实用表达**：
  - `I'm a freshman at my university.` —— 我是大一新生。（把 my university 替换成你的学校名即可，如 Sichuan University）
  - `I live in a dormitory on campus.` —— 我住在校内宿舍。（dormitory 口语中常简称为 dorm）
  - `On a typical day, I have classes in the morning and study in the library in the afternoon.` —— 平常我上午上课，下午在图书馆自习。（用 On a typical day 描述日常安排）
  - `My favorite part of campus life is the clubs and activities.` —— 校园生活里我最喜欢的是社团和活动。（用 My favorite part is ... 表达偏好）
  - `What about campus life in your country?` —— 你们国家的校园生活怎么样？（用 What about ... 把话题抛回去，让对话继续）
- **情境互动**：对话对象「外国朋友」，4 轮，开场：I heard you're in university now! I'd love to know more about campus life in China. Can you tell me about your school?
- **迁移练习**：向外国朋友介绍你的专业 (your major) —— 这次聚焦你的专业：用英语告诉一位外国朋友你学什么、最喜欢哪门课。请试一句。
- **注意事项**：
  - 描述日常用一般现在时即可，不用刻意堆时态
  - 介绍时给出具体细节（数字、名称），交流感更强
- **常见错误**：
  - ❌ I am a student of the university from... → ✅ I'm a freshman at CQU.
  - ❌ My university has many building → ✅ many buildings（many 后接复数）
  - ❌ 只罗列事实不给细节，加上感受更自然：I love the library because it's quiet.
- **下一步建议**：可以扩展练习：把「校园生活」讲成一个 1 分钟小演讲（my campus / my classes / my friends）。

### 课堂提问与答疑（`class_question`）

- **情境**：在课堂上用英语向老师提问、追问细节并致谢
- **学习目标**：学会在课堂上礼貌地用英语提问、追问和致谢，做到不打断、不冒犯。
- **核心关键词**：课堂提问、向老师提问、课上提问、提问、答疑、不懂就问
- **扩展关键词**：老师、教授、上课、课件、作业、没听懂、再讲一遍、office hour
- **实用表达**：
  - `Excuse me, could I ask a quick question?` —— 不好意思，我可以问一个简短的问题吗？（提问前先礼貌地争取发言机会）
  - `Sorry, I didn't quite catch that. Could you explain it again?` —— 抱歉，我没太听懂，可以再讲一遍吗？（没听懂时用这句，比 I don't understand 更自然）
  - `Do you mean that we should submit it before Friday?` —— 您的意思是我们应该在周五前交吗？（用 Do you mean... 复述确认，避免误解）
  - `Could you give us an example of that?` —— 能给我们举个例子吗？（要求举例的高频句式）
  - `Thank you, that's much clearer now.` —— 谢谢，现在清楚多了。（得到解答后礼貌收尾）
- **情境互动**：对话对象「老师」，4 轮，开场：Alright, does anyone have questions about today's material?
- **迁移练习**：向助教（TA）请教作业 (teaching assistant) —— 假设你在课后向助教请教一道作业题，请用本场景学过的句式（如 Could I ask... / Could you give me an example...）说一句话。
- **注意事项**：
  - 提问前先说 Excuse me / Sorry to interrupt，避免显得唐突
  - 没听懂是正常的，用 Could you explain it again? 比沉默更有效
- **常见错误**：
  - ❌ I don't understand. 语气偏生硬 → ✅ Sorry, I didn't quite catch that.
  - ❌ How to say this word? → ✅ How do you say this word in English?
  - ❌ 直接打断老师说 No, you're wrong → 先礼貌争取：Excuse me, could I ask...?
- **下一步建议**：下次可以练习在小组讨论中用英语提出不同意见：I see your point, but I think...

### 兼职面试与工作沟通（`part_time_job`）

- **情境**：用英语应对校园兼职/实习面试的自我介绍与问答
- **学习目标**：学会用英语完成一次兼职/实习面试：自我介绍、说明经历、询问工作安排。
- **核心关键词**：兼职面试、求职面试、英文面试、实习面试、找工作、面试
- **扩展关键词**：兼职、实习、简历、经验、岗位、招人、薪资、排班、打工
- **实用表达**：
  - `Thanks for having me. I'm a freshman majoring in Electrical Engineering.` —— 谢谢给我这个机会。我是电气工程专业的大一新生。（面试开场的自我介绍句式）
  - `I have some experience in customer service from a campus event.` —— 我在一次校园活动中有过客服经验。（用 I have experience in ... 说明相关经历）
  - `Could you tell me more about the working hours?` —— 能详细说说工作时间安排吗？（询问岗位信息用 Could you tell me...）
  - `I'm available on weekends and weekday evenings.` —— 我周末和工作日晚上都有空。（说明可用时间，体现可靠性）
  - `I'm a fast learner and I work well in a team.` —— 我学得很快，也善于团队合作。（概括自身优势的高频表达）
- **情境互动**：对话对象「面试官」，5 轮，开场：Hi, thanks for coming in. Could you start by telling me a bit about yourself?
- **迁移练习**：参加社团干部面试 (club officer interview) —— 假设你在面试社团干部，请用本场景学过的句式（如 I have experience in... / I'm a fast learner...）说一句话介绍自己。
- **注意事项**：
  - 面试开场用 Thanks for having me 比 Hello 更专业
  - 回答优势时给具体例子，比空泛的 I'm good 更可信
- **常见错误**：
  - ❌ Hello, I want a job. → ✅ Thanks for having me. I'd like to apply for...
  - ❌ I have interest in this job → ✅ I'm interested in this position.
  - ❌ I can work any time 太空泛 → 说清时间：I'm available on weekends and weekday evenings.
- **下一步建议**：下次可以练习用英语写一段求职邮件（cover letter）：简单说明来意、优势与可到岗时间。

### 食堂点餐与沟通（`campus_canteen`）

- **情境**：在食堂用英语点餐、询问口味与结账
- **学习目标**：学会在食堂用英语点餐、说明份量、询问口味并结账。
- **核心关键词**：食堂、打饭、点菜、食堂点餐、食堂点单
- **扩展关键词**：吃饭、餐、窗口、套餐、米饭、面、菜、打菜、饭卡
- **实用表达**：
  - `Hi, could I get the set meal with rice, please?` —— 你好，请给我一份带米饭的套餐。（点套餐用 set meal，句式仍是 Could I get...）
  - `Is this dish spicy?` —— 这道菜辣吗？（询问口味的常用句式）
  - `Could I have a smaller portion, please?` —— 可以给我小份的吗？（份量请求用 a smaller/larger portion）
  - `Do you take the campus card?` —— 可以用校园卡吗？（询问支付方式 Do you take...?）
  - `That looks great, thanks. How much is it?` —— 看起来不错，谢谢。多少钱？（询问价格的简洁说法）
- **情境互动**：对话对象「食堂工作人员」，5 轮，开场：Hi, welcome! What would you like today?
- **迁移练习**：在便利店买早餐 (convenience store) —— 假设你在便利店买早餐，请用本场景学过的句式（如 Could I get... / Do you take...）说一句话。
- **注意事项**：
  - 套餐说 set meal，加主食用 with rice / with noodles
  - 询问辣度说 Is this spicy?，怕辣可加 not too spicy
- **常见错误**：
  - ❌ I want rice. → ✅ Could I get the rice, please?
  - ❌ This is how much? → ✅ How much is it?
  - ❌ 说 I don't eat spicy 中式 → ✅ I'd prefer something not too spicy.
- **下一步建议**：下次可以练习在食堂询问菜品的食材：What's in this dish? Does it have any pork?

### 宿舍生活与舍友沟通（`dorm_life`）

- **情境**：用英语与舍友沟通作息、分工与生活小事
- **学习目标**：学会用英语和舍友沟通作息、值日分工与委婉提出请求。
- **核心关键词**：宿舍、舍友、室友、宿舍生活、同宿舍
- **扩展关键词**：晚睡、噪音、打扫、值日、空调、熄灯、打水、合租、作息
- **实用表达**：
  - `Would you mind keeping it down a bit? I have an early class.` —— 可以小声一点吗？我明早有课。（委婉请求用 Would you mind...?）
  - `Shall we take turns cleaning the room?` —— 我们轮流打扫房间好吗？（提出建议用 Shall we...?）
  - `Could we agree on a lights-out time?` —— 我们要不要统一一下熄灯时间？（商量作息用 agree on）
  - `No worries, it happens to everyone.` —— 没事，谁都会这样。（表示包容的高频口语）
  - `Thanks for covering me — I owe you one.` —— 谢谢你帮我顶上，我欠你一次。（道谢并显亲近的地道说法）
- **情境互动**：对话对象「舍友」，5 轮，开场：Hey, do you have a minute? I wanted to talk about a few things in our room.
- **迁移练习**：与同组同学协调小组作业分工 (group project) —— 假设你在和同组同学商量小组作业分工，请用本场景学过的句式（如 Shall we... / Would you mind...）说一句话。
- **注意事项**：
  - 对舍友提要求尽量用 Would you mind...? / Could we...?，避免命令语气
  - 对方答应了要说 Thanks for... / I owe you one，维持好关系
- **常见错误**：
  - ❌ You must be quiet! 太命令 → ✅ Would you mind keeping it down a bit?
  - ❌ I want you clean the room → ✅ Shall we take turns cleaning the room?
  - ❌ 直接抱怨显生硬，先说 I have an early class 给出理由更易被接受
- **下一步建议**：下次可以练习和舍友商量周末出行计划：Shall we go hiking this Saturday?

## 匹配规则

| 用户输入 | 系统行为 |
|---|---|
| 命中核心关键词（core，计 3 分） | 完全匹配，直接进入学习任务 |
| 仅命中扩展关键词（extra，计 1 分） | 部分匹配，先询问确认再复用模板 |
| 无任何命中 | 明确告知暂不支持，推荐最接近的 2–3 个场景 |
| 空输入 / 无关或无法理解的输入 | 给出明确提示，允许重试 |