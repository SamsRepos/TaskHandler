import os
import subprocess
import signal
import json
import wx

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

class Task:
  def __init__(self, name, cmd, cwd):
    self.name    = name
    self.cmd     = cmd
    self.cwd     = cwd
    self.running = False

  def start(self):
    SW_MINIMISE = 6
    info = subprocess.STARTUPINFO()
    info.dwFlags = subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = SW_MINIMISE

    print(f"Preparing to start task: {self.name}")
    print(f" - Setting cwd to: {self.cwd}")
    cwd_stack.push(self.cwd)
    print(f" - cwd set to: {os.getcwd()}")
    print(f" - command: {self.cmd}")
    self.process = subprocess.Popen(self.cmd, cwd=self.cwd, creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=info)
    print(f" - task started, pid: {self.process.pid}")
    cwd_stack.pop()
    print(f" - cwd restored to: {os.getcwd()}")
    print()
    self.running = True
    return self.process
  
  def kill(self):
    self.process.kill()
    self.running = False

tasks = []

JSON_TASKS_NAME = "tasks"
JSON_NAME_KEY   = 'name'
JSON_CMD_KEY    = 'cmd'
JSON_CWD_KEY    = 'cwd'

with open( "tasks.json") as tasks_json_file:
  tasks_data = json.load(tasks_json_file)
  for task_data in tasks_data[JSON_TASKS_NAME]:
    task = Task(
      name=task_data[JSON_NAME_KEY],
      cmd=task_data[JSON_CMD_KEY],
      cwd=task_data[JSON_CWD_KEY]
    )
    tasks.append(task)


# battery_name = "Battery Alerter"
# battery_cwd = r'C:\Python_Tools\BatteryAlerter'
# battery_cmd = 'python battery_alerter.py' # r'b.bat'
# battery_task = Task(name=battery_name, cmd=battery_cmd, cwd=battery_cwd)
# tasks.append(battery_task)

# reconnecter_name = "Reconnecter"
# reconnecter_cwd = r'C:\Python_Tools\Reconnecter'
# reconnecter_cmd = r'python reconnecter.py' # r'r.bat'
# reconnecter_task = Task(name=reconnecter_name, cmd=reconnecter_cmd, cwd=reconnecter_cwd)
# tasks.append(reconnecter_task)


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

class GuiFrame(wx.Frame):

  def __init__(self):
    super().__init__(None, title="Tasks", pos=(50, 60), size=(850, 150))
    panel = GuiPanel(self)


if __name__ == '__main__':

  # if prompt_yn("Start all tasks?"):
  #   for task in tasks:
  #     task.start()
  # else:
  #   for task in tasks:
  #     if prompt_yn(f"Start {task.name}?"):
  #       task.start()

  app = wx.App()
  frame = GuiFrame()
  frame.Show()
  app.MainLoop()
  
  if any(task.running for task in tasks):
    if prompt_yn("Kill all?"):
      for task in tasks:
        task.kill()
