# ai-kigurumi-head-reference


[中文](#中文) | [English](#English)

---

# 中文

一个用于将动漫/游戏角色参考图转换为 **Kigurumi 头壳多视图参考图** 的 AI 图像生成工作流。

本项目的目标是提供一套可复用的 Prompt 工作流，帮助用户稳定生成可用于头壳定制沟通的参考图。

使用模型：gpt-image-2

## 前端页面

在线前端页面：

[https://zhiyuan338.github.io/ai-kigurumi-head-reference/](https://zhiyuan338.github.io/ai-kigurumi-head-reference/)
[https://enderxie23.github.io/ai-kigurumi-head/](https://enderxie23.github.io/ai-kigurumi-head/)

参考图：

![workflow reference](web/assets/workflow-reference.jpeg)

## 项目目标

输入：

- 角色 2D 官方图
- 游戏内 3D 截图
- 去遮挡角色头部图
- 优秀 Kigurumi 头壳案例图

输出：

- 去遮挡角色头部四视图
- Kigurumi 头壳四视图设计图
- 商品照风格四面或八面头壳参考图

## 核心思路

不要一步直接从角色图生成最终头壳图。

推荐流程：

1. **角色参考图 → 去遮挡角色头部四视图**
2. **角色头部四视图 → Kigurumi 头壳四视图设计图**
3. **Kigurumi 头壳设计图 → 商品照风格四面/八面图**

核心原则：

- 先稳定结构
- 再头壳化
- 最后商品照化
- 参考图必须明确分工
- 每次修正只解决一个主要问题

## 文件说明

```text
ai-kigurumi-head-reference/
├─ README.md
├─ SKILL.md
├─ LICENSE
├─ .gitignore
├─ web/
│  ├─ index.html
│  ├─ styles.css
│  ├─ app.js
│  └─ assets/
│     └─ workflow-reference.jpeg
└─ prompts/
   ├─ step1-head-reference.md
   ├─ step2-kigurumi-design.md
   ├─ step3-product-view.md
   └─ troubleshooting.md
```

## 快速开始

1. 准备角色参考图。
2. 按照 `prompts/step1-head-reference.md` 生成去遮挡角色头部四视图。
3. 按照 `prompts/step2-kigurumi-design.md` 转换为 Kigurumi 头壳四视图设计图。
4. 按照 `prompts/step3-product-view.md` 生成商品照风格四面或八面视图。
5. 如果结果不理想，参考 `prompts/troubleshooting.md` 修改 Prompt。
6. 也可以使用在线前端页面辅助执行流程：
   [https://zhiyuan338.github.io/ai-kigurumi-head-reference/](https://zhiyuan338.github.io/ai-kigurumi-head-reference/)
   [https://enderxie23.github.io/ai-kigurumi-head/](https://enderxie23.github.io/ai-kigurumi-head/)

## Web 前端

本仓库包含一个无需构建步骤的静态前端：

- `web/index.html`
- `web/styles.css`
- `web/app.js`
- `web/assets/workflow-reference.jpeg`

直接打开 `web/index.html` 即可本地使用。

API Base URL 和 API Key 只会保存在用户浏览器本地，不会写入仓库。执行生成时，Key 会发送给用户配置的图像或文本 API 端点。若 API 服务不允许浏览器跨域请求，请在页面中填写一个兼容 OpenAI API 的、允许 CORS 的代理 Base URL。

## 素材准备建议

建议将素材分为以下几类：

```text
目标角色_头壳参考/
├─ 01_角色3D结构参考/
├─ 02_角色2D气质表情参考/
├─ 03_kigurumi优秀案例/
├─ 04_实际上传组合/
├─ 05_生成结果/
└─ 06_失败记录/
```

## 注意事项

- 不建议上传未授权的角色原图、游戏截图、店家商品图或他人私有生成图到公开仓库。
- 本仓库主要保存工作流和 Prompt，不保存完整聊天记录。
- 如果使用他人的图片作为参考，请遵守对应素材的版权与使用规则。
- 本项目输出结果仅作为设计沟通参考，不保证可直接用于生产或建模。

## 开源协议与使用条款

本项目采用 CC BY-NC 4.0 协议，并附带额外社区使用条款。

参见:

- LICENSE
- ADDITIONAL_TERMS.md


---

# English

An AI image-generation workflow for converting anime/game character references into **multi-view Kigurumi head shell reference images**.

The goal of this project is to provide a reusable Prompt workflow that helps users generate stable reference images for communicating custom Kigurumi head shell designs.

Model used: gpt-image-2

## Frontend Page

Online frontend page:

[https://zhiyuan338.github.io/ai-kigurumi-head-reference/](https://zhiyuan338.github.io/ai-kigurumi-head-reference/)
   [https://enderxie23.github.io/ai-kigurumi-head/](https://enderxie23.github.io/ai-kigurumi-head/)

Reference image:

![workflow reference](web/assets/workflow-reference.jpeg)

## Project Goals

Input:

* Official 2D character artwork
* In-game 3D screenshots
* Unobstructed character head references
* High-quality Kigurumi head shell case references

Output:

* Unobstructed four-view character head references
* Four-view Kigurumi head shell design references
* Product-photo-style four-view or eight-view head shell references

## Core Idea

Do not generate the final head shell image directly from the character reference in a single step.

Recommended workflow:

1. **Character reference → unobstructed four-view character head reference**
2. **Character head reference → four-view Kigurumi head shell design**
3. **Kigurumi head shell design → product-photo-style four-view/eight-view output**

Core principles:

* Stabilize the structure first
* Then convert the design into a Kigurumi head shell
* Finally convert it into a product-photo-style reference
* Each reference image should have a clear purpose
* Each revision should focus on solving one major issue at a time

## File Structure

```text
ai-kigurumi-head-reference/
├─ README.md
├─ SKILL.md
├─ LICENSE
├─ .gitignore
├─ web/
│  ├─ index.html
│  ├─ styles.css
│  ├─ app.js
│  └─ assets/
│     └─ workflow-reference.jpeg
└─ prompts/
   ├─ step1-head-reference.md
   ├─ step2-kigurumi-design.md
   ├─ step3-product-view.md
   └─ troubleshooting.md
```

## Quick Start

1. Prepare character reference images.
2. Use `prompts/step1-head-reference.md` to generate unobstructed four-view character head references.
3. Use `prompts/step2-kigurumi-design.md` to convert the result into a four-view Kigurumi head shell design.
4. Use `prompts/step3-product-view.md` to generate product-photo-style four-view or eight-view images.
5. If the result is not ideal, use `prompts/troubleshooting.md` to refine the Prompt.
6. You can also use the online frontend page to assist with the workflow:

   [https://zhiyuan338.github.io/ai-kigurumi-head-reference/](https://zhiyuan338.github.io/ai-kigurumi-head-reference/)
   [https://enderxie23.github.io/ai-kigurumi-head/](https://enderxie23.github.io/ai-kigurumi-head/)

## Web Frontend

This repository includes a static frontend that does not require a build step:

* `web/index.html`
* `web/styles.css`
* `web/app.js`
* `web/assets/workflow-reference.jpeg`

You can open `web/index.html` directly for local use.

The API Base URL and API Key are stored only in the user’s browser and are not written to the repository. When generation is executed, the key is sent to the image or text API endpoint configured by the user. If the API service does not allow browser CORS requests, enter an OpenAI-compatible proxy Base URL that supports CORS.

## Material Preparation Suggestions

It is recommended to organize materials into the following categories:

```text
TargetCharacter_KigurumiHeadReference/
├─ 01_Character3DStructureReference/
├─ 02_Character2DMoodExpressionReference/
├─ 03_HighQualityKigurumiExamples/
├─ 04_ActualUploadCombinations/
├─ 05_GeneratedResults/
└─ 06_FailedAttempts/
```

## Notes

* Do not upload unauthorized character artwork, game screenshots, shop product photos, or other people’s private generated images to the public repository.
* This repository mainly stores workflows and Prompts, not complete chat logs.
* If you use other people’s images as references, follow the copyright and usage rules of the corresponding materials.
* The output of this project is intended only as a design communication reference and is not guaranteed to be directly usable for production or modeling.

## License & Additional Terms

This project uses CC BY-NC 4.0 with additional community-use restrictions.

See:

* LICENSE
* ADDITIONAL_TERMS.md
