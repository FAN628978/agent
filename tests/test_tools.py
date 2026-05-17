import pytest
from src.tools import ToolLoader
from src.tools.base import Permission


@pytest.fixture
def loader():
    l = ToolLoader()
    l.load()
    l.set_permission_checker(lambda name, params: True)  # 测试时默认批准所有 ASK 工具
    return l


@pytest.fixture
def loader_no_checker():
    """无权限检查器的加载器，用于测试 ASK 工具被阻止"""
    l = ToolLoader()
    l.load()
    return l


class TestToolLoader:
    def test_load(self, loader):
        assert len(loader.tools) == 6

    def test_get_definitions(self, loader):
        defs = loader.get_definitions()
        names = [d["function"]["name"] for d in defs]
        for name in ["bash", "read", "write", "edit", "grep", "glob"]:
            assert name in names

    def test_permission_flags(self, loader):
        assert loader.tools["bash"]["permission"] == Permission.ASK
        assert loader.tools["write"]["permission"] == Permission.ASK
        assert loader.tools["edit"]["permission"] == Permission.ASK
        assert loader.tools["read"]["permission"] == Permission.ALLOW
        assert loader.tools["grep"]["permission"] == Permission.ALLOW
        assert loader.tools["glob"]["permission"] == Permission.ALLOW

    def test_read_only_flags(self, loader):
        for name in ["read", "grep", "glob"]:
            assert loader.tools[name]["read_only"] is True
        for name in ["bash", "write", "edit"]:
            assert loader.tools[name]["read_only"] is False

    def test_concurrency_safe_flags(self, loader):
        for name in ["read", "grep", "glob"]:
            assert loader.tools[name]["concurrency_safe"] is True
        for name in ["bash", "write", "edit"]:
            assert loader.tools[name]["concurrency_safe"] is False


class TestRead:
    def test_read_file(self, loader):
        result = loader.execute("read", {"file_path": "tests/test_tools.py", "limit": 3})
        assert "import" in result

    def test_read_nonexistent(self, loader):
        result = loader.execute("read", {"file_path": "/nonexistent/file.py"})
        assert "不存在" in result


class TestWrite:
    def test_write_create(self, loader):
        import os, tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            tmp = f.name
        try:
            result = loader.execute("write", {"file_path": tmp, "content": "hello"})
            assert "已写入" in result
            with open(tmp) as f:
                assert f.read() == "hello"
        finally:
            os.unlink(tmp)

    def test_write_overwrite(self, loader):
        import os, tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"original")
            tmp = f.name
        try:
            result = loader.execute("write", {"file_path": tmp, "content": "new"})
            with open(tmp) as f:
                assert f.read() == "new"
        finally:
            os.unlink(tmp)


class TestEdit:
    def test_edit_replace(self, loader):
        import os, tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"hello world")
            tmp = f.name
        try:
            result = loader.execute("edit", {"file_path": tmp, "old_string": "world", "new_string": "claude"})
            with open(tmp) as f:
                assert f.read() == "hello claude"
        finally:
            os.unlink(tmp)

    def test_edit_not_found(self, loader):
        import os, tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"hello")
            tmp = f.name
        try:
            result = loader.execute("edit", {"file_path": tmp, "old_string": "xyz", "new_string": "abc"})
            assert "未找到" in result
        finally:
            os.unlink(tmp)


class TestGlob:
    def test_glob_python(self, loader):
        result = loader.execute("glob", {"pattern": "**/*.py", "path": "tests"})
        assert ".py" in result

    def test_glob_nonexistent_path(self, loader):
        result = loader.execute("glob", {"pattern": "**/*.py", "path": "/nonexistent"})
        assert "不存在" in result


class TestBash:
    def test_bash_echo(self, loader):
        result = loader.execute("bash", {"command": "echo hello", "timeout": 5})
        assert "hello" in result

    def test_bash_invalid_command(self, loader):
        result = loader.execute("bash", {"command": "badcommandthatdoesnotexist123", "timeout": 5})
        assert "不是内部" in result

    def test_bash_timeout(self, loader):
        result = loader.execute("bash", {"command": "sleep 10", "timeout": 1})
        assert "超时" in result


class TestGrep:
    def test_grep_found(self, loader):
        result = loader.execute("grep", {"pattern": "import pytest", "path": "tests", "glob": "*.py", "max_results": 10})
        assert "import" in result or "未找到" in result

    def test_grep_nonexistent(self, loader):
        result = loader.execute("grep", {"pattern": "XYZ_NOT_EXIST_123", "path": ".", "glob": "*.toml"})
        assert "未找到" in result


class TestPermission:
    """工具权限控制测试"""

    def test_allow_direct_execute(self, loader):
        """ALLOW 权限无需批准直接执行"""
        result = loader.execute("read", {"file_path": "tests/test_tools.py", "limit": 1})
        assert "import" in result

    def test_ask_without_checker_blocked(self, loader_no_checker):
        """ASK 权限无检查器时被阻止"""
        result = loader_no_checker.execute("bash", {"command": "echo hello", "timeout": 5})
        assert "需要用户批准" in result or "拒绝" in result

    def test_ask_with_checker_approved(self, loader_no_checker):
        """ASK 权限检查器批准后执行"""
        loader_no_checker.set_permission_checker(lambda name, params: True)
        result = loader_no_checker.execute("bash", {"command": "echo hello", "timeout": 5})
        assert "hello" in result

    def test_ask_with_checker_denied(self, loader_no_checker):
        """ASK 权限检查器拒绝后被阻止"""
        loader_no_checker.set_permission_checker(lambda name, params: False)
        result = loader_no_checker.execute("write", {"file_path": "test.txt", "content": "hello"})
        assert "拒绝" in result

    def test_denied_always_blocked(self, loader_no_checker):
        """DENY 权限始终被阻止"""
        loader_no_checker._metadata["bash"] = {**loader_no_checker._metadata["bash"], "permission": Permission.DENY}
        result = loader_no_checker.execute("bash", {"command": "echo hello", "timeout": 5})
        assert "禁止" in result

    def test_not_loaded_tool_blocked(self, loader_no_checker):
        """未加载的工具被阻止"""
        result = loader_no_checker.execute("nonexistent", {})
        assert "未加载" in result or "找不到" in result


class TestNotFound:
    def test_nonexistent_tool(self, loader_no_checker):
        result = loader_no_checker.execute("nonexistent", {})
        assert "错误" in result or "未加载" in result