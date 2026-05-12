const STORAGE_KEY = "kigurumi-head-studio-v1";

const dictionaries = {
  zh: {
    brand: "Kigurumi 头壳工作台",
    clearLocal: "清除本地数据",
    eyebrow: "三阶段图像工作流",
    headline: "AI Kigurumi Head Reference Workflow",
    lede: "从角色参考图生成去遮挡头部四视图、Kigurumi 头壳设计图和商品照风格多视图参考。",
    apiEyebrow: "连接设置",
    apiTitle: "图像 API 设置",
    apiStatusMissing: "需要 API Key",
    apiStatusReady: "已在本地保存",
    apiBase: "API Base URL",
    apiKey: "API Key",
    imageModel: "图像模型",
    size: "输出尺寸",
    count: "数量",
    quality: "质量",
    privacyNotice: "API Base URL 和 Key 只保存在当前浏览器中，不会写入 GitHub 仓库，也不会公开。执行阶段时，Key 只会发送给你配置的 API 端点。",
    promptPreset: "Prompt 模板",
    uploadRefs: "上传参考图",
    uploadSlot: "上传",
    replaceSlot: "更换",
    deleteSlot: "删除",
    otherRefs: "其他参考图",
    otherRefsHelp: "上传补充材料，避免过多重复或分工不清的图片。",
    previousCarryNote: "已使用上一阶段选中的图片作为主参考，因此该槽位已禁用。",
    includePrev: "包含上一阶段选中的图片",
    includeCurrent: "使用本阶段选中图片继续微调（生成图片后可用，将禁用 Prompt）",
    useRefinementRefs: "微调时同时使用上传的参考图",
    details: "详细修改要求",
    detailsPlaceholder: "例如：只修正表情，保持发型结构和四视图排版不变。",
    prompt: "Prompt",
    runStage: "执行阶段",
    copyPrompt: "复制 Prompt",
    select: "选中",
    selected: "已选中",
    download: "下载",
    running: "正在请求图像 API...",
    missingKey: "请先填写图像 API Key。",
    missingPrompt: "请先填写要发送的 Prompt。",
    noImage: "还没有结果。上传参考图并执行本阶段。",
    done: "完成。可以选中一张图片进入下一阶段。",
    failed: "执行失败：",
    copied: "已复制。",
    helperEyebrow: "故障排查",
    helperTitle: "自动 Prompt 生成器",
    textApiBase: "文本 API Base URL",
    textApiKey: "文本 API Key",
    textModel: "文本模型",
    helperStage: "阶段",
    refsUsed: "参考图和分工",
    refsPlaceholder: "1. 正面结构参考图\n2. 表情参考图\n3. Kigurumi 案例图",
    currentPrompt: "当前 Prompt",
    whatWorked: "正确且希望保留的部分",
    whatFailed: "错误且希望修正的部分",
    generatePrompt: "生成更强 Prompt",
    copy: "复制",
    helperMissing: "请填写文本 API Key，或复用上方图像 API Key。",
    helperRunning: "正在生成修正 Prompt...",
    helperDone: "已生成。"
  },
  en: {
    brand: "Kigurumi Head Studio",
    clearLocal: "Clear local data",
    eyebrow: "Three-stage image workflow",
    headline: "AI Kigurumi Head Reference Workflow",
    lede: "Turn character references into clean head turnarounds, kigurumi shell designs, and product-style multi-view references.",
    apiEyebrow: "Connection",
    apiTitle: "Image API settings",
    apiStatusMissing: "API key required",
    apiStatusReady: "Saved locally",
    apiBase: "API base URL",
    apiKey: "API key",
    imageModel: "Image model",
    size: "Output size",
    count: "Number",
    quality: "Quality",
    privacyNotice: "Your API base URL and keys are stored only in this browser. They are never written into this GitHub repository or made public. When you run a stage, the key is sent only to the API endpoint you configured.",
    promptPreset: "Prompt preset",
    uploadRefs: "Upload reference images",
    uploadSlot: "Upload",
    replaceSlot: "Replace",
    deleteSlot: "Delete",
    otherRefs: "Other reference images",
    otherRefsHelp: "Upload supporting references, while avoiding too many duplicate or unclear-role images.",
    previousCarryNote: "The selected previous-stage image is already used as the main reference, so this slot is disabled.",
    includePrev: "Include selected image from previous stage",
    includeCurrent: "Use selected image from this stage for refinement (available after generation; disables Prompt)",
    useRefinementRefs: "Use uploaded reference images during refinement",
    details: "Detailed modification notes",
    detailsPlaceholder: "Example: only fix the expression; keep hairstyle structure and four-view layout unchanged.",
    prompt: "Prompt",
    runStage: "Run stage",
    copyPrompt: "Copy prompt",
    select: "Select",
    selected: "Selected",
    download: "Download",
    running: "Requesting the image API...",
    missingKey: "Fill in the image API key first.",
    missingPrompt: "Fill in the prompt that should be sent first.",
    noImage: "No results yet. Upload references and run this stage.",
    done: "Done. Select one image to carry into the next stage.",
    failed: "Failed: ",
    copied: "Copied.",
    helperEyebrow: "Troubleshooting",
    helperTitle: "Auto-prompt generator",
    textApiBase: "Text API base URL",
    textApiKey: "Text API key",
    textModel: "Text model",
    helperStage: "Stage",
    refsUsed: "Reference images and roles",
    refsPlaceholder: "1. Front structure reference\n2. Expression reference\n3. Kigurumi example",
    currentPrompt: "Current prompt",
    whatWorked: "What is correct and should be kept",
    whatFailed: "What is wrong and should be fixed",
    generatePrompt: "Generate stronger prompt",
    copy: "Copy",
    helperMissing: "Fill in a text API key, or reuse the image API key above.",
    helperRunning: "Generating revised prompt...",
    helperDone: "Generated."
  }
};

