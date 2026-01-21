# -*- coding: utf-8 -*-
"""测试思维导图生成器"""

import pytest

from app.core.mind_map_generator import MindMapGenerator, MindMapNode


def test_mind_map_node_to_dict():
    """测试MindMapNode转换为字典"""
    # 创建测试节点
    child1 = MindMapNode("子节点1")
    child2 = MindMapNode("子节点2", [MindMapNode("孙节点1")])
    root = MindMapNode("根节点", [child1, child2])

    # 转换为字典
    result = root.to_dict()

    # 验证结构
    assert result["text"] == "根节点"
    assert len(result["children"]) == 2
    assert result["children"][0]["text"] == "子节点1"
    assert result["children"][1]["text"] == "子节点2"
    assert len(result["children"][1]["children"]) == 1
    assert result["children"][1]["children"][0]["text"] == "孙节点1"


def test_build_tree():
    """测试从JSON构建树"""
    generator = MindMapGenerator()

    # 测试数据
    data = {
        "title": "测试主题",
        "children": [
            {
                "text": "子主题1",
                "children": [
                    {"text": "要点1", "children": []},
                    {"text": "要点2", "children": []},
                ],
            },
            {"text": "子主题2", "children": []},
        ],
    }

    # 构建树
    tree = generator._build_tree(data)

    # 验证
    assert tree.text == "测试主题"
    assert len(tree.children) == 2
    assert tree.children[0].text == "子主题1"
    assert len(tree.children[0].children) == 2
    assert tree.children[0].children[0].text == "要点1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
