import datetime
import json
import random

import sys

import time

import requests
from playsound3 import playsound
from winotify import Notification

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
ARTICLE_FEED_URL = "https://www.minecraft.net/content/minecraftnet/language-masters/en-us/jcr:content/root/container/image_grid_a_copy_64.articles.page-1.json"  # from https://github.com/Teahouse-Studios/akari-bot/blob/51ec0995fd8e3eb0ab962abe157ab1badf1d13f0/modules/minecraft_news/__init__.py#L65
WIKI_BASE_URL = "https://zh.minecraft.wiki/w/"
sound_files = [
    "warn1.mp3",
    "warn2.mp3",
    "warn3.mp3",
]

def get_json(url):
    try:
        response = session.get(url)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        toast_notification("网络请求出现异常", False)
        print(f"网络请求出现异常，内容为{e}")
        input("按回车键退出")
        sys.exit(1)


def get_json_conditional(url):
    try:
        headers = {}
        etag = etag_cache.get(url)
        if etag:
            headers["If-None-Match"] = etag

        response = session.get(url, headers=headers)

        if response.status_code == 304:
            return None, True

        response.raise_for_status()

        new_etag = response.headers.get("ETag")
        if new_etag:
            etag_cache[url] = new_etag

        return response.json(), False

    except requests.exceptions.RequestException as e:
        toast_notification("网络请求出现异常", False)
        print(f"网络请求出现异常，内容为{e}")
        input("按回车键退出")
        sys.exit(1)


def toast_notification(msg_str, doplaysound=True):  # 播放音效并产生弹窗通知
    if doplaysound:
        selected_sound = random.choice(sound_files)
        playsound(selected_sound, block=False)

    toast = Notification(
        app_id="mcw-snapshot-tools",
        title="",
        msg=msg_str
    )
    toast.show()


def check_new_version(selected_version):  # 检测新版本发布
    manifest_json, _ = get_json_conditional(MANIFEST_URL)
    latest_snapshot = manifest_json["latest"]["snapshot"]
    latest_release = manifest_json["latest"]["release"]

    if selected_version != "":
        versions = manifest_json["versions"]
        for i, version in enumerate(versions):
            if version["id"] == selected_version:
                return selected_version, versions[i:]

        print("未找到版本，请检查输入是否正确")
        input("按回车键退出")
        sys.exit(1)

    # article_json, _ = get_json_conditional(ARTICLE_FEED_URL)

    while True:
        time.sleep(interval)
        cur_manifest_json, not_modified = get_json_conditional(MANIFEST_URL)
        if not_modified:
            continue

        cur_latest_snapshot = cur_manifest_json["latest"]["snapshot"]
        cur_latest_release = cur_manifest_json["latest"]["release"]
        if cur_latest_snapshot != latest_snapshot:
            return cur_latest_snapshot, cur_manifest_json["versions"]
        if cur_latest_release != latest_release:
            return cur_latest_release, cur_manifest_json["versions"]

        '''
        检测官网新文章，似乎用处不大
        cur_article_json, not_modified = get_json_conditional(ARTICLE_FEED_URL)
        if not_modified:
            continue

        if cur_article_json != article_json:
            current_year = time.strftime("%y")
            article_url = cur_article_json["article_grid"][0]["article_url"]
            title = cur_article_json["article_grid"][0]["title"]
            if any(x in article_url for x in [f"minecraft-snapshot-{current_year}w", "-pre-release-", "-release-candidate-", "minecraft-java-edition-1-"]):
                toast_notification(f"Minecraft官网发布了新的文章：\n{title}\n请重启程序以尝试获取新版本json", False)
                print(f"Minecraft官网发布了新的文章：{title}，请重启程序以尝试获取新版本json")
                input("按回车键退出")
                sys.exit(1)
            else:
                article_json = cur_article_json
                continue
        '''


