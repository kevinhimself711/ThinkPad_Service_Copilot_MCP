# ThinkPad Service Copilot MCP · 项目开发 1 号指导文件

> 文档版本：v1.0  
> 生成日期：2026-06-08  
> 项目定位：面向 Agent 开发 / LLM 应用开发 / RAG 工程实习申请的垂直 Agentic RAG MCP 项目  
> 母项目：`jerry-ai-dev/MODULAR-RAG-MCP-SERVER`  
> 母项目链接：https://github.com/jerry-ai-dev/MODULAR-RAG-MCP-SERVER  
> 派生项目建议名称：`ThinkPad_Service_Copilot_MCP`  
> 推荐项目标题：**ThinkPad Service Copilot: Agentic RAG MCP Server for Hardware Maintenance Manuals**

---

## 0. 本文档的用途

本文档是 `ThinkPad_Service_Copilot_MCP` 的一号开发指导文件。它不是普通 README，而是用于指导整个项目从立项、风险验证、开发、评估、展示、简历转化到面试叙事的总纲。

你后续开发时应把它当成以下几类文件的上位文档：

1. `README.md`：面向外部展示项目价值和使用方式。
2. `DEV_SPEC.md`：面向开发过程的模块规格、接口定义、任务拆解。
3. `EXPERIMENTS.md`：记录检索、分块、rerank、多模态、Graph RAG 的实验结果。
4. `EVAL_REPORT.md`：记录 Golden Test Set、指标、baseline 对比和结论。
5. `INTERVIEW_NOTES.md`：沉淀面试讲法、难点回答、追问准备。

本项目的核心目标不是“把 ThinkPad 手册塞进 RAG”，而是：

> 把 ThinkPad Hardware Maintenance Manual 中的型号、FRU、错误码、螺丝规格、拆卸图、警告和拆卸依赖关系，结构化成 Agent 可调用、可评估、可观测、可溯源的 MCP 工具系统。

---

## 1. 项目背景：为什么要做这个项目

### 1.1 求职背景

目标岗位：

- Agent 开发实习生
- LLM 应用开发实习生
- RAG 工程实习生
- AI 应用工程 / 大模型应用工程相关岗位

当前求职场景下，普通的“PDF 问答机器人”已经不够有说服力。面试官更容易追问：

- 你的数据为什么适合 RAG？
- 你的检索为什么不是简单 embedding search？
- 为什么需要 MCP？
- 为什么需要 Agent？
- 如何评估？
- 如何减少幻觉？
- PDF 表格、图片、页码、chunk 断裂怎么处理？
- 如果已有 ChatGPT / Context7 / 通用搜索，为什么还需要你这个系统？

因此，本项目必须从一开始就避免成为 toy project。它应当具备：

1. 真实业务场景。
2. 明确用户和痛点。
3. 非 trivial 的数据结构。
4. 可演示的 RAG 工程难点。
5. 可量化的评估闭环。
6. Agent / MCP 交付形态。
7. 能转化成简历 bullet 和面试答案的工程过程。

### 1.2 为什么选择 ThinkPad HMM 场景

ThinkPad Hardware Maintenance Manual，简称 HMM，是 Lenovo 为 ThinkPad 系列机器发布的硬件维修手册。它包含：

- 机型与机器类型。
- FRU（Field Replaceable Unit）编号和部件名称。
- 拆卸 / 更换流程。
- 前置拆卸依赖。
- 错误码表。
- 螺丝规格、数量、扭矩。
- 拆装图、线稿图、爆炸图。
- DANGER / CAUTION 等安全警告。
- 页级结构和章节编号。

这些内容有几个特点：

1. 事实密度高。
2. 专有名词多。
3. 错误代价高。
4. 跨型号 / 跨代内容相似但细节不同。
5. 图片和表格非常重要。
6. 通用 LLM 很容易编造 FRU、步骤、螺丝数量或混淆代际。

这使得它非常适合做一个垂直 RAG + MCP 项目。

### 1.3 目标用户画像

本项目面向的真实用户不是普通消费者，而是以下角色：

1. 笔记本维修店技师。
2. 企业 IT helpdesk / IT support。
3. 二手翻新商 / ITAD 资产处置公司。
4. 管理大量 ThinkPad 设备的内部运维人员。
5. 上层 Agent / AI assistant，需要调用维修知识工具来完成诊断和维修计划生成。

典型任务包括：

- “X1 Carbon Gen 9 怎么拆 built-in battery？”
- “T14 Gen 2 error code 0271 是什么意思？”
- “拆 system board 前必须先拆哪些 FRU？”
- “P1 Gen 4 风扇拆卸图在哪一页？”
- “T14 Gen 2 和 Gen 3 的 SSD removal 有什么差异？”
- “如果用户只说 X1 Carbon，要不要直接给拆机步骤？”

### 1.4 项目一句话定位

英文定位：

> ThinkPad Service Copilot is an Agentic RAG MCP Server that grounds AI agents in model-specific ThinkPad Hardware Maintenance Manuals, enabling accurate retrieval of FRU procedures, error codes, screw specifications, safety warnings, diagrams, and dependency chains with page-level citations.

中文定位：

> ThinkPad Service Copilot 是一个面向 ThinkPad 硬件维修手册的 Agentic RAG MCP 系统。它通过混合检索、多模态图文处理、型号/代际规则精排、FRU 依赖图和页级 citation，把维修手册知识变成 Agent 可调用的工具能力。

---

## 2. 母项目说明

### 2.1 母项目链接

母项目：

```text
https://github.com/jerry-ai-dev/MODULAR-RAG-MCP-SERVER
```

母项目名称：

```text
MODULAR-RAG-MCP-SERVER
```

母项目定位：

```text
一个可插拔、可观测的模块化 RAG MCP Server 工程框架。
```

### 2.2 母项目提供的核心能力

母项目已经提供以下基础能力：

1. Ingestion Pipeline  
   PDF → Markdown → Chunk → Transform → Embedding → Upsert。

2. Hybrid Search  
   Dense vector search + Sparse BM25 + RRF fusion + rerank。

3. Multimodal Image Captioning  
   使用 Vision LLM 将图片转换成文字描述，再进入文本 RAG 链路。

4. MCP Server  
   通过 MCP 协议暴露 tools，让 Claude / Copilot / 其他 MCP client 调用。

5. Dashboard  
   Streamlit 六页面：系统总览、数据浏览、ingestion 管理、摄取追踪、查询追踪、评估面板。

