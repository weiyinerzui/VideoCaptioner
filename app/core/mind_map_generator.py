# -*- coding: utf-8 -*-
"""思维导图生成器 - 使用LLM分析字幕内容生成结构化摘要"""

import json
from typing import Dict, List, Optional

from openai import OpenAI

from app.common.config import cfg
from app.core.entities import LLMServiceEnum


class MindMapNode:
    """思维导图节点"""

    def __init__(self, text: str, children: Optional[List["MindMapNode"]] = None):
        self.text = text
        self.children = children or []

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "text": self.text,
            "children": [child.to_dict() for child in self.children],
        }


class MindMapGenerator:
    """思维导图生成器"""

    DEFAULT_PROMPT = """请分析以下视频字幕内容，生成一个结构化的思维导图摘要。

要求：
1. 提取视频的主题和核心观点
2. 将内容组织成层级结构（主题 -> 子主题 -> 要点）
3. 每个节点应简洁明了，不超过20个字
4. 最多3层深度
5. 以JSON格式返回，格式如下：
{
  "title": "视频主题",
  "children": [
    {
      "text": "子主题1",
      "children": [
        {"text": "要点1", "children": []},
        {"text": "要点2", "children": []}
      ]
    },
    {
      "text": "子主题2",
      "children": []
    }
  ]
}

字幕内容：
{subtitle_text}

请直接返回JSON，不要包含任何其他文字。"""

    def __init__(self, custom_prompt: Optional[str] = None):
        """
        初始化思维导图生成器

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

    def generate(self, subtitle_text: str) -> MindMapNode:
        """
        生成思维导图

        Args:
            subtitle_text: 字幕文本内容

        Returns:
            MindMapNode: 思维导图根节点

        Raises:
            Exception: 生成失败时抛出异常
        """
        # 构建提示词 - 使用replace而不是format,避免字幕中的花括号被误解析
        prompt = self.custom_prompt or self.DEFAULT_PROMPT
        prompt = prompt.replace("{subtitle_text}", subtitle_text)

        try:
            # 调用LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )

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

            # 尝试提取JSON对象 (处理LLM在JSON前后添加额外文字的情况)
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

            # 构建思维导图
            return self._build_tree(data)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"DEBUG: Exception occurred:\n{tb}")
            
            error_msg = str(e)
            # 如果是KeyError，添加额外说明
            if isinstance(e, KeyError):
                error_msg = f"KeyError: {error_msg}"
                
            if "无法解析" in error_msg or "LLM" in error_msg:
                raise Exception(f"{error_msg}\n\n详细错误:\n{tb}")
            raise Exception(f"生成思维导图失败: {error_msg}\n\n详细错误:\n{tb}")

    def _build_tree(self, data: Dict) -> MindMapNode:
        """
        从JSON数据构建思维导图树

        Args:
            data: JSON数据

        Returns:
            MindMapNode: 根节点
        """
        # 获取标题
        title = data.get("title", "视频摘要")

        # 递归构建子节点
        children = []
        for child_data in data.get("children", []):
            children.append(self._build_node(child_data))

        return MindMapNode(title, children)

    def _build_node(self, data) -> MindMapNode:
        """
        递归构建节点

        Args:
            data: 节点数据 (可以是dict或str)

        Returns:
            MindMapNode: 节点
        """
        # 如果data是字符串,直接作为叶子节点
        if isinstance(data, str):
            return MindMapNode(data, [])
        
        # 如果不是字典,尝试转换
        if not isinstance(data, dict):
            return MindMapNode(str(data), [])
        
        text = data.get("text", "")
        children = []

        for child_data in data.get("children", []):
            children.append(self._build_node(child_data))

        return MindMapNode(text, children)