def get_version_type(version_name):  # 返回版本类型
    v1_year = ["11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"]
    v2_year = ["26", "27", "28", "29", "30", "31", "32", "33", "34", "35"]
    v2_num = ["1", "2", "3", "4"]

    if version_name in {f"{y}.{n}" for y in v2_year for n in v2_num}:
        return "Release"
    if "-snapshot-" in version_name:
        return "Snapshot"
    elif "-pre-" in version_name:
        return "Pre-release"
    elif "-rc-" in version_name:
        return "Release Candidate"

    return "N/A"


def get_zh_version_type(version_type):  # 返回版本类型的中文名称
    if version_type == "Pre-release":
        return "预发布版"
    elif version_type == "Release Candidate":
        return "发布候选版本"
    elif version_type == "Release":
        return "正式版"
    elif version_type == "Snapshot":
        return "快照"
    else:
        return "（未指定版本类型）"


def get_release_type(version_name):  # 返回正式版的更新类型
    parts = version_name.split('.')
    if len(parts) == 2:
        return "小更新"
    elif len(parts) == 3:
        return "热修复更新"
    else:
        return "更新"


def get_timestamp(timestamp_str):
    dt = datetime.datetime.fromisoformat(timestamp_str)
    dt_8 = dt + datetime.timedelta(hours=8)
    return dt, dt_8


def get_mojira_version(version_name):  # 返回Mojira形式的版本号
    version_type = get_version_type(version_name)
    if version_type == "Snapshot":
        parts = version_name.split('-')
        return f"{parts[0]} Snapshot {parts[2]}"
    
    return version_name  # 其余类型暂无实际案例


def get_article(version_name):  # 返回官网博文链接
    version_type = get_version_type(version_name)
    if version_type == "Snapshot":
        url_name = version_name.replace('.', '-')
        title_name = version_name.replace('-', ' ').replace('snapshot', 'Snapshot')
        return f"""article|minecraft-{url_name}|Minecraft {title_name}"""
    
    return ""  # 其余类型暂无实际案例


def get_page_url(version_name):  # 返回页面链接
    return WIKI_BASE_URL + "Java%E7%89%88" + version_name


with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    user_agent = config["user_agent"]
    interval = int(config["interval"])

session = requests.Session()
session.headers.update({"User-Agent": user_agent})

etag_cache = {}

selected_version = input("输入一个版本号，留空则自动检测最新版本：")

new_version, all_version_info = check_new_version(selected_version)
version_type = get_version_type(new_version)
zh_version_type = get_zh_version_type(version_type)
release_time = all_version_info[0]["releaseTime"]
release_dt, release_dt_8 = get_timestamp(release_time)
release_dt_date = f"{release_dt.year}年{release_dt.month}月{release_dt.day}日"

version_json_type = all_version_info[0]["type"]
version_json_url = all_version_info[0]["url"]
version_json = get_json(version_json_url)
version_json_downloads = version_json["downloads"]

if selected_version == "":
    toast_notification(f"{zh_version_type}{new_version}已发布。")
print(f"{zh_version_type}{new_version}已发布。")
print(f"发布时间：{release_dt_8.strftime("%Y年%m月%d日%H:%M:%S（北京时间）")}")

version_page_url = get_page_url(new_version)

print(f"新页面链接：{version_page_url}?action=edit")
print("内容为：")
print("----")

parts = new_version.split('-')

parent = ""
prevparent = ""
prev = ""
next = ""
nextparent = ""

last_release_found = False
last_snapshot_found = False
for version in all_version_info[1:]:
    if version["type"] == "release" and not last_release_found:
        last_release = version["id"]
        last_release_found = True
    if version["type"] == "snapshot" and not last_snapshot_found:
        last_snapshot = version["id"]
        last_snapshot_found = True
    if last_release_found and last_snapshot_found:
        break

if version_type == "Release":
    prev = last_release
else:
    parent = parts[0]
    prevparent = last_release
    prev = last_snapshot

