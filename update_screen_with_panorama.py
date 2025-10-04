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
BASE_NAME_LIST = ['AccessibilitySettings', 'BuffetWorldCustomization', 'ChatSettings', 'Controls', 'Control Settings', 'Create New World Gamerule', 'Credits and Attribution', 'Datapack selection', 'Data Packs Screen Warning', 'Debug Mode Button', 'Debug Options', 'Experiments Screen Warning', 'Font Settings', 'Language settings', 'MouseSettings', 'Multiplayer Screen', 'Multiplayer Warning', 'NewWorld More', 'NewWorld', 'NewWorld World', 'Online Options', 'Select resource pack', 'Settings Screen', 'SkinCustomizationOptions', 'Sound Options Screen', 'Telemetry Data', 'VideoSettings', 'World Selection Menu Delete', 'World Selection Menu Edit', 'World Selection Menu Optimize', 'World Selection Menu']
SUFFIXES = ['Literary', 'Traditional HK', 'Traditional', 'Simplified']

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("截图重命名工具")
        self.state('zoomed')

        # --- 1. 定义一个大按钮样式 ---
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

        # --- 2. 创建右侧框架来容纳按钮 ---
        right_frame = ttk.Frame(self, padding="10")
        right_frame.pack(side="right", fill="both", expand=True)

        # 底部：操作按钮和状态栏
        bottom_frame = ttk.Frame(self, padding="10")
        bottom_frame.pack(side="bottom", fill="x", expand=False)

        # --- 3. 将按钮放入右侧框架，并应用新样式 ---
        self.process_button = ttk.Button(right_frame, text="选择文件并处理", command=self.process_files, style='Big.TButton')
        # --- 4. 使用 place 将按钮居中 ---
        self.process_button.place(relx=0.5, rely=0.5, anchor="center")
        
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
        # 1. 获取选中的目标名称
        base_name_indices = self.base_name_listbox.curselection()
        if not base_name_indices:
            messagebox.showwarning("操作失败", "请先从左侧列表选择一个目标名称。")
            return
        base_name = self.base_name_listbox.get(base_name_indices[0])

        # 2. --- 使用 filedialog 获取选中的源文件 ---
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
        
        # 3. 执行复制和重命名
        try:
            for i, file_path in enumerate(selected_filepaths):
                new_name = f"{base_name} {SUFFIXES[i]}.png"
                new_path = os.path.join(DESTINATION_FOLDER, new_name)
                
                # 将 copy2 替换为 move
                shutil.move(file_path, new_path) 
            
            # 4. 成功后更新UI
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
