import tkinter as tk
from tkinter import scrolledtext
import copy

# Global definitions
PROCESS_NAMES = ["P1", "P2", "P3"]

def initial_matrix():
    """
    Create an initial matrix clock: a dictionary-of-dictionaries
    with all entries set to 0.
    """
    return {p: {q: 0 for q in PROCESS_NAMES} for p in PROCESS_NAMES}

def matrix_to_string(mc):
    """
    Convert a matrix clock (dict-of-dict) into a multi-line string.
    Each row is shown as a list in the order of PROCESS_NAMES.
    """
    rows = []
    for p in PROCESS_NAMES:
        row = [mc[p][q] for q in PROCESS_NAMES]
        rows.append(str(row))
    return "\n".join(rows)

###############################################################################
# Message class: carries message ID, sender, a snapshot of the matrix clock, and content.
###############################################################################
class Message:
    def __init__(self, msg_id, sender, matrix_snapshot, content):
        self.msg_id = msg_id      # e.g., "m0"
        self.sender = sender      # e.g., "P1"
        self.matrix = matrix_snapshot  # Snapshot of sender's matrix clock (dict-of-dict)
        self.content = content    # Chat message text

###############################################################################
# Deliverability check for matrix clocks.
# For a message m sent by process i to be deliverable at process j:
#   - m.matrix[i][i] == local.matrix[i][i] + 1
#   - For every other process k: m.matrix[k][k] <= local.matrix[k][k]
###############################################################################
def is_deliverable(process, message):
    sender = message.sender
    local = process.matrix
    if message.matrix[sender][sender] != local[sender][sender] + 1:
        return False
    for p in PROCESS_NAMES:
        if p != sender:
            if message.matrix[p][p] > local[p][p]:
                return False
    return True

###############################################################################
# Process class: represents a chat client with a matrix clock.
###############################################################################
class Process:
    def __init__(self, name, parent_frame):
        self.name = name
        self.matrix = initial_matrix()  # full matrix clock
        self.delivered = []  # list of delivered message IDs
        self.pending = []    # buffered messages (not yet deliverable)
        
        # Create a frame to represent this process's chat panel.
        self.frame = tk.Frame(parent_frame, bd=2, relief=tk.GROOVE)
        self.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Header label shows process name and its full matrix clock.
        self.header_label = tk.Label(self.frame, text=self.get_header_text(),
                                     font=("Arial", 12, "bold"), justify=tk.LEFT)
        self.header_label.pack(anchor="w", padx=5, pady=5)
        
        # Chat area to display sent and received messages.
        self.chat_area = scrolledtext.ScrolledText(self.frame, width=40, height=20, font=("Arial", 10))
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.chat_area.config(state=tk.DISABLED)
    
    def get_header_text(self):
        header = f"{self.name}\nMatrix Clock:\n{matrix_to_string(self.matrix)}"
        return header
    
    def update_header(self):
        self.header_label.config(text=self.get_header_text())
    
    def append_message(self, text):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, text + "\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)
    
    def send_message(self, msg_id, content):
        """
        Process a send event:
          - Increment own matrix clock (diagonal) and update header.
          - Append the sent message to the chat area.
          - Return a deep copy of the matrix as a snapshot.
        """
        self.matrix[self.name][self.name] += 1
        snapshot = copy.deepcopy(self.matrix)
        self.update_header()
        self.append_message(f"Sent {msg_id}: {content}  [Matrix:\n{matrix_to_string(snapshot)}]")
        return snapshot

    def deliver_message(self, message):
        """
        Deliver a message:
          - Merge the message's matrix into the local matrix (component-wise maximum).
          - Increment the local diagonal entry.
          - Update header and append the received message to the chat area.
        """
        self.delivered.append(message.msg_id)
        # Merge: take maximum for each entry.
        for p in PROCESS_NAMES:
            for q in PROCESS_NAMES:
                self.matrix[p][q] = max(self.matrix[p][q], message.matrix[p][q])
        # Local event: increment own counter.
        self.matrix[self.name][self.name] += 1
        self.update_header()
        self.append_message(f"Received {message.msg_id}: {message.content}  [Matrix Snapshot:\n{matrix_to_string(message.matrix)}]")
    
    def try_deliver_pending(self, simulation_log):
        delivered_now = True
        while delivered_now:
            delivered_now = False
            for msg in self.pending[:]:
                if is_deliverable(self, msg):
                    self.pending.remove(msg)
                    simulation_log(f"{self.name} delivers buffered {msg.msg_id}")
                    self.deliver_message(msg)
                    delivered_now = True
                    break
    
    def receive_message(self, message, simulation_log):
        if is_deliverable(self, message):
            simulation_log(f"{self.name} delivers {message.msg_id}: {message.content}")
            self.deliver_message(message)
            self.try_deliver_pending(simulation_log)
        else:
            simulation_log(f"{self.name} buffers {message.msg_id} (pending)")
            self.pending.append(message)

