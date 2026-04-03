import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, scrolledtext
import os
import re
import requests
import base64
import json
from cryptography.fernet import Fernet

# ==== 配置文件 ==============
class ConfigCrypto:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.script_dir, "GiteeConfig.json")

    def load_config(self):
        if not os.path.exists(self.config_file):
            return {"key": Fernet.generate_key().decode(), "token": "", "repo_url": ""}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"key": Fernet.generate_key().decode(), "token": "", "repo_url": ""}

    def save_config(self, token, repo_url):
        data = self.load_config()
        key = data.get("key", Fernet.generate_key().decode())
        f = Fernet(key.encode())
        encrypted_token = f.encrypt(token.encode()).decode()
        final_data = {"key": key, "token": encrypted_token, "repo_url": repo_url}
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

    def get_decrypted(self):
        data = self.load_config()
        key = data.get("key")
        token_encrypted = data.get("token", "")
        repo_url = data.get("repo_url", "")
        try:
            f = Fernet(key.encode())
            token = f.decrypt(token_encrypted.encode()).decode()
        except:
            token = ""
        return token, repo_url

# ====Gitee仓库管理器 ======================
class GiteeTreeManager:
    def __init__(self, root):
        self.root = root
        self.root.title("GiteeMiniMan Gitee 迷你仓库管理器")
        self.root.geometry("920x680")

        self.main_bg = "#ECEFF4"
        self.card_bg = "#FFFFFF"
        self.btn_color = "#5E81AC"
        self.btn_hover = "#4C6D92"
        self.text_color = "#2E3440"

        self.root.configure(bg=self.main_bg)
        self.center_window(920, 680)
        self.setup_style()

        self.crypto = ConfigCrypto()
        self.token = ""
        self.owner = ""
        self.repo = ""
        self.base_api = "https://gitee.com/api/v5"
        self.path_map = {}
        self.read_only_mode = False
        
        self.edit_ext = (
            ".txt", ".md", ".yaml", ".yml", ".xml", ".json", ".ini", ".toml", ".cfg", ".conf",
            ".html",".mhtml", ".css", ".js", ".vue", ".svg", ".csv", ".log", ".sql", ".env",
            ".py", ".sh", ".bat", ".php", ".java", ".c", ".cpp", ".h", ".go", ".rb", ".lua",
            ".swift", ".bas", ".cls", ".vba", ".vbs"
        )

        self.last_token, self.last_repo = self.crypto.get_decrypted()

        frame_top = tk.Frame(root, bg=self.card_bg, padx=16, pady=14, relief="flat", bd=0)
        frame_top.pack(fill=tk.X, padx=12, pady=8)

        tk.Label(frame_top, text="令牌Access Token", bg=self.card_bg, fg=self.text_color, font=("微软雅黑",9,"bold")) \
            .grid(row=0, column=0, sticky="w")
        self.entry_token = tk.Entry(frame_top, width=55, font=("微软雅黑",9), bd=1, relief="solid")
        self.entry_token.grid(row=0, column=1, padx=10, pady=2)
        self.entry_token.insert(0, self.last_token)

        tk.Label(frame_top, text="仓库链接", bg=self.card_bg, fg=self.text_color, font=("微软雅黑",9,"bold")) \
            .grid(row=1, column=0, sticky="w")
        self.entry_repo = tk.Entry(frame_top, width=55, font=("微软雅黑",9), bd=1, relief="solid")
        self.entry_repo.grid(row=1, column=1, padx=10)
        self.entry_repo.insert(0, self.last_repo)

        self.btn_load = tk.Button(
            frame_top, text="加载仓库", command=self.load_repo,
            bg=self.btn_color, fg="white", font=("微软雅黑",9,"bold"),
            relief="flat", bd=0, padx=12, pady=5
        )
        self.btn_load.grid(row=0, column=2, rowspan=2, padx=8)

        frame_tool = tk.Frame(root, bg=self.main_bg, padx=12, pady=4)
        frame_tool.pack(fill=tk.X)

        btn_common = {
            "bg": self.btn_color, "fg": "white", "font": ("微软雅黑",9),
            "relief": "flat", "bd":0, "padx":10, "pady":4
        }

        self.btn_refresh = tk.Button(frame_tool, text="刷新", command=self.refresh_tree, **btn_common)
        self.btn_create = tk.Button(frame_tool, text="新建文件夹", command=self.create_folder, **btn_common)
        self.btn_upload = tk.Button(frame_tool, text="上传文件", command=self.upload_file, **btn_common)
        self.btn_download = tk.Button(frame_tool, text="下载选中", command=self.download_file, **btn_common)
        self.btn_delete = tk.Button(frame_tool, text="删除选中", command=self.delete_file, **btn_common)
        self.btn_edit = tk.Button(frame_tool, text="编辑文件", command=self.open_edit_window, **btn_common)
        self.btn_help = tk.Button(frame_tool, text="使用帮助", command=self.show_help, **btn_common)

        self.btn_refresh.pack(side=tk.LEFT, padx=3)
        self.btn_create.pack(side=tk.LEFT, padx=3)
        self.btn_upload.pack(side=tk.LEFT, padx=3)
        self.btn_download.pack(side=tk.LEFT, padx=3)
        self.btn_edit.pack(side=tk.LEFT, padx=3)
        self.btn_delete.pack(side=tk.LEFT, padx=3)
        self.btn_help.pack(side=tk.LEFT, padx=3)

        frame_tree = tk.Frame(root, bg=self.card_bg, relief="flat", bd=0)
        frame_tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self.tree = ttk.Treeview(frame_tree, columns=("size"), show="tree headings", style="Modern.Treeview")
        self.tree.heading("#0", text="名称")
        self.tree.heading("size", text="大小")
        self.tree.column("#0", width=720)
        self.tree.column("size", width=120)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.tree.bind("<<TreeviewOpen>>", self.on_folder_open)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.root.after(300, self.auto_load_repo)

    # ========== 帮助窗口 ==========
    def show_help(self):
        help_text = """
Gitee 迷你仓库管理器GiteeMiniMan 使用帮助

【1】使用前准备
• 需要在 Gitee 个人头像-设置/个人设置-安全设置-私人令牌--生成新令牌 Access Token（权限：repo）
• 填入 Token 和仓库链接，点击加载仓库

【2】功能说明
• 刷新：重新加载仓库文件列表
• 新建文件夹：在选中目录下创建文件夹
• 上传文件：支持文本、图片、压缩包等，选中已有文件再上传，默认和选中的文件同路径
• 下载选中：下载选中的文件到本地
• 删除选中：删除文件或整个文件夹
• 编辑文件：支持几乎所有文本格式
.txt ,  .md ,  .yaml ,  .yml ,  .xml ,  .json ,  .ini ,  .toml ,  .cfg ,  .conf ,
.html , .mhtml ,  .css ,  .js ,  .vue ,  .svg ,  .csv ,  .log ,  .sql ,  .env ,
.py ,  .sh ,  .bat ,  .php ,  .java ,  .c ,  .cpp ,  .h ,  .go ,  .rb ,  .lua ,
.swift ,  .bas ,  .cls ,  .vba ,  .vbs 

【3】上传限制（重要）
• 本工具上传单文件建议不超过 10MB
• 超过容易出现 SSL/网络断开错误
• exe/二进制大文件建议分卷压缩后上传

【4】权限说明
• 填写 个人令牌Token：拥有完整读写权限
• 不填 个人令牌Token：自动进入只读模式
• 程序旁边默认生成GiteeConfig.json存储记录令牌、仓库路径，程序打开时默认读取，如需保密请自行删除这个文件。
        """
        messagebox.showinfo("使用帮助", help_text.strip())

    # ========== 按钮状态 ==========
    def set_button_state(self):
        if self.read_only_mode:
            self.btn_create.config(state=tk.DISABLED)
            self.btn_upload.config(state=tk.DISABLED)
            self.btn_delete.config(state=tk.DISABLED)
            self.btn_edit.config(state=tk.DISABLED)
            self.btn_download.config(state=tk.NORMAL)
            self.btn_refresh.config(state=tk.NORMAL)
            self.btn_help.config(state=tk.NORMAL)
        else:
            self.btn_create.config(state=tk.NORMAL)
            self.btn_upload.config(state=tk.NORMAL)
            self.btn_download.config(state=tk.NORMAL)
            self.btn_edit.config(state=tk.NORMAL)
            self.btn_delete.config(state=tk.NORMAL)
            self.btn_refresh.config(state=tk.NORMAL)
            self.btn_help.config(state=tk.NORMAL)

    def center_window(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def setup_style(self):
        style = ttk.Style()
        style.configure("Modern.Treeview", rowheight=26, font=("微软雅黑",9), background="#F8F9FA")
        style.configure("Modern.Treeview.Heading", font=("微软雅黑",9,"bold"), background="#D8DEE9", foreground="#2E3440")

    def auto_load_repo(self):
        if self.last_repo:
            self.load_repo()

    def parse_repo_url(self, url):
        patterns = [r"gitee\.com/([^/]+)/([^/?#]+)", r"gitee\.com/api/v5/repos/([^/]+)/([^/]+)"]
        for p in patterns:
            match = re.search(p, url)
            if match: return match.group(1), match.group(2)
        return None, None

    def load_repo(self):
        self.token = self.entry_token.get().strip()
        repo_url = self.entry_repo.get().strip()
        self.owner, self.repo = self.parse_repo_url(repo_url)

        if not self.owner or not self.repo:
            messagebox.showerror("错误", "仓库链接格式不正确")
            return

        if not self.token:
            self.read_only_mode = True
            messagebox.showinfo("只读模式", "未填写 Token → 仅支持查看/下载")
        else:
            self.read_only_mode = False
            self.crypto.save_config(self.token, repo_url)

        self.set_button_state()
        self.refresh_tree()
        self.btn_load.config(bg="#A3BE8C", text="已加载")
        self.root.title(f"Gitee 管理器 - {self.owner}/{self.repo}")

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.path_map.clear()
        self.load_dir("", "")

    def load_dir(self, parent_node, path):
        try:
            url = f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{path}"
            params = {"access_token": self.token} if self.token else {}
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            items = r.json()
            if not isinstance(items, list): items = [items]

            for item in items:
                name = item["name"]
                typ = item["type"]
                size = item.get("size", 0)
                full_path = os.path.join(path, name).replace("\\", "/")
                node = self.tree.insert(parent_node, "end", text=name, values=(f"{size} B"))
                self.path_map[node] = (full_path, typ)
                if typ == "dir": self.tree.insert(node, "end")
        except Exception as e: pass

    def on_folder_open(self, event):
        node = self.tree.focus()
        if not node or node not in self.path_map: return
        path, typ = self.path_map[node]
        if typ != "dir": return
        for child in self.tree.get_children(node): self.tree.delete(child)
        self.load_dir(node, path)

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item: return
        path, typ = self.path_map[item[0]]
        if typ == "file" and path.lower().endswith(self.edit_ext):
            self.open_edit_window()

    def get_selected(self):
        item = self.tree.selection()
        if not item: return None
        return self.path_map[item[0]]

    # ====================== 编辑文件 ======================
    def open_edit_window(self):
        if self.read_only_mode:
            messagebox.showwarning("只读", "只读模式无法编辑")
            return
        sel = self.get_selected()
        if not sel or sel[1] != "file":
            messagebox.showinfo("提示", "请选择文本文件")
            return
        file_path, _ = sel
        if not file_path.lower().endswith(self.edit_ext):
            messagebox.showwarning("不支持", "仅支持文本文件编辑")
            return

        try:
            url = f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{file_path}"
            params = {"access_token": self.token} if self.token else {}
            data = requests.get(url, params=params, timeout=15).json()
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            sha = data["sha"]
        except Exception as e:
            messagebox.showerror("错误", f"加载文件失败：{str(e)}")
            return

        win = tk.Toplevel(self.root)
        win.title(f"编辑：{os.path.basename(file_path)}")
        win.geometry("800x600")

        text_editor = scrolledtext.ScrolledText(win, font=("微软雅黑", 10), wrap=tk.WORD)
        text_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_editor.insert("1.0", content)

        def save_file():
            new_content = text_editor.get("1.0", tk.END).rstrip("\n")
            try:
                encoded = base64.b64encode(new_content.encode("utf-8")).decode()
                update_url = f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{file_path}"
                payload = {
                    "access_token": self.token,
                    "message": f"更新 {os.path.basename(file_path)}",
                    "content": encoded,
                    "sha": sha
                }
                res = requests.put(update_url, json=payload, timeout=15)
                res.raise_for_status()
                messagebox.showinfo("成功", "文件已保存到 Gitee 仓库！")
                win.destroy()
                self.refresh_tree()
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(btn_frame, text="保存到仓库", command=save_file, bg="#2d8cf0", fg="white", padx=10, pady=4).pack(side=tk.RIGHT)

    # ====================== 新建文件夹 ======================
    def create_folder(self):
        if self.read_only_mode:
            messagebox.showwarning("只读", "只读模式无法新建")
            return
        sel = self.get_selected()
        parent = ""
        if sel:
            p, t = sel
            parent = p if t == "dir" else os.path.dirname(p)
            parent = parent.replace("\\", "/")

        name = simpledialog.askstring("新建文件夹", "输入名称：", parent=self.root)
        if not name or not name.strip():
            messagebox.showwarning("提示", "名称不能为空")
            return
        name = name.strip()
        folder = os.path.join(parent, name).replace("\\", "/")
        keep = f"{folder}/.gitkeep"
        content = base64.b64encode(b"keep").decode()

        try:
            u = f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{keep}"
            d = {"access_token": self.token, "message": f"创建 {name}", "content": content}
            requests.post(u, json=d, timeout=15)
            messagebox.showinfo("成功", f"已创建：{folder}")
            self.refresh_tree()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    # ====================== 上传 ======================
    def upload_file(self):
        if self.read_only_mode:
            messagebox.showwarning("只读", "无法上传")
            return
        sel = self.get_selected()
        parent = ""
        if sel:
            p, t = sel
            parent = p if t == "dir" else os.path.dirname(p)
            parent = parent.replace("\\", "/")

        fp = filedialog.askopenfilename()
        if not fp: return
        fn = os.path.basename(fp)
        target = os.path.join(parent, fn).replace("\\", "/")
        with open(fp, "rb") as f:
            c = base64.b64encode(f.read()).decode()
        try:
            u = f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{target}"
            d = {"access_token": self.token, "message": f"上传 {fn}", "content": c}
            requests.post(u, json=d, timeout=15)
            messagebox.showinfo("成功", f"已上传")
            self.refresh_tree()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    # ====================== 下载 ======================
    def download_file(self):
        sel = self.get_selected()
        if not sel:
            messagebox.showinfo("提示", "请选择文件")
            return
        p, t = sel
        if t == "dir":
            messagebox.showwarning("提示", "不能下载目录")
            return
        try:
            u = f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{p}"
            params = {"access_token": self.token} if self.token else {}
            data = requests.get(u, params=params, timeout=15).json()
            raw = base64.b64decode(data["content"])
            save = filedialog.asksaveasfilename(initialfile=os.path.basename(p))
            if save:
                with open(save, "wb") as f:
                    f.write(raw)
                messagebox.showinfo("成功", "下载完成")
        except Exception as e:
            messagebox.showerror("失败", str(e))

    # ====================== 删除 ======================
    def delete_file(self):
        if self.read_only_mode:
            messagebox.showwarning("只读", "无法删除")
            return
        sel = self.get_selected()
        if not sel: return
        p, t = sel

        if t == "dir":
            if not messagebox.askyesno("确认", f"删除文件夹：{p}？"):
                return
            self.del_folder(p)
        else:
            if not messagebox.askyesno("确认", f"删除文件：{p}？"):
                return
            try:
                u = f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{p}"
                sha = requests.get(u, params={"access_token": self.token}).json()["sha"]
                requests.delete(u, json={"access_token": self.token, "message": "del", "sha": sha})
            except:
                pass
        self.refresh_tree()
        messagebox.showinfo("完成", "已删除")

    def del_folder(self, path):
        try:
            u = f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{path}"
            items = requests.get(u, params={"access_token": self.token}).json()
            if not isinstance(items, list): items = [items]
            for it in items:
                fp = f"{path}/{it['name']}"
                if it["type"] == "file":
                    sha = requests.get(f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{fp}",
                                       params={"access_token": self.token}).json()["sha"]
                    requests.delete(f"{self.base_api}/repos/{self.owner}/{self.repo}/contents/{fp}",
                                    json={"access_token": self.token, "message": "del", "sha": sha})
                else:
                    self.del_folder(fp)
        except:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = GiteeTreeManager(root)
    root.mainloop()
