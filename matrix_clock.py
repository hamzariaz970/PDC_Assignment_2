import tkinter as tk
import copy

###############################################################################
# Global definitions and helper functions for matrix clocks.
###############################################################################
PROCESS_NAMES = ["P1", "P2", "P3"]
PROCESS_Y = {"P1": 100, "P2": 200, "P3": 300}  # fixed y-coordinates
BASE_X = 50
X_SPACING = 80

def initial_matrix():
    """
    Create an initial matrix clock: a dictionary-of-dictionaries with all entries = 0.
    Example:
      {
        "P1": {"P1": 0, "P2": 0, "P3": 0},
        "P2": {"P1": 0, "P2": 0, "P3": 0},
        "P3": {"P1": 0, "P2": 0, "P3": 0}
      }
    """
    return {p: {q: 0 for q in PROCESS_NAMES} for p in PROCESS_NAMES}

def matrix_to_string(mc):
    """
    Convert a matrix clock (dict-of-dict) into a multi-line string.
    Each row is displayed in the order of PROCESS_NAMES.
    """
    rows = []
    for p in PROCESS_NAMES:
        row = [mc[p][q] for q in PROCESS_NAMES]
        rows.append(str(row))
    return "\n".join(rows)

###############################################################################
# Message class: holds the message ID, sender, and matrix clock snapshot.
###############################################################################
class Message:
    def __init__(self, msg_id, sender, matrix_snapshot):
        self.msg_id = msg_id
        self.sender = sender
        self.matrix = matrix_snapshot  # dict-of-dict snapshot

###############################################################################
# Deliverability check for matrix clocks (diagonal-based).
###############################################################################
def is_deliverable(process, message):
    """
    For a message m sent by process i to be deliverable at process j:
      - m.matrix[i][i] == process.matrix[i][i] + 1  (sender's diagonal)
      - for all k != i, m.matrix[k][k] <= process.matrix[k][k]
    """
    sender = message.sender
    local = process.matrix
    # Check sender's diagonal
    if message.matrix[sender][sender] != local[sender][sender] + 1:
        return False
    # Check other diagonals
    for p in PROCESS_NAMES:
        if p != sender:
            if message.matrix[p][p] > local[p][p]:
                return False
    return True

###############################################################################
# Process class: maintains matrix clock, buffers messages, draws events.
###############################################################################
class Process:
    def __init__(self, name, canvas):
        self.name = name
        self.canvas = canvas

        # Initialize matrix clock with all zeros
        self.matrix = initial_matrix()
        self.delivered = []
        self.pending = []
        self.next_x = BASE_X
        self.y = PROCESS_Y[name]
        self.text_id = None  # will hold the ID for the matrix display text

        self.update_matrix_display()

    def update_matrix_display(self):
        """
        Show this process's matrix clock further above the timeline to avoid overlap.
        """
        if self.text_id is not None:
            self.canvas.delete(self.text_id)

        m_str = matrix_to_string(self.matrix)
        self.text_id = self.canvas.create_text(
            10, self.y - 60,  # Moved higher up (y-60) and further left (x=10)
            text=f"{self.name}\n{m_str}",
            font=("Arial", 10),
            fill="blue",
            anchor="w"
        )

    def deliver_message(self, message, simulation):
        """
        Deliver a message:
          1. Merge the local matrix with the message's matrix (component-wise max).
          2. Increment the local diagonal entry (self.name).
          3. Draw a light green circle for receive, plus the updated matrix below.
          4. Draw arrow from the sender's send event.
        """
        self.delivered.append(message.msg_id)
        x = self.next_x
        y = self.y
        self.next_x += X_SPACING
        r = 15

        # Draw a green circle for the receive
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="lightgreen")
        self.canvas.create_text(x, y, text=message.msg_id, font=("Arial", 10), fill="black")

        # Merge
        for p in PROCESS_NAMES:
            for q in PROCESS_NAMES:
                self.matrix[p][q] = max(self.matrix[p][q], message.matrix[p][q])
        # Increment local diagonal
        self.matrix[self.name][self.name] += 1

        # Draw updated matrix below the circle, with more vertical space
        updated_str = matrix_to_string(self.matrix)
        self.canvas.create_text(x, y + r + 15, text=f"{updated_str}", font=("Arial", 8), fill="purple")
        self.update_matrix_display()

        # Arrow from sender's x to receiver's x
        if self.name != message.sender:
            send_x = simulation.send_positions.get(message.msg_id, BASE_X)
            self.canvas.create_line(
                send_x, PROCESS_Y[message.sender],
                x, y,
                arrow=tk.LAST, dash=(4, 2), fill="black"
            )

    def try_deliver_pending(self, simulation, log_func):
        """
        Attempt to deliver any pending messages that have become deliverable.
        Keep trying until no more messages can be delivered.
        """
        delivered_now = True
        while delivered_now:
            delivered_now = False
            for m in self.pending[:]:
                if is_deliverable(self, m):
                    self.pending.remove(m)
                    log_func(f"{self.name} delivers buffered {m.msg_id}")
                    self.deliver_message(m, simulation)
                    delivered_now = True
                    break

    def receive_message(self, message, simulation, log_func):
        """
        On receiving a message, check if it's deliverable. If yes, deliver.
        Otherwise, buffer it.
        """
        if is_deliverable(self, message):
            log_func(f"{self.name} delivers {message.msg_id}")
            self.deliver_message(message, simulation)
            self.try_deliver_pending(simulation, log_func)
        else:
            log_func(f"{self.name} buffers {message.msg_id} (pending)")
            self.pending.append(message)

