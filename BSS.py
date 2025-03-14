import tkinter as tk  # Import tkinter for GUI

# Global definitions:
PROCESS_NAMES = ["P1", "P2", "P3"]
# Assigning a fixed y-coordinate for each process's horizontal timeline
PROCESS_Y = {"P1": 100, "P2": 200, "P3": 300}
# Starting x-coordinate and spacing for events on each process's timeline
BASE_X = 50
X_SPACING = 80

def vector_clock_list(vc):
    """
    Convert the vector clock dictionary (e.g. {'P1': 1, 'P2': 0, 'P3': 0})
    into a list form [1, 0, 0] in the order P1, P2, P3.
    """
    return [vc[p] for p in PROCESS_NAMES]

class Message:
    def __init__(self, msg_id, sender, tag):
        # A Message carries its id, sender, and the vector clock snapshot (tag).
        self.msg_id = msg_id
        self.sender = sender
        self.tag = tag  # Dictionary form, e.g. {'P1': 2, 'P2': 0, 'P3': 0}

class Process:
    def __init__(self, name, canvas):
        self.name = name
        self.canvas = canvas
        # Initialize vector clock: all zero for each process
        self.vector_clock = {p: 0 for p in PROCESS_NAMES}
        self.delivered = []      # List of delivered message IDs
        self.pending = []        # List of buffered (pending) messages
        self.next_x = BASE_X     # Next x-position for this process's timeline
        self.y = PROCESS_Y[name] # Fixed y-position for this process
        self.text_id = None      # Canvas ID for vector clock display text

    def update_vector_display(self):
        """
        Update the text that displays this process's current vector clock
        (shown as a simple list like [1, 0, 0]).
        """
        if self.text_id is not None:
            self.canvas.delete(self.text_id)

        # Convert the process's vector clock dictionary to a simple list
        vc_list = vector_clock_list(self.vector_clock)
        # Draw the process name and the clock list above the timeline
        self.text_id = self.canvas.create_text(
            20, self.y - 30,  # slightly above the line
            text=f"{self.name}\n{vc_list}",
            font=("Arial", 10),
            fill="blue",
            anchor="w"
        )

    def deliver_message(self, message, simulation):
        """
        Deliver a message to this process:
         - update vector clock for sender
         - draw the event
         - show the message's vector clock snapshot
        """
        self.delivered.append(message.msg_id)
        sender = message.sender

        # Update vector clock for the sender following BSS rule:
        self.vector_clock[sender] = message.tag[sender]

        x = self.next_x
        y = self.y
        self.next_x += X_SPACING

        r = 15
        # Draw a light green circle for a delivered (receive) event
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="lightgreen")
        # Label the circle with the message ID
        self.canvas.create_text(x, y, text=message.msg_id, font=("Arial", 10), fill="black")
        # Show the message's snapshot as [1, 0, 0], etc.
        tag_list = vector_clock_list(message.tag)
        self.canvas.create_text(x, y + r + 10, text=f"{tag_list}", font=("Arial", 8), fill="purple")

        # Update the process's own vector clock display
        self.update_vector_display()

        # Draw an arrow if the message came from another process
        if self.name != sender:
            send_x = simulation.send_positions.get(message.msg_id, BASE_X)
            self.canvas.create_line(
                send_x, PROCESS_Y[sender],
                x, y,
                arrow=tk.LAST, dash=(4, 2), fill="black"
            )

    def try_deliver_pending(self, simulation, log_func):
        """
        Attempt to deliver any buffered messages that have become deliverable
        now that the vector clock might have changed.
        """
        delivered_now = True
        while delivered_now:
            delivered_now = False
            for message in self.pending[:]:
                if is_deliverable(self, message):
                    self.pending.remove(message)
                    log_func(f"{self.name} delivers pending {message.msg_id}")
                    self.deliver_message(message, simulation)
                    delivered_now = True
                    break

    def receive_message(self, message, simulation, log_func):
        """
        On receiving a message, deliver it if possible; otherwise buffer it.
        """
        if is_deliverable(self, message):
            log_func(f"{self.name} delivers {message.msg_id}")
            self.deliver_message(message, simulation)
            # After delivering, see if any pending messages are now deliverable
            self.try_deliver_pending(simulation, log_func)
        else:
            log_func(f"{self.name} buffers {message.msg_id} (pending)")
            self.pending.append(message)

def is_deliverable(process, message):
    """
    Check if a message is deliverable under BSS causal ordering:
     - For the sender: the message's timestamp must be process's clock + 1
     - For all others: the message's timestamp <= process's clock
    """
    sender = message.sender
    for p in PROCESS_NAMES:
        if p == sender:
            if message.tag[p] != process.vector_clock[p] + 1:
                return False
        else:
            if message.tag[p] > process.vector_clock[p]:
                return False
    return True