###############################################################################
# Simulation class: coordinates events and provides control buttons and logs.
###############################################################################
class Simulation:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Chat Application with Matrix Clocks")
        
        # Top frame holds the chat panels for each process.
        self.chat_frame = tk.Frame(root)
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a Process object for each process.
        self.processes = {p: Process(p, self.chat_frame) for p in PROCESS_NAMES}
        
        # Log area for simulation events.
        self.log_area = scrolledtext.ScrolledText(root, width=100, height=8, font=("Arial", 10))
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_area.config(state=tk.DISABLED)
        
        # Control buttons.
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
        self.next_button = tk.Button(self.button_frame, text="Next Step", command=self.next_step)
        self.next_button.pack(side=tk.LEFT, padx=10)
        self.reset_button = tk.Button(self.button_frame, text="Reset", command=self.reset_simulation)
        self.reset_button.pack(side=tk.RIGHT, padx=10)
        
        self.messages = {}  # Store Message objects by msg_id.
        self.events = self.create_events()
        self.current_event_index = 0
    
    def log(self, text):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.config(state=tk.DISABLED)
        self.log_area.see(tk.END)
    
    def create_events(self):
        """
        Create a short list of events simulating a distributed chat application using matrix clocks.
        This example ensures at least one message is buffered.
        Event types:
          - "send": a process sends a message.
          - "receive": a process receives a message.
        The events are designed so that P1 sends two messages (m0 and m1),
        and P2 receives m1 before m0, forcing m1 to be buffered.
        """
        return [
            {"type": "send", "process": "P1", "msg_id": "m0",
             "content": "Hello, world!"},
            {"type": "send", "process": "P1", "msg_id": "m1",
             "content": "How are you?"},
            {"type": "receive", "process": "P2", "msg_id": "m1",  # out-of-order: m1 arrives before m0
             "description": "P2 receives m1 (should buffer)"},
            {"type": "receive", "process": "P2", "msg_id": "m0",
             "description": "P2 receives m0, then buffered m1 is delivered"},
            {"type": "receive", "process": "P3", "msg_id": "m0",
             "description": "P3 receives m0"}
        ]
    
    def next_step(self):
        if self.current_event_index < len(self.events):
            event = self.events[self.current_event_index]
            self.log(f"Step {self.current_event_index + 1}: {event.get('description', event.get('content', ''))}")
            if event["type"] == "send":
                proc = self.processes[event["process"]]
                snapshot = proc.send_message(event["msg_id"], event["content"])
                msg = Message(event["msg_id"], event["process"], snapshot, event["content"])
                self.messages[event["msg_id"]] = msg
                # Try delivering any buffered messages (if applicable)
                proc.try_deliver_pending(self.log)
            elif event["type"] == "receive":
                proc = self.processes[event["process"]]
                msg = self.messages.get(event["msg_id"])
                if msg:
                    proc.receive_message(msg, self.log)
                else:
                    self.log(f"Error: Message {event['msg_id']} not found!")
            self.current_event_index += 1
        else:
            self.log("Simulation complete.")
    
    def reset_simulation(self):
        for proc in self.processes.values():
            proc.matrix = initial_matrix()
            proc.delivered = []
            proc.pending = []
            proc.chat_area.config(state=tk.NORMAL)
            proc.chat_area.delete("1.0", tk.END)
            proc.chat_area.config(state=tk.DISABLED)
            proc.update_header()
        self.messages = {}
        self.events = self.create_events()
        self.current_event_index = 0
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete("1.0", tk.END)
        self.log_area.config(state=tk.DISABLED)
        self.log("Simulation reset.")

if __name__ == "__main__":
    root = tk.Tk()
    sim = Simulation(root)
    root.mainloop()
