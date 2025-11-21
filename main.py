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

        article_code = '''
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
                continue'''


def get_version_type(version_name):  # 返回版本类型
    current_year = time.strftime("%y")
    if "1." in version_name:
        if "-pre" in version_name:
            return "Pre-release"
        elif "-rc" in version_name:
            return "Release Candidate"
        else:
            return "Release"
    elif f"{current_year}w" in version_name:
        return "Snapshot"
    else:
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


def get_timestamp(timestamp_str):
    dt = datetime.datetime.fromisoformat(timestamp_str)
    dt_8 = dt + datetime.timedelta(hours=8)
    return dt, dt_8


def get_mojira_version(version_name):  # 返回Mojira形式的版本号
    version_type = get_version_type(version_name)
    if version_type == "Pre-release":
        parts = version_name.split('-')
        parent = parts[0]
        pre_number = parts[1].replace("pre", "")
        return f"""{parent} Pre-Release {pre_number}"""
    elif version_type == "Release Candidate":
        parts = version_name.split('-')
        parent = parts[0]
        rc_number = parts[1].replace("rc", "")
        return f"""{parent} Release Candidate {rc_number}"""


def get_article(version_name):  # 返回官网博文链接
    left_str = "{{"
    version_type = get_version_type(version_name)
    if version_type == "Pre-release":
        parts = version_name.split('-')
        parent = parts[0]
        pre_number = parts[1].replace("pre", "")
        return left_str + f"""article|minecraft-{parent.replace(".", "-")}-pre-release-{pre_number}|Minecraft {parent} Pre-Release {pre_number}"""
    elif version_type == "Release Candidate":
        parts = version_name.split('-')
        parent = parts[0]
        rc_number = parts[1].replace("rc", "")
        return left_str + f"""article|minecraft-{parent.replace(".", "-")}-release-candidate-{rc_number}|Minecraft {parent} Release Candidate {rc_number}"""
    elif version_type == "Release":
        return left_str + f"""article|minecraft-java-edition-{version_name.replace(".", "-")}|Minecraft Java Edition {version_name}"""
    elif version_type == "Snapshot":
        return left_str + f"""snap|{version_name}"""
    else:
        return ""


def get_page_url(version_name):  # 返回页面链接
    version_type = get_version_type(version_name)
    if version_type == "Snapshot":
        version_page_name = version_name
    else:
        version_page_name = "Java%E7%89%88" + version_name

    version_page_url = WIKI_BASE_URL + version_page_name
    return version_page_url


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
is_initial_snapshot = False

if selected_version == "":
    toast_notification(f"{zh_version_type}{new_version}已发布。")
print(f"{zh_version_type}{new_version}已发布。")
print(f"发布时间：{release_dt_8.strftime("%Y年%m月%d日%H:%M:%S（北京时间）")}")

parent_is_predicted = True
if version_type in ["Pre-release", "Release Candidate"]:
    parent = new_version.split('-')[0]
    parent_is_predicted = False
elif version_type == "Release":
    parent = ""
    parent_is_predicted = False

if parent_is_predicted == True:
    parent = input("正式版版本号未知，请预测：")

version_page_url = get_page_url(new_version)

print(f"新页面链接：{version_page_url}?action=edit")
print("内容为：")
print("----")

version_json_url = all_version_info[0]["url"]
version_json = get_json(version_json_url)
version_json_downloads = version_json["downloads"]

previous_versions = []  # 用于第几个同类开发版本的计数
prevparent = "" if version_type != "Release" else "1.21" # 1.21为硬编码

version_json_type = all_version_info[0]["type"]
for version in all_version_info[1:]:
    if version["type"] == version_json_type:
        prev = version["id"]
        break

