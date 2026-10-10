"""Open Product Research settings and save the customer's choices locally."""
import argparse
import json
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from amazon_catalog import Catalog
from settings import execute


class SetupWindow:
    def __init__(self, root, workspace, timezone='', catalog=None):
        self.root = root
        self.workspace = Path(workspace).resolve()
        self.config_path = self.workspace / 'product-research.config.json'
        self.previous = json.loads(self.config_path.read_text(encoding='utf-8-sig')) if self.config_path.exists() else {}
        self.catalog = catalog or Catalog(self.workspace / 'work/product-research-catalog.json')
        self.events = queue.Queue()
        self.generation = 0
        self.busy = False
        self.markets = []
        self.levels = []
        self.path = []
        self.saved = False
        self.restore = self.previous.get('category_path', [])
        root.title('Product Research · 选品设置')
        root.geometry(f'880x{min(790, root.winfo_screenheight() - 100)}')
        root.minsize(800, 550)
        root.configure(bg='#fff8f2')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background='#fff8f2')
        style.configure('TLabel', background='#fff8f2', font=('Microsoft YaHei UI', 10))
        style.configure('TCheckbutton', background='#fff8f2', font=('Microsoft YaHei UI', 10))
        style.configure('Title.TLabel', foreground='#bd4c08', font=('Microsoft YaHei UI', 20, 'bold'))
        style.configure('Accent.TButton', foreground='white', background='#ef711b', padding=8)
        canvas = tk.Canvas(root, background='#fff8f2', highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient='vertical', command=canvas.yview)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        frame = ttk.Frame(canvas, padding=24)
        frame_id = canvas.create_window((0, 0), window=frame, anchor='nw')
        frame.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(frame_id, width=event.width))
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text='Product Research', style='Title.TLabel').grid(row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(frame, text='选择研究范围，保存后由 Codex 采集并生成 HTML 报告。').grid(row=1, column=0, columnspan=3, sticky='w', pady=(4, 18))
        ttk.Label(frame, text='目标平台').grid(row=2, column=0, sticky='w', padx=(0, 16))
        platform = ttk.Combobox(frame, values=['Amazon'], state='readonly')
        platform.current(0)
        platform.grid(row=2, column=1, sticky='ew')
        ttk.Label(frame, text='目标国家').grid(row=3, column=0, sticky='w', pady=12)
        self.country = ttk.Combobox(frame, state='readonly')
        self.country.grid(row=3, column=1, sticky='ew')
        self.country.bind('<<ComboboxSelected>>', lambda _: self.select_market())
        self.refresh_markets = ttk.Button(frame, text='更新国家列表', command=lambda: self.load_markets(True))
        self.refresh_markets.grid(row=3, column=2, padx=(12, 0))
        ttk.Label(frame, text='目标品类').grid(row=4, column=0, sticky='nw', pady=8)
        self.category_frame = ttk.Frame(frame)
        self.category_frame.grid(row=4, column=1, sticky='ew')
        self.category_frame.columnconfigure(0, weight=1)
        self.refresh_categories = ttk.Button(frame, text='更新当前分类树', command=self.refresh_tree)
        self.refresh_categories.grid(row=4, column=2, sticky='n', padx=(12, 0))
        self.selection = tk.StringVar(value='先选择国家，再选择大类或下级类目。')
        ttk.Label(frame, textvariable=self.selection, wraplength=730).grid(row=5, column=0, columnspan=3, sticky='w', pady=8)
        self.custom = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text='自定义榜单链接（默认使用所选类目）', variable=self.custom, command=self.toggle_links).grid(row=6, column=0, columnspan=3, sticky='w')
        self.urls = [tk.StringVar(), tk.StringVar()]
        self.url_entries = []
        for i, name in enumerate(('Best Sellers', 'New Releases')):
            ttk.Label(frame, text=name).grid(row=7+i, column=0, sticky='w', pady=5)
            entry = ttk.Entry(frame, textvariable=self.urls[i], state='readonly')
            entry.grid(row=7+i, column=1, columnspan=2, sticky='ew')
            self.url_entries.append(entry)
        self.scheduled = tk.BooleanVar(value=bool(self.previous.get('schedule_enabled')))
        ttk.Checkbutton(frame, text='启用 Codex 每日定时计划', variable=self.scheduled, command=self.toggle_schedule).grid(row=9, column=0, columnspan=3, sticky='w', pady=(16, 6))
        time_frame = ttk.Frame(frame)
        time_frame.grid(row=10, column=0, columnspan=3, sticky='ew')
        ttk.Label(time_frame, text='运行时间 HH:MM').pack(side='left')
        self.time = tk.StringVar(value=self.previous.get('time') or '')
        self.time_entry = ttk.Entry(time_frame, textvariable=self.time, width=9)
        self.time_entry.pack(side='left', padx=12)
        ttk.Label(time_frame, text='时区').pack(side='left')
        self.timezone = tk.StringVar(value=self.previous.get('timezone') or timezone)
        self.timezone_entry = ttk.Entry(time_frame, textvariable=self.timezone, width=28)
        self.timezone_entry.pack(side='left', padx=12)
        self.default_output = tk.BooleanVar(value=not self.previous.get('output_directory') or Path(self.previous['output_directory']) == self.workspace / 'outputs')
        ttk.Checkbutton(frame, text='报告保存到当前任务的 outputs 文件夹', variable=self.default_output, command=self.toggle_output).grid(row=11, column=0, columnspan=3, sticky='w', pady=(16, 6))
        self.output = tk.StringVar(value=self.previous.get('output_directory') or str(self.workspace / 'outputs'))
        self.output_entry = ttk.Entry(frame, textvariable=self.output)
        self.output_entry.grid(row=12, column=0, columnspan=2, sticky='ew')
        self.browse_button = ttk.Button(frame, text='浏览文件夹…', command=self.browse)
        self.browse_button.grid(row=12, column=2, padx=(12, 0))
        ttk.Label(frame, text='先访问公开页面；实际需要登录时，Codex 再提示在浏览器登录。\n合计目标 200 个不重复商品；两榜去重后不足时保留真实缺口。', wraplength=730).grid(row=13, column=0, columnspan=3, sticky='w', pady=16)
        self.status = tk.StringVar()
        ttk.Label(frame, textvariable=self.status, wraplength=730, foreground='#b94700').grid(row=14, column=0, columnspan=3, sticky='w')
        actions = ttk.Frame(frame)
        actions.grid(row=15, column=0, columnspan=3, sticky='e', pady=16)
        ttk.Button(actions, text='取消', command=root.destroy).pack(side='left', padx=12)
        self.save_button = ttk.Button(actions, text='保存并开始', command=self.save, style='Accent.TButton')
        self.save_button.pack(side='left')
        self.toggle_schedule()
        self.toggle_output()
        self.poll_id = self.root.after(100, self.poll)
        self.root.bind('<Destroy>', self.on_destroy, add=True)
        self.load_markets()

    def on_destroy(self, event):
        if event.widget is self.root:
            self.root.after_cancel(self.poll_id)

    def run(self, operation, callback):
        self.busy = True
        self.save_button.state(['disabled'])
        self.refresh_markets.state(['disabled'])
        self.refresh_categories.state(['disabled'])
        generation = self.generation
        def worker():
            try:
                result = operation()
                self.events.put((generation, callback, result, None))
            except Exception as error:
                self.events.put((generation, callback, None, str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            generation, callback, result, error = self.events.get_nowait()
            if generation == self.generation:
                self.busy = False
                self.save_button.state(['!disabled'])
                self.refresh_markets.state(['!disabled'])
                self.refresh_categories.state(['!disabled'])
                if error:
                    self.status.set('读取失败：' + error + ' 可由 Codex 使用正常浏览器读取后重开设置。')
                else:
                    self.status.set('选项来自 Amazon；已缓存的列表不会自动刷新。')
                    callback(result)
        except queue.Empty:
            pass
        self.poll_id = self.root.after(100, self.poll)

    def load_markets(self, refresh=False):
        self.generation += 1
        self.status.set('正在读取国家列表…')
        self.run(lambda: self.catalog.markets(refresh), self.set_markets)

    def set_markets(self, markets):
        self.markets = markets
        self.country['values'] = [m['label'] for m in markets]
        old_country = self.previous.get('country')
        index = next((i for i, m in enumerate(markets) if m['country'] == old_country), None)
        self.country.set('')
        self.clear_levels(0)
        self.path = []
        if index is not None:
            self.country.current(index)
            self.select_market(restore=True)

    def market(self):
        index = self.country.current()
        return self.markets[index] if index >= 0 else None

    def select_market(self, restore=False):
        self.generation += 1
        self.clear_levels(0)
        self.path = []
        if not restore:
            self.restore = []
        self.custom.set(False)
        self.update_selection()
        self.toggle_links()
        origin = self.market()['origin']
        self.status.set('正在读取该国家的大类…')
        self.run(lambda: self.catalog.categories(origin + '/Best-Sellers/zgbs'), lambda items: self.add_level(items, 0))

    def refresh_tree(self):
        if self.market():
            self.catalog.invalidate_categories(self.market()['origin'])
            self.select_market()

    def clear_levels(self, depth):
        for box, _ in self.levels[depth:]:
            box.destroy()
        del self.levels[depth:]

    def add_level(self, items, depth):
        if self.path and self.previous.get('category_path') == self.path and len(self.restore) <= depth:
            previous_urls = [s['url'] for s in self.previous.get('sources', [])]
            if len(previous_urls) == 2 and previous_urls != [v.get() for v in self.urls]:
                self.custom.set(True)
                for variable, url in zip(self.urls, previous_urls):
                    variable.set(url)
                self.toggle_links()
        if not items:
            if depth == 0:
                self.status.set('该站点未返回可选大类；请由 Codex 检查实际页面。')
            return
        box = ttk.Combobox(self.category_frame, state='readonly', values=(['全部（保留上级类目）'] if depth else []) + [i['label'] for i in items])
        box.grid(row=depth, column=0, sticky='ew', pady=3)
        self.levels.append((box, items))
        box.bind('<<ComboboxSelected>>', lambda _, d=depth: self.select_category(d))
        if depth:
            box.current(0)
        if len(self.restore) > depth:
            index = next((i for i, item in enumerate(items) if item['key'] == self.restore[depth]['key']), None)
            if index is not None:
                box.current(index + bool(depth))
                self.select_category(depth, restore=True)

    def select_category(self, depth, restore=False):
        self.generation += 1
        box, items = self.levels[depth]
        index = box.current() - bool(depth)
        self.clear_levels(depth + 1)
        self.path = self.path[:depth]
        if not restore:
            self.restore = []
        if index >= 0:
            self.path.append(items[index])
        self.update_selection()
        if index >= 0:
            url = items[index]['url']
            self.status.set('正在读取下级类目…')
            self.run(lambda: self.catalog.categories(url), lambda children: self.add_level(children, depth + 1))
        else:
            self.busy = False
            for button in (self.save_button, self.refresh_markets, self.refresh_categories):
                button.state(['!disabled'])

    def update_selection(self):
        self.selection.set('当前范围：' + ' › '.join(c['label'] for c in self.path) if self.path else '请选择大类；下级选择“全部”可保留上级。')
        if not self.custom.get():
            urls = [self.path[-1]['url'], self.market()['origin'] + '/gp/new-releases/' + self.path[-1]['key']] if self.path else ['', '']
            for variable, value in zip(self.urls, urls):
                variable.set(value)

    def toggle_links(self):
        for entry in self.url_entries:
            entry.configure(state='normal' if self.custom.get() else 'readonly')
        if not self.custom.get():
            self.update_selection()

    def toggle_schedule(self):
        for entry in (self.time_entry, self.timezone_entry):
            entry.configure(state='normal' if self.scheduled.get() else 'disabled')

    def toggle_output(self):
        default = self.default_output.get()
        if default:
            self.output.set(str(self.workspace / 'outputs'))
        self.output_entry.configure(state='disabled' if default else 'normal')
        self.browse_button.configure(state='disabled' if default else 'normal')

    def browse(self):
        directory = filedialog.askdirectory(parent=self.root, title='选择 HTML 报告保存位置', initialdir=self.output.get() or str(self.workspace))
        if directory:
            self.output.set(directory)

    def save(self):
        if self.busy:
            return
        try:
            market = self.market()
            if not market or not self.path:
                raise ValueError('请选择国家及至少一个大类。')
            execute('save', {
                'country': market['country'],
                'category_keys': [item['key'] for item in self.path],
                'custom_sources': [v.get().strip() for v in self.urls],
                'schedule_enabled': self.scheduled.get(),
                'time': self.time.get().strip(),
                'timezone': self.timezone.get().strip(),
                'output_directory': None if self.default_output.get() else self.output.get(),
            }, self.workspace, catalog=self.catalog)
        except (ValueError, OSError) as error:
            messagebox.showerror('配置未保存', str(error), parent=self.root)
            return
        self.saved = True
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--timezone', default='')
    args = parser.parse_args()
    root = tk.Tk()
    app = SetupWindow(root, args.workspace, args.timezone)
    root.mainloop()
    print(json.dumps({'saved': app.saved, 'config_path': str(app.config_path) if app.saved else None}))


if __name__ == '__main__':
    main()
