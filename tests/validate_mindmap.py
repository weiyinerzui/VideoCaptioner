# -*- coding: utf-8 -*-
"""验证思维导图功能的简单测试脚本"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.mind_map_generator import MindMapNode


def test_mind_map_node():
    """测试MindMapNode基本功能"""
    print("测试 MindMapNode...")
    
    # 创建测试节点
    child1 = MindMapNode("子节点1")
    child2 = MindMapNode("子节点2", [MindMapNode("孙节点1")])
    root = MindMapNode("根节点", [child1, child2])
    
    # 转换为字典
    result = root.to_dict()
    
    # 验证
    assert result["text"] == "根节点", "根节点文本错误"
    assert len(result["children"]) == 2, "子节点数量错误"
    assert result["children"][0]["text"] == "子节点1", "子节点1文本错误"
    assert result["children"][1]["text"] == "子节点2", "子节点2文本错误"
    assert len(result["children"][1]["children"]) == 1, "孙节点数量错误"
    
    print("✓ MindMapNode 测试通过")
    return True


def main():
    """运行所有测试"""
    print("=" * 50)
    print("开始验证思维导图功能")
    print("=" * 50)
    
    try:
        # 运行测试
        test_mind_map_node()
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过!")
        print("=" * 50)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