6. Evaluation  
   Ragas + Custom eval + Golden Test Set。

7. Observability  
   Ingestion 和 Query 链路可追踪。

8. 可插拔架构  
   LLM / embedding / reranker / splitter / vector store / evaluator 可替换。

### 2.3 为什么本项目适合基于母项目改造

ThinkPad HMM 场景能用满母项目的关键能力：

| 母项目能力 | ThinkPad 场景中的真实用途 |
|---|---|
| PDF 摄取 | HMM 原始语料就是 PDF |
| Image Captioning | 拆装图、线稿图、爆炸图需要自然语言检索和返回 |
| Hybrid Search | 错误码、FRU、扭矩适合 BM25；症状描述适合 Dense |
| Rerank | 型号、代际、版次必须规则精排 |
| Citation | 维修步骤必须页级溯源 |
| Dashboard | 展示 BM25/Dense/rerank 前后变化 |
| Evaluation | 手册就是 ground truth，适合做 Golden Set |
| MCP Server | 给上层 Agent 暴露维修知识工具 |

### 2.4 分支策略

推荐策略：

```text
优先使用 main 分支跑通完整功能，再新建 thinkpad-domain 分支做垂域改造。
```

分支规划：

```text
main                         # 来自母项目的完整代码
thinkpad-domain-mvp          # ThinkPad HMM 基座 RAG MVP
thinkpad-domain-eval         # 增加 golden test set 和实验记录
thinkpad-agent-graph         # 增加 Agent + FRU Graph RAG 深化
thinkpad-release             # 最终展示和简历版本
```

如果时间非常充足，可以从 `clean-start` 分支重走 Spec-driven development。但对于找实习目标，推荐先 fork `main`，快速跑通，再做垂直化贡献。

---

## 3. 项目目标与非目标

### 3.1 最终目标

最终系统应支持：

1. 摄取 ThinkPad T 系 + X1 + E 系 + P 系，2018–2025 的 HMM PDF。
2. 对每本 HMM 建立手册级 metadata。
3. 对 FRU procedure、错误码表、螺丝规格表、拆装图做结构化处理。
4. 支持混合检索：Dense + BM25 + RRF。
5. 支持 ThinkPad domain rerank：型号、代际、机器类型、FRU、错误码、版次。
6. 支持页级 citation。
7. 支持返回相关拆装图。
8. 暴露 MCP tools 供 Agent 调用。
9. 建立 Golden Test Set 和 baseline 对比实验。
10. 实现一个轻量 Agent client，展示 multi-step repair planning。
11. 构建轻量 FRU dependency graph，支持多跳前置拆卸链查询。
12. 提供 Docker + HTTP MCP + CI 的基础生产化包装。

### 3.2 MVP 目标

MVP 不追求一次性覆盖 50 本 HMM，而是先覆盖 8–12 本代表性手册，验证核心技术风险。

MVP 必须完成：

1. 8–12 本 HMM PDF 摄取。
2. `manuals_manifest.yaml`。
3. FRU section 结构感知切分。
4. 错误码 / 螺丝规格表结构化抽取 spike。
5. 图纸抽取 + rasterize 兜底 spike。
6. 型号 / generation / machine type metadata。
7. Dense + BM25 hybrid retrieval。
8. ThinkPad domain rerank。
9. 至少 5 个 MCP tools。
10. 30 条 Golden Test Set。
11. Dashboard trace 展示 3 个代表 query。
12. README + DEMO script + 初版简历 bullet。

### 3.3 非目标

MVP 阶段不做：

1. 不做完整商业化维修平台。
2. 不做用户账号系统。
3. 不上传完整 Lenovo PDF 到 GitHub。
4. 不公开发布完整 extracted chunks / vector DB。
5. 不让系统执行真实维修操作。
6. 不承诺替代官方维修资质。
7. 不做复杂 K8s / 多租户权限系统。
8. 不追求所有 ThinkPad 机型全覆盖。

---

## 4. 数据范围与语料规划

### 4.1 最终语料范围

最终目标范围：

```text
ThinkPad T Series + X1 Series + E Series + P Series
Model years: 2018–2025
Document type: Hardware Maintenance Manual PDF
Estimated manuals: 40–60
Estimated pages: ~6000
Estimated chunks: 10k–30k, based on actual parsing density
```

### 4.2 MVP 语料范围

MVP 建议选择：

```text
T 系：
- T14 Gen 2
- T14 Gen 3
- T480 或 T490

X1：
- X1 Carbon Gen 9
- X1 Carbon Gen 10

E 系：
- E14 Gen 2
- E15 Gen 2

P 系：
- P1 Gen 4 或 P14s Gen 3
```

选择逻辑：

1. T14 Gen2 / Gen3：测试跨代近重复和型号消歧。
2. X1 Carbon Gen9 / Gen10：测试热门机型多代冲突。
3. E14 / E15 Gen2：测试错误码、螺丝规格、表格结构。
4. P1 / P14s：测试高性能机型、风扇/散热图纸。
5. T480/T490：测试较早机型和格式差异。

### 4.3 数据目录结构

建议目录：

```text
ThinkPad_Service_Copilot_MCP/
  data/
    raw_pdfs/
      t14_gen2_hmm.pdf
      t14_gen3_p14s_gen3_hmm.pdf
      x1_carbon_gen9_x1_yoga_gen6_hmm.pdf
    manifests/
      manuals_manifest.yaml
    extracted/
      markdown/
      tables/
      images/
      page_renders/
    processed/
      chunks.jsonl
      figures.jsonl
      tables.jsonl
      fru_graph.json
      golden_set.jsonl
  storage/
    chroma/
    bm25/
    image_store/
  docs/
    PROJECT_GUIDE.md
    DEV_SPEC_THINKPAD.md
    EXPERIMENTS.md
    EVAL_REPORT.md
    INTERVIEW_NOTES.md
```

### 4.4 版权与开源规则

GitHub 仓库中不要上传：

1. Lenovo 原始 HMM PDF。
2. 完整 extracted markdown。
3. 完整 chunks JSONL。
4. 完整 vector DB。
5. 完整拆装图片。

可以上传：

1. 下载脚本。
2. `manuals_manifest.example.yaml`。
3. 少量 redacted sample。
4. 抽取脚本。
5. metadata schema。
6. evaluation schema。
7. dashboard screenshots。
8. demo video 链接。
9. README 中的官方 Lenovo source URL。

---