###############################################################################
# Simulation class: sets up the GUI, horizontal lines, and events.
###############################################################################
class Simulation:
    def __init__(self, root):
        self.root = root
        self.root.configure(bg="white")
        self.canvas = tk.Canvas(root, width=800, height=400, bg="white", highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=2)

        self.log_text = tk.Text(root, width=100, height=10, bg="white", fg="black")
        self.log_text.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.next_button = tk.Button(root, text="Next Step", command=self.next_step)
        self.next_button.grid(row=2, column=0, sticky="w")
        self.reset_button = tk.Button(root, text="Reset", command=self.reset_simulation)
        self.reset_button.grid(row=2, column=1, sticky="e")

        # Draw horizontal lines for each process
        for p in PROCESS_NAMES:
            y = PROCESS_Y[p]
            self.canvas.create_line(0, y, 800, y, dash=(2, 2), fill="black")
            self.canvas.create_text(10, y, text=p, anchor="w", font=("Arial", 12, "bold"), fill="black")

        # Create processes
        self.processes = {p: Process(p, self.canvas) for p in PROCESS_NAMES}
        self.messages = {}
        self.send_positions = {}
        self.events = self.create_events()
        self.current_event_index = 0

    def create_events(self):
        """
        Some example events for matrix clocks with buffering and out-of-order receive.
        """
        return [
            {"type": "send", "process": "P1", "msg_id": "m0",
             "description": "P1 sends m0"},
            {"type": "send", "process": "P1", "msg_id": "m1",
             "description": "P1 sends m1"},
            {"type": "receive", "process": "P2", "msg_id": "m1",
             "description": "P2 receives m1 (buffers because m0 not delivered)"},
            {"type": "receive", "process": "P2", "msg_id": "m0",
             "description": "P2 receives m0, then delivers buffered m1"},
            {"type": "receive", "process": "P3", "msg_id": "m0",
             "description": "P3 receives m0"},
            {"type": "send", "process": "P2", "msg_id": "m2",
             "description": "P2 sends m2"},
            {"type": "send", "process": "P1", "msg_id": "m3",
             "description": "P1 sends m3"},
            {"type": "receive", "process": "P3", "msg_id": "m3",
             "description": "P3 receives m3"},
            {"type": "receive", "process": "P3", "msg_id": "m2",
             "description": "P3 receives m2"},
            {"type": "receive", "process": "P1", "msg_id": "m2",
             "description": "P1 receives m2"},
            {"type": "receive", "process": "P2", "msg_id": "m3",
             "description": "P2 receives m3"},
            {"type": "send", "process": "P2", "msg_id": "m4",
             "description": "P2 sends m4"},
            {"type": "receive", "process": "P3", "msg_id": "m4",
             "description": "P3 receives m4"},
            {"type": "receive", "process": "P1", "msg_id": "m4",
             "description": "P1 receives m4"},
            {"type": "send", "process": "P3", "msg_id": "m5",
             "description": "P3 sends m5"},
            {"type": "receive", "process": "P1", "msg_id": "m5",
             "description": "P1 receives m5"},
            {"type": "receive", "process": "P2", "msg_id": "m5",
             "description": "P2 receives m5"},
            {"type": "send", "process": "P2", "msg_id": "m6",
             "description": "P2 sends m6"},
            {"type": "receive", "process": "P1", "msg_id": "m6",
             "description": "P1 receives m6"},
            {"type": "receive", "process": "P3", "msg_id": "m6",
             "description": "P3 receives m6"}
        ]

    def log(self, text):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def next_step(self):
        if self.current_event_index < len(self.events):
            event = self.events[self.current_event_index]
            self.log(f"Step {self.current_event_index + 1}: {event['description']}")

            if event["type"] == "send":
                proc = self.processes[event["process"]]
                sender = event["process"]
                # Increment local diagonal for a send
                proc.matrix[sender][sender] += 1
                import copy
                snapshot = copy.deepcopy(proc.matrix)
                from_msg = Message(event["msg_id"], sender, snapshot)
                self.messages[event["msg_id"]] = from_msg

                x = proc.next_x
                y = proc.y
                self.send_positions[event["msg_id"]] = x

                r = 15
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="yellow")
                self.canvas.create_text(x, y, text=event["msg_id"], font=("Arial", 10), fill="black")
                # Show the matrix snapshot further below the circle
                self.canvas.create_text(x, y + r + 15, text=f"{matrix_to_string(snapshot)}",
                                        font=("Arial", 8), fill="purple")

                proc.next_x += X_SPACING
                proc.update_matrix_display()

            elif event["type"] == "receive":
                proc = self.processes[event["process"]]
                msg = self.messages.get(event["msg_id"])
                if msg:
                    proc.receive_message(msg, self, self.log)
                else:
                    self.log(f"Error: Message {event['msg_id']} not found!")

            self.current_event_index += 1
        else:
            self.log("Simulation complete.")

    def reset_simulation(self):
        self.canvas.delete("all")
        for p in PROCESS_NAMES:
            y = PROCESS_Y[p]
            self.canvas.create_line(0, y, 800, y, dash=(2, 2), fill="black")
            self.canvas.create_text(10, y, text=p, anchor="w", font=("Arial", 12, "bold"), fill="black")

        self.processes = {p: Process(p, self.canvas) for p in PROCESS_NAMES}
        self.messages = {}
        self.send_positions = {}
        self.events = self.create_events()
        self.current_event_index = 0
        self.log_text.delete("1.0", tk.END)
        self.log("Simulation reset.")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Matrix Clock Unicast Causal Ordering")
    sim = Simulation(root)
    root.mainloop()
