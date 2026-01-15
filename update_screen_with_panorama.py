import json
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, messagebox, Listbox, filedialog
from PIL import Image, ImageTk

if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"设置DPI感知失败: {e}")

try:
    with open("config.json", "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
        SOURCE_FOLDER = config["panorama_source"]
        DESTINATION_FOLDER = config["panorama_destination"]
except FileNotFoundError:
    messagebox.showerror("config.json文件未找到！")
    sys.exit(1)

PREVIEW_FOLDER = "screen_with_panorama"
BASE_NAME_LIST = ['AccessibilitySettings', 'BuffetWorldCustomization', 'ChatSettings', 'Controls', 'Control Settings', 'Create New World Gamerule', 'Credits and Attribution', 'Datapack selection', 'Data Packs Screen Warning', 'Debug Mode Button', 'Debug Options', 'Experiments Screen Warning', 'Font Settings', 'Language settings', 'MouseSettings', 'Multiplayer Screen', 'Multiplayer Warning', 'NewWorld More', 'NewWorld', 'NewWorld World', 'Online Options', 'Select resource pack', 'Settings Screen', 'SkinCustomizationOptions', 'Sound Options Screen', 'Superflat Customization', 'Superflat Preset', 'Telemetry Data', 'VideoSettings', 'World Selection Menu Delete', 'World Selection Menu Edit', 'World Selection Menu Optimize', 'World Selection Menu', 'World Selection Downgrading Warning', 'World Selection Upgrading Warning']
SUFFIXES = ['Simplified', 'Traditional', 'Traditional HK', 'Literary']

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("截图重命名工具")
        self.state('zoomed')

        # 定义一个大按钮样式
        style = ttk.Style(self)
        style.configure('Big.TButton', font=('宋体', 16), padding=15)

        self.base_names = tk.StringVar(value=BASE_NAME_LIST)

        # 左侧：预览和目标名称选择
        left_frame = ttk.Frame(self, padding="10")
        left_frame.pack(side="left", fill="y", expand=False)

        ttk.Label(left_frame, text="预览图", font=("宋体", 14)).pack(pady=5)
        self.preview_label = ttk.Label(left_frame, text="请选择一个目标名称以显示预览")
        self.preview_label.pack(pady=10, padx=10)

        ttk.Label(left_frame, text="选择目标名称", font=("宋体", 14)).pack(pady=(20, 5))
        self.base_name_listbox = Listbox(left_frame, listvariable=self.base_names, height=20, exportselection=False)
        self.base_name_listbox.pack(fill="both", expand=True)
        self.base_name_listbox.bind("<<ListboxSelect>>", self.on_base_name_select)

        # 右侧：按钮和提示
        right_frame = ttk.Frame(self, padding="10")
        right_frame.pack(side="right", fill="both", expand=True)

        hint_text = (
            "操作提示:\n\n"
            "1. 从左侧列表选择一个目标名称。\n"
            "2. 点击下方按钮，在弹出的窗口中选择4个文件。\n\n"
            "命名将基于您的点击顺序：\n"
            f"  - 第1个点击的文件 -> ... {SUFFIXES[0]}.png\n"
            f"  - 第2个点击的文件 -> ... {SUFFIXES[1]}.png\n"
            f"  - 第3个点击的文件 -> ... {SUFFIXES[2]}.png\n"
            f"  - 第4个点击的文件 -> ... {SUFFIXES[3]}.png"
        )
        hint_label = ttk.Label(right_frame, text=hint_text, justify="left", font=("宋体", 12))
        hint_label.pack(pady=20)

        # 底部：和状态栏
        bottom_frame = ttk.Frame(self, padding="10")
        bottom_frame.pack(side="bottom", fill="x", expand=False)

        # 将按钮放入右侧框架，并应用新样式
        self.process_button = ttk.Button(right_frame, text="选择文件并处理", command=self.process_files, style='Big.TButton')
        # 使用 pack 将按钮放置在提示下方
        self.process_button.pack(pady=20)
        
        self.status_label = ttk.Label(bottom_frame, text="准备就绪")
        self.status_label.pack(side="left")

        self.update_status("选择一个目标名称")

    def update_status(self, text, color="black"):
        self.status_label.config(text=text, foreground=color)

    def on_base_name_select(self, event):
        selection_indices = self.base_name_listbox.curselection()
        if not selection_indices:
            return
        
        selected_name = self.base_name_listbox.get(selection_indices[0])
        preview_image_path = os.path.join(PREVIEW_FOLDER, f"{selected_name}.png")

        if os.path.exists(preview_image_path):
            try:
                img = Image.open(preview_image_path)
                # 调整图片大小以适应标签
                img.thumbnail((400, 400))
                self.photo = ImageTk.PhotoImage(img)
                self.preview_label.config(image=self.photo, text="")
                self.update_status(f"已选择目标: {selected_name}")
            except Exception as e:
                self.preview_label.config(image=None, text=f"无法加载预览图:\n{e}")
        else:
            self.preview_label.config(image=None, text=f"未找到预览图:\n{selected_name}.png")

    def process_files(self):
        # 获取选中的目标名称
        base_name_indices = self.base_name_listbox.curselection()
        if not base_name_indices:
            messagebox.showwarning("操作失败", "请先从左侧列表选择一个目标名称。")
            return
        base_name = self.base_name_listbox.get(base_name_indices[0])

        # 使用filedialog获取选中的源文件
        selected_filepaths = filedialog.askopenfilenames(
            title="请选择4个截图文件",
            initialdir=SOURCE_FOLDER,
            filetypes=[("PNG 文件", "*.png"), ("所有文件", "*.*")]
        )

        # 检查用户是否选择了正确数量的文件
        if not selected_filepaths:
            self.update_status("操作已取消。")
            return # 用户关闭了窗口
        
        if len(selected_filepaths) != 4:
            messagebox.showwarning("选择错误", f"需要选择4个文件，您选择了 {len(selected_filepaths)} 个。")
            return
        
        # 执行移动和重命名
        try:
            for i, file_path in enumerate(selected_filepaths):
                new_name = f"{base_name} {SUFFIXES[i]}.png"
                new_path = os.path.join(DESTINATION_FOLDER, new_name)
                shutil.move(file_path, new_path) 
            
            # 成功后更新UI
            messagebox.showinfo("成功", f"已成功移动4个文件并重命名为 '{base_name} ...' 系列。")
            self.base_name_listbox.delete(base_name_indices[0])
            self.update_status(f"'{base_name}' 已处理完成并移除。")
            self.preview_label.config(image=None, text="请选择一个目标名称以显示预览")

        except Exception as e:
            messagebox.showerror("处理失败", f"处理文件时发生错误: {e}")
            self.update_status(f"处理 '{base_name}' 时失败。", "red")

if __name__ == "__main__":
    if not os.path.exists(DESTINATION_FOLDER):
        messagebox.showerror("错误", f"目标文件夹不存在:\n{DESTINATION_FOLDER}")
        sys.exit(1)
    app = App()
    app.mainloop()