if version_type in ["Release", "N/A"]:
    type_num = 0
else:
    type_num = int(parts[2])

if all_version_info[1]["type"] == "release":
    is_initial_snapshot = True
else:
    is_initial_snapshot = False

if version_type == "Release":
    release_type = get_release_type(parts[0])

version_page_content = f"""{{{{wip}}}}
{{{{Infobox version
|title={new_version}
|image={new_version}.png
|image2=Java Edition {new_version} Simplified.png\\Java Edition {new_version} Traditional.png\\Java Edition {new_version} Traditional HK.png
|edition=Java"""
version_page_content += """""" if version_type in ["N/A", "Release"] else f"""
|type={version_type}"""
version_page_content += f"""
|date={release_dt_date}
|jsonhash={version_json_url[len("https://piston-meta.mojang.com/v1/packages/"):].split('/')[0]}
|clienthash={version_json_downloads["client"]["sha1"]}"""
version_page_content += f"""
|serverhash={version_json_downloads["server"]["sha1"]}"""
version_page_content += """""" if version_type in ["N/A", "Release"] else f"""
|parent={parent}"""
version_page_content += f"""
|prevparent={prevparent}
|prev="""
version_page_content += f"""{prev}""" if not is_initial_snapshot else """"""
version_page_content += f"""
|next=
|nextparent=
}}}}"""
version_page_content += """<onlyinclude>""" if version_type not in ["Release", "N/A"] else """"""
version_page_content += f"""

'''{new_version}'''是"""
if version_type not in ["Release", "N/A"]:
    version_page_content += f"""[[Java版{parent}]]的"""
    version_page_content += f"""第{type_num}""" if type_num > 1 else """首"""
    version_page_content += f"""个{zh_version_type}，"""
else:
    version_page_content += f"""{{{{el|je}}}}的一次{release_type}，"""

version_page_content += f"""发布于{release_dt_date}<ref>"""
version_page_content += """{{"""
version_page_content += f"""{get_article(new_version)}"""
version_page_content += f"""|{release_dt.strftime("%b %d, %Y")}"""
version_page_content += """}}</ref>，修复了一些漏洞。"""

if version_type not in ["Release", "N/A"]:
    version_page_content += """

== 修复 ==
{{fixes|fixedin="""
    version_page_content += get_mojira_version(new_version)
    version_page_content += """|showdesc=1|new=1

}}</onlyinclude>

== 参考 ==
{{Reflist}}

== 导航 ==
{{Navbox Java Edition versions|"""
    version_page_content += f"""20{parts[0].split('.')[0]}"""
    version_page_content += """}}"""

print(version_page_content)
print("----")

print("编辑下面页面：")

if version_type not in ["Release", "N/A"]:
    redirect_page_url = WIKI_BASE_URL + new_version
    print(f"重定向页面：{redirect_page_url}?action=edit，内容为：#REDIRECT [[Java版{new_version}]]")
    if version_type == "Snapshot":
        other_name = new_version.replace("-", "_").replace("snapshot", "Snapshot")
        print(f"重定向页面：{WIKI_BASE_URL}{other_name}?action=edit，内容为：#REDIRECT [[Java版{new_version}]]")
        print(f"重定向页面：{WIKI_BASE_URL}Java%E7%89%88{other_name}?action=edit，内容为：#REDIRECT [[Java版{new_version}]]")

template_version_url = WIKI_BASE_URL + "Template:Version"
print(f"更新版本号：{template_version_url}?action=edit")

if version_type not in ["Release", "N/A"]:
    version_list_page_url = WIKI_BASE_URL + "Java%E7%89%88%E7%89%88%E6%9C%AC%E8%AE%B0%E5%BD%95/%E5%BC%80%E5%8F%91%E7%89%88%E6%9C%AC"
    print(f"添加版本链接：{version_list_page_url}?action=edit")
    navbox_page_url = WIKI_BASE_URL + "Template:Navbox_Java_Edition_versions"
    print(f"添加版本链接：{navbox_page_url}?action=edit")
    if not is_initial_snapshot:
        prev_page_url = get_page_url(prev)
        print(f"在infobox中添加next参数：{prev_page_url}?action=edit")
