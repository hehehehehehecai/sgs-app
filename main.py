import flet as ft
import requests
import os
import time
import zipfile
import json
import pandas as pd
import re
from datetime import datetime

# ================= 配置区域 =================
# 基础配置保持不变
BASE_URL = "https://web.sanguosha.com/220/u3d/AppCfgData/"
LOG_FILE = "update_changes.txt"     # 变更日志文件名
RECORD_FILE = "version_record.json" # 版本记录文件名
# ===========================================

def main(page: ft.Page):
    # 1. 设置 App 界面
    page.title = "三国杀监控 & 分析工具"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.window_width = 500
    page.window_height = 800

    # === 智能路径选择 (适配安卓/电脑) ===
    BASE_DIR = os.path.join(os.getcwd(), "sgs_data")
    try:
        if page.platform == ft.PagePlatform.ANDROID:
            BASE_DIR = "/storage/emulated/0/Download/sgs_data"
    except:
        pass
    
    # 确保目录存在
    if not os.path.exists(BASE_DIR):
        try:
            os.makedirs(BASE_DIR)
        except:
            pass # 可能是权限问题，后续会提示

    # 2. 界面控件
    log_view = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=400) # 日志滚动区
    status_text = ft.Text("等待指令...", size=16, color="yellow")
    progress_bar = ft.ProgressBar(width=400, color="blue", bgcolor="#222222", visible=False)

    # === 辅助函数：打印日志到屏幕 ===
    def app_print(message, color="white"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_view.controls.append(ft.Text(f"[{timestamp}] {message}", color=color))
        page.update()
        log_view.scroll_to(offset=-1, duration=100)

    # === 辅助函数：写变更日志到文件 ===
    def append_to_file_log(content):
        log_path = os.path.join(BASE_DIR, LOG_FILE)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n======== {timestamp} ========\n")
                f.write(content + "\n")
            app_print(f"📝 变更详情已保存到: {LOG_FILE}", "green")
        except Exception as e:
            app_print(f"⚠️ 无法写入日志文件: {e}", "red")

    # ===========================================
    #  核心逻辑：比对与解析 (移植自你的代码)
    # ===========================================
    
    def detect_and_log_changes(new_df, old_excel_path, id_col, name_col, label):
        """比对新旧数据，记录新增项"""
        if not os.path.exists(old_excel_path):
            return # 第一次运行，不比对

        try:
            # 读取旧 Excel (只读两列加速)
            old_df = pd.read_excel(old_excel_path, usecols=[id_col, name_col])
            
            old_ids = set(old_df[id_col].astype(str))
            new_ids = set(new_df[id_col].astype(str))

            # 计算差集
            added_ids = new_ids - old_ids

            if added_ids:
                added_rows = new_df[new_df[id_col].astype(str).isin(added_ids)]
                
                log_msg = f"检测到 [{label}] 更新，新增 {len(added_ids)} 条数据：\n"
                app_print(f"⚡ 发现 {len(added_ids)} 个新增项！", "pink")
                
                for _, row in added_rows.iterrows():
                    item_name = str(row[name_col]) if pd.notna(row[name_col]) else "无名称"
                    item_id = str(row[id_col])
                    log_msg += f"  [+] 新增: {item_name} (ID: {item_id})\n"
                
                # 写入文件
                append_to_file_log(log_msg)
            else:
                app_print(f"ℹ️ {label} 数据无新增ID。", "grey")

        except Exception as e:
            app_print(f"⚠️ 比对差异时出错: {e}", "red")

    # --- 处理 List1 (物品) ---
    def process_list1_goods(sgs_path, output_path):
        app_print(f"📊 解析 List1 (物品)...", "cyan")
        try:
            with open(sgs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            goods_list = data.get('sys_gs_dbs_fs_goodsbaseinfo', {}).get('root', {}).get('goodslist', {}).get('goods', [])
            
            if not goods_list: return

            df_goods = pd.DataFrame(goods_list)
            rename_map = {
                "a": "物品ID", "b": "物品名称", "e": "类型ID",
                "g": "有效期(秒)", "j": "价值", "l": "礼包内容", "m": "图标ID"
            }
            # 防止列不存在报错
            real_rename = {k:v for k,v in rename_map.items() if k in df_goods.columns}
            df_goods = df_goods.rename(columns=real_rename)

            # 比对
            detect_and_log_changes(df_goods, output_path, "物品ID", "物品名称", "List1-物品")

            # 保存
            df_goods.to_excel(output_path, index=False)
            app_print(f"✅ List1 Excel 已生成", "green")
            
        except Exception as e:
            app_print(f"❌ List1 失败: {e}", "red")

    # --- 处理 List2 (语音) ---
    def process_list2_music(sgs_path, output_path):
        app_print(f"📊 解析 List2 (语音)...", "cyan")
        try:
            with open(sgs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            hero_music_list = data.get('sys_h5_music', {}).get('root', {}).get('heromusic', [])
            if not hero_music_list: return

            df = pd.DataFrame(hero_music_list)
            col_map = {
                'a': '武将ID', 'b': '皮肤ID', 'c': '资源索引', 'd': '技能名称',
                'e': '事件类型', 'f': '语音路径_男', 'g': '语音路径_女',
                'm': '台词_男', 'n': '台词_女', 'SkinStyle': '皮肤样式'
            }
            real_map = {k:v for k,v in col_map.items() if k in df.columns}
            df = df.rename(columns=real_map).fillna('')

            # 比对
            detect_and_log_changes(df, output_path, "资源索引", "技能名称", "List2-语音")

            df.to_excel(output_path, index=False)
            app_print(f"✅ List2 Excel 已生成", "green")

        except Exception as e:
            app_print(f"❌ List2 失败: {e}", "red")

    # --- 处理 List6 (技能) ---
    def process_list6_skills(sgs_path, output_path):
        app_print(f"📊 解析 List6 (技能)...", "cyan")
        try:
            with open(sgs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 安全获取嵌套数据
            spells = data.get('cha_spell', {}).get('GameSpells', {}).get('spell', [])
            if not spells: return

            df = pd.DataFrame(spells)

            # 过滤逻辑
            def is_skill(type_str):
                if not isinstance(type_str, str): return False
                return '3' in type_str.split(',')
            
            if 'b' in df.columns:
                skill_df = df[df['b'].apply(is_skill)].copy()
            else:
                skill_df = df

            # 清洗 HTML
            def clean_html(raw_html):
                if not isinstance(raw_html, str): return ""
                return re.sub(re.compile('<.*?>'), '', raw_html).strip()

            if 'o' in skill_df.columns:
                skill_df['clean_desc'] = skill_df['o'].apply(clean_html)
            else:
                skill_df['clean_desc'] = ""

            # 选取需要的列
            cols = {'a': 'ID', 'c': '技能名', 'd': '代码', 'clean_desc': '技能描述'}
            final_cols = {k:v for k,v in cols.items() if k in skill_df.columns}
            output_df = skill_df[list(final_cols.keys())].rename(columns=final_cols)

            # 比对
            detect_and_log_changes(output_df, output_path, "ID", "技能名", "List6-技能")

            output_df.to_excel(output_path, index=False)
            app_print(f"✅ List6 Excel 已生成", "green")

        except Exception as e:
            app_print(f"❌ List6 失败: {e}", "red")

    # ===========================================
    #  主控流程：下载与调度
    # ===========================================
    def run_check_updates(e):
        btn_start.disabled = True
        btn_start.text = "正在运行中..."
        progress_bar.visible = True
        page.update()

        record_path = os.path.join(BASE_DIR, RECORD_FILE)
        
        # 加载本地记录
        records = {}
        if os.path.exists(record_path):
            try:
                with open(record_path, 'r') as f: records = json.load(f)
            except: pass

        has_updates = False
        app_print("🚀 开始检查更新...", "yellow")

        try:
            # 循环检查 list1 到 list7
            for i in range(1, 8):
                file_key = f"list{i}"
                server_filename = f"{file_key}.sgs"
                full_url = f"{BASE_URL}{server_filename}"
                local_zip = os.path.join(BASE_DIR, f"{file_key}.zip")
                local_sgs = os.path.join(BASE_DIR, f"{file_key}.sgs")

                app_print(f"[{i}/7] 检查 {file_key} ...")

                # 1. 获取服务器版本头信息
                try:
                    head_res = requests.head(full_url, timeout=5)
                    if head_res.status_code != 200:
                        app_print(f"  ❌ 跳过 (服务器返回 {head_res.status_code})", "red")
                        continue
                    
                    # 生成版本号 (时间_大小)
                    svr_ver = f"{head_res.headers.get('Last-Modified')}_{head_res.headers.get('Content-Length')}"
                    local_ver = records.get(file_key)

                    # 2. 判断是否需要下载
                    need_download = False
                    if not os.path.exists(local_zip):
                        app_print(f"  📥 本地缺失，准备下载...")
                        need_download = True
                    elif svr_ver != local_ver:
                        app_print(f"  🆕 发现新版本！", "pink")
                        need_download = True
                    else:
                        app_print(f"  ✅ 已是最新", "green")
                        # 即使不下载，如果本地没有解压后的文件，也需要解压一下
                        if not os.path.exists(local_sgs):
                            need_download = True # 复用下载逻辑里的解压部分

                    # 3. 执行下载和解压
                    if need_download:
                        app_print(f"  ⬇️ 正在下载...")
                        r = requests.get(full_url, stream=True, timeout=20)
                        with open(local_zip, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        app_print(f"  📦 解压中...")
                        try:
                            with zipfile.ZipFile(local_zip, 'r') as zf:
                                zf.extractall(BASE_DIR)
                        except:
                            app_print(f"  ⚠️ 解压失败，文件可能损坏", "red")
                            continue
                        
                        # 更新记录
                        records[file_key] = svr_ver
                        has_updates = True

                        # 4. 触发解析与比对
                        if file_key == "list1":
                            process_list1_goods(local_sgs, os.path.join(BASE_DIR, "SGS_物品表.xlsx"))
                        elif file_key == "list2":
                            process_list2_music(local_sgs, os.path.join(BASE_DIR, "SGS_武将语音表.xlsx"))
                        elif file_key == "list6":
                            process_list6_skills(local_sgs, os.path.join(BASE_DIR, "SGS_技能表.xlsx"))

                except Exception as err:
                    app_print(f"  ⚠️ 网络或文件错误: {err}", "red")

            if has_updates:
                with open(record_path, 'w') as f: json.dump(records, f)
                status_text.value = "更新完成！有新数据。"
                status_text.color = "green"
            else:
                status_text.value = "检查结束，暂无更新。"
                status_text.color = "white"

        except Exception as e:
            status_text.value = f"发生错误: {e}"
            status_text.color = "red"

        btn_start.disabled = False
        btn_start.text = "再次检查更新"
        progress_bar.visible = False
        page.update()

    # 3. 页面布局
    btn_start = ft.ElevatedButton("开始检查更新", on_click=run_check_updates, height=50, width=200)

    page.add(
        ft.Column(
            [
                ft.Text("🛡️ 三国杀自动更新监控", size=28, weight="bold"),
                ft.Text(f"数据目录: {BASE_DIR}", size=12, color="grey"),
                ft.Divider(),
                btn_start,
                progress_bar,
                status_text,
                ft.Divider(),
                ft.Text("运行日志 & 变更记录:", weight="bold"),
                ft.Container(
                    content=log_view,
                    bgcolor="#111111",
                    border_radius=10,
                    padding=10,
                    expand=True 
                )
            ],
            spacing=10,
            expand=True
        )
    )

ft.app(target=main)
