import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def find_shell() -> tuple[str, str]:
    """
    查找可用 shell。
    返回 (shell_path, shell_type)。若未找到可用的非 cmd shell，
    shell_path 为空字符串，调用方应退回 cmd。
    """
    if sys.platform == "win32":
        # 优先用 shutil.which 走 PATH
        bash_path = shutil.which("bash")
        if bash_path:
            return bash_path, "bash"

        # 备选: 通过 where.exe 查找
        try:
            proc = subprocess.run(
                ["where.exe", "bash"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                first_line = proc.stdout.strip().split("\n")[0]
                # 去掉 ANSI 颜色码
                first_line = re.sub(r"\x1b\[[0-9;]*[mK]", "", first_line)
                if first_line and Path(first_line).exists():
                    return first_line, "bash"
        except Exception:
            pass

        return "", "cmd"
    else:
        shell = os.environ.get("SHELL", "/bin/bash")
        if Path(shell).exists():
            return shell, "bash"
        return "/bin/sh", "sh"


def _convert_windows_path(path: str) -> str:
    """将 Windows 绝对路径转为 MSYS2 POSIX 路径。D:\\foo\\bar -> /d/foo/bar"""
    def _replacer(m: re.Match) -> str:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/")
        return f"/{drive}/{rest}"
    return re.sub(r"([A-Za-z]):\\(.+)", _replacer, path)


def _build_bash_command(command: str) -> str:
    """构造在 bash -c 中执行的命令，直接执行，agent 负责控制目录"""
    return command


def execute(command: str, timeout: int = 30) -> str:
    """
    通过 Git Bash (MSYS2) 执行 shell 命令。
    Windows 上找不到 bash 时自动退回 cmd.exe。
    """
    shell_path, shell_type = find_shell()

    if not shell_path or shell_type != "bash":
        return _execute_via_cmd(command, timeout)

    bash_cmd = _build_bash_command(command)

    try:
        proc = subprocess.Popen(
            [shell_path, "-c", bash_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        output = stdout if stdout else stderr
        return (output or "").strip() if output else "(空输出)"
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return f"错误: 命令执行超时 ({timeout}s)"
    except FileNotFoundError:
        # bash 二进制消失，退回 cmd
        return _execute_via_cmd(command, timeout)
    except Exception as e:
        return f"错误: {str(e)}"


def _execute_via_cmd(command: str, timeout: int) -> str:
    """Fallback: 通过 cmd.exe (shell=True) 执行"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
        output = result.stdout if result.stdout else result.stderr
        return (output or "").strip() if output else "(空输出)"
    except subprocess.TimeoutExpired:
        return f"错误: 命令执行超时 ({timeout}s)"
    except Exception as e:
        return f"错误: {str(e)}"