## 5. 核心系统架构

### 5.1 总体架构

```text
Lenovo HMM PDFs
   ↓
Manual Manifest Builder
   ↓
PDF Loader
   ├── Text / Markdown Extraction
   ├── Table Extraction
   ├── Image Extraction
   └── Page Rasterization Fallback
   ↓
Domain Transform Layer
   ├── Header/Footer Cleaner
   ├── Manual Metadata Enricher
   ├── FRU Section Parser
   ├── Error Code Table Parser
   ├── Screw Spec Parser
   ├── Figure Captioner
   └── FRU Dependency Extractor
   ↓
Chunk Store / Table Store / Image Store / Graph Store
   ↓
Embedding + BM25 Index
   ↓
Hybrid Retriever
   ├── Dense Retrieval
   ├── Sparse BM25 Retrieval
   └── RRF Fusion
   ↓
ThinkPad Domain Reranker
   ↓
MCP Tools
   ├── resolve_model
   ├── search_hmm
   ├── get_fru_procedure
   ├── get_error_code
   ├── get_screw_spec
   ├── get_diagram
   ├── get_safety_warnings
   └── get_fru_dependency_chain
   ↓
Agent Client / Claude / Codex / Other MCP Clients
   ↓
Dashboard + Trace + Evaluation
```

### 5.2 模块职责

| 模块 | 责任 |
|---|---|
| Manifest | 管理每本手册的型号、年份、机器类型、URL、版次 |
| Loader | 从 PDF 抽文本、表格、图片、页图 |
| Splitter | 以 FRU section 和表格行为核心切分 |
| Metadata Enricher | 给 chunk 注入 model/gen/fru/page/source 等字段 |
| Image Captioner | 给拆装图生成 caption 并绑定 page/fru |
| Retriever | Dense + BM25 召回 |
| Reranker | 按型号、代际、FRU、错误码、权威源重排 |
| MCP Server | 暴露标准化 tools |
| Graph Layer | 处理 FRU 前置依赖和多跳关系 |
| Agent Client | 编排多工具调用，生成维修计划 |
| Dashboard | 可视化 query trace / ingestion trace / eval |
| Eval | Golden Set 回归测试和 baseline 对比 |

---

## 6. Metadata 与数据结构设计

### 6.1 Manual-level metadata

`manuals_manifest.yaml` 示例：

```yaml
- manual_id: thinkpad_t14_gen3_p14s_gen3_hmm
  title: ThinkPad T14 Gen 3 and P14s Gen 3 Hardware Maintenance Manual
  series: [T, P]
  models:
    - ThinkPad T14 Gen 3
    - ThinkPad P14s Gen 3
  generations:
    - Gen 3
  machine_types:
    - 21AH
    - 21AJ
    - 21CF
    - 21CG
  year: 2022
  edition: "First Edition"
  source_type: lenovo_official
  source_url: "https://..."
  local_pdf_path: "data/raw_pdfs/t14_gen3_p14s_gen3_hmm.pdf"
  document_type: hmm
  language: en
  checksum_sha256: "..."
```

### 6.2 Chunk metadata

```json
{
  "chunk_id": "t14_gen3_hmm_p073_fru_1020_0001",
  "manual_id": "thinkpad_t14_gen3_p14s_gen3_hmm",
  "source_url": "https://...",
  "source_type": "lenovo_official",
  "models": ["ThinkPad T14 Gen 3", "ThinkPad P14s Gen 3"],
  "series": ["T", "P"],
  "generation": "Gen 3",
  "machine_types": ["21AH", "21AJ"],
  "year": 2022,
  "edition": "First Edition",
  "page_start": 73,
  "page_end": 75,
  "section_type": "fru_procedure",
  "section_title": "Removing and replacing a FRU",
  "fru_id": "1020",
  "fru_name": "Built-in battery",
  "prerequisites": ["1010 Base cover assembly"],
  "warning_level": "DANGER",
  "has_image": true,
  "related_image_ids": ["img_t14_gen3_p073_01"],
  "error_codes": [],
  "screw_specs": []
}
```

### 6.3 Table row record

```json
{
  "record_id": "e15_gen2_error_0271",
  "manual_id": "thinkpad_e15_gen2_hmm",
  "table_type": "error_code",
  "page": 42,
  "code": "0271",
  "symptom": "Check date and time settings",
  "action": "Run ThinkPad Setup and reset date/time",
  "related_fru": [],
  "models": ["ThinkPad E15 Gen 2"],
  "source_url": "https://..."
}
```

### 6.4 Figure record

```json
{
  "image_id": "img_x1c_gen9_p087_battery_01",
  "manual_id": "x1_carbon_gen9_x1_yoga_gen6_hmm",
  "page": 87,
  "models": ["ThinkPad X1 Carbon Gen 9", "ThinkPad X1 Yoga Gen 6"],
  "fru_id": "1020",
  "fru_name": "Built-in battery",
  "image_path": "data/extracted/images/img_x1c_gen9_p087_battery_01.png",
  "caption": "Diagram showing the built-in battery removal sequence and connector location for X1 Carbon Gen 9.",
  "surrounding_text": "...",
  "source_url": "https://..."
}
```

### 6.5 FRU dependency graph record

```json
{
  "model": "ThinkPad T14 Gen 2",
  "manual_id": "t14_gen2_hmm",
  "fru_id": "1150",
  "fru_name": "System board",
  "requires": [
    {"fru_id": "1010", "fru_name": "Base cover assembly"},
    {"fru_id": "1020", "fru_name": "Built-in battery"},
    {"fru_id": "1040", "fru_name": "M.2 solid-state drive"},
    {"fru_id": "1080", "fru_name": "Thermal fan assembly"}
  ],
  "page": 110
}
```

---

## 7. Ingestion 设计

### 7.1 Ingestion 流程

```text
1. 读取 manuals_manifest.yaml
2. 校验 PDF 是否存在、checksum 是否一致
3. 抽取标题页，校验 model / generation / machine type
4. PDF → markdown/text
5. 抽取表格：error codes / screw specs / FRU list
6. 抽取图片；如果失败则 rasterize page / region
7. 清理页眉页脚、版次水印、重复页码
8. 按 FRU section / table row / figure 切分
9. 生成 metadata
10. 对 figure 做 vision caption
11. 生成 embeddings
12. 构建 BM25 index
13. 写入 Chroma / image store / graph store
14. 记录 ingestion trace
```

### 7.2 风险 spike 必测项

