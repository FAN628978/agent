from src.tools.base import BaseTool


class CalculatorTool(BaseTool):
    """计算器工具，执行数学表达式计算"""

    name = "calculator"
    description = "执行数学表达式计算，返回计算结果"

    def execute(self, expression: str) -> str:
        """执行数学表达式

        Args:
            expression: 数学表达式，如 "2 + 3 * 4"
        """
        try:
            # 安全计算：只允许基本运算
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return "错误: 表达式包含非法字符"

            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"错误: {str(e)}"


tool = CalculatorTool()