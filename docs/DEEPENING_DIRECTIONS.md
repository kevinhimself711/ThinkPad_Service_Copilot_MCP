# ThinkPad Service Copilot MCP · 三个深化方向

> 对应母项目 README「方向 3:以本项目为起点扩展」的三条路。核心结论:三个方向在 ThinkPad 场景里**都有具体、不牵强的形态**(尤其 Graph RAG)。但**别三个都做**——按目标岗位 + 时间挑一个做透,深度 > 广度。

---

## 0. 一句话回答 + 一条主线

- **能深化,且每个方向都不是硬贴 buzzword**:诊断维修是真实的多步 Agent 流程;店级部署是真实的工程需求;FRU 拆卸依赖**天然就是一张图**,Graph RAG 在这里真有用。
- **一条贯穿主线**:R4 的 **FRU 依赖图**(拆 A 前要先拆 B/C)是 Direction 1 和 3 **共享的资产**——做扎实一次,两个方向都吃红利。
- **取舍**:先做透基座 RAG(施工规划 M0–M7),再选**一个**深方向(M8),每个约 2–4 周(业余)。

---

## Direction 1 — Agent + RAG:诊断维修 Agent

**真问题**:技师的真实任务**不是一次查询**,而是"症状 → 定位 → 拆解"的多步流程。单次 RAG 检索给不了一个**完整、有序、可执行的维修计划**。

**具体形态**:一个 ReAct / Tool-Calling Agent,把 RAG MCP 当成它的一个知识能力:
1. 输入症状,如"ThinkPad T14 Gen2 不开机、无 LED"。
2. **消歧型号/代**:不确定就反问(human-in-the-loop),解决"哪一代"的问题。
3. **走诊断逻辑**:查错误码/症状表(错误码表本就是"按序"的 FRU/action 决策),定位候选 FRU。
4. **取流程**:对候选 FRU 调 RAG 取拆卸步骤 + **前置链** + 图。
5. **组装计划**:输出完整有序的维修计划(这一步是 Agent 相对单次检索的增量价值)。

**用到的 Agent 能力**:Tool Calling(调 RAG MCP 工具)、ReAct(observe-think-act 循环)、Planning(组装有序计划)、Clarification/HITL(型号歧义时反问)。

**在 RAG 之上新增的工具**:
- `get_fru_prerequisites(model, fru_id)` → 返回有序前置拆卸链(来自 R4 依赖图)
- `lookup_error_code(model, code)` → 返回错误码→FRU/action 映射
- (可选)`diagnose(model, symptom)` → 更高层诊断工具

**架构契合 README**:RAG MCP 是 Agent 的一个**知识工具**,Agent 负责推理/规划/对话——正是"把本项目作为 Agent 的一个模块和能力"。

**可评估**:任务成功率(计划是否正确、完整、有序)、工具调用成功率/参数正确率、轨迹评估——正好是面经里 Agent 评估的五个维度。

**命中面经**:多 Agent 协同、Agent 评估、Tool Calling、ReAct、Handoff vs Tool Call。

**适合**:大模型应用 / Agent 方向,RAG 工程师想加 Agent 厚度。

---

## Direction 2 — 后端工程:从本地原型到"店级"可部署服务

**真问题**:基座是单用户 **stdio**;一个维修店 / 企业 IT 维修台有**多个技师**要共享一个知识服务,而且(企业资产场景)序列号/资产信息敏感,倾向 **on-prem** 部署——这给了"为什么自部署"一个真实理由。

**具体清单(也正好是面经 3.5.5 生产化的全套答案)**:
1. **stdio → Streamable HTTP/SSE**:已验证 Codex/Claude Code 支持远端 HTTP MCP,多技师连一个服务。
2. **容器化**:Dockerfile + docker-compose(MCP server + Chroma + BM25 索引 + 图存储 + Dashboard)。
3. **CI/CD**:GitHub Actions 跑 pytest(54 单元/13 集成/4 E2E)+ 构建并推镜像。
4. **摄取流水线工程化**:可重复的批量摄取 job——Lenovo 发新版 HMM 时增量拉取 + SHA256 去重(基座已有)+ 重建索引。这是真实的数据工程。
5. **监控与日志**:在现有 Trace 之上加指标(P95 延迟、检索 hit rate、错误率、每查询 LLM 成本)、结构化日志、health-check 端点。
6. **容错加固**:LLM 调用重试/指数退避(基座是"单次尝试")、限流。
7. **(可选)K8s**:HTTP 服务的 manifest,支撑"多店扩展"的故事。

