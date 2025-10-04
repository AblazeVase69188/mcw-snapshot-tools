import json
import os
import shutil
import sys

with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    panorama_source = config["panorama_source"]
    panorama_destination = config["panorama_destination"]

source_folder = panorama_source
destination_folder = panorama_destination

base_name_list = ['AccessibilitySettings', 'BuffetWorldCustomization', 'ChatSettings', 'Controls', 'Control Settings', 'Create New World Gamerule', 'Credits and Attribution', 'Datapack selection', 'Data Packs Screen Warning', 'Debug Mode Button', 'Debug Options', 'Experiments Screen Warning', 'Font Settings', 'Language settings', 'MouseSettings', 'Multiplayer Screen', 'Multiplayer Warning', 'NewWorld More', 'NewWorld', 'NewWorld World', 'Online Options', 'Select resource pack', 'Settings Screen', 'SkinCustomizationOptions', 'Sound Options Screen', 'Telemetry Data', 'VideoSettings', 'World Selection Menu Delete', 'World Selection Menu Edit', 'World Selection Menu Optimize', 'World Selection Menu']

suffixes = ['Literary', 'Traditional HK', 'Traditional', 'Simplified']

if not os.path.exists(destination_folder):
    print("目标文件夹不存在")
    input("按回车键退出")
    sys.exit(1)

# 循环直到列表为空
while base_name_list:
    print("给你刚截的图片选择名称：")
    
    for i, name in enumerate(base_name_list, 1):
        print(f"{i}. {name}")
    
    choice = -1
    try:
        choice_str = input("请输入编号，或输入0退出：")
        if choice_str == '0':
            break
        choice = int(choice_str)
        if not 1 <= choice <= len(base_name_list):
            print("错误：输入编号超出范围。")
            continue
    except ValueError:
        print("错误：请输入一个有效的数字。")
        continue

    base_name = base_name_list[choice - 1]
    print(f"\n已选择{base_name}")

    # 获取所有png文件并排序
    try:
        png_files = [f for f in os.listdir(source_folder) if f.lower().endswith('.png')]
        full_path_pngs = [os.path.join(source_folder, f) for f in png_files]
        full_path_pngs.sort(key=os.path.getmtime, reverse=True)
    except FileNotFoundError:
        print("源文件夹不存在")
        break

    latest_pngs = full_path_pngs[:4]

    # 移动
    if not latest_pngs:
        print("源文件夹中没有PNG文件")
    else:
        all_successful = True
        for i, file_path in enumerate(latest_pngs):
            try:
                copied_file_path = shutil.copy(file_path, destination_folder)  # 应用时改为move

                # 构建新文件名并重命名
                new_name = f"{base_name} {suffixes[i]}.png"
                new_path = os.path.join(destination_folder, new_name)
                os.rename(copied_file_path, new_path)

            except Exception as e:
                print(f"处理文件{os.path.basename(file_path)}时出错：{e}")
                all_successful = False
        
        # 处理成功后，从列表中删除该项
        if all_successful:
            base_name_list.pop(choice - 1)
