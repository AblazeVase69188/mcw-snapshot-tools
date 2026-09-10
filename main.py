import datetime
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

import requests
from PIL import Image
from playsound3 import playsound
from win11toast import notify

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest.json"
WIKI_BASE_URL = "https://zh.minecraft.wiki/w/"
MCNET_BASE_URL = "https://www.minecraft.net"
ARTICLE_FEED_URL = MCNET_BASE_URL + "/content/minecraftnet/language-masters/en-us/jcr:content/root/container/image_grid_a_copy_64.articles.page-1.json"  # from https://github.com/Teahouse-Studios/akari-bot/blob/51ec0995fd8e3eb0ab962abe157ab1badf1d13f0/modules/minecraft_news/__init__.py#L65
ARTICLE_BASE_URL = MCNET_BASE_URL + "/en-us/article/"
BROWSER_HEADER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
sound_file = "warn3.mp3"
dev_version_types = ["Snapshot", "Pre-release", "Release Candidate"]

def get_json(url):
    """获取json"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        toast_notification("网络请求出现异常", False)
        print(f"网络请求出现异常，内容为{e}")
        input("按回车键退出")
        sys.exit(1)


def get_json_conditional(url):
    """获取json（条件请求）"""
    try:
        headers = {}
        etag = etag_cache.get(url)
        if etag:
            headers["If-None-Match"] = etag

        response = requests.get(url, headers=headers)

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


def mcnet_dld(url, filename=None):
    """模拟浏览器获取官网内容"""
    try:
        response = requests.get(url, stream=True, headers=BROWSER_HEADER)
        response.raise_for_status()
        downloaded = 0
        start_time = time.time()

        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=1024):
            if not chunk:
                continue
            buffer.write(chunk)
            downloaded += len(chunk)

            elapsed = time.time() - start_time
            if elapsed > 0:
                speed = downloaded / elapsed / 1024
                print(f"\r已下载：{downloaded}B，速度：{speed:.3f}KB/s", end='', flush=True)
            else:
                print(f"\r已下载：{downloaded}B", end='', flush=True)
        print()
        buffer.seek(0)

        if not filename:
            return buffer.getvalue().decode('utf-8')

        try:
            with Image.open(buffer) as img:
                format = img.format.lower()
                if format == "jpeg":
                    format = "jpg"
                else:
                    do_transform = input(f"获取到的图片格式为{format}，强制转换成jpg按1：")
                    if do_transform == "1":
                        format = "jpg"
                
                width, height = img.size
                if width != 1170 or height != 500:
                    save_anyway = input(f"获取到的图片尺寸为{width}×{height}，继续保存按1：")
                    if save_anyway != "1":
                        return False

                save_path = f"{destination_path}\\{filename}.{format}"
                with open(save_path, "wb") as f:
                    img.save(f, format="JPEG" if format == "jpg" else format.upper())
            print(f"文件已保存至：{save_path}")
            return True

        except Exception as e:
            print(f"图片处理失败：{e}")
            return False

    except Exception as e:
        print(f"{url}下载失败：{e}")
        return False


def toast_notification(msg_str, doplaysound=True):
    """播放音效并产生弹窗通知"""
    if doplaysound:
        playsound(sound_file, block=False)

    notify("mcw-snapshot-tools", msg_str)


def check_new_version(selected_version):
    """检测新版本发布"""
    # 为缩写的版本号提供支持
    parts = selected_version.split('-')
    if len(parts) == 3:
        if parts[1] in ["s", "snap"]:
            selected_version = f"{parts[0]}-snapshot-{parts[2]}"
        elif parts[1] == "p":
            selected_version = f"{parts[0]}-pre-{parts[2]}"
        elif parts[1] == "r":
            selected_version = f"{parts[0]}-rc-{parts[2]}"

    # 获取当前版本列表
    manifest_json, _ = get_json_conditional(MANIFEST_URL)

    # 若已指定版本，尝试返回有关信息
    if selected_version != "":
        versions = manifest_json["versions"]
        for i, version in enumerate(versions):
            if version["id"] == selected_version:
                return selected_version, versions[i:]

        check_selected = input("未找到版本，按1继续尝试检查")
        if check_selected == "1":
            return get_selected_version(selected_version)
        else:
            sys.exit(1)

    # article_json, _ = get_json_conditional(ARTICLE_FEED_URL)

    latest_snapshot = manifest_json["latest"]["snapshot"]
    latest_release = manifest_json["latest"]["release"]
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


def get_selected_version(version_name):
    """尝试获取并返回已知的最新版本"""
    while True:
        manifest_json = get_json(MANIFEST_URL)
        if manifest_json["versions"][0]["id"] == version_name:
            return version_name, manifest_json["versions"]
        
        time.sleep(interval)


def get_version_type(version_name):
    """返回版本类型"""
    v1_year = {"11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"}
    v1_week = {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52"}
    v1_order = {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"}
    v2_year = {"26", "27", "28", "29", "30", "31", "32", "33", "34", "35"}
    v2_season = {"1", "2", "3", "4"}
    v2_hotfix = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10"}  # 我就不信Mojang发的热更新还能超过10个

    # v1
    if len(version_name) == 6:
        year_part = version_name[0:2]
        w_part = version_name[2]
        week_part = version_name[3:5]
        order_part = version_name[5]
        if year_part in v1_year and w_part == "w" and week_part in v1_week and order_part in v1_order:
            return "Snapshot"
    elif "-pre" in version_name:
        return "Pre-release"
    elif "-rc" in version_name:
        return "Release Candidate"

    # v2
    if "-snapshot-" in version_name:
        return "Snapshot"
    # 已被v1覆盖
    '''
    elif "-pre-" in version_name:
        return "Pre-release"
    elif "-rc-" in version_name:
        return "Release Candidate"
    '''
    parts = version_name.split('.')
    if len(parts) == 2 and parts[0] in v2_year and parts[1] in v2_season:
        return "Release"
    if len(parts) == 3 and parts[0] in v2_year and parts[1] in v2_season and parts[2] in v2_hotfix:
        return "Release"

    return "N/A"


def get_zh_version_type(version_type):
    """返回版本类型的中文名称"""
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


def get_release_type(version_name):
    """返回正式版的更新类型"""
    parts = version_name.split('.')
    if len(parts) == 2:
        return "小更新"
    elif len(parts) == 3:
        return "热修复更新"
    else:
        return "更新"


def get_mojira_version(version_name):
    """返回Mojira形式的版本号"""
    version_type = get_version_type(version_name)
    parts = version_name.split('-')
    if version_type == "Snapshot":
        return f"{parts[0]} Snapshot {parts[2]}"
    elif version_type == "Pre-release":
        return f"{parts[0]} Pre-Release {parts[2]}"
    elif version_type == "Release Candidate":
        return f"{parts[0]} Release Candidate {parts[2]}"
    
    return version_name  # 这一行实际上永远不会被执行


def get_article_url(version_name):
    """返回官网博文链接随标题变化的部分"""
    version_type = get_version_type(version_name)
    if version_type == "Snapshot":
        return f"minecraft-{version_name.replace('.', '-')}"
    elif version_type == "Pre-release":
        return f"minecraft-{version_name.replace('.', '-').replace('-pre-', '-pre-release-')}"
    elif version_type == "Release Candidate":
        return f"minecraft-{version_name.replace('.', '-').replace('-rc-', '-release-candidate-')}"
    elif version_type == "Release":
        return f"minecraft-java-edition-{version_name.replace('.', '-')}"
    
    return ""


def get_article(version_name):
    """返回模板格式的官网博文链接"""
    version_type = get_version_type(version_name)
    url_name = get_article_url(version_name)
    if version_type == "Snapshot":
        title_name = version_name.replace('-', ' ').replace('snapshot', 'Snapshot')
        return f"{url_name}|Minecraft {title_name}"
    elif version_type == "Pre-release":
        title_name = version_name.replace('-', ' ').replace('pre', 'Pre-Release')
        return f"{url_name}|Minecraft {title_name}"
    elif version_type == "Release Candidate":
        title_name = version_name.replace('-', ' ').replace('rc', 'Release Candidate')
        return f"{url_name}|Minecraft {title_name}"
    elif version_type == "Release":
        return f"{url_name}|Minecraft Java Edition {version_name}"
    
    return ""


def get_edit_url(page_name):
    """返回页面编辑链接"""
    # 为了能直接在命令行中点开，对页面名称执行URL编码
    return WIKI_BASE_URL + requests.utils.quote(page_name) + "?action=edit"


def get_prevparent_and_prev(version_name, all_version_info, is_first_snap):
    """
    返回prevparent和prev。

    开发版的prevparent是上一正式版（小更新或热修复更新），prev是上一开发版

    小更新的prevparent是上一小更新，prev是上一热修复更新（没有则为prevparent）

    热修复更新的prevparent是上一小更新，prev是上一热修复更新（没有则为prevparent）

    未知版本类型的prevparent和prev设为空
    """
    version_type = get_version_type(version_name)

    if version_type == "N/A":
        return "", ""

    if version_type == "Release":
        parts = version_name.split('.')
        if len(parts) == 3:  # 热修复更新
            prevparent = f"{parts[0]}.{parts[1]}"
            if parts[2] == "1":  # 上一正式版就是prevparent
                prev = ""
            else:
                prev = f"{parts[0]}.{parts[1]}.{int(parts[2]) - 1}"
            return prevparent, prev

        # 小更新
        if parts[0] == "26" and parts[1] == "1":
            return "1.21.11", ""

        if parts[1] == "1":
            prevparent = f"{int(parts[0]) - 1}.4"
        else:
            prevparent = f"{parts[0]}.{int(parts[1]) - 1}"

        for vi in all_version_info:
            if vi["type"] == "snapshot":
                continue
            if vi["id"] == prevparent:  # 上一正式版就是prevparent
                return prevparent, ""
            return prevparent, vi["id"]  # 是正式版而且不是prevparent

    # 开发版
    parts = version_name.split('-')
    parent = parts[0]
    parent_prevparent, prevparent = get_prevparent_and_prev(parent, all_version_info, False)
    if prevparent == "":
        prevparent = parent_prevparent
    type_num = int(parts[2])
    if type_num > 1:
        return prevparent, f"{parts[0]}-{parts[1]}-{type_num - 1}"
    if is_first_snap:
        return prevparent, ""
    for vi in all_version_info[1:]:
        if vi["id"].split('-')[0] == parent:
            return prevparent, vi["id"]


def is_first_snapshot(version_name, all_version_info):
    """判断首个开发版本"""
    version_type = get_version_type(version_name)
    if version_type not in dev_version_types:
        return False

    parts = version_name.split('-')
    type_num = int(parts[2])

    if type_num != 1:  # 不是同类型开发版中的第一个
        return False

    parent = parts[0]
    prevparent, _ = get_prevparent_and_prev(parent, all_version_info, False)
    for vi in all_version_info[1:]:
        if vi["id"] == prevparent:
            break
        if vi["id"].split('-')[0] == parent:
            return False

    return True


def get_version_log_headimg(version_name):
    """下载版本宣传图"""
    # 获取官网博文html
    print("正在查看官网博文")
    article_url = ARTICLE_BASE_URL + get_article_url(version_name)
    article_text = mcnet_dld(article_url)
    if not article_text:
        return

    # 尝试获取图片链接
    imgurl_start = '<meta property="og:image" content="'
    imgurl_end = '"/>'
    start_index = article_text.find(imgurl_start)
    if start_index != -1:
        start_index += len(imgurl_start)
        end_index = article_text.find(imgurl_end, start_index)
        img_url = article_text[start_index:end_index]

    if not img_url:
        imgurl_start = '<meta name="twitter:image" content="'
        start_index = article_text.find(imgurl_start)
        if start_index != -1:
            start_index += len(imgurl_start)
            end_index = article_text.find(imgurl_end, start_index)
            img_url = article_text[start_index:end_index]
        
    if not img_url:
        imgsrc_end = '" class="article-head__image img-fluid" alt="'
        imgsrc_start = '<img src="'
        end_index = article_text.find(imgsrc_end)
        start_index = article_text.rfind(imgsrc_start, 0, end_index)
        if end_index != -1 and start_index != -1:
            start_index += len(imgsrc_start)
            img_url = MCNET_BASE_URL + article_text[start_index:end_index]

    if not img_url:
        print("错误：没有找到版本宣传图")
        return

    # 下载图片并保存
    print("正在下载版本宣传图")
    mcnet_dld(img_url, version_name)


def get_version_protocol(version_name):
    """获取版本协议数据"""
    jar_path = f"{versions_path}\\{version_name}\\{version_name}.jar"
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            version_data = json.loads(jar.read('version.json'))
    except Exception as e:
        print(f"读取协议数据失败：{e}")
        return
    if int(version_data["protocol_version"]) > 1073741824:
        protocol_num = "0x" + hex(int(version_data["protocol_version"]))[2:].upper()
    else:
        protocol_num = version_data["protocol_version"]
    protocol_text = f"verJE( java, '{version_name}', {protocol_num}, {version_data['world_version']}, {{ {version_data['pack_version']['resource_major']}, {version_data['pack_version']['resource_minor']} }}, {{ {version_data['pack_version']['data_major']}, {version_data['pack_version']['data_minor']} }} )"
    print(f"协议数据：{get_edit_url('Module:Protocol_version/Versions')}")
    print(f"内容为：{protocol_text}")


def rename_version_screenshots(version_name):
    """重命名版本主菜单截图"""
    variants = ['Simplified', 'Traditional', 'Traditional HK', 'Literary']

    # 获取截图文件夹中所有png文件及其信息
    png_entries = [
        entry for entry in os.scandir(screenshot_path)
        if entry.is_file() and entry.name.lower().endswith(".png")
    ]
    
    if len(png_entries) < 4:
        print(f"重命名失败：截图文件夹中没有足够的图片")
        return

    # 从旧到新排序并选择最新4个文件
    src_file = [e for e in sorted(png_entries, key=lambda e: e.stat().st_mtime)[-4:]]

    # 检查图片尺寸
    for src in src_file:
        with Image.open(src.path) as img:
            width = img.width
            height = img.height
            if width != 854 or height != 480:
                move_anyway = input(f"{src.name}尺寸为{width}×{height}，继续重命名按1：")
                if move_anyway != "1":
                    return

    # 重命名并移动文件
    for src, variant in zip(src_file, variants):
        dst_name = f"Java Edition {version_name} {variant}.png"
        dst_path = os.path.join(destination_path, dst_name)
        shutil.move(src.path, dst_path)
        print(f"已完成：{src.name}->{dst_name}")


# 初始化
with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    user_agent = config["user_agent"]
    interval = int(config["interval"])
    screenshot_path = config["screenshot_path"]
    MCL_path = config["MCL_path"]
    versions_path = config["versions_path"]
    destination_path = config["destination_path"]

etag_cache = {}

selected_version = input("输入一个版本号，留空则自动检测最新版本：")

# 获取版本信息
new_version, all_version_info = check_new_version(selected_version)
version_type = get_version_type(new_version)
zh_version_type = get_zh_version_type(version_type)
release_time = all_version_info[0]["releaseTime"]
release_dt = datetime.datetime.fromisoformat(release_time)
release_dt_8 = release_dt + datetime.timedelta(hours=8)
release_dt_date = f"{release_dt.year}年{release_dt.month}月{release_dt.day}日"

version_json_type = all_version_info[0]["type"]
version_json_url = all_version_info[0]["url"]
version_json = get_json(version_json_url)
version_json_downloads = version_json["downloads"]

# 输出发布提示
if selected_version == "":
    toast_notification(f"{zh_version_type}{new_version}已发布。")
print(f"{zh_version_type}{new_version}已发布。")
print(f"发布时间：{release_dt_8.strftime("%Y年%m月%d日%H:%M:%S（北京时间）")}")

# 输出编辑提示
# 1. 版本页面
print(f"⭐ 新页面链接：{get_edit_url('Java版' + new_version)}")
print("内容为：")
print("----")

# 对开发版本而言，3个元素分别是正式版、类型和序数
parts = new_version.split('-')
if version_type in dev_version_types:
    parent = parts[0]
    parent_parts = parent.split('.')
    year_num = int(parent_parts[0])
    type_num = int(parts[2])

# 判断首个开发版本
if is_first_snapshot(new_version, all_version_info):
    is_first_snap = True
    is_second_snap = False
else:
    is_first_snap = False

prevparent, prev = get_prevparent_and_prev(new_version, all_version_info, is_first_snap)

if not is_first_snap:
    if is_first_snapshot(prev, all_version_info[1:]):
        is_second_snap = True
    else:
        is_second_snap = False

# 判断正式版类型
if version_type not in dev_version_types:
    release_type = get_release_type(new_version)

version_page_content = f"""{{{{wip}}}}
{{{{Infobox version
|title={new_version}
|image={new_version}.jpg
|image2=Java Edition {new_version} Simplified.png\\Java Edition {new_version} Traditional.png\\Java Edition {new_version} Traditional HK.png
|edition=Java"""
# 正式版infobox不填此项
version_page_content += "" if version_type in ["N/A", "Release"] else f"""
|type={version_type}"""
version_page_content += f"""
|date={release_dt_date}
|jsonhash={version_json_url[len("https://piston-meta.mojang.com/v1/packages/"):].split('/')[0]}
|clienthash={version_json_downloads["client"]["sha1"]}"""
version_page_content += f"""
|serverhash={version_json_downloads["server"]["sha1"]}"""
# 正式版infobox不填此项
version_page_content += "" if version_type in ["N/A", "Release"] else f"""
|parent={parent}"""
version_page_content += "" if version_type == "N/A" else f"""
|prevparent={prevparent}
|prev={prev}
|next=
|nextparent="""
version_page_content += """
}}"""
# 正式版不填onlyinclude
version_page_content += "<onlyinclude>" if version_type in dev_version_types else ""
version_page_content += f"""

'''{new_version}'''是"""
# 根据开发版本或正式版生成导言
if version_type in dev_version_types:
    version_page_content += f"[[Java版{parent}]]的"
    version_page_content += f"第{type_num}" if type_num > 1 else "首"
    version_page_content += f"个{zh_version_type}，"
else:
    version_page_content += f"{{{{el|je}}}}的一次{release_type}，"

version_page_content += f"发布于{release_dt_date}"
version_page_content += "<ref>{{article|"
version_page_content += f"{get_article(new_version)}"
version_page_content += f"|{release_dt.strftime("%b %d, %Y")}"
version_page_content += "}}</ref>"
version_page_content += "" if version_type == "N/A" else "，修复了一些漏洞"
version_page_content += "。"

# 正式版页面只生成infobox和导言
if version_type in dev_version_types:
    version_page_content += """
<!--
== 修复 ==
{{fixes|fixedin="""
    version_page_content += get_mojira_version(new_version)
    version_page_content += """|showdesc=1

}}</onlyinclude>
-->
== 参考 ==
{{Reflist}}

== 导航 ==
{{Navbox Java Edition versions|"""
    version_page_content += f"20{year_num}"
    version_page_content += "}}"

elif version_type == "N/A":
    version_page_content += """

== 参考 ==
{{Reflist}}

== 导航 ==
{{Navbox Java Edition versions}}"""

print(version_page_content)
print("----")

print("编辑下面页面：")

# 2. 记录开发版本和正式版的页面
if version_type != "N/A":
    print(f"⭐ 更新版本号：{get_edit_url('Template:Version')}")

# 3. 重定向
if version_type in dev_version_types:
    print(f"⭐ 重定向页面：{get_edit_url(new_version)}，内容为：#REDIRECT [[Java版{new_version}]]")
    if version_type == "Snapshot":
        other_name = new_version.replace("-", "_").replace("snapshot", "Snapshot")
    elif version_type == "Pre-release":
        other_name = new_version.replace("-", "_").replace("pre", "Pre-Release")
    elif version_type == "Release Candidate":
        other_name = new_version.replace("-", "_").replace("rc", "Release_Candidate")
    print(f"⭐ 重定向页面：{get_edit_url(other_name)}，内容为：#REDIRECT [[Java版{new_version}]]")
    print(f"⭐ 重定向页面：{get_edit_url('Java版' + other_name)}，内容为：#REDIRECT [[Java版{new_version}]]")

# 4. 其他记录开发版本的页面
if version_type in dev_version_types:
    print(f"⭐ 版本号消歧义页面：{get_edit_url(str(year_num) + '.x')}")
    print(f"⭐ 添加版本链接：{get_edit_url('Java版版本记录/开发版本')}")
    print(f"⭐ 添加版本链接：{get_edit_url('Template:Navbox_Java_Edition_versions')}")

    if zh_version_type == "发布候选版本":
        zh_version_type_c = "发布候选"
    else:
        zh_version_type_c = zh_version_type

    if type_num == 1:
        print(f"⭐ 按版本分类的Java版开发版本：{get_edit_url('Category:Java版' + parent + zh_version_type_c)}，内容为：[[Category:按版本分类的Java版开发版本]]")

    for vi in all_version_info[1:]:
        if get_version_type(vi["id"]) != version_type:
            continue
        cur_dt = datetime.datetime.fromisoformat(vi["releaseTime"])
        if cur_dt.year == release_dt.year:
            break
        elif cur_dt.year < release_dt.year:
            print(f"⭐ 按年分类的Java版开发版本：{get_edit_url('Category:发布于' + str(release_dt.year) + '年的' + zh_version_type_c)}，内容为：[[Category:按年分类的Java版开发版本]]")
            break

# 5. 其他记录正式版的页面
if version_type == "Release":
    print(f"⭐ 计划版本页面：{get_edit_url('计划版本')}")
    print("将段落内容替换为“Java版暂无已知的计划版本。”")
    
    print(f"⭐ 版本记录页面：{get_edit_url('Java版版本记录')}")
    print(f"在表格第一行添加更新名称，表格最后一行改为{release_dt_date}")

    print(f"⭐ 指南页面：{get_edit_url('Java版指南')}")
    print(f"在表格第一行添加以下内容：")
    guide_table = f"""|-
| [[/小鬼当家/]] || [[Java版{new_version}|{new_version}]]"""
    print("----")
    print(guide_table)
    print("----")

    print(f"⭐ 编辑主题更新页面：{WIKI_BASE_URL}")

    print(f"⭐ 编辑大事记页面：{get_edit_url('大事记')}")

# 如果不是首个开发版本，需要编辑前一版本的页面
if not is_first_snap and version_type != "N/A":
    if version_type in dev_version_types:  # 开发版
        prev_page_url = get_edit_url('Java版' + prev)
        if type_num == 1:  # 同类型开发版中的第一个
            print(f"⭐ 在infobox中添加next参数，并在导语中添加“，也是最后一个”：{prev_page_url}")
        else:
            print(f"⭐ 在infobox中添加next参数：{prev_page_url}")
    else:  # 正式版
        for vi in all_version_info[1:]:
            if vi["type"] == "release":
                continue
            if vi["id"].split('-')[0] == new_version:
                prev_page_url = get_edit_url('Java版' + vi["id"])
                break
        print(f"⭐ 在导语中添加“，也是最后一个”：{prev_page_url}")

print("")

# 如果是首个开发版本，创建下一正式版的页面
if is_first_snap:
    print("这是首个开发版本，编辑下面页面：")
    parent_version_page_section_0 = f"'''{parent}'''是{{{{el|je}}}}即将到来的一次{get_release_type(parent)}，发布时间待定。"
    parent_version_page_section_0 += "<ref>{{article|"
    parent_version_page_section_0 += f"{get_article(new_version)}"
    parent_version_page_section_0 += f"|{release_dt.strftime("%b %d, %Y")}"
    parent_version_page_section_0 += "}}</ref>"

    # 1. 版本页面
    print(f"⭐ 正式版页面：{get_edit_url('Java版' + parent)}")
    print("内容为：")
    print("----")
    parent_prevparent, parent_prev = get_prevparent_and_prev(parent, all_version_info, False)
    parent_version_page_content = "{{wip}}"
    parent_version_page_content += f"""
{{{{Infobox version
|title={parent}
|image=<!-- {parent}.jpg -->
|image2=<!-- Java Edition {parent} Simplified.png\\Java Edition {parent} Traditional.png\\Java Edition {parent} Traditional HK.png -->
|edition=Java
|date=未知 |planned=1
|jsonhash=
|clienthash=
|serverhash=
|prevparent={parent_prevparent}
|prev={parent_prev}
|next=
|nextparent=
}}}}

"""
    parent_version_page_content += parent_version_page_section_0
    parent_version_page_content += """

== 参考 ==
{{Reflist}}

== 导航 ==
{{Navbox Java Edition versions|"""
    parent_version_page_content += f"20{year_num}"
    parent_version_page_content += "}}"
    print(parent_version_page_content)
    print("----")

    # 2. 重定向
    print(f"⭐ 重定向页面：{get_edit_url(parent)}，内容为：#REDIRECT [[Java版{parent}]]")

    # 3. 其他记录正式版的页面
    print(f"⭐ 计划版本页面：{get_edit_url('计划版本')}")
    print("内容为：")
    print("----")
    planned_page_content = f"""=== {parent} ===
{{{{main|Java版{parent}}}}}

{parent_version_page_section_0}"""
    print(planned_page_content)
    print("----")
    print(f"⭐ 版本记录页面：{get_edit_url('Java版版本记录')}")
    print("内容为：")
    version_history_table = f"""|-
| 名称尚未公布
| [[Java版{parent}|{parent}]]
| {release_dt_date}
| 尚未发布"""
    print("----")
    if parent_parts[1] == "1" and len(parent_parts) == 2:  # 判定正式版是不是这一年发布的首个正式版
        table_header = f"""=== {parent_parts[0]}.x ===
{{| class="wikitable"
! 更新
! 版本
! 开发版本
! 正式版本"""
        print(table_header)
    print(version_history_table)
    if parent_parts[1] == "1" and len(parent_parts) == 2:
        print("|}")
    print("----")

    if parent_prev == "":
        parent_prev = parent_prevparent

    if len(parent_parts) == 2:  # 如果parent是小更新，上一小更新（prevparent）和之后的版本需要在nextparent参数添加
        prev_list = []
        for vi in all_version_info:
            if vi["type"] == "snapshot":
                continue
            prev_list.append(vi["id"])
            if vi["id"] == parent_prevparent:
                break
        print("⭐ 在前正式版页面的infobox中添加nextparent参数：")
        for pv in prev_list:
            print(f"{get_edit_url('Java版' + pv)}")
    elif len(parent_parts) == 3:  # 如果parent是热修复更新，上一正式版（prev）需要在next参数添加
        print(f"⭐ 在上一正式版页面的infobox中添加next参数：{get_edit_url('Java版' + parent_prev)}")

    if parent != "26.1":
        print(f"⭐ 在上一正式版所有开发版本页面的infobox中添加nextparent参数：")
        # 无论parent是什么类型，都只在上一正式版（prev）的开发版页面添加
        parent_prev_prevparent, parent_prev_prev = get_prevparent_and_prev(parent_prev, all_version_info, False)
        if parent_prev_prev == "":
            parent_prev_prev = parent_prev_prevparent

        snapshot_list = []
        for vi in all_version_info:
            if vi["type"] == "release":
                continue
            if vi["id"] == parent_prev_prev:
                break
            if vi["id"].split('-')[0] == parent_prev:
                snapshot_list.append(vi["id"])

        # 调整为Wiki页面标题
        for i, snapshot in enumerate(snapshot_list):
            print(f"{get_edit_url('Java版' + snapshot)}")

    print(f"⭐ {{{{Other editions}}}}：{get_edit_url('Template:Other editions')}")
    print("")

if is_second_snap:
    print("这是第二个开发版本，编辑下面页面：")
    print(f"⭐ 开发版本页面：{get_edit_url('Java版' + parent + '/开发版本')}，内容为：{{{{Development versions}}}}")
    print("")

# 7. 准备上传图片
print("上传5个文件：https://zh.minecraft.wiki/w/Special:BatchUpload")

print("⭐ 版本宣传图，内容为：")
print("----")
print("\n== 许可协议 ==\n{{License Mojang}}\n\n[[Category:截图]]\n[[Category:版本宣传图]]")
print("----")

print("⭐ 菜单屏幕截图，内容为：")
print("----")
print("== 摘要 ==\n{{Other translation files}}\n\n== 许可协议 ==\n{{License Mojang}}\n\n[[Category:主菜单截图]]")
print("----")
print(f"⭐ 菜单屏幕截图重定向：{get_edit_url(f'File:Java_Edition_{new_version}.png')}，内容为：{{{{Other translation files}}}}")
print("")

# 8. 其他
start_MCL = input("启动启动器按1：")
if start_MCL == "1":
    exe = MCL_path
    subprocess.Popen([exe])

get_img = input("下载版本宣传图按1：")
if get_img == "1":
    get_version_log_headimg(new_version)

get_protocol = input("若启动器已下载好jar，获取协议版本按1：")
if get_protocol == "1":
    get_version_protocol(new_version)

get_version_screenshot = input("若已生成好主菜单截图，自动重命名截图按1：")
if get_version_screenshot == "1":
    rename_version_screenshots(new_version)
