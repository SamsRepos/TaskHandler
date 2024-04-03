import os
import subprocess
import json
import wx
import threading
from time import sleep
from datetime import datetime

def datetime_formatted(dt):
  #return dt.strftime('%H:%M:%S %d/%m/%Y')
  return dt.strftime('%d/%m/%Y, %H:%M:%S')

def console_output(str=""):
  if str != "":
    print(f"{datetime_formatted(datetime.now())}: {str}")
  else:
    print()

def start_thread(func, *args):
  thread = threading.Thread(target=func, args=args)
  thread.daemon = True
  thread.start()

def prompt_yn(prompt):
  prompt += " Y/N:"
  input_str = ''
  while (input_str != 'Y') and (input_str != 'N'):
    input_str = input(prompt).upper()
  return (input_str.upper() == 'Y')

class CwdStack:
  def __init__(self):
    self.list = []
    self.push(os.getcwd())

  def push(self, path):
    self.list.append(path)
    os.chdir(path)

  def pop(self):
    self.list.pop()
    os.chdir(self.list[-1])

cwd_stack = CwdStack()

SW_MINIMISE = 6
task_startupinfo             = subprocess.STARTUPINFO()
task_startupinfo.dwFlags     = subprocess.STARTF_USESHOWWINDOW
task_startupinfo.wShowWindow = SW_MINIMISE

class Task:
  def __init__(self, name, cmd, cwd):
    self.name    = name
    self.cmd     = cmd
    self.cwd     = cwd
    self.running = False

  def start(self):
    console_output(f"Preparing to start task: {self.name}")
    console_output(f" - Setting cwd to: {self.cwd}")
    cwd_stack.push(self.cwd)
    console_output(f" - cwd set to: {os.getcwd()}")
    console_output(f" - command: {self.cmd}")
    self.process = subprocess.Popen(self.cmd, cwd=self.cwd, creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=task_startupinfo)
    console_output(f" - task started, pid: {self.process.pid}")
    cwd_stack.pop()
    console_output(f" - cwd restored to: {os.getcwd()}")
    console_output()
    self.running = True
    return self.process
  
  def kill(self):
    console_output(f"Preparing to kill task: {self.name}, pid: {self.process.pid}")
    self.process.kill()
    self.running = False
    console_output(f" - task killed")
    console_output()
    

  def check_running(self):
    if self.running:
      poll_res = self.process.poll()
      if poll_res != None:
        self.running = False
        console_output(f"Task ended: {self.name}")
        console_output(f" - Final output: {poll_res}")
        console_output()

tasks = []

def check_tasks_running():
  for task in tasks:
    task.check_running()

JSON_FILE_PATH = 'tasks.json'

JSON_TASKS_NAME = "tasks"
JSON_NAME_KEY   = 'name'
JSON_CMD_KEY    = 'cmd'
JSON_CWD_KEY    = 'cwd'
JSON_ACTIVE_KEY = 'active'

with open(JSON_FILE_PATH) as tasks_json_file:
  tasks_data = json.load(tasks_json_file)
  for task_data in tasks_data[JSON_TASKS_NAME]:
    if task_data[JSON_ACTIVE_KEY]:
      task = Task(
        name=task_data[JSON_NAME_KEY],
        cmd=task_data[JSON_CMD_KEY],
        cwd=task_data[JSON_CWD_KEY]
      )
      tasks.append(task)


