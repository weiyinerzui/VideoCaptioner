# -*- coding: utf-8 -*-
"""精彩片段生成器 - 使用LLM分析字幕内容提取精彩片段"""

import json
from typing import Dict, List, Optional

from openai import OpenAI

from app.common.config import cfg
from app.core.entities import LLMServiceEnum


class HighlightGenerator:
    """精彩片段生成器"""

    DEFAULT_PROMPT = """请分析以下视频字幕内容，提取视频的精彩片段（Highlight Reels）。

要求：
1. 识别视频中最重要的3-8个片段。
2. 每个片段应包含：
   - start_time: 开始时间 (HH:MM:SS)
   - end_time: 结束时间 (HH:MM:SS)
   - summary: 一句话总结 (不超过20字)
   - topic: 主题分类 (如: "核心观点", "案例分析", "总结", "背景介绍"等)
   - color: 对应主题的颜色代码 (从以下颜色中选择: #FF5733, #33FF57, #3357FF, #F3FF33, #FF33F3, #33FFF3, #FFA533, #33FFFF)
3. 确保片段之间不重叠。
4. 以JSON格式返回，格式如下：
{
  "highlights": [
    {
      "start_time": "00:00:10",
      "end_time": "00:00:45",
      "summary": "介绍LLM的核心概念",
      "topic": "背景介绍",
      "color": "#3357FF"
    }
  ],
  "topics": ["背景介绍", "核心观点"]
}

字幕内容：
{subtitle_text}

请直接返回JSON，不要包含任何其他文字。"""

    def __init__(self, custom_prompt: Optional[str] = None):
        """
        初始化精彩片段生成器

        Args:
            custom_prompt: 自定义提示词，如果为None则使用默认提示词
        """
        self.custom_prompt = custom_prompt
        self._init_llm_client()

    def _init_llm_client(self):
        """初始化LLM客户端"""
        # 根据当前选择的LLM服务获取对应的配置
        current_service = cfg.llm_service.value
        if current_service == LLMServiceEnum.OPENAI:
            base_url = cfg.openai_api_base.value
            api_key = cfg.openai_api_key.value
            self.model = cfg.openai_model.value
        elif current_service == LLMServiceEnum.SILICON_CLOUD:
            base_url = cfg.silicon_cloud_api_base.value
            api_key = cfg.silicon_cloud_api_key.value
            self.model = cfg.silicon_cloud_model.value
        elif current_service == LLMServiceEnum.DEEPSEEK:
            base_url = cfg.deepseek_api_base.value
            api_key = cfg.deepseek_api_key.value
            self.model = cfg.deepseek_model.value
        elif current_service == LLMServiceEnum.OLLAMA:
            base_url = cfg.ollama_api_base.value
            api_key = cfg.ollama_api_key.value
            self.model = cfg.ollama_model.value
        elif current_service == LLMServiceEnum.LM_STUDIO:
            base_url = cfg.lm_studio_api_base.value
            api_key = cfg.lm_studio_api_key.value
            self.model = cfg.lm_studio_model.value
        elif current_service == LLMServiceEnum.GEMINI:
            base_url = cfg.gemini_api_base.value
            api_key = cfg.gemini_api_key.value
            self.model = cfg.gemini_model.value
        elif current_service == LLMServiceEnum.CHATGLM:
            base_url = cfg.chatglm_api_base.value
            api_key = cfg.chatglm_api_key.value
            self.model = cfg.chatglm_model.value
        else:
            raise ValueError(f"Unsupported LLM service: {current_service}")

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, subtitle_text: str) -> Dict:
        """
        生成精彩片段

        Args:
            subtitle_text: 字幕文本内容

        Returns:
            Dict: 包含 highlights 和 topics 的字典

        Raises:
            Exception: 生成失败时抛出异常
        """
        # 构建提示词
        prompt = self.custom_prompt or self.DEFAULT_PROMPT
        prompt = prompt.replace("{subtitle_text}", subtitle_text)

        try:
            # 调用LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            print(f"DEBUG: LLM Response: {response}")

            # 检查响应是否有效
            if not hasattr(response, 'choices') or not response.choices:
                # 尝试提取错误信息
                error_msg = getattr(response, 'msg', None) or getattr(response, 'error', None) or "Unknown error"
                status = getattr(response, 'status', None)
                if str(status) == '439':
                    raise Exception(f"API Token 已过期，请更新配置。错误信息: {error_msg}")
                raise Exception(f"LLM 请求失败: {error_msg} (状态码: {status})")

            # 提取响应内容
            content = response.choices[0].message.content
            if not content:
                raise Exception("LLM返回内容为空")
            
            content = content.strip()

            # 尝试解析JSON - 清理markdown代码块标记
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # 尝试提取JSON对象
            json_start = content.find('{')
            json_end = content.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                content = content[json_start:json_end + 1]

            # 解析JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 尝试使用 json_repair 修复
                try:
                    from json_repair import repair_json
                    repaired = repair_json(content)
                    data = json.loads(repaired)
                except Exception:
                    print(f"DEBUG: JSON parse failed. Content: {content}")
                    raise Exception(f"无法解析LLM返回的JSON内容")

            print(f"DEBUG: Parsed data type: {type(data)}")
            if not isinstance(data, dict):
                print(f"DEBUG: Data is not a dict: {data}")
                raise Exception(f"LLM返回的数据格式不正确(需要JSON对象): {type(data)}")

            # 验证数据结构
            if "highlights" not in data:
                raise Exception("返回数据缺少 'highlights' 字段")

            return data

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"DEBUG: Exception occurred:\n{tb}")
            raise Exception(f"生成精彩片段失败: {str(e)}")
