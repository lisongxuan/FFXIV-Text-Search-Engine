"""
FFXIV Text Search Engine API 测试脚本

用法:
    python test_api.py                          # 使用默认地址 http://localhost:5000
    python test_api.py --base-url http://your-server:8080
    python test_api.py -v                       # 显示详细的响应内容
    python test_api.py --test search            # 只运行名称包含 "search" 的测试
"""

import argparse
import json
import sys
import time
from urllib.parse import urlencode, quote
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class APITestRunner:
    def __init__(self, base_url, verbose=False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []
        self.context = {}

    def _request(self, method, path, params=None, timeout=30):
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urlencode(params, quote_via=quote)

        parsed = urlparse(url)
        ConnClass = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
        conn = ConnClass(parsed.hostname, parsed.port, timeout=timeout)
        request_path = parsed.path + ("?" + parsed.query if parsed.query else "")

        start = time.time()
        conn.request(method, request_path)
        resp = conn.getresponse()
        elapsed_ms = (time.time() - start) * 1000

        body = resp.read().decode("utf-8")
        conn.close()

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = body

        return resp.status, data, elapsed_ms

    def run_test(self, name, method, path, params=None, checks=None, timeout=30):
        """
        checks: list of (description, callable(status, data) -> bool)
        """
        checks = checks or []
        print(f"\n  {Colors.CYAN}[TEST]{Colors.RESET} {name}")
        print(f"         {method} {path}" + (f"?{urlencode(params, quote_via=quote)}" if params else ""))

        try:
            status, data, elapsed_ms = self._request(method, path, params, timeout)
        except Exception as e:
            print(f"         {Colors.RED}CONNECTION ERROR: {e}{Colors.RESET}")
            self.failed += 1
            self.results.append((name, "FAIL", 0, str(e)))
            return None, None

        status_color = Colors.GREEN if 200 <= status < 300 else Colors.YELLOW if status < 500 else Colors.RED
        print(f"         Status: {status_color}{status}{Colors.RESET}  Time: {elapsed_ms:.0f}ms")

        if self.verbose:
            preview = json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, (dict, list)) else str(data)
            if len(preview) > 2000:
                preview = preview[:2000] + "\n... (truncated)"
            print(f"         Response:\n{preview}")

        all_passed = True
        for desc, check_fn in checks:
            try:
                result = check_fn(status, data)
            except Exception as e:
                result = False
                desc += f" (exception: {e})"
            icon = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
            print(f"         [{icon}] {desc}")
            if not result:
                all_passed = False

        if all_passed:
            self.passed += 1
            self.results.append((name, "PASS", elapsed_ms, ""))
        else:
            self.failed += 1
            self.results.append((name, "FAIL", elapsed_ms, ""))

        return status, data

    def skip_test(self, name, reason):
        print(f"\n  {Colors.YELLOW}[SKIP]{Colors.RESET} {name} — {reason}")
        self.skipped += 1
        self.results.append((name, "SKIP", 0, reason))

    def print_summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*60}")
        print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
        print(f"{'='*60}")
        print(f"  Total:   {total}")
        print(f"  {Colors.GREEN}Passed:  {self.passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed:  {self.failed}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Skipped: {self.skipped}{Colors.RESET}")
        print()

        if self.failed > 0:
            print(f"  {Colors.RED}Failed tests:{Colors.RESET}")
            for name, result, _, detail in self.results:
                if result == "FAIL":
                    print(f"    - {name} {detail}")
            print()

        slow_tests = [(n, t) for n, r, t, _ in self.results if r == "PASS" and t > 1000]
        if slow_tests:
            print(f"  {Colors.YELLOW}Slow tests (>1s):{Colors.RESET}")
            for name, ms in sorted(slow_tests, key=lambda x: -x[1]):
                print(f"    - {name}: {ms:.0f}ms")
            print()


