import datetime
import json
import random

import sys

import time

import requests
from playsound3 import playsound
from winotify import Notification

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
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


def check_new_version():
    manifest_json = get_json(MANIFEST_URL)
    latest_snapshot = manifest_json["latest"]["snapshot"]
    latest_release = manifest_json["latest"]["release"]

    #return "25w37a", manifest_json["versions"]  #调试内容

    while True:
        time.sleep(interval)
        cur_manifest_json = get_json(MANIFEST_URL)
        cur_latest_snapshot = cur_manifest_json["latest"]["snapshot"]
        cur_latest_release = cur_manifest_json["latest"]["release"]
        if cur_latest_snapshot != latest_snapshot:
            return cur_latest_snapshot, cur_manifest_json["versions"]
        if cur_latest_release != latest_release:
            return cur_latest_release, cur_manifest_json["versions"]


def get_version_type(version_name):
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


def get_zh_version_type(version_type):
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


def get_pre_or_rc_article(version_name):
    return


with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    user_agent = config["user_agent"]
    interval = int(config["interval"])

session = requests.Session()
session.headers.update({"User-Agent": user_agent})

print("启动成功", end='\n\n')

new_version, all_version_info = check_new_version()
version_type = get_version_type(new_version)
zh_version_type = get_zh_version_type(version_type)
release_time = all_version_info[0]["releaseTime"]
release_dt, release_dt_8 = get_timestamp(release_time)
release_dt_date = f"{release_dt.year}年{release_dt.month}月{release_dt.day}日"

toast_notification(f"{zh_version_type}{new_version}已发布。")
print(f"{zh_version_type}{new_version}已发布。")
print(f"发布时间：{release_dt_8.strftime("%Y年%m月%d日%H:%M:%S（北京时间）")}")

if version_type == "Snapshot":
    version_page_name = new_version
    zh_version_page_name = version_page_name
else:
    version_page_name = "Java%E6%90%9C%E7%B4%A2" + new_version
    zh_version_page_name = "Java版" + new_version

version_page_url = WIKI_BASE_URL + version_page_name

print(f"新页面链接：{version_page_url}?action=edit")
print("内容为：")
print("----")

version_json_url = all_version_info[0]["url"]
version_json = get_json(version_json_url)
version_json_downloads = version_json["downloads"]

previous_versions = []
prevparent = ""
prev = all_version_info[1]["id"]
parent = "1.（手动填写）"

if version_type not in ["Release", "N/A"]:
    for version in all_version_info:
        if get_version_type(version["id"]) == version_type:
            previous_versions.append(version)
        elif get_version_type(version["id"]) == "Release":
            prevparent = version["id"]
            break

if version_type in ["Pre-release", "Release Candidate"]:
    parent = new_version.split('-')[0]

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
|clienthash={version_json_downloads["client"]["sha1"]}
|clientmap={version_json_downloads["client_mappings"]["sha1"]}
|serverhash={version_json_downloads["server"]["sha1"]}
|servermap={version_json_downloads["server_mappings"]["sha1"]}
|parent={parent}
|prevparent={prevparent}
|prev={prev}
|next=
|nextparent=
}}}}<onlyinclude>

'''{new_version}'''是[[Java版{parent}]]"""
version_page_content += """{{conjecture tag}}""" if parent == "1.（手动填写）" else """"""
version_page_content += f"""的第{len(previous_versions)}个{zh_version_type}，发布于{release_dt_date}<ref>"""
version_page_content += f"""{{{{snap|{new_version}|{release_dt.strftime("%b %d, %Y")}}}}}""" if version_type == "Snapshot" else f"""{{{{article|minecraft-1-21-8-release-candidate-1|Minecraft 1.21.8 Release Candidate 1|{release_dt.strftime("%b %d, %Y")}}}}}"""
version_page_content += f"""</ref>。</onlyinclude>

== 参考 ==
{{{{Reflist}}}}

== 导航 ==
{{{{Navbox Java Edition versions|1.21}}}}"""

print(version_page_content)
print("----")

print("编辑下面页面：")

if version_type in ["Pre-release", "Release Candidate"]:
    redirect_page_url = WIKI_BASE_URL + new_version
    print(f"重定向页面链接：{redirect_page_url}?action=edit，内容为：#REDIRECT [[{zh_version_page_name}]]")
    disambig_page_url = WIKI_BASE_URL + parent
    print(f"{disambig_page_url}?action=edit")

template_version_url = WIKI_BASE_URL + "Template:Version"
print(f"{template_version_url}?action=edit")
prev_page_url = WIKI_BASE_URL + prev
print(prev_page_url)  # 目前可能为重定向，不编辑
version_list_page_url = WIKI_BASE_URL + "Java%E7%89%88%E7%89%88%E6%9C%AC%E8%AE%B0%E5%BD%95/%E5%BC%80%E5%8F%91%E7%89%88%E6%9C%AC"
print(f"{version_list_page_url}?action=edit")
navbox_page_url = WIKI_BASE_URL + "Template:Navbox_Java_Edition_versions"
print(f"{navbox_page_url}?action=edit")
# print(f"{WIKI_BASE_URL}Module:Protocol_version/Versions?action=edit")

input("按回车键退出")
sys.exit(1)
