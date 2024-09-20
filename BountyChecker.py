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
        self.start_bool = self.drone_bool = self.stage_bool = False
        self.start_time = self.counts = self.stages_int = self.drone_start = self.drone_end = self.drone_elapse = self.drone_time = 0
        self.stage_time = self.stage_start = self.stage_end = self.stage_elapse = 0
        self.drone_best = 0
        self.stages_start = ["ResIntro", "AssIntro", "CapIntro", "CacheIntro", "HijackIntro"]
        self.stages_end = ["ResWin","AssWin", "CapWin", "CacheWin", "HijackWin"]
        self.tent_mapping = {"TentA": "Tent A:  ", "TentB": "Tent B:  ", "TentC": "Tent C:  "}

        # Create labels
        self.label1 = tk.Label(self.root, text="", fg="white", bg="black",
                              font=('Times New Roman', 15, ''))
        self.label2 = tk.Label(self.root, text="", fg="white", bg="black",
                              font=('Times New Roman', 15, ''))
        self.label1.pack(fill="both", expand=True)
        self.label2.pack(fill="both", expand=True)

        # Configure window positio
        w, h = 0, 40  # Width and Height
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width / 2) - (w / 2)
        self.root.geometry(f'{w}x{h}+{int(x)}+0')

        # Set up logger
        self.logger = setup_custom_logger('Aya Bounty Tracker')

        self.path = os.getenv('LOCALAPPDATA') + "/Warframe/EE.log"
        
        # Fetching bounty data
        wanted_bounties = requests.get("https://gist.githubusercontent.com/ManInTheWallPog/d9cc2c83379a74ef57f0407b0d84d9b2/raw/").content
        bounty_translation = requests.get("https://gist.githubusercontent.com/ManInTheWallPog/02dfd3efdd62ed5b7061dd2e62324fa3/raw/").content
        self.wanted_bounties = json.loads(wanted_bounties.decode('utf-8'))
        self.bounty_translation = json.loads(bounty_translation.decode('utf-8'))

    def get_last_n_lines(self, file_name):
        # Create an empty list to keep the track of last N lines
        list_of_lines = []
        current_last_index = self.last_line_index

        with open(file_name, 'r', encoding="utf-8", errors='ignore') as read_obj:
            # Move the cursor to the end of the file
            read_obj.seek(0, os.SEEK_END)
            # Get the current position of pointer i.e eof
            last_line = read_obj.tell()
            if current_last_index == 0:
                return list_of_lines, last_line, False
            
            if last_line < current_last_index:
                return list_of_lines, current_last_index, False
            
            read_obj.seek(current_last_index)
            for line in read_obj:
                if line.endswith('\n'):
                    list_of_lines.append(line.strip())
                    current_last_index += len(line)
                else:
                    return list_of_lines, current_last_index - len(line), True  # if a partial line was detected

        return list_of_lines, current_last_index, False

    def update_overlay(self, text, text_color):
        # Update label if necessary
        if text != 'same' and text_color != 'same':
            self.label1.config(text=text, fg=text_color)

        # Initialize drone time tracking
        drone = [0, 0]

        # Convert the times to a readable format
        finish = str(datetime.timedelta(seconds=self.start_time if self.start_bool else self.elapsed))
        drone[0] = str(datetime.timedelta(seconds=self.drone_time if self.drone_bool else self.drone_elapse))
        best = str(datetime.timedelta(seconds=self.best_elapsed))
        drone[1] = str(datetime.timedelta(seconds=self.drone_best))
        stage = str(datetime.timedelta(seconds=self.stage_time if self.stage_bool else self.stage_elapse))

        # Ensure millisecond precision
        def append_milliseconds(time_str):
            return time_str[:11] if '.' in time_str else time_str + ".000"

        finish = append_milliseconds(finish)
        best = append_milliseconds(best)
        drone[0] = append_milliseconds(drone[0])
        drone[1] = append_milliseconds(drone[1])
        stage = append_milliseconds(stage)

        # Update label with formatted string
        self.label2.config(
            text=f" Bounties Completed: {self.bountycycles}  Timer: {finish}  "
                f"Best Time: {best}  Drone Timer: {drone[0]}  Best Drone: {drone[1]}  Stage Timer: {stage} "
        )

        # Update window size
        self.root.update_idletasks()
        width = max(self.label1.winfo_reqwidth(), self.label2.winfo_reqwidth()) + 2  # Add padding
        height = 50    # Fixed height

        # Calculate starting coordinates for the window
        screen_width = self.root.winfo_screenwidth()
        x = (screen_width / 2) - (width / 2)
        y = 0

        self.root.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

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
                if self.drone_bool:
                    self.drone_time += 1
                if self.stage_bool:
                    self.stage_time += 1

    def data_parser(self):
        while True:
            try:
                checkaccesstime = os.path.getmtime(self.path)
                if checkaccesstime != self.last_access:
                    self.last_access = checkaccesstime
                    breaker = True
                    while breaker:
                        try:
                            data, current_last_index, breaker = self.get_last_n_lines(self.path)
                        except Exception as e:
                            self.logger.info(f"Error reading EE.log1 {e}")
                        if self.first_run:
                            self.first_run = False
                            text = "Waiting for bounty"
                            self.update_overlay(text, "white")
                        self.parse_lines(data)
                        self.elapse(data)
                        self.update_overlay("same", "same")
                        self.last_line_index = current_last_index
            except Exception as e:
                self.logger.info(f"Error reading EE.log2 {e}")

    def parse_lines(self, data):
        for i in range(len(data)):
            line_data = data[i].split()
            if (len(line_data) <= 1):
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

                self.stages_int = len(json_data['jobStages'])
                stages = [self.bounty_translation.get(stage, stage) for stage in json_data['jobStages']]
                stages_string = " -> ".join(stages)
                tent = next((label for key, label in self.tent_mapping.items() if key in json_data['jobId']), "Konzu:  ")
                if any(stage not in self.wanted_bounties for stage in json_data['jobStages']):
                    # Update overlay with translation in red
                    self.update_overlay(tent + stages_string, "red")
                    continue
                # Valid stages found, update overlay with translation in green
                self.update_overlay(tent + stages_string, "green")

            except Exception as e:
                self.logger.error(f"Please Report this String4: {e} | Line: {line_data}")
                continue
                
    def elapse(self, data):
        for i in range(len(data)):
            line_data = data[i].split()
            if not line_data:
                continue  # Skip empty lines
            
            # Attempt to convert the first part of the line to float
            try:
                timestamp = float(line_data[0])  # Extract the timestamp
            except ValueError:
                continue  # Skip to the next line if conversion fails

            message = ' '.join(line_data[1:])

            try:
                if message == 'Script [Info]: EidolonMP.lua: EIDOLONMP: Going back to hub':
                    self.drone_time = self.drone_elapse = self.start_time = self.elapsed = self.stage_time = self.stage_elapse = 0
                    self.drone_bool = self.start_bool = self.stage_bool = False
                    self.counts = 0

                elif message in (
                    'Net [Info]: MISSION_READY message: 1',
                    'Net [Info]: SetSquadMissionReady(1)'
                ):
                    self.start = timestamp
                    self.start_time = 0
                    self.start_bool = True
                    self.counts = 0

                elif 'Script [Info]: HudRedux.lua: Queuing new transmission:' in message:
                    if "BountyFail" in message:
                        self.drone_time = self.drone_elapse = self.start_time = self.elapsed = self.stage_time = self.stage_elapse = 0
                        self.drone_bool = self.start_bool = self.stage_bool = False
                        self.counts = 0
                    #Stage Timer
                    elif any(stage in message for stage in self.stages_start):
                        self.stage_start = self.drone_start = timestamp
                        self.stage_time = self.drone_time = 0
                        self.stage_bool = True
                        if "HijackIntro" in message:
                            self.drone_bool = True
                    elif any(stage in message for stage in self.stages_end):
                        self.stage_end = self.drone_end = timestamp
                        if self.stage_start != 0:
                            self.stage_elapse = self.stage_end - self.stage_start
                        if "HijackWin" in message:
                            if self.drone_start != 0:
                                self.drone_elapse = self.stage_elapse
                            if (self.drone_best == 0) or (self.drone_elapse <= self.drone_best):
                                if self.drone_elapse >= 0:
                                    self.drone_best = self.drone_elapse
                        self.stage_start = self.drone_start = 0
                        self.stage_bool = self.drone_bool = False

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
                            self.best_elapsed = self.elapsed
                     
            except Exception as e:
                self.logger.error(f"Please Report this String5: {e} | Line: {line_data}")

if __name__ == "__main__":
    app = OverlayApp()
    app.run()