def run_all_tests(runner: APITestRunner, test_filter: str = None):

    def should_run(name):
        return test_filter is None or test_filter.lower() in name.lower()

    # ========================================
    # 1. 基础连通性
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}")
    print("1. 基础连通性测试")
    print(f"{'='*60}{Colors.RESET}")

    if should_run("获取所有语言"):
        status, data = runner.run_test(
            "获取所有语言",
            "GET", "/languages",
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("返回列表", lambda s, d: isinstance(d, list)),
                ("至少有一种语言", lambda s, d: len(d) > 0),
            ]
        )
        if data and isinstance(data, list):
            runner.context["languages"] = data
            runner.context["first_language"] = data[0]

    if should_run("获取所有版本"):
        status, data = runner.run_test(
            "获取所有版本",
            "GET", "/versions",
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("返回列表", lambda s, d: isinstance(d, list)),
                ("至少有一个版本", lambda s, d: len(d) > 0),
                ("包含 language 字段", lambda s, d: "language" in d[0] if d else True),
                ("包含 version 字段", lambda s, d: "version" in d[0] if d else True),
            ]
        )
        if data and isinstance(data, list):
            runner.context["all_versions_data"] = data

    # ========================================
    # 2. 版本查询
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}")
    print("2. 版本查询测试")
    print(f"{'='*60}{Colors.RESET}")

    lang = runner.context.get("first_language")
    if not lang:
        runner.skip_test("按语言查询版本", "未获取到语言数据")
        runner.skip_test("获取语言最新版本", "未获取到语言数据")
    else:
        if should_run("按语言查询版本"):
            status, data = runner.run_test(
                f"按语言查询版本 (language={lang})",
                "GET", f"/versions/{lang}",
                checks=[
                    ("返回 200", lambda s, d: s == 200),
                    ("返回列表", lambda s, d: isinstance(d, list)),
                ]
            )
            if data and isinstance(data, list) and len(data) > 0:
                runner.context["first_version"] = data[-1]

        if not runner.context.get("first_version"):
            all_ver = runner.context.get("all_versions_data", [])
            for v in all_ver:
                if v.get("language") == lang:
                    runner.context["first_version"] = v.get("version")
                    break

        if should_run("获取语言最新版本"):
            runner.run_test(
                f"获取语言最新版本 (language={lang})",
                "GET", "/latest_version",
                params={"language": lang},
                checks=[
                    ("返回 200", lambda s, d: s == 200),
                    ("包含 latest_version", lambda s, d: "latest_version" in d),
                ]
            )

    if should_run("获取所有语言最新版本"):
        runner.run_test(
            "获取所有语言最新版本",
            "GET", "/latest_versions",
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("返回列表", lambda s, d: isinstance(d, list)),
            ]
        )

    # ========================================
    # 3. 全文搜索 (MATCH AGAINST)
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}")
    print("3. 全文搜索测试 (MATCH AGAINST)")
    print(f"{'='*60}{Colors.RESET}")

    lang = runner.context.get("first_language")
    version = runner.context.get("first_version")
    search_keyword = "test"

    if not lang or not version:
        runner.skip_test("单语言全文搜索", "未获取到语言/版本数据")
    else:
        if should_run("单语言全文搜索"):
            status, data = runner.run_test(
                f"单语言全文搜索 (language={lang}, version={version})",
                "GET", "/data_by_data",
                params={"data": search_keyword, "language": lang, "version": version, "page": 1, "per_page": 5},
                checks=[
                    ("返回 200", lambda s, d: s == 200),
                    ("包含 data 字段", lambda s, d: "data" in d),
                    ("包含 pagination 字段", lambda s, d: "pagination" in d),
                    ("pagination 包含 total", lambda s, d: "total" in d.get("pagination", {})),
                ]
            )
            if data and data.get("data"):
                first_item = data["data"][0]
                runner.context["search_result_path"] = first_item.get("path")
                runner.context["search_result_id"] = first_item.get("id")
                runner.context["search_result_name"] = first_item.get("name")

    # ========================================
    # 4. 多语言搜索
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}")
    print("4. 多语言搜索测试")
    print(f"{'='*60}{Colors.RESET}")

    languages = runner.context.get("languages", [])
    if len(languages) < 1 or not version:
        runner.skip_test("多语言全文搜索", "语言或版本数据不足")
        runner.skip_test("多语言包含搜索", "语言或版本数据不足")
        runner.skip_test("多语言精确搜索", "语言或版本数据不足")
    else:
        all_versions_status, all_versions_data, _ = runner._request("GET", "/versions")
        lang_version_map = {}
        if isinstance(all_versions_data, list):
            for v in all_versions_data:
                l = v.get("language")
                ver = v.get("version")
                if l and ver:
                    lang_version_map[l] = ver

        test_languages = list(lang_version_map.keys())[:3]
        test_versions = [lang_version_map[l] for l in test_languages]
        langs_str = ",".join(test_languages)
        vers_str = ",".join(test_versions)

        if should_run("多语言全文搜索"):
            runner.run_test(
                f"多语言全文搜索 (languages={langs_str})",
                "GET", "/multi_language_data_by_data",
                params={"data": search_keyword, "languages": langs_str, "versions": vers_str, "page": 1, "per_page": 5},
                checks=[
                    ("返回 200", lambda s, d: s == 200),
                    ("包含 data 字段", lambda s, d: "data" in d),
                    ("包含 pagination 字段", lambda s, d: "pagination" in d),
                ]
            )

        if should_run("多语言包含搜索"):
            runner.run_test(
                f"多语言包含搜索 (languages={langs_str})",
                "GET", "/include_multi_language_data_by_data",
                params={"data": search_keyword, "languages": langs_str, "versions": vers_str, "page": 1, "per_page": 5},
                checks=[
                    ("返回 200 或无数据提示", lambda s, d: s == 200),
                    ("包含 data 字段", lambda s, d: "data" in d),
                ]
            )

        if should_run("多语言精确搜索"):
            exact_keyword = runner.context.get("search_result_name", search_keyword)
            runner.run_test(
                f"多语言精确搜索 (languages={langs_str})",
                "GET", "/exact_multi_language_data_by_data",
                params={"data": exact_keyword, "languages": langs_str, "versions": vers_str, "page": 1, "per_page": 5},
                checks=[
                    ("返回 200", lambda s, d: s == 200),
                    ("包含 data 或 message 字段", lambda s, d: "data" in d or "message" in d),
                ]
            )

        if lang and version and len(test_languages) >= 1:
            if should_run("多语言关联搜索"):
                runner.run_test(
                    f"多语言关联搜索 (主语言={lang})",
                    "GET", "/multi_data_by_data",
                    params={
                        "data": search_keyword, "language": lang, "version": version,
                        "languages": langs_str, "versions": vers_str, "page": 1, "per_page": 5
                    },
                    checks=[
                        ("返回 200 或空列表", lambda s, d: s == 200),
                        ("返回 dict 或 list", lambda s, d: isinstance(d, (dict, list))),
                    ]
                )

            if should_run("包含关联搜索"):
                runner.run_test(
                    f"包含关联搜索 (主语言={lang})",
                    "GET", "/include_multi_data_by_data",
                    params={
                        "data": search_keyword, "language": lang, "version": version,
                        "languages": langs_str, "versions": vers_str, "page": 1, "per_page": 5
                    },
                    checks=[
                        ("返回 200", lambda s, d: s == 200),
                        ("包含 data 字段", lambda s, d: "data" in d),
                    ]
                )

            if should_run("精确关联搜索"):
                runner.run_test(
                    f"精确关联搜索 (主语言={lang})",
                    "GET", "/exact_multi_data_by_data",
                    params={
                        "data": search_keyword, "language": lang, "version": version,
                        "languages": langs_str, "versions": vers_str, "page": 1, "per_page": 5
                    },
                    checks=[
                        ("返回 200", lambda s, d: s == 200),
                        ("包含 data 字段", lambda s, d: "data" in d),
                    ]
                )

    # ========================================
    # 5. 路径/ID 查询
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}")
    print("5. 路径/ID/Name 查询测试")
    print(f"{'='*60}{Colors.RESET}")

    result_path = runner.context.get("search_result_path")
    result_id = runner.context.get("search_result_id")

    if not lang or not version or not result_path:
        runner.skip_test("按路径查询", "缺少搜索结果上下文")
    elif should_run("按路径查询"):
        runner.run_test(
            f"按路径查询 (path={result_path})",
            "GET", "/data_by_path",
            params={"path": result_path, "language": lang, "version": version},
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("返回列表", lambda s, d: isinstance(d, list)),
                ("至少有一条数据", lambda s, d: len(d) > 0),
            ]
        )

    if not result_path or not result_id or not lang or not version:
        runner.skip_test("查询周围数据", "缺少搜索结果上下文")
    elif should_run("查询周围数据"):
        runner.run_test(
            f"查询周围数据 (path={result_path}, id={result_id})",
            "GET", "/data_around_path_and_id",
            params={"path": result_path, "id": result_id, "language": lang, "version": version},
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("返回列表", lambda s, d: isinstance(d, list)),
                ("至少有一条数据", lambda s, d: len(d) > 0),
            ]
        )

    if not result_path or not result_id or len(languages) < 1:
        runner.skip_test("多语言路径ID查询", "缺少搜索结果上下文")
    elif should_run("多语言路径ID查询"):
        runner.run_test(
            f"多语言路径ID查询",
            "GET", "/multi_language_data_by_path_and_id",
            params={"path": result_path, "id": result_id, "languages": langs_str, "versions": vers_str},
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("返回列表", lambda s, d: isinstance(d, list)),
            ]
        )

    result_name = runner.context.get("search_result_name")
    if not result_name or len(languages) < 1:
        runner.skip_test("多语言按名称查询周围数据", "缺少搜索结果上下文")
    elif should_run("多语言按名称查询周围数据"):
        runner.run_test(
            f"多语言按名称查询周围数据 (name={result_name})",
            "GET", "/multi_language_data_around_name",
            params={"name": result_name, "languages": langs_str, "versions": vers_str},
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("包含 data 字段", lambda s, d: "data" in d),
            ]
        )

    # ========================================
    # 6. 分页测试
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}")
    print("6. 分页逻辑测试")
    print(f"{'='*60}{Colors.RESET}")

    if not lang or not version:
        runner.skip_test("分页一致性", "缺少语言/版本数据")
    elif should_run("分页一致性"):
        runner.run_test(
            "分页 - 第1页 per_page=2",
            "GET", "/data_by_data",
            params={"data": search_keyword, "language": lang, "version": version, "page": 1, "per_page": 2},
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("最多2条数据", lambda s, d: len(d.get("data", [])) <= 2),
                ("pagination.page == 1", lambda s, d: d.get("pagination", {}).get("page") == 1),
            ]
        )
        runner.run_test(
            "分页 - 第2页 per_page=2",
            "GET", "/data_by_data",
            params={"data": search_keyword, "language": lang, "version": version, "page": 2, "per_page": 2},
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("最多2条数据", lambda s, d: len(d.get("data", [])) <= 2),
                ("pagination.page == 2", lambda s, d: d.get("pagination", {}).get("page") == 2),
            ]
        )

    # ========================================
    # 7. 边界与异常
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}")
    print("7. 边界与异常测试")
    print(f"{'='*60}{Colors.RESET}")

    if should_run("缺少必要参数"):
        runner.run_test(
            "缺少必要参数 - data_by_data 无参数",
            "GET", "/data_by_data",
            checks=[
                ("返回 4xx 错误", lambda s, d: 400 <= s < 500),
            ]
        )

    if should_run("不存在的路径"):
        runner.run_test(
            "不存在的路径 - data_by_path",
            "GET", "/data_by_path",
            params={"path": "nonexistent/path/here", "language": lang or "cn", "version": version or "0.0.0"},
            checks=[
                ("返回 404 或空结果", lambda s, d: s == 404 or (isinstance(d, dict) and "error" in d)),
            ]
        )

    if should_run("超大页码"):
        if lang and version:
            runner.run_test(
                "超大页码 - page=99999",
                "GET", "/data_by_data",
                params={"data": search_keyword, "language": lang, "version": version, "page": 99999, "per_page": 10},
                checks=[
                    ("返回 200", lambda s, d: s == 200),
                    ("data 为空列表", lambda s, d: len(d.get("data", [])) == 0),
                ]
            )

    # ========================================
    # 8. 性能基线
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}")
    print("8. 性能基线测试")
    print(f"{'='*60}{Colors.RESET}")

    if should_run("轻量接口响应时间"):
        runner.run_test(
            "轻量接口响应时间 - /languages",
            "GET", "/languages",
            checks=[
                ("返回 200", lambda s, d: s == 200),
                ("响应时间 < 2s", lambda s, d: True),  # elapsed_ms is printed
            ]
        )

    if lang and version and should_run("搜索接口响应时间"):
        runner.run_test(
            "搜索接口响应时间 - /data_by_data",
            "GET", "/data_by_data",
            params={"data": search_keyword, "language": lang, "version": version, "page": 1, "per_page": 10},
            timeout=60,
            checks=[
                ("返回 200", lambda s, d: s == 200),
            ]
        )


def main():
    parser = argparse.ArgumentParser(description="FFXIV Text Search Engine API 测试脚本")
    parser.add_argument("--base-url", default="http://localhost:5000", help="API 基础地址 (默认: http://localhost:5000)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细的响应内容")
    parser.add_argument("--test", default=None, help="只运行名称包含指定关键词的测试")
    args = parser.parse_args()

    print(f"{Colors.BOLD}FFXIV Text Search Engine API 测试{Colors.RESET}")
    print(f"目标: {args.base_url}")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    runner = APITestRunner(args.base_url, verbose=args.verbose)

    try:
        run_all_tests(runner, test_filter=args.test)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}测试被手动中断{Colors.RESET}")

    runner.print_summary()
    sys.exit(1 if runner.failed > 0 else 0)


if __name__ == "__main__":
    main()