const referenceGuidance = {
  1: {
    min: 4,
    max: 7,
    slots: [
      {
        title: { zh: "结构参考图", en: "Structure references" },
        help: { zh: "正面、背面、侧面或45度，用于发型和头部结构。", en: "Front, back, side, or 45-degree views for hairstyle and head structure." }
      },
      {
        title: { zh: "表情参考图", en: "Expression reference" },
        help: { zh: "用于眉毛、眼神、眼睑和嘴巴情绪。", en: "Used for eyebrows, gaze, eyelids, mouth, and emotion." }
      },
      {
        title: { zh: "官方角色图", en: "Official character art" },
        help: { zh: "用于气质、配色、虹膜颜色和角色识别感。", en: "Used for temperament, color palette, iris color, and identity." }
      }
    ]
  },
  2: {
    min: 4,
    max: 6,
    slots: [
      {
        title: { zh: "Step 1 最终四视图", en: "Final Step 1 turnaround" },
        help: { zh: "作为角色身份、发型和四视图关系的主参考。", en: "Main reference for identity, hairstyle, and view relationships." }
      },
      {
        title: { zh: "目标表情参考", en: "Target expression" },
        help: { zh: "1-2 张，用于固定最终头壳表情。", en: "1-2 images for final shell expression." }
      },
      {
        title: { zh: "Kigurumi 案例图", en: "Kigurumi examples" },
        help: { zh: "2-3 张，只参考头壳比例、眼眶和假发处理。", en: "2-3 images only for shell proportions, sockets, and wig handling." }
      }
    ]
  },
  3: {
    min: 2,
    max: 5,
    slots: [
      {
        title: { zh: "Step 2 最终头壳图", en: "Final Step 2 shell design" },
        help: { zh: "作为最终结构、发型、脸型和表情依据。", en: "Main basis for final structure, hairstyle, face shape, and expression." }
      },
      {
        title: { zh: "商品照案例图", en: "Product-photo examples" },
        help: { zh: "1-3 张，用于白底拍摄质量、材质和展示方式。", en: "1-3 images for white-background photo quality, material, and display." }
      },
      {
        title: { zh: "表情参考图（可选）", en: "Expression reference (optional)" },
        help: { zh: "用于确认最终眉毛、眼神和嘴巴。", en: "Used to confirm final eyebrows, gaze, and mouth." }
      }
    ]
  }
};

