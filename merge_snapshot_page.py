import json
import requests
import sys

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
WIKI_API_URL = "https://zh.minecraft.wiki/api.php"

release = input("输入一个版本号（留空则获取最新版本）：")

with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    user_agent = config["user_agent"]

session = requests.Session()
session.headers.update({"User-Agent": user_agent})

# 获取版本列表
try:
    response = session.get(MANIFEST_URL)
    response.raise_for_status()
    manifest_json = response.json()
except requests.exceptions.RequestException as e:
    print(f"piston-meta.mojang.com网络请求出现异常，内容为{e}")
    input("按回车键退出")
    sys.exit(1)

versions = manifest_json["versions"]

snapshot_list = []
flag = False

# 获取此版本下所有快照
for i, version in enumerate(versions):
    if version["id"] == release:
        flag = True
        continue
    elif release == "" and i == 0:
        flag = True
        if version["type"] == "release":
            continue
    if version["type"] == "release" and flag:
        break
    if flag:
        snapshot_list.append(version["id"])

if snapshot_list == []:
    print("未找到快照，请检查输入是否正确")
    input("按回车键退出")
    sys.exit(1)

print(f"已找到{len(snapshot_list)}个快照")

# 调整为Wiki页面标题
for i, snapshot in enumerate(snapshot_list):
    if "-pre" in snapshot or "-rc" in snapshot:
        snapshot_list[i] = "Java版" + snapshot

page_query_params = {
    "action": "query",
    "format": "json",
    "prop": "revisions",
    "titles": "|".join(snapshot_list),
    "formatversion": 2,
    "rvprop": "content"
}

try:
    response = session.get(WIKI_API_URL, params=page_query_params)
    response.raise_for_status()
    snapshot_page_json = response.json()
except requests.exceptions.RequestException as e:
    print(f"zh.minecraft.wiki网络请求出现异常，内容为{e}")
    input("按回车键退出")
    sys.exit(1)

# 得到所有快照的页面源代码，从旧到新
raw_pages = [
    page["revisions"][0]["content"]
    for page in snapshot_page_json["query"]["pages"]
    if "missing" not in page
]

print("已成功获取所有快照页面内容，正在处理中")
'''
# 临时功能：将API结果保存以便参考
try:
    output_filename = f"{release}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(raw_pages, f, ensure_ascii=False, indent=4)
    print(f"已将内容成功保存到文件：{output_filename}")
except Exception as e:
    print(f"保存文件时出错：{e}")

# 临时功能：加载保存的API结果
try:
    input_filename = "merge_snapshot_page_test.json"
    with open(input_filename, "r", encoding="utf-8") as f:
        raw_pages = json.load(f)
    print(f"已成功加载{len(raw_pages)}个页面。")
except FileNotFoundError:
    print(f"错误：找不到文件{input_filename}。")
    input("按回车键退出")
    sys.exit(1)
except Exception as e:
    print(f"读取文件时出错：{e}")
    input("按回车键退出")
    sys.exit(1)
'''
# 获取{{Undecided translation}}参数列表
ut_text = None
ut_params = set()

for page_content in raw_pages:
    if "{{Undecided translation" in page_content:
        start = page_content.index("{{Undecided translation|") + len("{{Undecided translation|")
        end = page_content.index("}}", start)
        params_str = page_content[start:end]
        param_list = params_str.split('|')
        for param in param_list:
            if param != "":
                ut_params.add(param)

if ut_params:
    sorted_params = sorted(list(ut_params))
    ut_text = "{{Undecided translation|" + "|".join(sorted_params) + "}}"

# 获取页面内容
additions_marker = "== 新内容 =="
changes_marker = "== 更改 =="
fixes_marker = "== 修复 =="
end_marker_list = ["== 参考 ==", "== 导航 ==", "== 你知道吗 ==", "== 注释 ==", "== 画廊 =="]
feature_marker_list = ["=== 方块 ===", "=== 物品 ===", "=== 生物 ===", "=== 非生物实体 ===", "=== 世界生成 ===", "=== 游戏内容 ===", "=== 命令格式 ===", "=== 常规 ==="]
merged_features_data = [
    # 新内容
    [
        {},
        {},
        {},
        {},
        {},
        {},
        {},
        {}
    ],
    # 更改
    [
        {},
        {},
        {},
        {},
        {},
        {},
        {},
        {}
    ]
]
merged_fixes_data = {
    "fixedin": [],
    "beforeVersion": "",
    "showdesc": 1,
    "new": 1,
    "otherissuescount": 0,
    "issues": {},
    "otherissues": {}
}