if version_type not in ["Release", "N/A"]:
    if all_version_info[1]["type"] == "release":
        is_initial_snapshot = True

    for version in all_version_info:
        if get_version_type(version["id"]) == version_type:
            previous_versions.append(version)
        elif get_version_type(version["id"]) == "Release":
            prevparent = version["id"]
            break

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
|clientmap={version_json_downloads["client_mappings"]["sha1"]}""" if version_json_downloads["client_mappings"] else """"""
version_page_content += f"""
|serverhash={version_json_downloads["server"]["sha1"]}"""
version_page_content += f"""
|servermap={version_json_downloads["server_mappings"]["sha1"]}""" if version_json_downloads["server_mappings"] else """"""
version_page_content += f"""
|parent={parent}
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
    version_page_content += f"""[[Java版{parent}]]"""
    version_page_content += """{{conjecture tag}}的""" if parent_is_predicted else """的"""
    version_page_content += f"""第{len(previous_versions)}""" if len(previous_versions) > 1 else """首"""
    version_page_content += f"""个{zh_version_type}，"""
else:
    version_page_content += """{{el|je}}的一次次要更新，"""

version_page_content += f"""发布于{release_dt_date}<ref>"""
version_page_content += f"""{get_article(new_version)}"""
version_page_content += f"""|{release_dt.strftime("%b %d, %Y")}"""
version_page_content += """}}</ref>，修复了一些漏洞。"""
version_page_content += """

== 修复 ==
{{fixes|fixedin="""
version_page_content += f"""{get_mojira_version(new_version)}""" if version_type in ["Pre-release", "Release Candidate"] else f"""{new_version}"""
version_page_content += """|showdesc=1|new=1

}}</onlyinclude>

== 参考 ==
{{Reflist}}

== 导航 ==
{{Navbox Java Edition versions|1.21}}""" if version_type not in ["Release", "N/A"] else """"""

print(version_page_content)
print("----")

print("编辑下面页面：")

if version_type in ["Pre-release", "Release Candidate"]:
    redirect_page_url = WIKI_BASE_URL + new_version
    print(f"重定向页面：{redirect_page_url}?action=edit，内容为：#REDIRECT [[Java版{new_version}]]")
    disambig_page_url = WIKI_BASE_URL + parent
    print(f"添加版本链接：https://zh.minecraft.wiki/w/1.21?action=edit")  # 1.21为硬编码

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
    parent_version_page_content = """{{conjecture}}
{{wip}}""" if parent_is_predicted else """{{wip}}"""
    parent_version_page_content += f"""
{{{{Infobox version
|title={parent}
|image=<!-- {parent}.png -->
|image2=<!-- Java Edition {parent} Simplified.png\\Java Edition {parent} Traditional.png\\Java Edition {parent} Traditional HK.png -->
|edition=Java
|date=未知 |planned=1
|jsonhash=
|clienthash=
|clientmap=
|serverhash=
|servermap="""
    parent_version_page_content += f"""
|prevparent=1.21"""  # 1.21为硬编码
    parent_version_page_content += f"""
|prev={prevparent}"""  # 借用开发版本的参数
    parent_version_page_content += f"""
|next=
|nextparent=
}}}}

'''{parent}'''是{{{{el|je}}}}的一次次要更新，发布时间待定。<ref>"""
    parent_version_page_content += f"""{get_article(new_version)}"""
    parent_version_page_content += f"""|{release_dt.strftime("%b %d, %Y")}"""
    parent_version_page_content += """}}</ref>。

== 参考 ==
{{Reflist}}

== 导航 ==
{{Navbox Java Edition versions|1.21}}"""
    print(parent_version_page_content)
    print("----")
    print(f"重定向页面：{WIKI_BASE_URL}{parent}?action=edit，内容为：#REDIRECT [[Java版{parent}]]或者如果基岩版有相同页面，则为#REDIRECT [[1.21]]")  # 1.21为硬编码
    print(f"在上一正式版页面的infobox中添加next参数：{WIKI_BASE_URL}{prevparent}?action=edit")
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
        if "-pre" in snapshot or "-rc" in snapshot:
            snapshot_list[i] = "Java版" + snapshot
        print(f"{WIKI_BASE_URL}{snapshot}?action=edit")
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
print(f"菜单屏幕截图重定向：{WIKI_BASE_URL}File:Java_Edition_{new_version}.png?action=edit，内容为：#REDIRECT [[File:Java Edition {new_version} Simplified.png]]")
print("")

print(f"客户端jar文件内的version.json -> protocol_version：{WIKI_BASE_URL}Module:Protocol_version/Versions?action=edit")

input("按回车键退出")
sys.exit(1)