const stages = [
  {
    id: 1,
    kicker: { zh: "Step 1", en: "Step 1" },
    title: { zh: "去遮挡角色头部四视图", en: "Unobstructed character head turnaround" },
    presets: [
      {
        key: "general",
        label: { zh: "通用 Prompt", en: "General prompt" },
        zh: `请根据我上传的参考图，生成这个角色“去遮挡后的头部四视图设定图”。\n\n参考图分工如下：\n1. 结构参考图：用于确定角色的头部结构、发型轮廓、耳朵位置、侧脸轮廓、后脑和背面发型。\n2. 表情参考图：用于确定角色的眉毛、眼神、眼睑形状、嘴巴和整体表情。\n3. 官方角色图：用于确定角色气质、配色、虹膜颜色和角色识别感。\n\n请生成一张干净的角色头部四视图设定图，包括：正面、左前45度、左侧面、背面。\n\n要求：去掉遮挡物，例如兜帽、帽子、面罩等，但保留角色必要的小发饰。只保留头部、头发、耳朵和必要饰品。保留角色原本的表情、眼神和气质。发型结构应根据结构参考图合理补全。不要改成普通萌系脸。不要把脸做得太3D、太写实、太立体。不要生成kigurumi头壳。不要生成真人、cosplay、娃娃、手办、3D渲染风格。白色背景，角色设定图风格，结构清晰。四个视角必须是同一个角色、同一个发型、同一个表情系统。`,
        en: `Use the uploaded references to generate an unobstructed four-view character head design sheet.\n\nReference roles:\n1. Structure references define head shape, hairstyle silhouette, ear position, side profile, back of head, and rear hairstyle.\n2. Expression references define eyebrows, gaze, eyelids, mouth shape, and emotion.\n3. Official character art defines character identity, color palette, iris color, and overall temperament.\n\nCreate a clean head turnaround with front, left 45-degree, left side, and back views.\n\nRequirements: remove obstructing items such as hoods, hats, masks, or face coverings, while keeping necessary small hair accessories. Keep only the head, hair, ears, and required accessories. Preserve the character's original expression, gaze, and temperament. Complete the hairstyle logically from structural references. Do not turn it into a generic cute face. Do not make the face too 3D, realistic, or sculpted. Do not create a kigurumi head shell yet. Do not create a real person, cosplay, doll, figure, or 3D render. Use a white background and clear character design-sheet style. All four views must show the same character, same hairstyle, and same expression system.`
      },
      {
        key: "expression",
        label: { zh: "表情修正", en: "Expression fix" },
        zh: "请基于当前四视图设定图进行微调，不要重新设计角色。\n\n当前发型结构和四视图一致性基本正确，请保持不变。这次只重点修正表情。\n\n请根据目标表情参考图调整：眉毛角度、眼神、上眼睑和下眼睑形状、嘴巴形状、整体情绪。\n\n要求：表情更接近参考图。不要自动微笑，除非参考图本身就是微笑。不要改成普通可爱表情。不要让表情过度夸张。保持角色原本气质。\n\n输出仍然是同一个角色的头部四视图设定图。",
        en: "Refine the current four-view design sheet without redesigning the character.\n\nThe hairstyle structure and four-view consistency are mostly correct; keep them unchanged. Focus only on the expression.\n\nAdjust eyebrow angle, gaze, upper and lower eyelid shapes, mouth shape, and overall emotion according to the target expression reference.\n\nRequirements: make the expression closer to the reference. Do not add a smile unless the reference is smiling. Do not turn it into a generic cute expression. Do not exaggerate the expression. Preserve the character's temperament.\n\nOutput the same character head four-view design sheet."
      },
      {
        key: "face",
        label: { zh: "正脸修正", en: "Front face fix" },
        zh: "请基于当前四视图设定图进行微调，不要重新设计角色。\n\n当前发型和四视图一致性基本正确，请保持不变。这次重点修正正脸五官。\n\n请根据正脸参考图调整：眼睛形状、眼距、眉眼关系、嘴巴位置、脸部比例、虹膜颜色和眼神。\n\n要求：正脸更接近目标角色。不要改变发型结构。不要改变角色身份。不要变成普通模板脸。不要把脸变得更3D、更写实或更立体。\n\n输出仍然是角色头部四视图设定图。",
        en: "Refine the current four-view design sheet without redesigning the character.\n\nThe hairstyle and four-view consistency are mostly correct; keep them unchanged. Focus on the front-view facial features.\n\nAdjust eye shape, eye spacing, eyebrow-eye relationship, mouth position, facial proportions, iris color, and gaze according to the front-face reference.\n\nRequirements: make the front face closer to the target character. Do not change the hairstyle structure or character identity. Do not turn it into a generic template face. Do not make it more 3D, realistic, or sculpted.\n\nOutput the character head four-view design sheet."
      },
      {
        key: "childlike",
        label: { zh: "脸型幼态化", en: "Rounder childlike face" },
        zh: "请基于当前四视图设定图进行脸型修正，不要重新设计角色。\n\n当前问题是脸型偏尖、偏成熟，不够幼态。\n\n请重点调整：下巴缩短；下巴更圆、更钝、更小；下半张脸缩短；脸颊更饱满；下颌线更柔和；整体脸型更圆润、更幼态；不要长脸；不要尖下巴；不要成熟脸。\n\n同时保持：发型结构不变；表情不变；角色识别度不变；四视图排版不变。\n\n输出仍然是同一个角色的头部四视图设定图。",
        en: "Correct the face shape in the current four-view design sheet without redesigning the character.\n\nThe current issue is that the face is too sharp, mature, and not childlike enough.\n\nAdjust: shorten the chin; make the chin rounder, blunter, and smaller; shorten the lower face; make cheeks fuller; soften the jawline; make the overall face rounder and more childlike; avoid a long face, pointed chin, or mature face.\n\nKeep the hairstyle structure, expression, character identity, and four-view layout unchanged.\n\nOutput the same character head four-view design sheet."
      }
    ]
  },
  {
    id: 2,
    kicker: { zh: "Step 2", en: "Step 2" },
    title: { zh: "Kigurumi 头壳四视图设计图", en: "Kigurumi head shell design turnaround" },
    presets: [
      {
        key: "general",
        label: { zh: "通用 Prompt", en: "General prompt" },
        zh: `请根据我上传的参考图，把角色头部四视图设定图转换成 animegao kigurumi 头壳四视图设计图。\n\n参考图分工如下：\n1. 角色头部四视图设定图：作为最重要的主参考，用于确定目标角色的身份、发型结构、发色、耳朵位置、脸型方向、眼睛形状、整体比例和四视图关系。\n2. 目标表情参考图：只用于参考最终表情，尤其是眉毛、眼神、眼睑形状和嘴巴形状。\n3. kigurumi头壳案例图：只用于参考animegao kigurumi头壳的比例语言、面壳结构、眼眶处理、假发处理方式和设计完成度。不要复制案例图中的角色五官、发型和配色。\n\n请生成一张kigurumi头壳四视图设计图，包括：正面、左前45度、左侧面、背面。\n\n要求：必须是kigurumi头壳设计图，不是普通动漫头像。必须是实体可制作的头壳，有硬质面壳、固定表情、假发和必要饰品。保留目标角色的发型、发色、耳朵、眼睛颜色、眼神和整体气质。表情必须接近目标表情参考图。脸型保持幼态、圆润、短下巴，不要变成长脸或尖下巴。面部适合animegao kigurumi头壳：鼻子弱化，嘴巴简化，脸部平滑，不要过度立体。眼睛应是animegao kigurumi风格的大眼睛，有明确眼眶结构、眼线和睫毛。不要变成真人眼、玻璃眼或3D娃娃眼。假发可以有真实发丝质感，但整体发型轮廓必须保持角色设定图中的形状。四个视角必须是同一个头壳连续旋转展示。白色背景，清晰设计图风格，适合作为后续商品照和店家制作参考。\n\n禁止：不要生成真人。不要生成cosplay妆面。不要生成普通动漫插画头像。不要生成3D手办或BJD娃娃。不要生成过度写实的皮肤纹理。不要生成明显唇彩。不要让脸部变得太立体。不要改变角色发型结构。不要加入原本已经去掉的遮挡物。`,
        en: `Convert the uploaded character head four-view design sheet into an animegao kigurumi head shell four-view design sheet.\n\nReference roles:\n1. Character head turnaround is the primary reference for identity, hairstyle structure, hair color, ear position, face direction, eye shape, proportions, and view relationships.\n2. Target expression references are only for final expression: eyebrows, gaze, eyelids, and mouth shape.\n3. Kigurumi examples are only for animegao kigurumi proportions, face shell structure, eye-socket treatment, wig handling, and design finish. Do not copy their character features, hairstyle, or colors.\n\nCreate a kigurumi head shell four-view design sheet with front, left 45-degree, left side, and back views.\n\nRequirements: it must be a kigurumi head shell design, not a normal anime avatar. It must look like a physical manufacturable shell with a hard face shell, fixed expression, wig, and required accessories. Preserve the target character's hairstyle, hair color, ears, eye color, gaze, and temperament. The expression must match the target expression reference. Keep the face childlike, round, and short-chinned; avoid a long or pointed chin. The face should suit animegao kigurumi: weakened nose, simplified mouth, smooth face, and not overly sculpted. Eyes should be large animegao kigurumi eyes with clear eye-socket structure, eyeliner, and lashes. Do not make them real human eyes, glass eyes, or 3D doll eyes. The wig may have realistic fiber texture, but the overall silhouette must match the character design sheet. All four views must show the same head shell as a continuous rotation. White background, clear design-sheet style, suitable for product-photo generation and maker reference.\n\nForbidden: real person, cosplay makeup, normal anime illustration avatar, 3D figure, BJD doll, realistic skin texture, obvious lip gloss, overly sculpted face, changed hairstyle structure, or reintroduced removed obstructions.`
      },
      {
        key: "shell",
        label: { zh: "头壳感不足", en: "More shell-like" },
        zh: "请基于当前结果继续修改，不要重新设计角色。\n\n当前问题是：结果仍然太像普通动漫头像，kigurumi头壳感不足。\n\n请加强kigurumi头壳特征：明确表现为实体animegao kigurumi头壳。面部是硬质平滑面壳，不是普通绘画脸。眼睛有头壳眼眶结构，不是普通插画眼睛。眼线、睫毛、眼眶厚度更像真实kigurumi头壳。脸部保持固定表情，有面具感和实体头壳感。假发作为头壳上的真实假发存在，而不是普通插画头发。侧面要有头壳厚度和后脑体积。\n\n请保持：目标角色的发型、发色、耳朵、眼睛颜色和整体气质。当前四视图排版。幼态圆润脸型。目标表情。\n\n输出仍然是kigurumi头壳四视图设计图。",
        en: "Continue modifying the current result without redesigning the character.\n\nThe current issue: it still looks too much like a normal anime avatar and not enough like a kigurumi head shell.\n\nStrengthen the kigurumi shell features: clearly present it as a physical animegao kigurumi head shell. The face should be a hard smooth shell, not a normal drawn face. Eyes should have head-shell eye-socket structure, not ordinary illustration eyes. Eyeliner, lashes, and socket thickness should look closer to a real kigurumi shell. The face should have a fixed expression with mask-like physical shell presence. The wig should exist as a real wig mounted on the shell, not ordinary illustrated hair. Side view should show shell thickness and back-head volume.\n\nKeep the target character's hairstyle, hair color, ears, eye color, temperament, current four-view layout, round childlike face, and target expression.\n\nOutput the kigurumi head shell four-view design sheet."
      },
      {
        key: "too3d",
        label: { zh: "太3D/太娃娃", en: "Less 3D or doll-like" },
        zh: "请基于当前结果继续修改，不要重新设计角色。\n\n当前问题是：脸部太3D、太立体、太像娃娃或手办，不够像animegao kigurumi头壳。\n\n请调整为更平滑、更简化的kigurumi面壳风格：脸部不要有过强的立体塑形。鼻子进一步弱化。嘴巴进一步简化。不要明显唇彩。不要真实皮肤纹理。不要真人感。面壳应是平滑硬质表面，而不是3D角色脸或BJD娃娃脸。脸型保持圆润幼态，短下巴，柔和脸颊。眼睛保持animegao大眼风格，但不要变成玻璃眼或3D眼球。\n\n请保持：目标角色的发型结构和耳朵。四视图一致。目标表情。白色背景和设计图排版。\n\n输出仍然是kigurumi头壳四视图设计图。",
        en: "Continue modifying the current result without redesigning the character.\n\nThe current issue: the face is too 3D, too sculpted, too much like a doll or figure, and not enough like an animegao kigurumi shell.\n\nAdjust it to a smoother, simpler kigurumi face-shell style: avoid strong facial sculpting. Weaken the nose further. Simplify the mouth further. Avoid obvious lip gloss, realistic skin texture, and human realism. The shell should be a smooth hard surface, not a 3D character face or BJD doll face. Keep the face round, childlike, short-chinned, and soft-cheeked. Keep animegao large-eye style, but avoid glass eyes or 3D eyeballs.\n\nKeep the target character's hairstyle structure, ears, four-view consistency, target expression, white background, and design-sheet layout.\n\nOutput the kigurumi head shell four-view design sheet."
      },
      {
        key: "expression",
        label: { zh: "表情跑偏", en: "Expression drift" },
        zh: "请基于当前kigurumi头壳四视图进行表情修正，不要重新设计头壳。\n\n当前头壳结构、发型和四视图关系基本保留，请重点修改表情。\n\n请根据目标表情参考图调整：眉毛角度、眼神方向和情绪、上眼睑和下眼睑形状、嘴巴形状、整体气质。\n\n要求：表情必须更接近参考图。不要自动微笑，除非参考图本身就是微笑。不要改成普通可爱表情。不要让表情过度夸张。表情修改时不要改变发型、耳朵、脸型和四视图排版。\n\n输出仍然是同一个kigurumi头壳四视图设计图。",
        en: "Fix the expression in the current kigurumi head shell four-view sheet without redesigning the shell.\n\nThe shell structure, hairstyle, and view relationships are mostly preserved; focus on expression.\n\nAdjust eyebrow angle, gaze direction and emotion, upper and lower eyelid shapes, mouth shape, and overall temperament according to the expression reference.\n\nRequirements: the expression must be closer to the reference. Do not add a smile unless the reference is smiling. Do not turn it into a generic cute expression. Do not exaggerate. Do not change hairstyle, ears, face shape, or four-view layout while fixing expression.\n\nOutput the same kigurumi head shell four-view design sheet."
      },
      {
        key: "face",
        label: { zh: "脸型变尖", en: "Pointed face fix" },
        zh: "请基于当前kigurumi头壳四视图进行脸型修正，不要重新设计头壳。\n\n当前问题是：脸型又变得偏尖、偏成熟，不够幼态。\n\n请重点修正脸型：下巴缩短。下巴更圆、更钝、更小。下半张脸缩短。脸颊更饱满。下颌线更柔和。整体脸型更偏圆润幼态。不要长脸。不要尖下巴。不要成熟脸。\n\n同时保持：发型结构不变。耳朵位置不变。表情不变。眼睛颜色和角色气质不变。四视图排版不变。仍然是kigurumi头壳设计图。",
        en: "Correct the face shape in the current kigurumi head shell four-view sheet without redesigning the shell.\n\nThe current issue: the face became too pointed, mature, and not childlike enough.\n\nFix the face shape: shorten the chin; make the chin rounder, blunter, and smaller; shorten the lower face; make cheeks fuller; soften the jawline; make the overall face rounder and more childlike; avoid a long face, pointed chin, or mature face.\n\nKeep hairstyle structure, ear position, expression, eye color, character temperament, four-view layout, and kigurumi shell design identity unchanged."
      }
    ]
  },
  {
    id: 3,
    kicker: { zh: "Step 3", en: "Step 3" },
    title: { zh: "商品照风格四面/八面视图", en: "Product-style four/eight-view reference" },
    presets: [
      {
        key: "four",
        label: { zh: "四面图 Prompt", en: "Four-view prompt" },
        zh: `请基于上传的kigurumi头壳设计图，生成最终的kigurumi头壳商品照四面视图。\n\n参考图分工如下：\n1. kigurumi头壳设计图：作为最终头壳结构、发型、脸型、眼睛、耳朵和表情的主要依据。\n2. 商品照案例图：只用于参考拍摄质量、白底商品照风格、头壳材质、假发质感和展示方式。\n3. 表情参考图：用于确认最终眉毛、眼神和嘴巴的情绪。\n\n请生成一张白底商品照风格的kigurumi头壳四面视图，包括：正面、左前45度、左侧面、背面。\n\n要求：成品必须是kigurumi头壳商品照，不是插画，不是普通动漫头像，不是真人cosplay。四个视角必须是同一个头壳，结构一致。保留目标角色的发型、耳朵、发色、眼睛颜色和整体气质。表情必须符合参考图，尤其是眉毛、眼神、嘴巴。面壳为平滑硬质头壳，脸部不要过度立体。鼻子弱化，嘴巴简洁。不要明显唇彩，不要真人皮肤纹理，不要真实人脸感。假发可以有真实纤维质感，但整体仍然保持animegao kigurumi风格。白色背景，干净商品图排版，高质量。`,
        en: `Generate the final kigurumi head shell product-photo four-view sheet based on the uploaded kigurumi shell design.\n\nReference roles:\n1. Kigurumi head shell design is the main basis for final shell structure, hairstyle, face shape, eyes, ears, and expression.\n2. Product photo examples are only for shooting quality, white-background product style, shell material, wig texture, and display method.\n3. Expression reference confirms eyebrow, gaze, and mouth emotion.\n\nCreate a white-background product-photo style kigurumi head shell four-view sheet: front, left 45-degree, left side, and back.\n\nRequirements: the final image must be a kigurumi head shell product photo, not an illustration, normal anime avatar, or real cosplay. All four views must show the same head shell with consistent structure. Preserve the target character's hairstyle, ears, hair color, eye color, and temperament. Expression must match the reference, especially eyebrows, gaze, and mouth. The face shell should be smooth and hard, not overly sculpted. Weaken the nose and keep the mouth simple. Avoid obvious lip gloss, realistic skin texture, or real human face feeling. Wig may have realistic fiber texture while staying animegao kigurumi. White background, clean product layout, high quality.`
      },
      {
        key: "eight",
        label: { zh: "八面图 Prompt", en: "Eight-view prompt" },
        zh: `请基于上传的kigurumi头壳设计图，生成最终的kigurumi头壳商品照八面视图。\n\n请输出八个视角：正面、左前45度、左侧面、左后45度、背面、右后45度、右侧面、右前45度。\n\n参考图分工如下：\n1. kigurumi头壳设计图：作为最终头壳结构、发型、脸型、眼睛、耳朵和表情的主要依据。\n2. 商品照案例图：只用于参考拍摄质量、白底商品照风格、头壳材质、假发质感和展示方式。\n3. 表情参考图：用于确认最终眉毛、眼神和嘴巴的情绪。\n\n要求：成品必须是kigurumi头壳商品照八面视图。八个视角必须是同一个头壳连续旋转展示，不能变成八个不同角色。保留目标角色的发型、耳朵、发色、眼睛颜色和整体气质。表情必须符合参考图，尤其是眉毛、眼神、嘴巴。面壳为平滑硬质头壳，脸部不要过度立体。鼻子弱化，嘴巴简洁。不要明显唇彩，不要真人皮肤纹理，不要真实人脸感。假发可以有真实纤维质感，但整体仍然保持animegao kigurumi风格。白色背景，干净商品图排版，高质量。`,
        en: `Generate the final kigurumi head shell product-photo eight-view sheet based on the uploaded kigurumi shell design.\n\nOutput eight views: front, left 45-degree, left side, left rear 45-degree, back, right rear 45-degree, right side, and right 45-degree.\n\nReference roles:\n1. Kigurumi head shell design is the main basis for final shell structure, hairstyle, face shape, eyes, ears, and expression.\n2. Product photo examples are only for shooting quality, white-background product style, shell material, wig texture, and display method.\n3. Expression reference confirms eyebrow, gaze, and mouth emotion.\n\nRequirements: the final image must be a kigurumi head shell product-photo eight-view sheet. All eight views must show the same head shell as a continuous rotation, not eight different characters. Preserve the target character's hairstyle, ears, hair color, eye color, and temperament. Expression must match the reference, especially eyebrows, gaze, and mouth. The face shell should be smooth and hard, not overly sculpted. Weaken the nose and keep the mouth simple. Avoid obvious lip gloss, realistic skin texture, or real human face feeling. Wig may have realistic fiber texture while staying animegao kigurumi. White background, clean product layout, high quality.`
      }
    ]
  }
];