class Simulation:
    def __init__(self, root):
        # Configure the main window
        self.root = root
        self.root.configure(bg="white")

        # Create a canvas for drawing
        self.canvas = tk.Canvas(root, width=800, height=400, bg="white", highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=2)

        # Create a text widget for logs
        self.log_text = tk.Text(root, width=100, height=10, bg="white", fg="black")
        self.log_text.grid(row=1, column=0, columnspan=2, sticky="nsew")

        # "Next Step" button
        self.next_button = tk.Button(root, text="Next Step", command=self.next_step)
        self.next_button.grid(row=2, column=0, sticky="w")

        # "Reset" button
        self.reset_button = tk.Button(root, text="Reset", command=self.reset_simulation)
        self.reset_button.grid(row=2, column=1, sticky="e")

        # Draw horizontal dashed lines for each process
        for p in PROCESS_NAMES:
            y = PROCESS_Y[p]
            self.canvas.create_line(0, y, 800, y, dash=(2, 2), fill="black")
            self.canvas.create_text(10, y, text=p, anchor="w", font=("Arial", 12, "bold"), fill="black")

        # Create process objects
        self.processes = {p: Process(p, self.canvas) for p in PROCESS_NAMES}
        for proc in self.processes.values():
            proc.update_vector_display()

        self.messages = {}         # Holds all messages by id
        self.send_positions = {}   # Maps msg_id to x-position of its send event
        self.events = self.create_events()  # Build event list
        self.current_event_index = 0

    def create_events(self):
        """
        List of send/receive events to demonstrate causal ordering.
        We start with an out-of-order scenario to show buffering.
        """
        return [
            {"type": "send", "process": "P1", "msg_id": "m0",
             "description": "P1 sends m0 with timestamp [1,0,0]"},
            {"type": "send", "process": "P1", "msg_id": "m1",
             "description": "P1 sends m1 with timestamp [2,0,0]"},
            {"type": "receive", "process": "P2", "msg_id": "m1",
             "description": "P2 receives m1 (likely buffers because m0 not delivered)"},
            {"type": "receive", "process": "P2", "msg_id": "m0",
             "description": "P2 receives m0, then can deliver m1"},
            {"type": "receive", "process": "P3", "msg_id": "m0",
             "description": "P3 receives m0"},

            {"type": "send", "process": "P2", "msg_id": "m2",
             "description": "P2 sends m2 (timestamp updated)"},
            {"type": "send", "process": "P1", "msg_id": "m3",
             "description": "P1 sends m3 (timestamp updated)"},
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
        """Append a line to the log text widget."""
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def next_step(self):
        """Execute the next event in the sequence."""
        if self.current_event_index < len(self.events):
            event = self.events[self.current_event_index]
            self.log(f"Step {self.current_event_index + 1}: {event['description']}")

            if event["type"] == "send":
                proc = self.processes[event["process"]]
                sender = event["process"]
                # Increase the sender's own counter
                proc.vector_clock[sender] += 1
                # Snapshot of current vector clock
                tag = proc.vector_clock.copy()
                # Create and store the message
                msg = Message(event["msg_id"], sender, tag)
                self.messages[event["msg_id"]] = msg

                x = proc.next_x
                y = proc.y
                self.send_positions[event["msg_id"]] = x

                r = 15
                # Draw a yellow circle for sending
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="yellow")
                self.canvas.create_text(x, y, text=event["msg_id"], font=("Arial", 10), fill="black")
                # Show the clock snapshot below the circle in [1, 0, 0] format
                tag_list = vector_clock_list(tag)
                self.canvas.create_text(x, y + r + 10, text=f"{tag_list}", font=("Arial", 8), fill="purple")

                proc.next_x += X_SPACING
                proc.update_vector_display()
                # Also check if any pending messages can now be delivered
                proc.try_deliver_pending(self, self.log)

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
        """Reset the simulation to its initial state."""
        self.canvas.delete("all")
        # Redraw horizontal timelines
        for p in PROCESS_NAMES:
            y = PROCESS_Y[p]
            self.canvas.create_line(0, y, 800, y, dash=(2, 2), fill="black")
            self.canvas.create_text(10, y, text=p, anchor="w", font=("Arial", 12, "bold"), fill="black")

        # Recreate processes
        self.processes = {p: Process(p, self.canvas) for p in PROCESS_NAMES}
        for proc in self.processes.values():
            proc.update_vector_display()

        self.messages = {}
        self.send_positions = {}
        self.events = self.create_events()
        self.current_event_index = 0
        self.log_text.delete("1.0", tk.END)
        self.log("Simulation reset.")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("BSS-Based Causal Ordering Visualization (Horizontal Timelines)")
    sim = Simulation(root)
    root.mainloop()
