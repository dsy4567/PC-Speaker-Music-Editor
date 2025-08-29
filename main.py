#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import re
import time
import os
import platform
import sys
from threading import Timer


def debounce(wait_time):
    """防抖装饰器"""
    def decorator(func):
        def debounced(*args, **kwargs):
            # 如果已有定时器，则取消
            if hasattr(debounced, "_timer"):
                debounced._timer.cancel()

            # 设置新的定时器
            debounced._timer = Timer(wait_time, func, args=args, kwargs=kwargs)
            debounced._timer.start()

        return debounced
    return decorator


# 音符频率映射表 (C调基准)
NOTE_FREQUENCIES = {
    -1: [130.81, 146.83, 164.81, 174.61, 196.00, 220.00, 246.94],  # 低音
    0: [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88],   # 中音
    1: [523.25, 587.33, 659.25, 698.46, 783.99, 880.00, 987.77]    # 高音
}

# 调性偏移映射 (半音数)
KEY_OFFSETS = {
    "C": 0, "C♯": 1, "Db": 1, "D": 2, "D♯": 3, "Eb": 3,
    "E": 4, "F": 5, "F♯": 6, "Gb": 6, "G": 7, "G♯": 8,
    "Ab": 8, "A": 9, "A♯": 10, "Bb": 10, "B": 11
}

MULTIPLE = {
    "0.125": 0.125,
    "0.25": 0.25,
    "0.375": 0.375,
    "0.5": 0.5,
    "0.625": 0.625,
    "0.75": 0.75,
    "0.875": 0.875,
    "1.0": 1.0,
    "1.125": 1.125,
    "1.25": 1.25,
    "1.375": 1.375,
    "1.5": 1.5,
    "1.625": 1.625,
    "1.75": 1.75,
    "2.0": 2.0,
    "2.25": 2.25,
    "2.5": 2.5,
    "2.75": 2.75,
    "3.0": 3.0
}


class BeepPlayer:
    def __init__(self, device):
        self.device = device
        self.process = None
        # self.playing = False

    def play_notes(self, notes, default_duration, default_delay, key_offset, bpm):
        """播放音符序列"""
        self.stop()
        if not notes:
            return

        try:
            # args = ["beep", "--device", self.device]
            args = ["beep"]

            for i, note in enumerate(notes):
                # 解析音符参数
                pitch, delay, duration, key_offset, bpm = self.parse_note(
                    note, default_duration, default_delay, key_offset, bpm
                )

                # 计算频率（考虑调性偏移）
                freq = self.calculate_frequency(pitch, key_offset)
                if freq is None:
                    continue

                # 添加音符参数
                    # 添加新音符标记
                if i > 0:
                    args.append("-n")
                if pitch[1] != -1:
                    args.extend(["-f", str(freq), "-l", str(duration)])
                    if delay > 0:
                        args.extend(["-D", str(delay)])
                else:
                    args.extend(["-f", "1", "-l", str(duration + delay)])

            # self.playing = True
            self.process = subprocess.Popen(args)
            start = time.time()
            self.process.wait()
            print('已结束，用时', time.time() - start)

        except Exception as e:
            messagebox.showerror("播放错误", f"播放失败: {str(e)}")

    def stop(self):
        """停止播放"""
        if self.process:
            self.process.terminate()
            # self.playing = False

    def parse_note(self, note_str, default_duration, default_delay, key_offset, bpm):
        """解析音符字符串"""
        # 默认值
        pitch = 0
        duration = default_duration
        delay = default_delay
        offset = key_offset

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

            # 1 s/n   s/n      str    num
            # 1 delay duration offset bpm
            # 2 delay duration offset
            # 3 delay duration
            # 4 duration offset bpm
            # 5 duration offset
            # 6 duration
            # 7

            # 解析第四/三个参数（bpm），对后面 note 均生效 #1,2,4
            if len(params) > 2 and params[-1].strip():
                try:
                    # 1,4
                    bpm = int(params[-1])
                except ValueError:
                    pass
            default_delay = default_duration = 60000 / bpm

            # 解析第一个参数（假定为延时，可能为持续时间） #1,2,3
            if params[0].strip():
                try:
                    # 支持倍数表示法 (如 *1.5)
                    if params[0].strip().startswith("*"):
                        factor = float(params[0].strip()[1:])
                        delay = float(default_delay * factor)
                    else:
                        delay = float(params[0].strip())
                except ValueError:
                    pass
            else:
                delay = 0

            # 解析第二/一个参数（持续时间）
            i = 1
            #  1,2,3,4,5
            if len(params) > 1:
                if params[1].strip().startswith("*"):  # 123
                    i = 1
                else:
                    try:
                        # 123
                        float(params[1].strip())
                        i = 1
                    except ValueError:
                        i = 0
                        pass
            else:
                # 4,5,6
                i = 0
            if params[i].strip():
                try:
                    # 支持倍数表示法 (如 *1.5)
                    if params[i].strip().startswith("*"):
                        factor = float(params[i].strip()[1:])
                        duration = float(default_duration * factor)
                    else:
                        duration = float(params[i].strip())
                except ValueError:
                    pass
            if i == 0:
                delay = 0

            # 解析第三/二个参数（调），对后面 note 均生效
            if (len(params) > i + 1) and params[i + 1].strip():
                try:
                    offset = KEY_OFFSETS[params[i + 1]]
                except KeyError:
                    pass
        else:
            delay = 0
            duration = 60000 / bpm

        return pitch, delay, duration, offset, bpm

    def calculate_frequency(self, pitch, key_offset):
        """计算音符频率（考虑调性偏移）"""
        if not pitch:
            return None

        octave, note_index = pitch

        # 检查音符是否有效
        if octave not in NOTE_FREQUENCIES or note_index < -1 or note_index > 6:
            return None

        base_freq = NOTE_FREQUENCIES[octave][note_index]

        # 应用调性偏移（十二平均律）
        return base_freq * (2 ** (key_offset / 12))


