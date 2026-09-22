import requests


v1_year = {"11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"}
v1_week = {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52"}
v1_num = {"a", "b", "c", "d", "e"}
v1_release_num1 = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"}
v1_release_num2 = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"}
v2_year = {"26", "27", "28", "29", "30", "31", "32", "33", "34", "35"}
v2_season = {"1", "2", "3", "4"}
v2_hotfix = {"1", "2", "3", "4", "5", "6", "7", "8"}
dev_type_order = {"snapshot": 0, "pre": 1, "rc": 2}


def is_regular_version(version_name):
    """
    返回版本类型
    - False：非常规版本，通常为愚人节版本
    - "v1"：2011-2025的版本
    - "v2"：2026+的版本
    
    来自main.get_version_type()
    """
    version_type_parts = version_name.split("-")
    version_release_parts = version_type_parts[0].split(".")
    
    # v1
    if len(version_name) == 6:
        if version_name == "15w14a":
            return False
        year_part = version_name[0:2]
        w_part = version_name[2]
        week_part = version_name[3:5]
        num_part = version_name[5]
        if year_part in v1_year and w_part == "w" and week_part in v1_week and num_part in v1_num:
            return "v1"
    if len(version_release_parts) == 2:
        if version_release_parts[0] == "1" and version_release_parts[1] in v1_release_num1:
            return "v1"
    if len(version_release_parts) == 3:
        if version_release_parts[0] == "1" and version_release_parts[1] in v1_release_num1 and version_release_parts[2] in v1_release_num2:
            return "v1"

    # v1/v2
    if len(version_type_parts) > 1:
        if "pre" in version_type_parts[1] or "rc" in version_type_parts[1]:
            if len(version_type_parts) == 2:
                return "v1"
            if len(version_type_parts) == 3:
                return "v2"
        if version_type_parts[1] == "snapshot":
            return "v2"
    
    # v2
    if len(version_release_parts) == 2:
        if version_release_parts[0] in v2_year and version_release_parts[1] in v2_season:
            return "v2"
    if len(version_release_parts) == 3:
        if version_release_parts[0] in v2_year and version_release_parts[1] in v2_season and version_release_parts[2] in v2_hotfix:
            return "v2"
    
    return False


def get_last_release_and_dev():
    """
    返回最新正式版和最新开发版
    
    如果最新开发版是非常规版本，则返回逻辑顺序上最新的开发版
    """
    response = requests.get("https://piston-meta.mojang.com/mc/game/version_manifest.json")
    response.raise_for_status()
    version_latest = response.json()["latest"]
    last_release = version_latest["release"]
    last_dev = version_latest["snapshot"]
    if is_regular_version(last_dev):
        return last_release, last_dev

    version_list = response.json()["versions"]
    last_release_tuple = tuple(int(x) for x in last_release.split("."))
    last_release_tuple.append(0) if len(last_release_tuple) == 2 else None
    for version in version_list:
        if version["id"] == last_dev:
            continue
        version_release_tuple = tuple(int(x) for x in version["id"].split("-")[0].split("."))
        if version_release_tuple >= last_release_tuple:
            last_dev = version["id"]
            break
    return last_release, last_dev


def mojira_v_to_manifest_v(version_name):
    """
    将mojira的版本号转换为manifest的版本号

    如果正式版部分被识别为v1，直接返回正式版
    """
    if version_name.startswith("Minecraft "):
        version_name = version_name[10:]
    version_release = version_name.split(" ")[0]
    if is_regular_version(version_release) == "v1":
        return version_release
    version_name = version_name.replace(" Pre-Release ", "-pre-")
    version_name = version_name.replace(" Release Candidate ", "-rc-")
    return version_name


def cmp_version(ver_cmp, ver_base):
    """
    按版本号比较先后顺序
    - -1：ver_cmp在ver_base之前发布
    - 0：ver_cmp = ver_base
    - 1：ver_cmp在ver_base之后发布

    如果影响版本为v1，因查询版本应为v2，直接返回-1

    取出影响版本和查询版本的正式版，不相等返回相应值

    如果一个是正式版一个是开发版，则开发版<正式版

    都是开发版，则根据ver_parts[1]比较

    ver_parts[1]相同，则根据ver_parts[2]比较
    """
    if ver_cmp == ver_base:
        return 0

    if is_regular_version(ver_cmp) == "v1":
        return -1

    cmp_parts = ver_cmp.split("-")
    base_parts = ver_base.split("-")
    cmp_release_parts = cmp_parts[0].split(".")
    base_release_parts = base_parts[0].split(".")
    cmp_release_parts.append("0") if len(cmp_release_parts) == 2 else None
    base_release_parts.append("0") if len(base_release_parts) == 2 else None
    cmp_release_tuple = tuple(int(x) for x in cmp_release_parts)
    base_release_tuple = tuple(int(x) for x in base_release_parts)
    if cmp_release_tuple < base_release_tuple:
        return -1
    elif cmp_release_tuple > base_release_tuple:
        return 1

    if len(cmp_parts) < len(base_parts):
        return 1
    elif len(cmp_parts) > len(base_parts):
        return -1

    cmp_dev_type = dev_type_order[cmp_parts[1]]
    base_dev_type = dev_type_order[base_parts[1]]
    if cmp_dev_type < base_dev_type:
        return -1
    elif cmp_dev_type > base_dev_type:
        return 1

    cmp_dev_num = int(cmp_parts[2])
    base_dev_num = int(base_parts[2])
    if cmp_dev_num < base_dev_num:
        return -1
    elif cmp_dev_num > base_dev_num:
        return 1


raw_issue_data = []

url = "https://bugs.mojang.com/api/jql-search-post"
query = {
    "advanced": True,
    "search": 'fixVersion = "Future Update"',
    "project": "MC",
    "isForge": False,
    "sortField": "created",
    "sortAsc": False,
    "filter": "all",
    "page": 0,
    "maxResults": 25,
    "workspaceId": "",
}
while True:
    print(f'正在获取第{query["page"] + 1}页数据')
    response = requests.post(url, json=query)
    response.raise_for_status()
    cur_data = response.json()
    raw_issue_data.extend(cur_data["issues"])
    if cur_data["isLast"]:
        break
    query["page"] += 1

if not raw_issue_data:
    print('没有修复版本为Future Update的漏洞')
else:
    print(f'找到{len(raw_issue_data)}个漏洞')

fixes_old = []
fixes_dev = []
fixes_prev = []
last_release, last_dev = get_last_release_and_dev()

# 未来可能会做细化热修复更新修复漏洞的功能
for raw_issue in reversed(raw_issue_data):
    key = raw_issue["key"].split("-")[1]
    title = raw_issue["fields"]["summary"]
    # 偷个懒
    if int(key) < 300000:
        fixes_old.append((key, title))
        continue
    # 如果最新版是正式版，所有漏洞归为old
    if last_release == last_dev:
        fixes_old.append((key, title))
        continue
    
    versions = [mojira_v_to_manifest_v(v["name"]) for v in raw_issue["fields"]["versions"]]
    oldest_version = None
    for version in versions:
        if is_regular_version(version) == "v1":
            oldest_version = version
            break

        if oldest_version is None or cmp_version(version, oldest_version) < 0:
            oldest_version = version

    # 漏洞影响版本包含最新正式版及之前的版本，归为old
    if cmp_version(oldest_version, last_release) <= 0:
        fixes_old.append((key, title))
    # 漏洞影响版本包含最新开发版，归为prev
    elif cmp_version(oldest_version, last_dev) == 0:
        fixes_prev.append((key, title))
    # 其他漏洞归为dev
    else:
        fixes_dev.append((key, title))

with open("fixes.txt", "a", encoding="utf-8") as f:
    print('正在写入：')
    if fixes_old:
        f.write("|;old\n")
        for key, title in fixes_old:
            f.write(f"|{key}|{title}\n")
    print(f'|;old：{len(fixes_old)}个')
    if fixes_dev:
        f.write("|;dev\n")
        for key, title in fixes_dev:
            f.write(f"|{key}|{title}\n")
    print(f'|;dev：{len(fixes_dev)}个')
    if fixes_prev:
        f.write("|;prev\n")
        for key, title in fixes_prev:
            f.write(f"|{key}|{title}\n")
    print(f'|;prev：{len(fixes_prev)}个')
    f.write("\n")