MVP 第一周必须验证：

1. R1 表格解析  
   至少抽 2–3 张错误码表 / 螺丝规格表，检查行列是否对齐。

2. R2 图纸抽取  
   至少抽 10 张图，检查 PyMuPDF 原图抽取与 rasterize fallback 的质量。

3. R3 型号 metadata  
   从标题页 + 文件名抽取 models / generation / machine_types，人工抽检。

4. R4 FRU section 切分  
   检查 procedure 和 prerequisite 是否被切在同一逻辑单元或可拼回。

5. R5 安全边界  
   检查 DANGER / CAUTION 是否能进入 metadata 和最终回答。

### 7.3 分块策略

不要只用普通定长 chunk。采用多粒度：

1. FRU procedure chunk  
   以 FRU 编号段为边界，如 `1010 Base cover assembly`、`1020 Built-in battery`。

2. Table row chunk  
   错误码表、螺丝规格表、FRU BOM 表每行单独结构化。

3. Figure chunk  
   每张图保留 image_id、page、caption、surrounding_text、related_fru_id。

4. Parent-child retrieval  
   小单元用于检索，返回时带上父级 FRU section / page context。

### 7.4 图像处理策略

图片处理目标不是“让模型从图里读出所有规格”，而是：

```text
用户能用自然语言搜索拆装图，系统能返回正确图、caption、页码和相关 FRU。
```

处理策略：

1. 优先抽取 PDF 内嵌图。
2. 如果抽不出来或为空白，对页面或图区域 rasterize。
3. caption prompt 必须包含 surrounding text。
4. caption 只描述图的对象、部件、操作，不编造扭矩/数量。
5. 精确规格仍以文本和表格为准。

---

## 8. Retrieval 与 Rerank 设计

### 8.1 查询类型分类

| 查询类型 | 示例 | 主力检索方式 |
|---|---|---|
| 错误码 | `0271` | BM25 / table record |
| FRU 编号 | `1020 built-in battery` | BM25 + metadata |
| 螺丝规格 | `LCD hinge torque 0.294 Nm` | BM25 + table row |
| 症状描述 | `换完主板后不能充电` | Dense |
| 图纸查询 | `P1 Gen4 fan removal diagram` | caption dense + metadata |
| 型号消歧 | `X1 Carbon 拆电池` | metadata + domain rerank |
| 多跳流程 | `拆 system board 前要先拆什么` | graph traversal + retrieval |

### 8.2 Hybrid retrieval

基础流程：

```text
query
  ↓
query parser: model / gen / machine type / fru / error code / section type
  ↓
dense retrieval top_k=20
sparse BM25 top_k=20
  ↓
RRF fusion
  ↓
domain rerank
  ↓
context packing
  ↓
answer generation with citation
```

### 8.3 ThinkPad Domain Rerank 规则

建议初版规则：

```text
score = base_score

+ exact_machine_type_match * 5.0
+ exact_model_generation_match * 4.0
+ exact_model_family_match * 2.0
+ exact_fru_id_match * 4.0
+ exact_error_code_match * 4.0
+ exact_screw_spec_match * 3.0
+ section_type_match * 2.0
+ official_source_boost * 1.5
+ newer_edition_boost * 1.0
+ safety_warning_boost * 0.8
- wrong_generation_penalty * 5.0
- ambiguous_model_penalty * 2.0
```

关键原则：

1. 用户明确指定 Gen 9，就不能让 Gen 10 覆盖。
2. 用户只说 X1 Carbon，不应直接给唯一步骤，应先提示补充 generation / machine type。
3. FRU、错误码、扭矩这类精确字段优先 BM25 和 metadata。
4. 症状描述可以依赖 dense，但最终必须落回手册 citation。

### 8.4 Answer policy

回答必须满足：

1. 标明手册、型号、generation。
2. 标明页码或 page range。
3. 给出 citation。
4. 涉及电池、系统板、DANGER / CAUTION 时必须显示 warning。
5. 不确定型号时不能给唯一拆机步骤。
6. 不编造 FRU、螺丝数量、扭矩。
7. 如果检索不到，应说明未在当前语料中找到。

---

## 9. MCP Tools 设计

### 9.1 Tool 列表

MVP 至少实现：

```text
resolve_model
search_hmm
get_fru_procedure
get_error_code
get_screw_spec
get_diagram
get_safety_warnings
list_supported_models
```

深化阶段增加：

```text
get_fru_dependency_chain
compare_model_generations
diagnose_symptom
plan_repair_workflow
```

### 9.2 `resolve_model`

用途：从用户输入中解析 ThinkPad 型号、generation、machine type。

Input：

```json
{
  "query": "X1 Carbon Gen 9 电池怎么拆"
}
```

Output：

```json
{
  "status": "resolved",
  "model": "ThinkPad X1 Carbon Gen 9",
  "generation": "Gen 9",
  "machine_types": ["20XW", "20XX"],
  "confidence": 0.93,
  "needs_clarification": false
}
```

如果不明确：

```json
{
  "status": "ambiguous",
  "candidates": ["X1 Carbon Gen 7", "X1 Carbon Gen 8", "X1 Carbon Gen 9", "X1 Carbon Gen 10"],
  "needs_clarification": true,
  "clarifying_question": "请补充 X1 Carbon 的 generation 或 machine type，例如 Gen 9 / 20XW。"
}
```

### 9.3 `search_hmm`

用途：通用 HMM 检索。

Input：

```json
{
  "query": "T14 Gen 3 built-in battery removal",
  "model": "ThinkPad T14 Gen 3",
  "section_type": "fru_procedure",
  "top_k": 5
}
```

Output：

```json
{
  "results": [
    {
      "chunk_id": "...",
      "manual_id": "...",
      "title": "Built-in battery removal",
      "page_start": 73,
      "page_end": 75,
      "score": 0.87,
      "citation": "ThinkPad T14 Gen 3 HMM, pp.73-75",
      "snippet": "..."
    }
  ]
}
```

### 9.4 `get_fru_procedure`

用途：返回特定 FRU 的拆卸流程。

Input：

```json
{
  "model": "ThinkPad X1 Carbon Gen 9",
  "fru_name": "built-in battery",
  "include_prerequisites": true,
  "include_diagrams": true
}
```

Output：