**可观测/评估**:复用 Dashboard + 上面的指标。

**命中面经**:3.5.5 生产化(容错/安全合规/部署运维)、3.5.x 异步/并发/吞吐。

**适合**:全栈 / 后端定位。**实习生建议只做 table-stakes 切片**(Docker + CI + HTTP transport),不必上 K8s——既补工程能力又能答生产化题,性价比高。

---

## Direction 3 — RAG 做深:Graph RAG(标杆)+ Agentic RAG + 检索优化

### 3a · Graph RAG —— 本场景的标杆(因为图是真实存在的)

**为什么是天作之合**:这个领域天然有图,不用硬造——
- **FRU 拆卸依赖图**:1150 系统板 ← 需先拆 1010 电池 / 1040 SSD / 1060 内置电池…
- **症状 → 错误码 → FRU → 流程** 链。
- **跨型号关系**:哪些型号共享同一块 FRU / 同一套流程。

**向量检索答不好、Graph RAG 能答的真实查询**:
- "拆到 T14 Gen2 系统板的**完整拆卸顺序**?"(多跳依赖遍历)
- "哪些型号和 **X1 Carbon Gen9 用同一块电池 FRU**?"(跨型号关系)
- "我已经在拆键盘了,**顺手还能修什么**不用额外拆解?"(图邻域查询)

**做法**:摄取时抽实体(FRU / 型号 / 错误码)+ 关系,建知识图谱(HMM 结构规整,抽取可行,不像散文那么难);检索时做图遍历,与向量/BM25 互补。这是 **R4 依赖图的自然延伸**。

**为什么值钱**:Graph RAG 在这里**不是 buzzword,是真解决向量 RAG 解决不了的关系/多跳查询**——这正是面试官想听的"你懂 Graph RAG 用在哪"。

### 3b · Agentic RAG(和 Direction 1 配对)

检索后让 Agent **自检并纠正**:结果是否匹配型号/代?前置链是否完整?是否最新版次?不满足就**纠正性重检(Corrective RAG)**或换策略。正好解**版本混代**问题:混代结果 → 纠正过滤到对的代。这层和 Direction 1 的 Agent 自然合体。

### 3c · 检索优化实验(可量化,直接喂 EXPERIMENTS.md)

一批**可测**的实验(对上你看重的"可评估"):
- 精排策略对比(规则 vs Cross-Encoder vs 混合)在**版本陷阱测试集**上的 precision。
- FRU **同义词扩展**("palm rest" / "keyboard bezel assembly" / "upper case" 指同一部件)。
- **结构感知 vs 定长切分**在"前置完整性"上的对比。
- **多模态**:加 image caption 对"图类问题"召回的提升(实测数字)。

**命中面经**:RAG 新方向(Agentic/Graph RAG)、检索优化、为什么精排这么做、怎么评估。

**适合**:RAG 工程师 / 想秀 RAG 深度。

---

## 4. 给你的建议(实习 · 无垂域背景 · 偏 RAG/应用)

- **顺序**:先做透基座 RAG(施工规划 M0–M7),再选**一个**深方向(M8)。别贪三个都做——**深度 > 广度**,三个浅尝不如一个做透。
- **推荐组合**:**Direction 1(诊断 Agent)为主 + Direction 3a(FRU Graph RAG)一小块**。
  - 理由:这俩组合起来一次性秀 **Agent + Graph RAG + RAG**,全是面试热点、最差异化;而且**天然能组合**(Agent 可以调用那张图来组装拆卸计划)。
  - **Direction 2 做 table-stakes 切片**(Docker + CI + HTTP transport)即可,顺带答生产化题。
- **共享红利**:把 **R4 的 FRU 依赖图**做扎实——它同时喂 Direction 1(Agent 组装有序计划)和 Direction 3a(Graph RAG 遍历)。一份投入,两处收益。
- **如果你想往全栈/后端走**:把重心换成 Direction 2 做全(含 K8s + 监控),Direction 1 做轻量版。

---

## 5. 一句话收尾

三个方向都能深化,且在 ThinkPad 场景里都有**具体、不牵强**的形态(Graph RAG 尤其天作之合)。选一个做透,你的项目就从"一个 RAG demo"升级成"**Agent / Graph RAG 驱动的维修助手**"——面经里 Agent 与高级 RAG 的题,你全都有**真东西**可讲,而不是背概念。