const state = {
  lang: "zh",
  settings: {
    apiBase: "",
    apiKey: "",
    imageModel: "gpt-image-2",
    imageSize: "1024x1024",
    imageCount: "1",
    imageQuality: "high",
    textApiBase: "",
    textApiKey: "",
    textModel: "gpt-4.1-mini"
  },
  results: { 1: [], 2: [], 3: [] },
  selected: { 1: null, 2: null, 3: null }
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

init();

function init() {
  loadState();
  bindSettings();
  renderStaticText();
  renderStages();
  bindHelper();
  $("#langToggle").addEventListener("click", toggleLanguage);
  $("#clearLocal").addEventListener("click", clearLocalData);
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    Object.assign(state.settings, saved.settings || {});
    state.lang = saved.lang || state.lang;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function saveState() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      lang: state.lang,
      settings: state.settings
    })
  );
}

function bindSettings() {
  for (const key of Object.keys(state.settings)) {
    const el = document.getElementById(key);
    if (!el) continue;
    el.value = state.settings[key];
    el.addEventListener("input", () => {
      state.settings[key] = el.value.trim();
      updateApiStatus();
      saveState();
    });
  }
  updateApiStatus();
}

function renderStaticText() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  $$("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  $$("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  $("#langToggle").textContent = state.lang === "zh" ? "English" : "中文";
  updateApiStatus();
}