class MusicEditor:
    def __init__(self, root: tk.Tk):
        self.autoPlayVar = tk.BooleanVar(value=False)
        self.root = root
        self.root.title("曲谱编辑器")
        self.root.geometry("1024x768")

        # 创建播放器
        self.player = BeepPlayer(
            "/dev/input/by-path/platform-pcspkr-event-spkr")

        # 默认参数
        self.default_bpm = round(60 * 1000 / 300)
        self.default_duration = 300  # 毫秒
        self.default_delay = 300     # 毫秒
        self.key = "C"               # 调性

        # 创建界面
        self.create_widgets()

        self.root.bind("<FocusOut>", self.on_focus_out)

        # # 加载示例曲谱
        # self.load_example()

        # 高亮标签
        self.highlight_tag = "highlight"
        self.score_text.tag_config(self.highlight_tag, background="yellow")

    @debounce(0.05)
    def on_focus_out(self, arg):
        if self.autoPlayVar and self.autoPlayVar.get() and not root.focus_displayof():
            self.play()
            self.autoPlayVar.set(False)

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
            left_frame, width=50, height=25, font=("Courier", 12), wrap=tk.WORD, spacing1=4, spacing2=4, spacing3=4
        )
        self.score_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 右侧控制区
        right_frame = ttk.Frame(main_frame, width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 参数设置
        param_frame = ttk.LabelFrame(right_frame, text="参数设置", padding=10)
        param_frame.pack(fill=tk.X, pady=5)

        # # 默认持续时间
        # ttk.Label(param_frame, text="默认持续时间(ms):").grid(
        #     row=0, column=0, sticky=tk.W)
        # self.duration_var = tk.StringVar(value=str(self.default_duration))
        # ttk.Entry(param_frame, textvariable=self.duration_var,
        #           width=10).grid(row=0, column=1)

        # # 默认延时
        # ttk.Label(param_frame, text="默认延时(ms):").grid(
        #     row=1, column=0, sticky=tk.W)
        # self.delay_var = tk.StringVar(value=str(self.default_delay))
        # ttk.Entry(param_frame, textvariable=self.delay_var,
        #           width=10).grid(row=1, column=1)

        # bpm
        ttk.Label(param_frame, text="bpm:").grid(
            row=1, column=0, sticky=tk.W)
        self.bpm_var = tk.StringVar(value=str(self.default_bpm))
        ttk.Entry(param_frame, textvariable=self.bpm_var,
                  width=10).grid(row=1, column=1)

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

        ttk.Button(btn_frame, text="播放", command=self.play).pack(
            fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="播放选中", command=self.play_selected).pack(
            fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="停止", command=self.stop).pack(
            fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="加载示例", command=self.load_example).pack(
            fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清除", command=self.clear).pack(
            fill=tk.X, pady=2)
        checkbutton = ttk.Checkbutton(
            btn_frame,
            text="窗口失焦自动播放",
            variable=self.autoPlayVar
        )
        checkbutton.pack(fill=tk.X, pady=5)

        # 音符按钮区
        note_frame = ttk.LabelFrame(right_frame, text="快速插入音符", padding=10)
        note_frame.pack(fill=tk.X, pady=5)

        # 休止符
        ttk.Label(note_frame, text="休止符:").pack(anchor=tk.W)
        sp_frame = ttk.Frame(note_frame)
        sp_frame.pack(fill=tk.X)
        ttk.Button(
            sp_frame, text=str("0"), width=3,
            command=lambda: self.insert_note(
                f"0(*{self.duration_factor_var.get().replace("0.", '.')})".replace("(*1)", ''),
                True
            )
        ).pack(side=tk.LEFT, padx=2)

        # 高音区
        ttk.Label(note_frame, text="高音:").pack(anchor=tk.W, pady=(5, 0))
        high_frame = ttk.Frame(note_frame)
        high_frame.pack(fill=tk.X)
        for i in range(1, 8):
            ttk.Button(
                high_frame, text=f"+{i}", width=3,
                command=lambda n=i: self.insert_note(
                    f"+{n}(*{self.duration_factor_var.get().replace("0.", '.')})".replace("(*1)", ''),
                    True
                )
            ).pack(side=tk.LEFT, padx=2)

        # 中音区
        ttk.Label(note_frame, text="中音:").pack(anchor=tk.W)
        mid_frame = ttk.Frame(note_frame)
        mid_frame.pack(fill=tk.X)
        for i in range(1, 8):
            ttk.Button(
                mid_frame, text=str(i), width=3,
                command=lambda n=i: self.insert_note(
                    f"{n}(*{self.duration_factor_var.get().replace("0.", '.')})".replace("(*1)", ''),
                    True
                )
            ).pack(side=tk.LEFT, padx=2)

        # 低音区
        ttk.Label(note_frame, text="低音:").pack(anchor=tk.W, pady=(5, 0))
        low_frame = ttk.Frame(note_frame)
        low_frame.pack(fill=tk.X)
        for i in range(1, 8):
            ttk.Button(
                low_frame, text=f"-{i}", width=3,
                command=lambda n=i: self.insert_note(
                    f"-{n}(*{self.duration_factor_var.get().replace("0.", '.')})".replace("(*1)", ''),
                    True
                )
            ).pack(side=tk.LEFT, padx=2)

        # 参数按钮区
        param_btn_frame = ttk.LabelFrame(right_frame, text="参数设置", padding=10)
        param_btn_frame.pack(fill=tk.X, pady=5)

        # 延时倍数
        # ttk.Label(param_btn_frame, text="延时倍数:").grid(
        #     row=0, column=0, sticky=tk.W)
        # self.delay_factor_var = tk.StringVar(value="0")
        # ttk.Entry(param_btn_frame, textvariable=self.delay_factor_var,
        #           width=6).grid(row=0, column=1, padx=5)

        # ttk.Label(param_btn_frame, text="延时倍数:").grid(
        #     row=0, column=0, sticky=tk.W)
        # self.delay_factor_var = tk.StringVar(value="0")
        # key_combo = ttk.Combobox(
        #     param_btn_frame, textvariable=self.delay_factor_var,
        #     values=list(MULTIPLE.keys()), width=6
        # )
        # key_combo.grid(row=0, column=1)

        # 长音倍数
        # ttk.Label(param_btn_frame, text="长音倍数:").grid(
        #     row=0, column=2, sticky=tk.W)
        # self.duration_factor_var = tk.StringVar(value="1")
        # ttk.Entry(param_btn_frame, textvariable=self.duration_factor_var,
        #           width=6).grid(row=0, column=3, padx=5)

        ttk.Label(param_btn_frame, text="长音倍数:").grid(
            row=0, column=0, sticky=tk.W)
        self.duration_factor_var = tk.StringVar(value="1")
        key_combo = ttk.Combobox(
            param_btn_frame, textvariable=self.duration_factor_var,
            values=list(MULTIPLE.keys()), width=6
        )
        key_combo.grid(row=0, column=1)

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
        example = """3(*0,*1) 2(*0,*1) 1(*0,*1) 2(*0,*1) #我有一只
3(*0,*1) 3(*0,*1) 3(*0,*2) #小羊羔
2(*0,*1) 2(*0,*1) 2(*0,*2) #小羊羔
3(*0,*1) 5(*0,*1) 5(*0,*2) #小羊羔

3(*0,*1) 2(*0,*1) 1(*0,*1) 2(*0,*1) #长着一身
3(*0,*1) 3(*0,*1) 3(*0,*1) 1(*0,*1) #洁白绒毛
2(*0,*1) 2(*0,*1) 3(*0,*1) 2(*0,*1) #洁白绒
1(*0,*2) #毛"""
        self.score_text.insert(tk.END, example)

    def clear(self):
        """清除编辑框"""
        response = messagebox.askyesno(
            title="确认操作",
            message="确定要清除吗？",
            icon="warning"
        )
        if response:
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
            bpm = self.default_bpm = int(self.bpm_var.get())
            self.default_duration = self.default_delay = 60 * 1000 / bpm
            self.key = self.key_var.get()
        except ValueError:
            messagebox.showerror("参数错误", "bpm 必须是整数")
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
            args=(notes, self.default_duration,
                  self.default_delay, key_offset, self.default_bpm),
            daemon=True
        ).start()

    def stop(self):
        """停止播放"""
        self.player.stop()


if platform.system() != 'Linux':
    print("错误：此脚本仅支持 Linux 系统", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    try:
        os.system('sudo -n renice -10 ' + str(os.getpid()))
    except:
        print('无法设置优先级')
    root = tk.Tk()
    app = MusicEditor(root)
    root.mainloop()