```json
{
  "model": "ThinkPad X1 Carbon Gen 9",
  "fru_id": "1020",
  "fru_name": "Built-in battery",
  "prerequisites": ["1010 Base cover assembly"],
  "steps": ["Step 1...", "Step 2..."],
  "warnings": ["DANGER: ..."],
  "diagrams": ["img_x1c_gen9_p087_battery_01"],
  "citations": ["X1 Carbon Gen 9 HMM, p.87"]
}
```

### 9.5 `get_error_code`

用途：查询错误码含义和建议动作。

Input：

```json
{
  "model": "ThinkPad E15 Gen 2",
  "error_code": "0271"
}
```

Output：

```json
{
  "error_code": "0271",
  "meaning": "...",
  "recommended_action": "...",
  "related_fru": [],
  "citation": "ThinkPad E15 Gen 2 HMM, p.xx"
}
```

### 9.6 `get_fru_dependency_chain`

用途：Graph RAG / Agent 深化核心 tool。返回拆某个 FRU 前的完整前置链。

Input：

```json
{
  "model": "ThinkPad T14 Gen 2",
  "fru_name": "system board"
}
```

Output：

```json
{
  "target_fru": "System board",
  "ordered_chain": [
    "1010 Base cover assembly",
    "1020 Built-in battery",
    "1040 M.2 solid-state drive",
    "1080 Thermal fan assembly",
    "1150 System board"
  ],
  "graph_path": ["1010", "1020", "1040", "1080", "1150"],
  "citations": ["ThinkPad T14 Gen 2 HMM, pp.xx-yy"]
}
```

---

## 10. Agent 深化设计

### 10.1 Agent 的价值

MCP server 本体解决“查得准”。Agent 解决“多步任务怎么组织”。

真实维修不是一次查询，而是：

```text
症状 → 型号消歧 → 错误码/症状表 → 候选 FRU → 前置拆卸链 → 图纸 → 安全警告 → 有序维修计划
```

### 10.2 Agent MVP

实现一个轻量 Agent client，不必复杂多 Agent。

Agent 能力：

1. Tool Calling。
2. ReAct 循环。
3. 型号不明时 clarification。
4. 调用 MCP tools。
5. 输出维修计划。
6. 自检：型号是否匹配、前置链是否完整、citation 是否存在。

### 10.3 Agent workflow

```text
User query
  ↓
resolve_model
  ↓
if ambiguous → ask clarification
  ↓
classify intent: error_code / fru_procedure / symptom_diagnosis / diagram / comparison
  ↓
call relevant MCP tools
  ↓
if procedure → get_fru_dependency_chain
  ↓
if risky component → get_safety_warnings
  ↓
compose repair plan
  ↓
validate citations and model match
  ↓
final answer
```

### 10.4 Agent demo 脚本

Demo Query 1：

```text
我的 ThinkPad T14 Gen2 不开机，没有 LED，应该怎么排查？
```

预期展示：

1. Agent 识别型号。
2. 查症状 / error code / power checkout。
3. 给出候选 FRU。
4. 调用 get_fru_procedure。
5. 调用 get_fru_dependency_chain。
6. 输出有序计划。

Demo Query 2：

```text
X1 Carbon 电池怎么拆？
```

预期展示：

1. Agent 不直接回答。
2. 询问 generation 或 machine type。
3. 展示安全边界。

Demo Query 3：

```text
X1 Carbon Gen 9 电池鼓包，怎么更换？
```

预期展示：

1. resolve_model。
2. get_fru_procedure。
3. get_diagram。
4. get_safety_warnings。
5. 最终答案带 DANGER warning、图、页码。

---

## 11. Graph RAG 深化设计

### 11.1 为什么 Graph RAG 在本项目中成立

Graph RAG 不是为了追热点。ThinkPad HMM 天然存在关系图：

```text
Model → Manual
Manual → FRU
FRU → prerequisite FRU
FRU → Diagram
FRU → Screw Spec
Error Code → Action
Action → FRU
Model → Shared FRU / Shared Procedure
```

普通向量检索很难稳定回答多跳问题，例如：

```text
拆到 T14 Gen2 system board 的完整拆卸顺序是什么？
```

这需要遍历依赖链，而不是只找一个相似 chunk。

### 11.2 Graph MVP

不需要一开始上 Neo4j。MVP 用 JSON / networkx 即可。

Graph nodes：

```text
Model
Manual
FRU
ErrorCode
Figure
TableRow
Procedure
```

Graph edges：

```text
COVERS_MODEL
HAS_FRU
REQUIRES
HAS_DIAGRAM
HAS_SCREW_SPEC
ERROR_POINTS_TO_ACTION
ACTION_RELATED_TO_FRU
SHARES_FRU_WITH
```

### 11.3 Graph RAG 查询类型

1. 前置链：

```text
拆 system board 前要先拆哪些 FRU？
```

2. 邻域查询：

```text
我已经拆到 keyboard bezel，顺手还能更换哪些部件？
```

3. 跨型号关系：

```text
哪些型号和 X1 Carbon Gen9 用同一块 battery FRU？
```

4. 图文结合：

```text
列出拆 fan assembly 所需前置步骤，并返回相关图。
```

### 11.4 Graph 与 RAG 的关系

Graph 不替代 RAG。

```text
Graph 负责关系和多跳路径。
Vector/BM25 负责文本证据和 citation。
最终答案必须回到 HMM chunk / page citation。
```

---

## 12. 后端工程与部署深化

MVP 后端工程只做必要切片：

1. Dockerfile。
2. docker-compose。
3. HTTP / Streamable HTTP MCP transport。
4. GitHub Actions。
5. basic logging。
6. health check。
7. `.env.example`。

### 12.1 Docker compose 目标

```text
services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./storage:/app/storage

  dashboard:
    build: .
    command: streamlit run dashboard/app.py
    ports:
      - "8501:8501"

  chroma:
    image: chromadb/chroma
    ports:
      - "8001:8000"
```

### 12.2 CI 目标

GitHub Actions 至少跑：

```text
pytest tests/unit
pytest tests/integration
ruff check
mypy optional
build docker image
```

### 12.3 Logging 指标

每次 query 记录：

```json
{
  "query_id": "...",
  "query": "...",
  "resolved_model": "ThinkPad X1 Carbon Gen 9",
  "dense_hits": 20,
  "sparse_hits": 20,
  "reranked_top1_manual": "...",
  "latency_ms": 1840,
  "has_citation": true,
  "has_warning": true,
  "tool_name": "get_fru_procedure"
}
```

---

## 13. Evaluation 设计

### 13.1 Golden Test Set 分类