print("")

if is_initial_snapshot:
    print("这是首个开发版本，编辑下面页面：")
    print(f"新页面链接：{WIKI_BASE_URL}Java%E7%89%88{parent}?action=edit")
    print("内容为：")
    print("----")
    parent_version_page_content = """{{wip}}"""
    parent_version_page_content += f"""
{{{{Infobox version
|title={parent}
|image=<!-- {parent}.png -->
|image2=<!-- Java Edition {parent} Simplified.png\\Java Edition {parent} Traditional.png\\Java Edition {parent} Traditional HK.png -->
|edition=Java
|date=未知 |planned=1
|jsonhash=
|clienthash=
|serverhash=
|prevparent="""
    parent_version_page_content += f"""
|prev={last_release}"""
    parent_version_page_content += f"""
|next=
|nextparent=
}}}}

'''{parent}'''是{{{{el|je}}}}即将到来的一次{get_release_type(parent)}，发布时间待定。"""
    parent_version_page_content += """<ref>{{"""
    parent_version_page_content += f"""{get_article(new_version)}"""
    parent_version_page_content += f"""|{release_dt.strftime("%b %d, %Y")}"""
    parent_version_page_content += """}}</ref>

== 参考 ==
{{Reflist}}

== 导航 ==
{{Navbox Java Edition versions|"""
    parent_version_page_content += f"""20{parent.split('.')[0]}"""
    parent_version_page_content += """}}"""
    print(parent_version_page_content)
    print("----")
    print(f"重定向页面：{WIKI_BASE_URL}{parent}?action=edit，内容为：#REDIRECT [[Java版{parent}]]")
    print(f"在上一正式版页面的infobox中添加next参数：{WIKI_BASE_URL}Java%E7%89%88{last_release}?action=edit")
    print(f"在上一正式版所有开发版本页面的infobox中添加nextparent参数：")

    snapshot_list = []
    flag = False

    # 获取此版本下所有开发版本
    for version in all_version_info:
        if version["id"] == prevparent:
            flag = True
            continue
        if version["type"] == "release" and flag:
            break
        if flag:
            snapshot_list.append(version["id"])

    # 调整为Wiki页面标题
    for i, snapshot in enumerate(snapshot_list):
        print(f"{WIKI_BASE_URL}Java%E7%89%88{snapshot}?action=edit")
    print("")

print("上传5个文件：https://zh.minecraft.wiki/w/Special:BatchUpload")
print("版本宣传图文件名为：")
print(f"{new_version}")
print("版本宣传图，内容为：")
print("----")
print("\n== 许可协议 ==\n{{License Mojang}}\n\n[[Category:截图]]\n[[Category:版本宣传图]]")
print("----")
print("菜单屏幕截图文件名为：")
print(f"Java Edition {new_version} Simplified")
print(f"Java Edition {new_version} Traditional")
print(f"Java Edition {new_version} Traditional HK")
print(f"Java Edition {new_version} Literary")
print("菜单屏幕截图，内容为：")
print("----")
print("== 摘要 ==\n{{Other translation files}}\n\n== 许可协议 ==\n{{License Mojang}}\n\n[[Category:主菜单截图]]")
print("----")
print(f"菜单屏幕截图重定向：{WIKI_BASE_URL}File:Java_Edition_{new_version}.png?action=edit，内容为：{{{{Other translation files}}}}")
print("")

print(f"客户端jar文件内的version.json -> protocol_version：{WIKI_BASE_URL}Module:Protocol_version/Versions?action=edit")

input("按回车键退出")
sys.exit(1)
