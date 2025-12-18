import flet as ft
import requests
import os
import time
import zipfile
import json
import pandas as pd

def main(page: ft.Page):
    # 1. 设置 App 基础样式
    page.title = "三国杀数据解析工具 (纯净版)"
    page.window_width = 500
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK 

    # 定义数据保存的基础目录
    BASE_DIR = os.path.join(os.getcwd(), "sgs_data")

    # 2. 界面元素定义
    log_view = ft.Column(scroll=ft.ScrollMode.AUTO, height=400)
    progress_bar = ft.ProgressBar(width=400, color="blue", bgcolor="#222222", visible=False)
    status_text = ft.Text("准备就绪", size=16)

    # --- 辅助函数：打印日志到屏幕 ---
    def app_print(message, color="white"):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_view.controls.append(ft.Text(f"[{timestamp}] {message}", color=color))
        page.update()
        log_view.scroll_to(offset=-1, duration=100)

    # ============================
    # 功能 A: 下载并解压
    # ============================
    def run_download(e):
        btn_download.disabled = True
        progress_bar.visible = True
        page.update()

        try:
            app_print("🚀 开始初始化下载任务...", "cyan")
            if not os.path.exists(BASE_DIR):
                os.makedirs(BASE_DIR)
                app_print(f"📂 创建目录: {BASE_DIR}")

            base_url = "https://web.sanguosha.com/220/u3d/AppCfgData/"
            
            for i in range(1, 8):
                server_filename = f"list{i}.sgs"
                local_filename = f"list{i}.zip"
                full_url = f"{base_url}{server_filename}"
                file_path = os.path.join(BASE_DIR, local_filename)

                app_print(f"⬇️ [{i}/7] 正在下载: {server_filename}...")
                
                try:
                    response = requests.get(full_url, stream=True, timeout=15)
                    if response.status_code == 200:
                        with open(file_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        app_print(f"✅ 下载完成", "green")
                    else:
                        app_print(f"❌ 下载失败: {response.status_code}", "red")
                        continue
                except Exception as dl_err:
                    app_print(f"❌ 网络错误: {dl_err}", "red")
                    continue

                app_print(f"📦 正在解压...", "yellow")
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(BASE_DIR)
                    app_print(f"✨ 解压成功！", "green")
                except Exception as zip_err:
                    app_print(f"⚠️ 解压出错: {zip_err}", "red")

                time.sleep(0.5)

            app_print("🎉 所有下载任务结束！请进行下一步解析。", "green")

        except Exception as err:
            app_print(f"系统错误: {err}", "red")
        
        btn_download.disabled = False
        progress_bar.visible = False
        page.update()

    # ============================
    # 功能 B: 解析 list1 生成物品表
    # ============================
    def run_parse_goods(e):
        btn_goods.disabled = True
        app_print("📊 正在解析 list1.sgs (物品数据)...", "cyan")
        
        sgs_file = os.path.join(BASE_DIR, "list1.sgs")
        excel_file = os.path.join(BASE_DIR, "SGS_物品列表.xlsx")

        if not os.path.exists(sgs_file):
            app_print(f"❌ 找不到文件: {sgs_file}", "red")
            app_print("请先点击“下载并解压数据”按钮！", "yellow")
            btn_goods.disabled = False
            page.update()
            return

        try:
            with open(sgs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            goods_list = data.get('sys_gs_dbs_fs_goodsbaseinfo', {}).get('root', {}).get('goodslist', {}).get('goods', [])
            
            if not goods_list:
                app_print("❌ 数据解析失败：找不到 goods 节点", "red")
            else:
                app_print(f"✅ 提取到 {len(goods_list)} 条数据", "green")
                
                df_goods = pd.DataFrame(goods_list)
                rename_map = {
                    "a": "物品ID", "b": "物品名称", "e": "类型ID",
                    "g": "有效期(秒)", "j": "价值", "l": "礼包内容", "m": "图标ID"
                }
                df_goods = df_goods.rename(columns=rename_map)
                
                df_goods.to_excel(excel_file, index=False)
                app_print(f"💾 Excel 已保存: {excel_file}", "green")
                status_text.value = f"物品表生成成功！"

        except Exception as err:
            app_print(f"❌ 解析错误: {err}", "red")

        btn_goods.disabled = False
        page.update()

    # ============================
    # 功能 C: 解析 list2 生成台词表
    # ============================
    def run_parse_voice(e):
        btn_voice.disabled = True
        app_print("🎵 正在解析 list2.sgs (武将台词)...", "cyan")

        sgs_file = os.path.join(BASE_DIR, "list2.sgs")
        excel_file = os.path.join(BASE_DIR, "SGS_武将台词.xlsx")

        if not os.path.exists(sgs_file):
            app_print(f"❌ 找不到文件: {sgs_file}", "red")
            app_print("请先点击“下载并解压数据”按钮！", "yellow")
            btn_voice.disabled = False
            page.update()
            return

        try:
            with open(sgs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            hero_music_list = data.get('sys_h5_music', {}).get('root', {}).get('heromusic', [])

            if not hero_music_list:
                app_print("❌ 未找到 heromusic 数据节点", "red")
            else:
                app_print(f"✅ 提取到 {len(hero_music_list)} 条语音数据", "green")
                
                df = pd.DataFrame(hero_music_list)
                column_mapping = {
                    'a': '武将ID', 'b': '皮肤ID', 'd': '技能名称', 'e': '事件类型',
                    'f': '语音路径_男', 'g': '语音路径_女', 'm': '台词_男', 'n': '台词_女',
                    'SkinStyle': '皮肤样式', 'author': '画师'
                }
                df = df.rename(columns=column_mapping)
                df = df.fillna('')
                
                df.to_excel(excel_file, index=False)
                app_print(f"💾 Excel 已保存: {excel_file}", "green")
                status_text.value = f"台词表生成成功！"

        except Exception as err:
            app_print(f"❌ 解析错误: {err}", "red")

        btn_voice.disabled = False
        page.update()

    # 3. 创建按钮控件 (已移除 icon 参数)
    btn_download = ft.ElevatedButton("第一步：下载并解压数据", on_click=run_download, height=50)
    btn_goods = ft.ElevatedButton("导出：物品列表 (Excel)", on_click=run_parse_goods)
    btn_voice = ft.ElevatedButton("导出：武将台词 (Excel)", on_click=run_parse_voice)

    # 4. 页面布局
    page.add(
        ft.Column(
            [
                ft.Text("三国杀资源提取器 v1.0", size=30, weight="bold"),
                ft.Divider(),
                btn_download,
                progress_bar,
                ft.Divider(),
                ft.Row([btn_goods, btn_voice], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Text("运行日志:", weight="bold"),
                ft.Container(
                    content=log_view,
                    border=ft.border.all(1, "#444444"),
                    border_radius=10,
                    padding=10,
                    bgcolor="#111111",
                    height=300
                ),
                status_text
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        )
    )

# 运行 App
ft.app(target=main)