至少 30 条 MVP，最终 100 条。

分类：

1. 精确查询  
   FRU、错误码、螺丝规格、扭矩。

2. 流程查询  
   拆某个 FRU 的步骤和前置链。

3. 多模态查询  
   找某个部件拆卸图。

4. 型号陷阱  
   X1 Carbon Gen9 vs Gen10，T14 Gen2 vs Gen3。

5. 安全警告  
   battery / system board / DANGER / CAUTION。

6. 负例 / 拒答  
   未指定 generation 时是否要求 clarification。

### 13.2 Golden Set 示例

```jsonl
{"id":"G001","query":"E15 Gen 2 error code 0271 是什么意思？","expected_manual":"thinkpad_e15_gen2_hmm","expected_type":"error_code","expected_code":"0271"}
{"id":"G002","query":"X1 Carbon Gen 9 怎么拆 built-in battery？","expected_model":"ThinkPad X1 Carbon Gen 9","expected_fru":"Built-in battery","must_include_warning":true,"must_include_citation":true}
{"id":"G003","query":"X1 Carbon 怎么拆电池？","expected_behavior":"ask_clarification","reason":"generation ambiguous"}
{"id":"G004","query":"T14 Gen 2 拆 system board 前要先拆什么？","expected_type":"dependency_chain","must_include_ordered_chain":true}
{"id":"G005","query":"P1 Gen 4 fan assembly 的拆卸图在哪？","expected_type":"diagram","must_return_image":true}
```

### 13.3 Baseline 对比

必须做分层实验：

```text
A. Dense only
B. BM25 only
C. Hybrid without rerank
D. Hybrid + generic rerank
E. Hybrid + ThinkPad domain rerank
F. Hybrid + domain rerank + graph dependency
```

### 13.4 指标

Retrieval 指标：

```text
Hit@1
Hit@3
Hit@5
MRR
Context Precision
Context Recall
Model/generation accuracy
Citation accuracy
Diagram retrieval accuracy
```

Answer 指标：

```text
Faithfulness
Answer Relevancy
Procedure completeness
Safety warning inclusion rate
Hallucinated FRU rate
Clarification accuracy
```

Agent 指标：

```text
Task success rate
Tool call accuracy
Tool argument accuracy
Step order correctness
Trajectory faithfulness
```

### 13.5 实验报告模板

每个实验记录：

```text
Experiment ID:
Hypothesis:
Dataset:
Baseline:
Variant:
Metrics:
Result:
Failure cases:
Decision:
Next action:
```

---

## 14. Dashboard Demo 设计

Dashboard 必须能展示以下 5 个场景：

### Demo 1：BM25 的价值

Query：

```text
0271
```

展示：

1. Sparse 命中错误码表。
2. Dense 可能不稳定。
3. Hybrid 后 top result 正确。

### Demo 2：Dense 的价值

Query：

```text
换完主板后机器无法充电
```

展示：

1. Dense 命中 power checkout / system board / battery 相关内容。
2. BM25 不一定命中。

### Demo 3：Domain rerank 的价值

Query：

```text
X1 Carbon Gen 9 built-in battery removal
```

展示：

1. rerank 前可能混入 Gen8 / Gen10。
2. domain rerank 后 Gen9 手册排第一。

### Demo 4：多模态的价值

Query：

```text
P1 Gen4 fan assembly removal diagram
```

展示：

1. 命中 figure caption。
2. 返回原图 / 页图。
3. 带 page citation。

### Demo 5：Graph RAG 的价值

Query：

```text
拆 T14 Gen2 system board 的完整前置拆卸顺序
```

展示：

1. Graph traversal 返回 ordered chain。
2. RAG chunk 提供 citation。
3. Agent 组织成维修计划。

---

## 15. 风险清单与缓解策略

### R1：表格解析失败

风险：错误码表、螺丝规格表行列错位。  
影响：答案会引用到错误的 code / action / torque。  
缓解：`pdfplumber` / PyMuPDF 表格抽取；失败时人工规则 parser；表格行单独存储。  
验收：至少 3 张表格抽取准确率 > 90%。

### R2：图纸抽取失败

风险：矢量线稿抽不出或空白。  
影响：多模态 demo 失败。  
缓解：页面 rasterize fallback；图区域裁剪；surrounding text caption。  
验收：10 张典型拆装图至少 8 张可正确返回。

### R3：型号 metadata 错误

风险：一本手册覆盖多个型号，标题页格式不统一。  
影响：rerank 错代，回答危险。  
缓解：标题页 + 文件名 + manifest 人工抽检。  
验收：MVP 手册 metadata 100% 人工确认。

### R4：拆卸前置链被切断

风险：普通 chunk 切断 prerequisite 和 procedure。  
影响：步骤不完整。  
缓解：FRU section parser + dependency graph。  
验收：10 个 FRU procedure 的前置链可完整返回。

### R5：高风险步骤无安全边界

风险：型号不明也给拆机步骤；电池/系统板警告缺失。  
影响：安全和专业性问题。  
缓解：ambiguous model clarification；DANGER / CAUTION metadata；safety_check。  
验收：负例测试中 clarification accuracy > 90%，battery/system board 问题 warning inclusion rate > 95%。

### R6：项目过大导致延期

风险：一开始铺 50 本，陷入数据搬运。  
影响：无法形成可展示 MVP。  
缓解：8–12 本 MVP；先做 spike；全量作为后续扩展。  
验收：第 2 周末必须有端到端 demo。

---

## 16. 工期规划

### 16.1 推荐节奏：业余 8–10 周

适合每天 2–3 小时。

| 阶段 | 时间 | 目标 | 主要产出 |
|---|---:|---|---|
| M0 | 0.5 周 | 环境与母项目跑通 | fork、setup、baseline demo |
| M1 | 1 周 | 风险 spike | R1–R4 验证报告 |
| M2 | 1 周 | 语料与 manifest | 8–12 本 HMM、manifest、metadata schema |
| M3 | 1.5 周 | Ingestion 垂直化 | FRU parser、table parser、image fallback |
| M4 | 1 周 | Retrieval + rerank | hybrid retrieval、domain rerank |
| M5 | 1 周 | MCP tools | 8 个 ThinkPad tools |
| M6 | 1 周 | Eval + dashboard | 30–50 条 golden set、trace demo |
| M7 | 0.5–1 周 | README + demo polish | 项目展示、录屏、简历 bullet |
| M8 | 1.5–2 周 | Agent + Graph RAG 深化 | FRU graph、Agent repair planner |
| M9 | 0.5–1 周 | 部署工程切片 | Docker、HTTP MCP、CI |