for i, page_content in enumerate(raw_pages):
    # 分割内容
    additions_index = page_content.find(additions_marker)
    changes_index = page_content.find(changes_marker)
    fixes_index = page_content.find(fixes_marker)

    end_index = -1
    for end_marker in end_marker_list:
        idx = page_content.find(end_marker)
        if idx != -1:
            if end_index == -1 or idx < end_index:
                end_index = idx

    if end_index == -1:
        print(f"{snapshot_list[i]}段落格式不符合格式指导，请检查。")
        input("按回车键退出")
        sys.exit(1)

    if additions_index == -1:
        additions_text = ""
    else:
        additions_end_index = next(x for x in [changes_index, fixes_index, end_index] if x != -1)
        additions_text = page_content[additions_index:additions_end_index].strip()
    if changes_index == -1:
        changes_text = ""
    else:
        changes_end_index = next(x for x in [fixes_index, end_index] if x != -1)
        changes_text = page_content[changes_index:changes_end_index].strip()
    if fixes_index == -1:
        fixes_text = ""
    else:
        fixes_end_index = end_index
        fixes_text = page_content[fixes_index:fixes_end_index].strip()

    # 解析“新内容”部分
    if additions_text:
        feature_indexes = [additions_text.find(feature_marker) for feature_marker in feature_marker_list]
        if not any(index != -1 for index in feature_indexes):
            print(f"{snapshot_list[i]}“新内容”段落不符合格式指导，请检查。")
            input("按回车键退出")
            sys.exit(1)
        
        for j, index in enumerate(feature_indexes):
            if index == -1:
                continue
            else:
                next_indexes = [idx for idx in feature_indexes[j+1:] if idx != -1]
                end_index = next_indexes[0] if next_indexes else len(additions_text)
                raw_text = additions_text[index:end_index].strip()

                # 解析最小段落部分到merged_features_data[0][i]
                lines = raw_text.splitlines()
                current_title = ""
                current_content = []
                for line in lines:
                    if line.startswith(';') and len(line) > 1 and line[1] != ' ':
                        print(f"{snapshot_list[i]}“新内容”段落有假标题不符合格式指导，请检查。")
                        input("按回车键退出")
                        sys.exit(1)

                    if line.startswith('; '):
                        if current_title and current_content:  # 并非首个假标题
                            if current_title in merged_features_data[0][j]:
                                merged_features_data[0][j][current_title].append(current_content)
                            else:
                                merged_features_data[0][j][current_title] = current_content
                        # 获取当前假标题，并重置内容列表
                        current_title = line[2:].strip()
                        current_content = []
                    else:  # 获取内容
                        stripped_line = line.rstrip()  # 要使用rstrip，以免行首表缩进的空格被错误移除
                        if stripped_line:
                            current_content.append(stripped_line)

                # 添加最后一个假标题及其内容
                if current_title and current_content:
                    if current_title in merged_features_data[0][j]:
                        merged_features_data[0][j][current_title].append(current_content)
                    else:
                        merged_features_data[0][j][current_title] = current_content
            
    # 解析“更改”部分
    if changes_text:
        feature_indexes = [changes_text.find(feature_marker) for feature_marker in feature_marker_list]
        if not any(index != -1 for index in feature_indexes):
            print(f"{snapshot_list[i]}“更改”段落不符合格式指导，请检查。")
            input("按回车键退出")
            sys.exit(1)
        
        for j, index in enumerate(feature_indexes):
            if index == -1:
                continue
            else:
                next_indexes = [idx for idx in feature_indexes[j+1:] if idx != -1]
                end_index = next_indexes[0] if next_indexes else len(changes_text)
                raw_text = changes_text[index:end_index].strip()

                # 解析最小段落部分到merged_features_data[1][i]
                lines = raw_text.splitlines()
                current_title = ""
                current_content = []
                for line in lines:
                    if line.startswith(';') and len(line) > 1 and line[1] != ' ':
                        print(f"{snapshot_list[i]}“更改”段落有假标题不符合格式指导，请检查。")
                        input("按回车键退出")
                        sys.exit(1)

                    if line.startswith('; '):
                        if current_title and current_content:  # 并非首个假标题
                            if current_title in merged_features_data[1][j]:  # 之前已经检查过，确定不应该移去“新内容”
                                merged_features_data[1][j][current_title].append(current_content)
                            else:
                                ismoved = False
                                for title in merged_features_data[0][j]:
                                    if current_title == title:
                                        merged_features_data[0][j][current_title].append(current_content)
                                        ismoved = True
                                        break
                                if not ismoved:
                                    merged_features_data[1][j][current_title] = current_content
                        # 获取当前假标题，并重置内容列表
                        current_title = line[2:].strip()
                        current_content = []
                    else:  # 获取内容
                        stripped_line = line.rstrip()  # 要使用rstrip，以免行首表缩进的空格被错误移除
                        if stripped_line:
                            current_content.append(stripped_line)
                
                # 添加最后一个假标题及其内容
                if current_title and current_content:
                    if current_title in merged_features_data[1][j]:  # 之前已经检查过，确定不应该移去“新内容”
                        merged_features_data[1][j][current_title].append(current_content)
                    else:
                        ismoved = False
                        for title in merged_features_data[0][j]:
                            if current_title == title:
                                merged_features_data[0][j][current_title].append(current_content)
                                ismoved = True
                                break
                        if not ismoved:
                            merged_features_data[1][j][current_title] = current_content

    # 解析“修复”部分
    if fixes_text:
        fixes_start_index = fixes_text.find("{{fixes|")
        if fixes_start_index == -1:
            print(f"{snapshot_list[i]}“修复”段落中缺少{{{{fixes}}}}模板，请检查。")
            input("按回车键退出")
            sys.exit(1)

        matches = 0
        for j, char in enumerate(fixes_text[fixes_start_index:]):
            if char == '{':
                matches += 1
            elif char == '}':
                matches -= 1
            if matches == 0:
                fixes_end_index = fixes_start_index + j + 1
                break
        if matches != 0:
            print(f"{snapshot_list[i]}“修复”段落中的{{{{fixes}}}}模板未闭合，请检查。")
            input("按回车键退出")
            sys.exit(1)
            
        fixes_template_text = fixes_text[fixes_start_index:fixes_end_index]
        lines = fixes_template_text.splitlines()
        fixes_params = lines[0]

        # 获取beforeVersion、fixedin和otherissuescount参数
        fixedin_start_index = fixes_params.find("|fixedin=")
        if fixedin_start_index == -1:
            print(f"{snapshot_list[i]}“修复”段落中的{{{{fixes}}}}模板缺少fixedin参数，请检查。")
            input("按回车键退出")
            sys.exit(1)
            
        fixedin_start_index = fixedin_start_index + len("|fixedin=")
        fixedin_end_index = fixes_params.find("|", fixedin_start_index)
        if fixedin_end_index == -1:
            fixedin_value = fixes_params[fixedin_start_index:].strip()
        else:
            fixedin_value = fixes_params[fixedin_start_index:fixedin_end_index].strip()

        if not merged_fixes_data['fixedin']:
            merged_fixes_data['beforeVersion'] = fixedin_value
        merged_fixes_data['fixedin'].append(fixedin_value)

        otherissuescount_value = None
        otherissuescount_start_index = fixes_params.find("|otherissuescount=")
        if otherissuescount_start_index != -1:
            otherissuescount_start_index += len("|otherissuescount=")
            
            # 查找"|"或"}}"
            otherissuescount_end_index = fixes_params.find("|", otherissuescount_start_index)
            if otherissuescount_end_index != -1:
                otherissuescount_value = fixes_params[otherissuescount_start_index:otherissuescount_end_index].strip()
            else:
                otherissuescount_end_index = fixes_params.find("}}", otherissuescount_start_index)
                if otherissuescount_end_index != -1:
                    otherissuescount_value = fixes_params[otherissuescount_start_index:otherissuescount_end_index].strip()
                else:
                    otherissuescount_value = fixes_params[otherissuescount_start_index:].strip()

            if otherissuescount_value:
                merged_fixes_data['otherissuescount'] += int(otherissuescount_value)

        # 获取漏洞列表
        current_title = ""
        skipping = False
        for line in lines:
            if skipping and line.startswith('|;'):
                skipping = False

            if skipping:
                continue

            if line.startswith('|;'):
                category = line[2:].strip()
                if category == 'dev' or category == 'prev':  # 跳过开发版本中的漏洞
                    skipping = True
                    current_title = ""
                    continue
                
                current_title = ";" + category
                if current_title not in merged_fixes_data['issues']:
                    merged_fixes_data['issues'][current_title] = {}
            elif '|' in line and current_title:
                parts = line.split('|', 2)
                bug_id = parts[1].strip()
                bug_desc = parts[2].strip()
                merged_fixes_data['issues'][current_title][bug_id] = bug_desc

        # 解析“其他漏洞”部分
        fixesother_text = fixes_text[fixes_end_index:]
        if fixesother_text.strip() and otherissuescount_value is not None:
            lines = fixesother_text.strip().splitlines()
            current_title = ""
            current_content = []
            for line in lines:
                if line.startswith('; '):
                    if current_title and current_content:
                        if current_title in merged_fixes_data['otherissues']:
                            merged_fixes_data['otherissues'][current_title].extend(current_content)
                        else:
                            merged_fixes_data['otherissues'][current_title] = current_content
                    current_title = line[2:].strip()
                    current_content = []
                else:
                    stripped_line = line.strip()
                    if stripped_line:
                        current_content.append(stripped_line)
            
            if current_title and current_content:
                if current_title in merged_fixes_data['otherissues']:
                    merged_fixes_data['otherissues'][current_title].extend(current_content)
                else:
                    merged_fixes_data['otherissues'][current_title] = current_content