function updateApiStatus() {
  const status = $("#apiStatus");
  const ready = Boolean(state.settings.apiKey);
  status.classList.toggle("ready", ready);
  status.textContent = ready ? t("apiStatusReady") : t("apiStatusMissing");
}

function renderStages() {
  const host = $("#pipeline");
  host.innerHTML = "";
  for (const stage of stages) {
    const node = $("#stageTemplate").content.firstElementChild.cloneNode(true);
    node.dataset.stageId = stage.id;
    $(".stage-number", node).textContent = stage.id;
    $(".stage-kicker", node).textContent = stage.kicker[state.lang];
    $(".stage-title", node).textContent = stage.title[state.lang];

    const presetSelect = $(".preset-select", node);
    for (const preset of stage.presets) {
      const option = document.createElement("option");
      option.value = preset.key;
      option.textContent = preset.label[state.lang];
      presetSelect.appendChild(option);
    }

    const promptInput = $(".prompt-input", node);
    const setPrompt = () => {
      const preset = stage.presets.find((item) => item.key === presetSelect.value);
      promptInput.value = preset[state.lang];
    };
    presetSelect.addEventListener("change", setPrompt);
    setPrompt();

    renderReferenceGuidance(stage, node);
    $(".run-stage", node).addEventListener("click", () => runStage(stage, node));
    $(".copy-stage", node).addEventListener("click", async () => {
      await navigator.clipboard.writeText(buildPrompt(node));
      $(".stage-status", node).textContent = t("copied");
    });

    if (stage.id === 1) {
      $(".carry-prev", node).closest("label").style.display = "none";
    }

    bindExclusiveCarryOptions(node);
    updateDetailVisibility(node);

    localizeNode(node);
    $(".stage-status", node).textContent = t("noImage");
    host.appendChild(node);
    renderResults(stage.id);
  }
}

