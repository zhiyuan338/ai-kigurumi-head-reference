# Changelog / 更新日志

## 0.2.0 - Frontend Workflow Studio / 前端工作台

- Added a static GitHub Pages-ready frontend under `frontend/` for running the three-stage image workflow.  
  在 `frontend/` 下新增可直接用于 GitHub Pages 的静态前端，用于执行三阶段图像工作流。

- Added bilingual UI, local-only API key settings, stage prompt presets, image result selection, and download actions.  
  新增中英文界面、本地保存 API Key 设置、阶段 Prompt 模板、结果图片选择和下载功能。

- Added guided reference upload slots with previews, per-stage reference suggestions, minimum-reference warnings, replacement, and delete controls.  
  新增带预览的参考图上传槽位、分阶段参考图建议、最低参考图数量提醒、更换和删除控制。

- Added refinement mode for generated outputs; selecting a current-stage image for refinement disables the base Prompt and uses the detailed modification request instead.  
  新增基于本阶段生成结果的微调模式；选择本阶段图片继续微调时会禁用基础 Prompt，并改用详细修改要求。

- Added an auto-prompt generator based on the troubleshooting template, with optional separate text-model API settings.  
  新增基于问题排查模板的自动 Prompt 生成器，并支持单独配置文本模型 API。

## 0.1.0 - Initial Release / 初始发布

- Added a three-stage Kigurumi head reference workflow.  
  新增三阶段 Kigurumi 头壳参考图工作流。

- Added prompts for hoodless character head references, Kigurumi head shell design, and product-view output.  
  新增去遮挡角色头部参考、Kigurumi 头壳设计、商品视图输出的提示词。

- Added troubleshooting templates for prompt refinement.  
  新增用于优化提示词的问题排查模板。

