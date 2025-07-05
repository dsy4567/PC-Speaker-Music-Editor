#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import re

# 音符频率映射表 (C调基准)
NOTE_FREQUENCIES = {
    -1: [130.81, 146.83, 164.81, 174.61, 196.00, 220.00, 246.94],  # 低音
    0: [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88],   # 中音
    1: [523.25, 587.33, 659.25, 698.46, 783.99, 880.00, 987.77]    # 高音
}

# 调性偏移映射 (半音数)
KEY_OFFSETS = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
}

class BeepPlayer:
    def __init__(self, device):
        self.device = device
        self.process = None
        self.playing = False

    def play_notes(self, notes, default_duration, default_delay, key_offset):
        """播放音符序列"""
        if not notes:
            return

        try:
            args = ["beep", "--device", self.device]

            for i, note in enumerate(notes):
                # 解析音符参数
                pitch, delay, duration = self.parse_note(
                    note, default_duration, default_delay
                )

                # 计算频率（考虑调性偏移）
                freq = self.calculate_frequency(pitch, key_offset)
                if freq is None:
                    continue

                # 添加新音符标记
                if i > 0:
                    args.append("-n")

                # 添加音符参数
                args.extend(["-f", str(freq), "-l", str(duration)])
                if delay > 0:
                    args.extend(["-D", str(delay)])

            self.playing = True
            self.process = subprocess.Popen(args)
            self.process.wait()

        except Exception as e:
            messagebox.showerror("播放错误", f"播放失败: {str(e)}")
        finally:
            self.playing = False

    def stop(self):
        """停止播放"""
        if self.playing and self.process:
            self.process.terminate()
            self.playing = False

    def parse_note(self, note_str, default_duration, default_delay):
        """解析音符字符串"""
        # 默认值
        pitch = 0
        duration = default_duration
        delay = default_delay

        # 解析音高部分
        pitch_match = re.match(r"([+-]?)(\d+)", note_str)
        if pitch_match:
            sign = pitch_match.group(1)
            note_num = int(pitch_match.group(2))

            # 确定八度
            if sign == "-":
                pitch = (-1, note_num - 1)
            elif sign == "+":
                pitch = (1, note_num - 1)
            else:
                pitch = (0, note_num - 1)

        # 解析参数部分
        params_match = re.search(r"\(([^)]*)\)", note_str)
        if params_match:
            params = params_match.group(1).split(",")

            # 解析第一个参数（延时）
            if params[0].strip():
                try:
                    # 支持倍数表示法 (如 *1.5)
                    if params[0].strip().startswith("*"):
                        factor = float(params[0].strip()[1:])
                        delay = int(default_delay * factor)
                    else:
                        delay = int(params[0].strip())
                except ValueError:
                    pass

            # 解析第二个参数（持续时间）
            if len(params) > 1 and params[1].strip():
                try:
                    # 支持倍数表示法 (如 *1.5)
                    if params[1].strip().startswith("*"):
                        factor = float(params[1].strip()[1:])
                        duration = int(default_duration * factor)
                    else:
                        duration = int(params[1].strip())
                except ValueError:
                    pass

        return pitch, delay, duration

    def calculate_frequency(self, pitch, key_offset):
        """计算音符频率（考虑调性偏移）"""
        if not pitch:
            return None

        octave, note_index = pitch

        # 检查音符是否有效
        if octave not in NOTE_FREQUENCIES or note_index < 0 or note_index > 6:
            return None

        base_freq = NOTE_FREQUENCIES[octave][note_index]

        # 应用调性偏移（十二平均律）
        return base_freq * (2 ** (key_offset / 12))


class MusicEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("曲谱编辑器")
        self.root.geometry("900x650")

        # 创建播放器
        self.player = BeepPlayer("/dev/input/by-path/platform-pcspkr-event-spkr")

        # 默认参数
        self.default_duration = 300  # 毫秒
        self.default_delay = 100     # 毫秒
        self.key = "C"               # 调性

        # 创建界面
        self.create_widgets()

        # 加载示例曲谱
        self.load_example()

        # 高亮标签
        self.highlight_tag = "highlight"
        self.score_text.tag_config(self.highlight_tag, background="yellow")

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧编辑区
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 曲谱编辑框
        ttk.Label(left_frame, text="曲谱编辑:").pack(anchor=tk.W)
        self.score_text = scrolledtext.ScrolledText(
            left_frame, width=50, height=25, font=("Courier", 12)
        )
        self.score_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 右侧控制区
        right_frame = ttk.Frame(main_frame, width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 参数设置
        param_frame = ttk.LabelFrame(right_frame, text="参数设置", padding=10)
        param_frame.pack(fill=tk.X, pady=5)

        # 默认持续时间
        ttk.Label(param_frame, text="默认持续时间(ms):").grid(row=0, column=0, sticky=tk.W)
        self.duration_var = tk.StringVar(value=str(self.default_duration))
        ttk.Entry(param_frame, textvariable=self.duration_var, width=10).grid(row=0, column=1)

        # 默认延时
        ttk.Label(param_frame, text="默认延时(ms):").grid(row=1, column=0, sticky=tk.W)
        self.delay_var = tk.StringVar(value=str(self.default_delay))
        ttk.Entry(param_frame, textvariable=self.delay_var, width=10).grid(row=1, column=1)

        # 调性选择
        ttk.Label(param_frame, text="调性:").grid(row=2, column=0, sticky=tk.W)
        self.key_var = tk.StringVar(value=self.key)
        key_combo = ttk.Combobox(
            param_frame, textvariable=self.key_var,
            values=list(KEY_OFFSETS.keys()), width=8
        )
        key_combo.grid(row=2, column=1)

        # 控制按钮
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="播放", command=self.play).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="播放选中", command=self.play_selected).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="停止", command=self.stop).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="加载示例", command=self.load_example).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清除", command=self.clear).pack(fill=tk.X, pady=2)

        # 音符按钮区
        note_frame = ttk.LabelFrame(right_frame, text="快速插入音符", padding=10)
        note_frame.pack(fill=tk.X, pady=5)

        # 中音区
        ttk.Label(note_frame, text="中音:").pack(anchor=tk.W)
        mid_frame = ttk.Frame(note_frame)
        mid_frame.pack(fill=tk.X)
        for i in range(1, 8):
            ttk.Button(
                mid_frame, text=str(i), width=3,
                command=lambda n=i: self.insert_note(str(n), True)
            ).pack(side=tk.LEFT, padx=2)

        # 低音区
        ttk.Label(note_frame, text="低音:").pack(anchor=tk.W, pady=(5,0))
        low_frame = ttk.Frame(note_frame)
        low_frame.pack(fill=tk.X)
        for i in range(1, 8):
            ttk.Button(
                low_frame, text=f"-{i}", width=3,
                command=lambda n=i: self.insert_note(f"-{n}", True)
            ).pack(side=tk.LEFT, padx=2)

        # 高音区
        ttk.Label(note_frame, text="高音:").pack(anchor=tk.W, pady=(5,0))
        high_frame = ttk.Frame(note_frame)
        high_frame.pack(fill=tk.X)
        for i in range(1, 8):
            ttk.Button(
                high_frame, text=f"+{i}", width=3,
                command=lambda n=i: self.insert_note(f"+{n}", True)
            ).pack(side=tk.LEFT, padx=2)

        # 参数按钮区
        param_btn_frame = ttk.LabelFrame(right_frame, text="参数设置", padding=10)
        param_btn_frame.pack(fill=tk.X, pady=5)

        # 延时倍数
        ttk.Label(param_btn_frame, text="延时倍数:").grid(row=0, column=0, sticky=tk.W)
        self.delay_factor_var = tk.StringVar(value="1.0")
        ttk.Entry(param_btn_frame, textvariable=self.delay_factor_var, width=6).grid(row=0, column=1, padx=5)

        # 长音倍数
        ttk.Label(param_btn_frame, text="长音倍数:").grid(row=0, column=2, sticky=tk.W)
        self.duration_factor_var = tk.StringVar(value="1.0")
        ttk.Entry(param_btn_frame, textvariable=self.duration_factor_var, width=6).grid(row=0, column=3, padx=5)

        # 按钮行
        btn_row = ttk.Frame(param_btn_frame)
        btn_row.grid(row=1, column=0, columnspan=4, pady=5)

        ttk.Button(
            btn_row, text="延时", width=6,
            command=lambda: self.insert_note(f"(*{self.delay_factor_var.get()})", False)
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_row, text="长音", width=6,
            command=lambda: self.insert_note(f"(,*{self.duration_factor_var.get()})", False)
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_row, text="带参数", width=6,
            command=lambda: self.insert_note(
                f"(*{self.delay_factor_var.get()},*{self.duration_factor_var.get()})",
                False
            )
        ).pack(side=tk.LEFT, padx=2)

    def insert_note(self, text, add_space=True):
        """插入音符到编辑框"""
        # 获取当前光标位置
        cursor_pos = self.score_text.index(tk.INSERT)

        # 如果文本不为空且不是开头，添加空格
        if add_space and self.score_text.get("1.0", tk.END).strip():
            # 检查光标前是否有空格
            prev_char = self.score_text.get(f"{cursor_pos}-1c", cursor_pos)
            if prev_char and not prev_char.isspace():
                text = " " + text

        self.score_text.insert(tk.INSERT, text)
        self.score_text.focus_set()

    def load_example(self):
        """加载小星星示例"""
        self.clear()
        example = """1 1 5 5 6 6 5
4 4 3 3 2 2 1
5 5 4 4 3 3 2
5 5 4 4 3 3 2
1 1 5 5 6 6 5
4 4 3 3 2 2 1"""
        self.score_text.insert(tk.END, example)

    def clear(self):
        """清除编辑框"""
        self.score_text.delete(1.0, tk.END)


    def get_notes(self, selected_only=False):
        """从编辑框获取音符列表"""
        if selected_only:
            try:
                # 获取选中文本
                text = self.score_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                if not text:
                    return []
            except tk.TclError:
                return []
        else:
            # 获取全部文本
            text = self.score_text.get(1.0, tk.END).strip()
            if not text:
                return []

        # === 添加的注释处理代码开始 ===
        # 处理注释：移除所有注释行（以 # 开头的行）
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            stripped_line = line.strip()
            # 保留非注释行
            if stripped_line and not stripped_line.startswith('#'):
                cleaned_lines.append(stripped_line)

        # 重新组合文本
        cleaned_text = ' '.join(cleaned_lines)
        # === 添加的注释处理代码结束 ===

        # 分割音符（支持空格和换行分隔）
        return re.split(r"\s+", cleaned_text) if cleaned_text else []

    def play(self):
        """播放整个曲谱"""
        self.play_with_selection(False)

    def play_selected(self):
        """播放选中部分曲谱"""
        self.play_with_selection(True)

    def play_with_selection(self, selected_only):
        """播放曲谱（可选择仅播放选中部分）"""
        # 获取参数
        try:
            self.default_duration = int(self.duration_var.get())
            self.default_delay = int(self.delay_var.get())
            self.key = self.key_var.get()
        except ValueError:
            messagebox.showerror("参数错误", "持续时间、延时必须是整数")
            return

        if self.key not in KEY_OFFSETS:
            messagebox.showerror("参数错误", "无效的调性")
            return

        # 获取音符
        notes = self.get_notes(selected_only)
        if not notes:
            if selected_only:
                messagebox.showinfo("提示", "未选中任何内容")
            else:
                messagebox.showinfo("提示", "曲谱为空")
            return

        # 停止当前播放
        self.stop()

        # 在新线程中播放
        key_offset = KEY_OFFSETS[self.key]
        threading.Thread(
            target=self.player.play_notes,
            args=(notes, self.default_duration, self.default_delay, key_offset),
            daemon=True
        ).start()

    def stop(self):
        """停止播放"""
        self.player.stop()


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicEditor(root)
    root.mainloop()