function renderReferenceGuidance(stage, node) {
  const guidance = referenceGuidance[stage.id];
  const host = $(".reference-guidance", node);
  host.innerHTML = "";

  const slotGrid = document.createElement("div");
  slotGrid.className = "slot-grid";
  guidance.slots.forEach((slot, index) => {
    slotGrid.appendChild(createUploadSlot(slot.title[state.lang], slot.help[state.lang], stage, node, false, stage.id > 1 && index === 0));
  });

  const otherSlot = createUploadSlot(t("otherRefs"), t("otherRefsHelp"), stage, node, true, false);

  const warning = document.createElement("p");
  warning.className = "reference-warning";
  host.append(slotGrid, otherSlot, warning);
  updatePreviousSlotState(node);
  updateReferenceWarning(stage, node);
}

function createUploadSlot(titleText, helpText, stage, node, isWide, isPreviousCarrySlot) {
  const card = document.createElement("div");
  card.className = isWide ? "reference-slot upload-slot upload-slot-wide" : "reference-slot upload-slot";
  if (isPreviousCarrySlot) {
    card.dataset.previousCarrySlot = "true";
  }

  const title = document.createElement("strong");
  title.textContent = titleText;
  const help = document.createElement("span");
  help.textContent = helpText;

  const inputId = `stage-${stage.id}-upload-${Math.random().toString(36).slice(2)}`;
  const input = document.createElement("input");
  input.id = inputId;
  input.className = "slot-file-input";
  input.type = "file";
  input.accept = "image/*";
  input.multiple = true;

  const actions = document.createElement("div");
  actions.className = "slot-actions";

  const button = document.createElement("button");
  button.className = "upload-button";
  button.type = "button";
  button.textContent = t("uploadSlot");

  const deleteButton = document.createElement("button");
  deleteButton.className = "delete-upload-button";
  deleteButton.type = "button";
  deleteButton.textContent = t("deleteSlot");
  deleteButton.hidden = true;

  const preview = document.createElement("div");
  preview.className = "slot-preview";
  preview.setAttribute("aria-live", "polite");

  const carryNote = document.createElement("p");
  carryNote.className = "previous-carry-note";
  carryNote.textContent = t("previousCarryNote");

  button.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    if (!input.files.length) return;
    card._files = [...input.files];
    renderSlotPreview(card);
    updateReferenceWarning(stage, node);
  });
  deleteButton.addEventListener("click", () => {
    clearUploadSlot(card);
    updateReferenceWarning(stage, node);
  });

  actions.append(button, deleteButton);
  card.append(title, help, input, actions, preview, carryNote);
  return card;
}

function updateReferenceWarning(stage, node) {
  const guidance = referenceGuidance[stage.id];
  const count = getStageReferenceFiles(node).length;
  const warning = $(".reference-warning", node);
  const ok = count >= guidance.min;
  warning.classList.toggle("ok", ok);
  if (state.lang === "zh") {
    warning.textContent = ok
      ? `已选择 ${count} 张参考图。建议范围：${guidance.min}-${guidance.max} 张。`
      : `已选择 ${count} 张参考图。建议至少 ${guidance.min} 张，图片太少可能会降低结构、表情或风格稳定性。`;
  } else {
    warning.textContent = ok
      ? `${count} reference image(s) selected. Recommended range: ${guidance.min}-${guidance.max}.`
      : `${count} reference image(s) selected. Use at least ${guidance.min}; too few images may compromise structure, expression, or style stability.`;
  }
}

function renderSlotPreview(slot) {
  const preview = $(".slot-preview", slot);
  const button = $(".upload-button", slot);
  const deleteButton = $(".delete-upload-button", slot);
  const previousUrls = preview.dataset.objectUrls ? JSON.parse(preview.dataset.objectUrls) : [];
  previousUrls.forEach((url) => URL.revokeObjectURL(url));

  preview.innerHTML = "";
  const urls = [];
  (slot._files || []).forEach((file) => {
    const url = URL.createObjectURL(file);
    urls.push(url);

    const item = document.createElement("figure");
    item.className = "upload-thumb";

    const image = document.createElement("img");
    image.src = url;
    image.alt = file.name;

    const caption = document.createElement("span");
    caption.title = file.name;
    caption.textContent = file.name;

    item.append(image, caption);
    preview.appendChild(item);
  });
  preview.dataset.objectUrls = JSON.stringify(urls);
  button.textContent = slot._files?.length ? t("replaceSlot") : t("uploadSlot");
  deleteButton.hidden = !slot._files?.length;
}

