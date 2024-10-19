import logging
import os
import time
import tkinter as tk
import json
import threading
import requests
import datetime

def setup_custom_logger(name):
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

class OverlayApp:
    def __init__(self):
        # Initialize path and main window
        self.path = None
        self.root = tk.Tk()
        self.root.overrideredirect(True)  
        self.root.attributes("-topmost", True) 
        self.root.geometry("10x10")
        self.root.configure(bg='black')
        self.root.attributes("-alpha", 0.5)

        # Initialize variables
        self.first_run = True
        self.last_line_index = self.last_access = self.bountycycles = 0
        self.start = self.end = self.elapsed = self.best_elapsed = 0
        self.start_bool = self.stage_bool = self.parse_success = self.good_bounty = False
        self.start_time = self.counts = self.stages_int = 0
        self.stage_time = self.stage_start = self.stage_end = self.stage_elapse = self.elapsed_prev = 0
        self.stages_start = ["ResIntro", "AssIntro", "CapIntro", "CacheIntro", "HijackIntro", "FinalIntro"]
        self.stages_translate_start = {"ResIntro":"Rescue", "AssIntro":"Assassinate", "CapIntro":"Capture", "CacheIntro":"Cache", "HijackIntro":"Drone", "FinalIntro":"Capture"}
        self.stages_translate_end = {"ResWin":"Rescue", "AssWin":"Assassinate", "CapWin":"Capture", "CacheWin":"Cache", "HijackWin":"Drone", "FinalWin":"Capture"}
        self.stages_end = ["ResWin", "AssWin", "CapWin", "CacheWin", "HijackWin", "FinalWin"]
        self.tent_mapping = {"TentA": "Tent A: ", "TentB": "Tent B: ", "TentC": "Tent C: "}
        self.stage_to_index = {"Rescue": 0,"Assassinate": 1,"Capture": 2,"Cache": 3,"Drone": 4}
        self.dataset = []  # Store inliers
        self.mean = 0  # Running average
        self.stage = ""
        self.best_stage_elapses = [0,0,0,0,0]

        # Create labels
        self.label1 = tk.Label(self.root, text="", fg="white", bg="black",
                              font=('Times New Roman', 15, ''))
        self.label2 = tk.Label(self.root, text="", fg="white", bg="black",
                              font=('Times New Roman', 15, ''))
        self.label1.pack(fill="both", expand=True)
        self.label2.pack(fill="both", expand=True)

        self.label1.bind("<Button-1>", self.start_drag)
        self.label1.bind("<ButtonRelease-1>", self.stop_drag)
        self.label1.bind("<B1-Motion>", self.on_drag)
        self.label2.bind("<Button-1>", self.start_drag)
        self.label2.bind("<ButtonRelease-1>", self.stop_drag)
        self.label2.bind("<B1-Motion>", self.on_drag)

        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0

        # # Configure window position
        self.width = max(self.label1.winfo_reqwidth(), self.label2.winfo_reqwidth()) + 2  # Add padding
        height = 50    # Fixed height
        self.screen_width = self.root.winfo_screenwidth()
        self.x = (self.screen_width / 2) - (self.width / 2)
        self.y = 0
        self.center = self.x + (self.width / 2)
        self.root.geometry(f'{self.width}x{height}+{int(self.x)}+{int(self.y)}')

        # Set up logger
        self.logger = setup_custom_logger('Aya Bounty Tracker')

        self.path = os.path.join(os.getenv('LOCALAPPDATA'), "Warframe", "EE.log")

        # Fetching bounty data
        wanted_bounties = requests.get("https://gist.githubusercontent.com/ManInTheWallPog/d9cc2c83379a74ef57f0407b0d84d9b2/raw/").content
        bounty_translation = requests.get("https://gist.githubusercontent.com/ManInTheWallPog/02dfd3efdd62ed5b7061dd2e62324fa3/raw/").content
        self.wanted_bounties = json.loads(wanted_bounties.decode('utf-8'))
        self.bounty_translation = json.loads(bounty_translation.decode('utf-8'))

    def start_drag(self, event):
        self.dragging = True
        self.offset_x = event.x
        self.offset_y = event.y

    def stop_drag(self, _):
        self.dragging = False

    def on_drag(self, event):
        if self.dragging:
            self.x = self.root.winfo_pointerx() - self.offset_x
            self.y = self.root.winfo_pointery() - self.offset_y
            self.center = self.x + (self.width/2)
            self.root.geometry(f"+{int(self.x)}+{int(self.y)}")

    def get_last_n_lines(self, file_name):
        current_last_index = self.last_line_index

        with open(file_name, 'r', encoding="utf-8", errors='ignore') as read_obj:
            # Move the cursor to the end of the file
            read_obj.seek(0, os.SEEK_END)
            # Get the current position of pointer i.e eof
            last_line = read_obj.tell()
            if current_last_index == 0:
                self.last_line_index = last_line
                return  # No lines to yield if the index is 0
            
            if last_line < current_last_index:
                return  # Return early if there are no new lines

            while True:
                read_obj.seek(self.last_line_index)
                line = read_obj.readline()
                if line.endswith('\n'):
                    # Yield each line as it is read
                    current_last_index += len(line)
                    self.last_line_index = current_last_index
                    yield line.strip()
                else:
                    time.sleep(0.1)
                    self.last_line_index = current_last_index  # Update index

    def update_overlay(self, text, text_color):
        # Update label if necessary
        if text != 'same' and text_color != 'same':
            self.label1.config(text=text, fg=text_color)

        best_stages = ""
        if self.stage in self.stage_to_index:
            index = self.stage_to_index[self.stage]
            best_stages = str(datetime.timedelta(seconds=self.best_stage_elapses[index]))

        # Convert the times to a readable format
        finish = str(datetime.timedelta(seconds=self.start_time if self.start_bool else self.elapsed))
        best = str(datetime.timedelta(seconds=self.best_elapsed))
        stage = str(datetime.timedelta(seconds=self.stage_time if self.stage_bool else self.stage_elapse))
        mean = str(datetime.timedelta(seconds=self.mean))

        # Ensure millisecond precision
        def append_milliseconds(time_str):
            return time_str[:11] if '.' in time_str else time_str + ".000"

        finish = append_milliseconds(finish)
        best = append_milliseconds(best)
        mean = append_milliseconds(mean)
        stage = append_milliseconds(stage)
        best_stages = append_milliseconds(best_stages)

        # Update label with formatted string
        if best_stages == ".000":
            self.label2.config(text=f" Bounties Completed: {self.bountycycles}  Timer: {finish}  "
                                f"Best Time: {best}  Avg. Time: {mean} ")
        else:
            self.label2.config(text=f" Bounties Completed: {self.bountycycles}  Timer: {finish}  "
                                f"Best Time: {best}  Avg. Time: {mean}  Stage Timer: {stage}  Best {self.stage}: {best_stages} ")

        # Update window size
        self.root.update_idletasks()
        self.width = max(self.label1.winfo_reqwidth(), self.label2.winfo_reqwidth()) + 2  # Add padding
        height = 50    # Fixed height

        # Calculate starting coordinates for the window
        self.x = self.center - (self.width / 2)

        self.root.geometry(f'{self.width}x{height}+{int(self.x)}+{int(self.y)}')

    def calculate_running_average(self, value):
        # Add new value to the data
        self.dataset.append(value)

        if len(self.dataset) < 4:  # Need at least 4 values to reliably compute IQR
            self.mean = sum(self.dataset) / len(self.dataset) if self.dataset else 0
            return
        
        sorted_data = sorted(self.dataset)
        n = len(sorted_data)
        
        Q1 = sorted_data[n // 4]  # 25th percentile
        Q3 = sorted_data[3 * n // 4]  # 75th percentile
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Filter data points that are not outliers
        filtered_data = [x for x in self.dataset if lower_bound <= x <= upper_bound]
        
        # Update mean
        if filtered_data:
            self.mean = sum(filtered_data) / len(filtered_data)
        else:
            self.mean = 0  # No valid data points to average

    def run(self):
        threading.Thread(target=self.clock).start()
        threading.Thread(target=self.data_parser).start()
        self.update_overlay("starting...", "white")
        self.root.mainloop()            

    def clock(self):
        while True:
            if self.start_bool:
                self.update_overlay("same", "same")
                time.sleep(1)
                self.start_time += 1
                if self.stage_bool:
                    self.stage_time += 1
            else:
                time.sleep(0.5)

    def data_parser(self):
        while True:
            try:
                while True:
                    time.sleep(0.1)
                    self.parse_success = False
                    try:
                        for data in self.get_last_n_lines(self.path):
                            if self.first_run == True:
                                self.first_run = False
                                self.update_overlay("Waiting for bounty", "white")
                            if not data and not self.first_run:
                                continue
                            self.parse_lines(data)
                            self.elapse(data)
                            if self.parse_success:
                                self.update_overlay("same", "same")
                    except Exception as e:
                        self.logger.info(f"Error reading EE.log1 {e}")
            except Exception as e:
                self.logger.info(f"Error reading EE.log2 {e}")
                time.sleep(1)

    def parse_lines(self, data):
        for line in range(1):
            line_data = data.split()
            if not line_data:
                continue
            try:
                #Extract key line info and check conditions
                line_key = ' '.join(line_data[1:-1])
                if line_key not in (
                    'Net [Info]: Set squad mission:',
                    'Script [Info]: ThemedSquadOverlay.lua: LoadLevelMsg received. Client joining mission in-progress:',
                    'Net [Info]: MatchingServiceWeb::ProcessSquadMessage received MISSION message'
                ):
                    continue
                
                data_string = ' '.join(line_data[-1:])  # Capture the last part after splitting

                # Extract JSON data
                json_start_index = data_string.find("{")
                json_end_index = data_string.rfind("}") + 1
                if any(index == -1 for index in [json_start_index, json_end_index]):
                    continue
                json_data = data_string[json_start_index:json_end_index].replace(
                    'null', 'None'.replace('true', 'True').replace('false', 'False').replace("True", '"True"')
                )

                # Load the JSON
                try:
                    json_data = json.loads(json_data)
                except Exception as e:
                    self.logger.error(f"Please Report this String1: {e} | Line: {line_data}")
                    continue

                # Validate the JSON keys
                if not all(key in json_data for key in ['jobTier', 'jobStages', 'job']):
                    continue

                self.parse_success = True
                self.stages_int = len(json_data['jobStages'])
                stages = [self.bounty_translation.get(stage, stage) for stage in json_data['jobStages']]
                if any(stage not in self.bounty_translation for stage in json_data['jobStages']):
                    count = 0
                    for stage in stages:
                        index = stage.rfind("/") + 1
                        stages[count] = stages[count][index:].replace("Dynamic", "").replace("Narmer", "")
                        count += 1
                
                stages_string = " -> ".join(stages)
                tent = next((label for key, label in self.tent_mapping.items() if key in json_data['jobId']), "Konzu:  ")
                if any(stage not in self.wanted_bounties for stage in json_data['jobStages']):
                    # Update overlay with translation in red
                    self.update_overlay(tent + stages_string, "red")
                    self.good_bounty = False
                    continue
                # Valid stages found, update overlay with translation in green
                self.update_overlay(tent + stages_string, "green")
                if self.good_bounty == False:
                    print(stages_string)
                    self.good_bounty = True

            except Exception as e:
                self.logger.error(f"Please Report this String4: {e} | Line: {line_data}")
                continue
                
    def elapse(self, data):
        for line in range(1):
            line_data = data.split()
            if not line_data:
                continue  # Skip empty lines
            
            # Attempt to convert the first part of the line to float
            try:
                timestamp = float(line_data[0])  # Extract the timestamp
            except ValueError:
                continue  # Skip to the next line if conversion fails

            message = ' '.join(line_data[1:])

            try:
                if message in ('Script [Info]: EidolonMP.lua: EIDOLONMP: Going back to hub',
                               'Script [Info]: TopMenu.lua: Abort: host/no session'):
                    self.start_time = self.elapsed = self.stage_time = self.stage_elapse = 0
                    self.start_bool = self.stage_bool = False
                    self.counts = 0
                    self.parse_success = True

                elif message in (
                    'Net [Info]: MISSION_READY message: 1',
                    'Net [Info]: SetSquadMissionReady(1)'
                ):
                    self.start = timestamp
                    self.start_time = 0
                    self.start_bool = True
                    self.counts = 0
                    self.parse_success = True
                elif 'Sys [Info]: GiveItem Queuing resource load for Transmission:' in message:
                    if "BountyFail" in message:
                        self.start_time = self.elapsed = self.stage_time = self.stage_elapse = 0
                        self.start_bool = self.stage_bool = False
                        self.counts = 0
                    #Stage Start
                    elif any(stage in message for stage in self.stages_start):
                        self.stage_start = timestamp
                        self.stage_time = 0
                        self.stage_bool = True
                        stage = next((stage for stage in self.stages_start if stage in message), "")
                        self.stage = self.stages_translate_start[stage]
                    #Stage End
                    elif any(stage in message for stage in self.stages_end):
                        self.stage_end = timestamp
                        if self.stage_start != 0:
                            self.stage_elapse = self.stage_end - self.stage_start
                        stage = next((stage for stage in self.stages_end if stage in message), "")
                        self.stage = self.stages_translate_end[stage]
                        if self.stage in self.stage_to_index:
                            index = self.stage_to_index[self.stage]
                            # Check the conditions for updating the best_stage_elapses
                            if (self.best_stage_elapses[index] == 0) or (self.stage_elapse <= self.best_stage_elapses[index]):
                                if self.stage_elapse >= 0:
                                    self.best_stage_elapses[index] = round(self.stage_elapse, 3)
                        self.stage_start = 0
                        self.stage_bool = False
                    self.parse_success = True

                elif 'Script [Info]: EidolonMissionComplete.lua: EidolonMissionComplete:: Got Reward:' in message: 
                    self.counts += 1
                    if self.counts == self.stages_int:
                        self.end = timestamp
                        self.start_bool = False
                        self.bountycycles += 1
                        #Calculate elapsed time if conditions are met
                        if self.end > self.start:
                            self.elapsed = self.end - self.start
                        if (self.best_elapsed == 0) or (self.elapsed <= self.best_elapsed):
                            self.best_elapsed = round(self.elapsed, 3)
                        if self.elapsed != self.elapsed_prev and self.elapsed != 0:
                            self.calculate_running_average(self.elapsed)    
                            self.elapsed_prev = self.elapsed
                            print(f"Best Time: {self.best_elapsed} Avg. Time: {round(self.mean, 3)} Best Rescue: {self.best_stage_elapses[0]} Best Assassinate: {self.best_stage_elapses[1]} Best Capture: {self.best_stage_elapses[2]} Best Cache: {self.best_stage_elapses[3]} Best Drone: {self.best_stage_elapses[4]}")
                    self.parse_success = True
                     
            except Exception as e:
                self.logger.error(f"Please Report this String5: {e} | Line: {line_data}")

if __name__ == "__main__":
    app = OverlayApp()
    app.run()