总计：8–10 周可形成强面试版本。

### 16.2 全职冲刺：3–4 周

| 周 | 目标 |
|---|---|
| Week 1 | 跑通母项目 + 风险 spike + manifest + 8 本 HMM |
| Week 2 | ingestion 垂直化 + hybrid retrieval + domain rerank + MCP tools |
| Week 3 | golden set + dashboard + README + demo + eval report |
| Week 4 | Agent + FRU graph + Docker/CI + 简历/面试材料 |

### 16.3 最小可面试版本

如果时间非常紧，2 周内必须做到：

1. 5 本 HMM。
2. metadata schema。
3. hybrid retrieval。
4. domain rerank。
5. 3 个 MCP tools。
6. 20 条 golden set。
7. 3 个 dashboard demo。
8. README 中诚实写明 roadmap。

---

## 17. 任务拆解与验收标准

### Epic A：母项目启动

任务：

- Fork repo。
- 跑通 setup。
- 跑通原始 ingestion。
- 跑通原始 MCP tool。
- 截图 dashboard。

验收：

- 能本地启动 MCP server。
- 能通过默认 tool 查询测试文档。
- 能打开 dashboard。

### Epic B：语料与 manifest

任务：

- 下载 MVP 手册。
- 建立 `manuals_manifest.yaml`。
- 写 manifest validator。
- 生成 checksum。

验收：

- 每本手册都有 model / generation / machine type / year / source_url。
- validator 通过。

### Epic C：HMM ingestion

任务：

- 实现 HMM loader wrapper。
- 实现表格抽取。
- 实现图片抽取与 rasterize fallback。
- 实现 FRU section parser。
- 实现 metadata enricher。

验收：

- 8 本手册完成 ingestion。
- 至少 30 个 FRU section 被正确识别。
- 至少 20 个 figure record。
- 至少 2 类 table record。

### Epic D：Retrieval / Rerank

任务：

- query parser。
- metadata filter。
- domain rerank。
- citation formatter。

验收：

- `0271` 类 query 正确命中。
- `X1 Carbon Gen 9 battery` 不混代。
- ambiguous query 能触发 clarification。

### Epic E：MCP tools

任务：

- 实现 tool schemas。
- 实现 `resolve_model`。
- 实现 `get_fru_procedure`。
- 实现 `get_error_code`。
- 实现 `get_diagram`。
- 实现 `get_safety_warnings`。

验收：

- 每个 tool 有 unit test。
- 每个 tool 有示例输入输出。
- MCP client 可调用。

### Epic F：Evaluation

任务：

- 建立 30–50 条 golden set。
- 实现 baseline runner。
- 实现 metrics report。
- 记录 failure cases。

验收：

- 输出 baseline 对比表。
- 至少完成 Dense only / BM25 only / Hybrid / Hybrid + domain rerank 对比。

### Epic G：Agent + Graph

任务：

- 实现 FRU graph extractor。
- 实现 graph store。
- 实现 `get_fru_dependency_chain`。
- 实现 Agent client。

验收：

- 能回答完整拆卸链问题。
- Agent 能处理至少 3 个多步任务。

### Epic H：发布与面试材料

任务：

- README。
- DEMO.md。
- EVAL_REPORT.md。
- EXPERIMENTS.md。
- INTERVIEW_NOTES.md。
- resume bullets。

验收：

- GitHub 首页 30 秒内能看懂项目价值。
- 3 分钟 demo 可流畅展示。
- 简历 bullet 可直接使用。

---

## 18. README 结构建议

最终 README 应包括：

```text
1. Project Overview
2. Why ThinkPad HMM?
3. Key Features
4. Architecture
5. MCP Tools
6. Demo Scenarios
7. Dataset Scope
8. Evaluation Results
9. Development Roadmap
10. Installation
11. Usage
12. Compliance / Data Notice
13. Interview-oriented Highlights
```

首页最重要的是 4 件事：

1. 这不是 PDF chatbot。
2. 这是 Agentic RAG MCP Server。
3. 它解决型号消歧、FRU、图纸、前置链、安全警告。
4. 它有 eval 和 dashboard，不是凭感觉。

---

## 19. 简历转化

### 19.1 项目名称

```text
ThinkPad Service Copilot MCP | Agentic RAG System for Hardware Maintenance Manuals
```

### 19.2 简历 bullet 初版

```text
- Built a domain-specific Agentic RAG MCP Server for ThinkPad Hardware Maintenance Manuals, enabling AI agents to retrieve model-specific FRU procedures, error codes, screw specifications, safety warnings, and repair diagrams with page-level citations.

- Extended a modular RAG MCP framework with ThinkPad-specific corpus manifest, multi-value model metadata, FRU-aware chunking, table extraction, image captioning, and model/generation disambiguation across T, X1, E, and P series HMM PDFs.

- Implemented hybrid retrieval with BM25 + dense embeddings + RRF fusion + domain reranking rules to improve exact-match recall for FRU IDs, error codes, torque values, and machine types while reducing cross-generation retrieval errors.

- Built MCP tools including resolve_model, get_fru_procedure, get_error_code, get_diagram, get_safety_warnings, and get_fru_dependency_chain, allowing an Agent client to generate ordered repair plans grounded in HMM citations.

- Constructed a golden test set covering exact lookup, model ambiguity, multimodal diagram retrieval, FRU dependency chains, and safety-warning grounding; compared Dense-only, BM25-only, Hybrid, and Hybrid + domain rerank baselines through a dashboard-based evaluation workflow.
```

### 19.3 中文面试一句话

```text
我做的是一个 ThinkPad 维修手册场景下的 Agentic RAG MCP Server。它不是普通 PDF 问答，而是把 HMM 里的型号、FRU、错误码、螺丝规格、拆装图、安全警告和拆卸依赖关系结构化，暴露成 MCP tools 给 Agent 调用。系统用 BM25 + Dense 混合检索解决精确编号和语义症状问题，用型号/代际规则 rerank 防止混代，用 FRU dependency graph 处理多跳拆卸链，并通过 golden set 和 dashboard 做可评估迭代。
```

---

## 20. 面试追问准备

### Q1：为什么不用普通 RAG？

答：

普通定长 chunk + embedding search 会在三个地方失败：