function clearUploadSlot(slot) {
  const input = $(".slot-file-input", slot);
  const preview = $(".slot-preview", slot);
  const button = $(".upload-button", slot);
  const deleteButton = $(".delete-upload-button", slot);
  const previousUrls = preview.dataset.objectUrls ? JSON.parse(preview.dataset.objectUrls) : [];
  previousUrls.forEach((url) => URL.revokeObjectURL(url));
  input.value = "";
  slot._files = [];
  preview.innerHTML = "";
  preview.dataset.objectUrls = "[]";
  button.textContent = t("uploadSlot");
  deleteButton.hidden = true;
}

function getStageReferenceFiles(node) {
  return $$(".upload-slot", node)
    .filter((slot) => !$(".slot-file-input", slot).disabled)
    .flatMap((slot) => slot._files || []);
}

function bindExclusiveCarryOptions(node) {
  const carryPrev = $(".carry-prev", node);
  const carryCurrent = $(".carry-current", node);
  carryPrev.addEventListener("change", () => {
    if (carryPrev.checked) carryCurrent.checked = false;
    updateDetailVisibility(node);
    updatePreviousSlotState(node);
    updateReferenceSlotState(node);
  });
  carryCurrent.addEventListener("change", () => {
    if (carryCurrent.checked) carryPrev.checked = false;
    updateDetailVisibility(node);
    updatePreviousSlotState(node);
    updateReferenceSlotState(node);
  });
  $(".use-refinement-refs", node).addEventListener("change", () => {
    updateReferenceSlotState(node);
  });
}

function updatePreviousSlotState(node) {
  if ($(".carry-current", node).checked) return;
  const carryPrev = $(".carry-prev", node);
  const slot = $('[data-previous-carry-slot="true"]', node);
  if (!carryPrev || !slot) return;

  const disabled = carryPrev.checked;
  slot.classList.toggle("disabled", disabled);
  $$(".slot-file-input", slot).forEach((input) => {
    input.disabled = disabled;
  });
  $$(".upload-button", slot).forEach((button) => {
    button.setAttribute("aria-disabled", String(disabled));
  });
}

function updateReferenceSlotState(node) {
  const carryCurrent = $(".carry-current", node);
  const useRefinementRefs = $(".use-refinement-refs", node).checked;
  const disabled = carryCurrent.checked && !useRefinementRefs;
  $$(".upload-slot", node).forEach((slot) => {
    slot.classList.toggle("disabled", disabled);
    $$(".slot-file-input", slot).forEach((input) => {
      input.disabled = disabled;
    });
    $$(".upload-button, .delete-upload-button", slot).forEach((button) => {
      button.setAttribute("aria-disabled", String(disabled));
    });
  });
  if (!disabled) {
    updatePreviousSlotState(node);
  }
}

function updateDetailVisibility(node) {
  const detailLabel = $(".detail-input", node).closest("label");
  const refinementRefsLabel = $(".use-refinement-refs", node).closest("label");
  const promptInput = $(".prompt-input", node);
  const carryCurrent = $(".carry-current", node);
  const hasOutputs = Boolean(state.results[node.dataset.stageId]?.length);
  carryCurrent.disabled = !hasOutputs;
  if (!hasOutputs) carryCurrent.checked = false;
  const isRefinement = carryCurrent.checked;
  detailLabel.style.display = isRefinement ? "grid" : "none";
  refinementRefsLabel.style.display = isRefinement ? "flex" : "none";
  promptInput.disabled = isRefinement;
  updateReferenceSlotState(node);
}

function localizeNode(root) {
  $$("[data-i18n]", root).forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  $$("[data-i18n-placeholder]", root).forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}

function bindHelper() {
  $("#generatePrompt").addEventListener("click", generateHelperPrompt);
  $("#copyHelperPrompt").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("#helperOutput").value);
  });
}

function toggleLanguage() {
  state.lang = state.lang === "zh" ? "en" : "zh";
  saveState();
  renderStaticText();
  renderStages();
}

function clearLocalData() {
  localStorage.removeItem(STORAGE_KEY);
  for (const key of Object.keys(state.settings)) {
    state.settings[key] = key === "imageModel" ? "gpt-image-2" : key === "imageSize" ? "1024x1024" : key === "imageCount" ? "1" : key === "imageQuality" ? "high" : key === "textModel" ? "gpt-4.1-mini" : "";
    const el = document.getElementById(key);
    if (el) el.value = state.settings[key];
  }
  updateApiStatus();
}

function t(key) {
  return dictionaries[state.lang][key] || dictionaries.en[key] || key;
}

function buildPrompt(stageNode) {
  const prompt = $(".prompt-input", stageNode).value.trim();
  const detail = $(".detail-input", stageNode).value.trim();
  const isRefinement = $(".carry-current", stageNode).checked;
  return isRefinement ? detail : prompt;
}