# print(json.dumps(merged_features_data, ensure_ascii=False, indent=4))
# print(json.dumps(merged_fixes_data, ensure_ascii=False, indent=4))

# 打印
print("合并后的页面，内容为：")
print("----")
if ut_text:
    print(ut_text, end='\n\n')

for i, second_level_item in enumerate(merged_features_data):
    if not any(second_level_item):
        continue

    if i == 0:
        print("== 新内容 ==")
    elif i == 1:
        print("== 更改 ==")
    
    for j, third_level_item in enumerate(second_level_item):
        if third_level_item:
            print(feature_marker_list[j])
            for title, content_list in third_level_item.items():
                print(f"; {title}")
                init = [x for x in content_list if not isinstance(x, list)]
                after = [s for sub in content_list if isinstance(sub, list) for s in sub]
                # 打印首批内容
                for line in init:
                    print(line)
                
                # 后续内容手工处理
                if after:
                    print("<!--")
                    for content in after:
                        print(content)
                    print("-->")
                print()

if merged_fixes_data['issues'] or merged_fixes_data['otherissues']:
    print("== 修复 ==")

    fixes_params = [f"fixedin={','.join(merged_fixes_data['fixedin'])}"]
    if len(merged_fixes_data['fixedin']) > 1:
        fixes_params.append(f"beforeVersion={merged_fixes_data['beforeVersion']}")
    
    if merged_fixes_data['issues']:
        fixes_params.extend(["showdesc=1", "new=1"])

    if merged_fixes_data['otherissuescount'] != 0:
        fixes_params.append(f"otherissuescount={merged_fixes_data['otherissuescount']}")

    print("{{fixes|" + '|'.join(fixes_params), end="")

    if merged_fixes_data['issues']:
        print()
        
        def sort_key(k: str):
            if k == ';old':
                return (0,)
            if k.startswith(';1.21.'):
                num_part = k[len(';1.21.'):-len('的漏洞')]
                return (1, int(num_part))
            return (2, k)

        sorted_issues = sorted(merged_fixes_data['issues'].items(), key=lambda item: sort_key(item[0]))

        for category, bugs in sorted_issues:
            print(f"|{category}")
            
            sorted_bugs = sorted(bugs.items(), key=lambda item: int(item[0]))
            
            for bug_id, desc in sorted_bugs:
                print(f"|{bug_id}|{desc}")

    print("}}")

    if merged_fixes_data['otherissues']:
        for title, issues in merged_fixes_data['otherissues'].items():
            print(f"; {title}")
            for issue in issues:
                print(issue)