1. 错误码、FRU、扭矩是精确 token，Dense 容易漏。
2. 不同 generation 内容相似，容易混代。
3. 拆卸流程有前置依赖，普通 chunk 可能切断。

所以我做了混合检索、metadata filter、domain rerank 和 FRU dependency graph。

### Q2：为什么需要 MCP？

答：

因为这个系统不是单独给人聊天，而是作为上层 Agent 的工具层。Agent 负责规划和对话，MCP server 负责提供 grounded 的维修知识，比如解析型号、查 FRU 流程、查错误码、取图、查安全警告。

### Q3：为什么 Graph RAG 不是硬凑？

答：

HMM 里天然存在 FRU 前置依赖图，比如拆 system board 前必须先拆 base cover、battery、SSD、fan assembly。这个问题不是相似文本检索能稳定解决的，而是多跳依赖遍历，所以 Graph RAG 在这里是真有用。

### Q4：怎么评估？

答：

我建立了 Golden Test Set，覆盖错误码、FRU、扭矩、型号陷阱、图纸、前置链和拒答场景。对比 Dense only、BM25 only、Hybrid、Hybrid + domain rerank、Hybrid + graph。指标包括 Hit@K、MRR、Context Precision、model accuracy、citation accuracy、warning inclusion rate 和 hallucinated FRU rate。

### Q5：图片怎么处理？

答：

我使用 image-to-text，而不是直接 CLIP。因为拆装线稿里的语义要结合前后文本才能准确理解。图片 caption 负责让用户能用自然语言搜到正确图纸；精确螺丝数量和扭矩仍以文本和表格为准。

### Q6：如何处理版权？

答：

仓库不上传原始 PDF、完整 extracted chunks、完整图片和向量库。只上传代码、manifest template、少量 redacted sample、eval schema 和官方 source URL。用户本地自行下载手册并构建索引。

---

## 21. 开发纪律

1. 先 spike，后全量。
2. 每个模块必须有验收标准。
3. 每次改检索策略必须跑 golden set。
4. 不凭感觉说效果提升，必须记录实验。
5. 不上传版权数据。
6. 不在 README 夸大系统能替代官方维修。
7. 遇到 ambiguous model，优先 clarification。
8. 每周至少更新一次 `EXPERIMENTS.md`。
9. 每个失败样例都要记录原因和修复策略。
10. 项目叙事始终围绕“Agent 可调用的垂直维修知识工具系统”。

---

## 22. 第一周执行清单

### Day 1：母项目跑通

- Fork repo。
- 安装依赖。
- 跑通 setup。
- 跑通 dashboard。
- 跑通默认 MCP tool。

### Day 2：下载 MVP 手册

- 下载 5–8 本 HMM。
- 建立 `manuals_manifest.yaml`。
- 填写 source_url、model、gen、machine type。

### Day 3：表格 spike

- 找错误码表。
- 找螺丝规格表。
- 用 MarkItDown 原始结果检查。
- 用 pdfplumber / PyMuPDF 尝试结构化抽取。
- 记录失败样例。

### Day 4：图纸 spike

- 抽 10 张图。
- 对比内嵌图抽取和 rasterize。
- 做 caption prompt。
- 记录图像质量。

### Day 5：FRU section spike

- 识别 FRU 编号。
- 切分 10 个 procedure。
- 提取 prerequisites。
- 初步生成 dependency JSON。

### Day 6：检索 quick demo

- 建立小规模 index。
- 测试 5 个 query。
- 观察 Dense / BM25 差异。

### Day 7：Spike report

输出：

```text
SPIKE_REPORT.md
- 数据源列表
- 表格抽取结果
- 图片抽取结果
- metadata 抽取结果
- FRU 切分结果
- 当前最大风险
- 是否进入 M2
```

---

## 23. 最终交付物清单

必须交付：

```text
README.md
PROJECT_GUIDE.md
DEV_SPEC_THINKPAD.md
EXPERIMENTS.md
EVAL_REPORT.md
INTERVIEW_NOTES.md
manuals_manifest.example.yaml
src/thinkpad_domain/
tests/thinkpad_domain/
dashboard screenshots
demo video or GIF
```

推荐交付：

```text
SPIKE_REPORT.md
DEMO_SCRIPT.md
RESUME_BULLETS.md
docs/architecture.png
docs/retrieval_trace_examples.md
docs/failure_cases.md
```

不交付：

```text
raw PDFs
full extracted markdown
full chunks
full vector DB
full image store
```

---

## 24. 最终验收标准

项目达到强面试版本，需要满足：

1. GitHub README 能解释清楚业务场景和技术亮点。
2. MCP server 可本地运行。
3. 至少 8 本 HMM 完成 ingestion。
4. 至少 30 条 golden set。
5. Dense/BM25/Hybrid/Domain Rerank 有对比结果。
6. 至少 5 个 MCP tools 可调用。
7. 至少 3 个 dashboard trace demo。
8. 至少 1 个多模态图纸 demo。
9. 至少 1 个型号消歧 / 拒答 demo。
10. 至少 1 个 FRU dependency chain demo。
11. Agent client 能完成 2–3 个多步维修计划。
12. Docker + CI 基础工程化完成。
13. 简历 bullet 和面试讲稿准备好。

---

## 25. 项目主线总结

这个项目的主线必须始终保持清晰：

```text
不是：PDF chatbot
而是：Agentic RAG MCP Server

不是：只做 embedding search
而是：Dense + BM25 + RRF + domain rerank + graph dependency

不是：只回答文本
而是：文本 + 表格 + 图纸 + 页级 citation + 安全警告

不是：只给人聊天
而是：给上层 Agent 调用的维修知识工具系统

不是：凭感觉调参
而是：Golden Set + baseline + dashboard trace + eval report
```

最终你要让面试官相信：

> 你不是只会套 RAG 框架，而是知道一个真实垂域 RAG 系统会在哪里失败，并且能通过数据治理、检索策略、metadata、rerank、MCP tools、Graph RAG、Agent workflow 和 evaluation 把它做成可落地的 LLM 应用。

---

## 26. 下一步

立即开始：

1. Fork 母项目。
2. 新建 `thinkpad-domain-mvp` 分支。
3. 创建 `docs/PROJECT_GUIDE.md`，放入本文档。
4. 创建 `data/manifests/manuals_manifest.yaml`。
5. 下载 5–8 本 MVP HMM。
6. 开始第一周风险 spike。

第一阶段完成前，不要急着全量铺 50 本。