async function runStage(stage, node) {
  const status = $(".stage-status", node);
  const button = $(".run-stage", node);
  if (!state.settings.apiKey) {
    status.textContent = t("missingKey");
    return;
  }

  button.disabled = true;
  status.textContent = t("running");
  try {
    const prompt = buildPrompt(node);
    if (!prompt) {
      status.textContent = t("missingPrompt");
      return;
    }
    const isRefinement = $(".carry-current", node).checked;
    const useRefinementRefs = $(".use-refinement-refs", node).checked;
    const files = isRefinement && !useRefinementRefs ? [] : getStageReferenceFiles(node);
    const carryPrev = $(".carry-prev", node)?.checked && stage.id > 1 ? state.selected[stage.id - 1] : null;
    const carryCurrent = $(".carry-current", node).checked ? state.selected[stage.id] : null;
    const references = [...files];
    if (carryPrev) references.unshift(await dataUrlToFile(carryPrev.src, `step-${stage.id - 1}-selected.png`));
    if (carryCurrent) references.unshift(await dataUrlToFile(carryCurrent.src, `step-${stage.id}-refinement.png`));

    const images = await requestImages(prompt, references);
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    images.forEach((src, index) => {
      state.results[stage.id].unshift({
        id: `${stage.id}-${stamp}-${index}`,
        src,
        prompt
      });
    });
    state.selected[stage.id] = state.results[stage.id][0] || null;
    renderResults(stage.id);
    status.textContent = t("done");
  } catch (error) {
    status.textContent = `${t("failed")}${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function requestImages(prompt, references) {
  const base = normalizeBase(state.settings.apiBase);
  const headers = { Authorization: `Bearer ${state.settings.apiKey}` };
  const n = clamp(parseInt(state.settings.imageCount, 10) || 1, 1, 4);
  const quality = state.settings.imageQuality;
  const size = state.settings.imageSize;

  if (references.length) {
    const form = new FormData();
    form.append("model", state.settings.imageModel || "gpt-image-2");
    form.append("prompt", prompt);
    form.append("n", String(n));
    if (size !== "auto") form.append("size", size);
    if (quality !== "auto") form.append("quality", quality);
    references.slice(0, 16).forEach((file) => {
      form.append("image", file, file.name);
    });
    const response = await fetch(`${base}/images/edits`, {
      method: "POST",
      headers,
      body: form
    });
    return parseImageResponse(response);
  }

  headers["Content-Type"] = "application/json";
  const body = {
    model: state.settings.imageModel || "gpt-image-2",
    prompt,
    n
  };
  if (size !== "auto") body.size = size;
  if (quality !== "auto") body.quality = quality;
  const response = await fetch(`${base}/images/generations`, {
    method: "POST",
    headers,
    body: JSON.stringify(body)
  });
  return parseImageResponse(response);
}

async function parseImageResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error?.message || `${response.status} ${response.statusText}`);
  }
  const data = payload.data || [];
  const images = data
    .map((item) => item.b64_json ? `data:image/png;base64,${item.b64_json}` : item.url)
    .filter(Boolean);
  if (!images.length) {
    throw new Error("The API response did not include images.");
  }
  return images;
}

function renderResults(stageId) {
  const stageNode = $(`[data-stage-id="${stageId}"]`);
  if (!stageNode) return;
  updateDetailVisibility(stageNode);
  updateReferenceSlotState(stageNode);
  const grid = $(".result-grid", stageNode);
  grid.innerHTML = "";
  const results = state.results[stageId];
  for (const result of results) {
    const card = document.createElement("article");
    card.className = "result-card";
    card.classList.toggle("selected", state.selected[stageId]?.id === result.id);
    const image = document.createElement("img");
    image.src = result.src;
    image.alt = `Step ${stageId} result`;

    const actions = document.createElement("div");
    actions.className = "result-actions";
    const select = document.createElement("button");
    select.type = "button";
    const isSelected = state.selected[stageId]?.id === result.id;
    select.classList.toggle("active", isSelected);
    select.textContent = isSelected ? t("selected") : t("select");
    select.addEventListener("click", () => {
      state.selected[stageId] = result;
      renderResults(stageId);
    });

    const download = document.createElement("a");
    download.href = result.src;
    download.download = `kigurumi-step-${stageId}-${result.id}.png`;
    download.textContent = t("download");

    actions.append(select, download);
    card.append(image, actions);
    grid.appendChild(card);
  }
}

async function generateHelperPrompt() {
  const output = $("#helperOutput");
  const button = $("#generatePrompt");
  const apiKey = state.settings.textApiKey || state.settings.apiKey;
  if (!apiKey) {
    output.value = t("helperMissing");
    return;
  }
  button.disabled = true;
  output.value = t("helperRunning");
  try {
    const stage = $("#helperStage").value;
    const userContent = buildTroubleshootingRequest(stage);
    const response = await fetch(`${normalizeBase(state.settings.textApiBase || state.settings.apiBase)}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: state.settings.textModel || "gpt-4.1-mini",
        messages: [
          {
            role: "system",
            content: "You help rewrite image-generation prompts for an animegao kigurumi head workflow. Diagnose the issue briefly, then provide one stronger correction prompt. Keep the prompt concrete and avoid vague taste words."
          },
          { role: "user", content: userContent }
        ],
        temperature: 0.4
      })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error?.message || `${response.status} ${response.statusText}`);
    output.value = payload.choices?.[0]?.message?.content || "";
  } catch (error) {
    output.value = `${t("failed")}${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function buildTroubleshootingRequest(stage) {
  if (state.lang === "zh") {
    return `我现在在执行 Step ${stage}。\n\n我上传的参考图包括：\n${$("#helperRefs").value.trim()}\n\n我使用的 Prompt 是：\n${$("#helperPrompt").value.trim()}\n\n生成结果哪里正确，希望保留：\n${$("#helperKeep").value.trim()}\n\n生成结果哪里错误，希望修改：\n${$("#helperFix").value.trim()}\n\n请帮我分析问题原因，并给出一版更强、更明确的修正 Prompt。`;
  }
  return `I am currently executing Step ${stage}.\n\nUploaded reference images and their roles:\n${$("#helperRefs").value.trim()}\n\nCurrent prompt:\n${$("#helperPrompt").value.trim()}\n\nWhat is correct and should be kept:\n${$("#helperKeep").value.trim()}\n\nWhat is wrong and should be fixed:\n${$("#helperFix").value.trim()}\n\nPlease diagnose the likely cause and provide one stronger, clearer correction prompt.`;
}

function normalizeBase(base) {
  const clean = (base || "https://api.openai.com/v1").trim();
  return clean.replace(/\/+$/, "");
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

async function dataUrlToFile(dataUrl, name) {
  const response = await fetch(dataUrl);
  const blob = await response.blob();
  return new File([blob], name, { type: blob.type || "image/png" });
}