class TaskTool:

  def __init__(self, task, panel):
    self.task = task

    self.panel = panel
    
    self.run_button = wx.Button(panel, label=f"Run {task.name}")
    self.run_button.Bind(wx.EVT_BUTTON, self.on_click_run)
    self.run_button.Enable(task.running == False)

    self.kill_button = wx.Button(panel, label=f"Kill {task.name}")
    self.kill_button.Bind(wx.EVT_BUTTON, self.on_click_kill)
    self.kill_button.Enable(task.running == True)

    self.info_label = wx.StaticText(panel)
    self.update_info_label()

    self.sizer = wx.BoxSizer(wx.HORIZONTAL)
    self.sizer.Add(self.run_button)
    self.sizer.Add(self.kill_button)
    self.sizer.Add(self.info_label)

  def on_click_run(self, event):
    self.run()
    self.panel.update_top_buttons()

  def on_click_kill(self, event):
    self.kill()
    self.panel.update_top_buttons()

  def run(self):
    if self.task.running == False:
      self.task.start()
      self.run_button.Disable()
      self.kill_button.Enable()
      self.update_info_label()

  def kill(self):
    if self.task.running == True:
      self.task.kill()
      self.run_button.Enable()
      self.kill_button.Disable()
      self.update_info_label()    
  
  def update_info_label(self):
    task = self.task
    name = task.name
    if task.running:
      pid = task.process.pid
      self.info_label.SetLabel(f'{name} running, pid: {pid}')
    else:
      cmd = task.cmd
      cwd = task.cwd
      self.info_label.SetLabel(f'{name} not running. (Runs "{cmd}" at {cwd})')

  def update(self):
    self.update_info_label()
    self.run_button.Enable(self.task.running == False)
    self.kill_button.Enable(self.task.running == True)
      

class GuiPanel(wx.Panel):

  def __init__(self, parent):
    super().__init__(parent)

    main_sizer = wx.BoxSizer(wx.VERTICAL)

    top_sizer = wx.BoxSizer(wx.HORIZONTAL)
    self.run_all_button = wx.Button(self, label="Run All")
    self.run_all_button.Bind(wx.EVT_BUTTON, self.run_all)
    top_sizer.Add(self.run_all_button)
    self.kill_all_button = wx.Button(self, label="Kill All")
    self.kill_all_button.Bind(wx.EVT_BUTTON, self.kill_all)
    top_sizer.Add(self.kill_all_button)
    self.update_top_buttons()
    main_sizer.Add(top_sizer)

    self.task_tools = []
 
    for task in tasks:
      task_tool = TaskTool(task, self)
      self.task_tools.append(task_tool)
      main_sizer.Add(task_tool.sizer)


    self.SetSizer(main_sizer)

  def run_all(self, event):
    for task_tool in self.task_tools:
      task_tool.run()
      self.update_top_buttons()

  def kill_all(self, event):
    for task_tool in self.task_tools:
      task_tool.kill()
      self.update_top_buttons()
  
  def update_top_buttons(self):
    if any(task.running for task in tasks):
      self.kill_all_button.Enable()
    else:
      self.kill_all_button.Disable()
    
    if any(task.running == False for task in tasks):
      self.run_all_button.Enable()
    else:
      self.run_all_button.Disable()

  def update_all(self):
    self.update_top_buttons()
    for task_tool in self.task_tools:
      task_tool.update()

gui_running = False

class GuiFrame(wx.Frame):

  def __init__(self):
    super().__init__(None, title="Tasks", pos=(50, 60), size=(850, 150))
    self.panel = GuiPanel(self)
    global gui_running
    gui_running = True
    self.Bind(wx.EVT_CLOSE, self.on_close)
  
  def on_close(self, event):
    global gui_running
    gui_running = False
    self.Destroy()
    

SECONDS_BETWEEN_TASKS_CHECK = 0.5

def main_loop(frame):
  while gui_running:
    check_tasks_running()
    wx.CallAfter(frame.panel.update_all)
    sleep(SECONDS_BETWEEN_TASKS_CHECK)


if __name__ == '__main__':
  app = wx.App()
  frame = GuiFrame()
  start_thread(main_loop, frame)
  frame.Show()
  app.MainLoop()

  check_tasks_running()  
  if any(task.running for task in tasks):
    console_output("Tasks still running: ")
    for task in tasks:
      if task.running:
        console_output(f"  - {task.name} - pid:{task.process.pid}")
    if prompt_yn("Kill all?"):
      for task in tasks:
        task.kill()
