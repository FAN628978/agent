"""
LLM 调用日志钩子。
在 client.py 的 API 调用处集成，记录每次 LLM 请求和响应，格式为人类可读文本。
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any


class LLMLogger:
    def __init__(self, log_path: Path | None = None):
        if log_path is None:
            log_path = Path("llm_calls.txt")
        self.log_path = Path(log_path)
        self._call_id = 0
        self._rounds: dict[int, dict] = {}

    def _write(self, text: str) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(text)

    def log_request(
        self,
        messages: list[dict],
        model: str,
        tools: list | None = None,
    ) -> int:
        """记录 LLM 请求（每个 tool_call_id 对应一次请求）"""
        self._call_id += 1
        call_id = self._call_id
        self._rounds[call_id] = {
            "model": model,
            "messages": self._truncate_messages(messages),
            "tools": [t["function"]["name"] if isinstance(t, dict) else str(t) for t in (tools or [])],
            "tool_calls": [],
            "tool_results": [],
            "usage": None,
            "error": None,
        }
        return call_id

    def log_response(
        self,
        call_id: int,
        content: str | None,
        tool_calls: list | None = None,
        usage: dict | None = None,
        error: str | None = None,
    ) -> None:
        """记录 LLM 响应，累积到当前轮次"""
        if call_id not in self._rounds:
            return
        r = self._rounds[call_id]
        r["tool_calls"] = tool_calls or []
        r["usage"] = usage
        r["error"] = error
        r["content"] = content

    def log_tool_result(self, call_id: int, tool_name: str, tool_result: str) -> None:
        """记录工具执行结果，累积到当前轮次"""
        if call_id not in self._rounds:
            return
        self._rounds[call_id]["tool_results"].append((tool_name, tool_result))

    def _flush_all(self) -> None:
        """将所有轮次刷写到文件"""
        if not self._rounds:
            return

        for call_id in sorted(self._rounds.keys()):
            self._write(self._format_round(call_id, self._rounds[call_id]))

        self._rounds.clear()

    def flush(self) -> None:
        """手动刷写（保留，兼容接口）"""
        self._flush_all()

    def _format_round(self, call_id: int, r: dict) -> str:
        lines = []
        lines.append(f"\n{'='*70}")
        lines.append(f"[请求 #{call_id}] model={r['model']} | tools={r['tools']}")
        lines.append(f"{'-'*70}")

        for i, msg in enumerate(r["messages"]):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            if role == "system":
                # system_prompt 可能很长，截断显示
                lines.append(f"[{i}] role=system")
                for ln in content.split("\n"):
                    if ln.strip():
                        lines.append(f"    {ln}")
                lines.append("")
            elif role == "user":
                lines.append(f"[{i}] role=user")
                for j, ln in enumerate(content.split("\n")):
                    if j == 0:
                        lines.append(f"    {ln}")
                    elif ln.strip():
                        lines.append(f"    {ln}")
                lines.append("")
            elif role == "assistant":
                lines.append(f"[{i}] role=assistant (tool_calls={len(msg.get('tool_calls',[]))})")
                for tc in msg.get("tool_calls", []):
                    fname = tc.get("function", {}).get("name", "?")
                    fargs = tc.get("function", {}).get("arguments", "{}")
                    if isinstance(fargs, str):
                        try: fargs = json.loads(fargs)
                        except: pass
                    args_str = ", ".join(f"{k}={repr(v)[:40]}" for k, v in fargs.items())
                    lines.append(f"    -> {fname}({args_str})")
                if msg.get("content"):
                    for j, ln in enumerate(msg["content"].split("\n")):
                        if j == 0:
                            lines.append(f"    text: {ln[:100]}")
                lines.append("")
            elif role == "tool":
                lines.append(f"[{i}] role=tool ({msg.get('tool_call_id','')})")
                c = msg.get("content", "")
                for j, ln in enumerate(c.split("\n")):
                    if j == 0:
                        lines.append(f"    {ln[:100]}")
                    elif ln.strip():
                        lines.append(f"    {ln[:100]}")
                lines.append("")

        lines.append(f"{'='*70}")
        lines.append("[响应]")

        tcs = r.get("tool_calls", [])
        usage = r.get("usage", {})
        if usage:
            lines.append(f"  tokens: prompt={usage.get('prompt_tokens','?')} completion={usage.get('completion_tokens','?')} total={usage.get('total_tokens','?')}")

        if r.get("error"):
            lines.append(f"  ERROR: {r['error']}")

        for tc in tcs:
            fname = tc.get("name", "?")
            args_raw = tc.get("arguments", "{}")
            if isinstance(args_raw, str):
                try: args = json.loads(args_raw)
                except: args = args_raw
            else:
                args = args_raw
            args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
            lines.append(f"  -> {fname}({args_str})")

        content = r.get("content", "") or ""
        if content.strip():
            # 去掉思考标签
            clean = content.replace("\n<think>", "\n[思考]").replace("\n</think>", "\n[/思考]")
            for ln in clean.split("\n"):
                if ln.strip():
                    lines.append(f"  {ln[:120]}")
        elif not tcs:
            lines.append("  (空响应)")

        lines.append("")
        lines.append("[工具执行结果]")
        for tool, result in r.get("tool_results", []):
            for j, ln in enumerate(result.split("\n")):
                if j == 0:
                    lines.append(f"  {tool}: {ln[:120]}")
                elif ln.strip():
                    lines.append(f"  {ln[:120]}")
            if len(result) > 120:
                lines.append(f"  ... (共 {len(result)} 字)")
        lines.append("")

        return "\n".join(lines)

    def _truncate_messages(self, messages: list[dict], max_len: int = 600) -> list[dict]:
        """截断过长内容"""
        result = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > max_len:
                content = content[:max_len] + "..."
            result.append({**msg, "content": content})
        return result