import tkinter as tk

###############################################################################
# Global definitions and helper function to display vector clocks as [1,0,0]
###############################################################################
PROCESS_NAMES = ["P1", "P2", "P3"]
PROCESS_Y = {"P1": 100, "P2": 200, "P3": 300}  # fixed y-coordinates for horizontal timelines
BASE_X = 50       # starting x-coordinate for events
X_SPACING = 80    # spacing between events

def vector_clock_list(vc):
    """
    Convert a vector clock dictionary (e.g. {'P1': 1, 'P2': 0, 'P3': 0})
    into a list form [1, 0, 0] in the order P1, P2, P3.
    """
    return [vc[p] for p in PROCESS_NAMES]

###############################################################################
# Message class: holds the message id, sender, and attached vector clock snapshot.
###############################################################################
class Message:
    def __init__(self, msg_id, sender, tag):
        self.msg_id = msg_id   # e.g., "m1"
        self.sender = sender   # sender process, e.g. "P1"
        self.tag = tag         # vector clock snapshot at send time (a dict)

###############################################################################
# Deliverability check function for causal ordering (same for SES buffering)
###############################################################################
def is_deliverable(process, message):
    """
    In SES with buffering, a message m from sender i is deliverable at process j
    if:
      - m.tag[i] == VC_j[i] + 1, and
      - for every other process k, m.tag[k] <= VC_j[k].
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

###############################################################################
# Process class for SES with buffering.
###############################################################################
class Process:
    def __init__(self, name, canvas):
        self.name = name
        self.canvas = canvas
        # Initialize vector clock: start with zeros for every process.
        self.vector_clock = {p: 0 for p in PROCESS_NAMES}
        self.delivered = []      # delivered messages (by id)
        self.pending = []        # buffered messages not yet deliverable
        self.next_x = BASE_X     # next x-coordinate on the horizontal timeline
        self.y = PROCESS_Y[name] # fixed y-coordinate for this process
        self.text_id = None      # canvas text id for the vector clock display

        self.update_vector_display()  # initial display

    def update_vector_display(self):
        """Display the current vector clock as [x, y, z] above the timeline."""
        if self.text_id is not None:
            self.canvas.delete(self.text_id)
        vc_list = vector_clock_list(self.vector_clock)
        self.text_id = self.canvas.create_text(
            20, self.y - 30,  # positioned to the left of the timeline
            text=f"{self.name}\n{vc_list}",
            font=("Arial", 10),
            fill="blue",
            anchor="w"
        )

    def deliver_message(self, message, simulation):
        """
        Deliver a message:
         - Draw a light green circle at the next x-coordinate on the timeline.
         - Update the vector clock by merging the message's timestamp.
         - Increment the local clock entry.
         - Update the display and draw an arrow from sender's send event.
        """
        self.delivered.append(message.msg_id)
        x = self.next_x
        y = self.y
        self.next_x += X_SPACING
        r = 15

        # Draw the receive event as a light green circle.
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="lightgreen")
        self.canvas.create_text(x, y, text=message.msg_id, font=("Arial", 10), fill="black")

        # Update vector clock: merge (component-wise max) with the message's timestamp.
        for p in PROCESS_NAMES:
            self.vector_clock[p] = max(self.vector_clock[p], message.tag[p])
        # Then, increment the local clock for this process.
        self.vector_clock[self.name] += 1

        # Display the merged clock below the event.
        merged_list = vector_clock_list(self.vector_clock)
        self.canvas.create_text(x, y + r + 10, text=f"{merged_list}", font=("Arial", 8), fill="purple")
        self.update_vector_display()

        # Draw an arrow from the sender's send event to this receive event if not self.
        if self.name != message.sender:
            send_x = simulation.send_positions.get(message.msg_id, BASE_X)
            self.canvas.create_line(
                send_x, PROCESS_Y[message.sender],
                x, y,
                arrow=tk.LAST, dash=(4, 2), fill="black"
            )

    def try_deliver_pending(self, simulation, log_func):
        """
        Attempt to deliver any messages in the pending buffer that have become deliverable.
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
        On receiving a message, check deliverability:
         - If deliverable, merge vector clocks, increment local clock, and deliver.
         - Otherwise, buffer the message.
        """
        if is_deliverable(self, message):
            log_func(f"{self.name} delivers {message.msg_id}")
            self.deliver_message(message, simulation)
            self.try_deliver_pending(simulation, log_func)
        else:
            log_func(f"{self.name} buffers {message.msg_id} (pending)")
            self.pending.append(message)

###############################################################################
# Simulation class sets up the GUI, horizontal timelines, and events.
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

        # Draw horizontal dashed lines for each process.
        for p in PROCESS_NAMES:
            y = PROCESS_Y[p]
            self.canvas.create_line(0, y, 800, y, dash=(2, 2), fill="black")
            self.canvas.create_text(10, y, text=p, anchor="w", font=("Arial", 12, "bold"), fill="black")

        # Create Process objects.
        self.processes = {p: Process(p, self.canvas) for p in PROCESS_NAMES}

        self.messages = {}         # stores Message objects by id
        self.send_positions = {}   # records x-position of send events for drawing arrows
        self.events = self.create_events()  # list of send/receive events
        self.current_event_index = 0

    def create_events(self):
        """
        Create a list of events demonstrating SES with buffering.
        Events include out-of-order deliveries that require buffering.
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
        """Append a line of text to the log widget."""
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def next_step(self):
        """Process the next event (send or receive) in the simulation."""
        if self.current_event_index < len(self.events):
            event = self.events[self.current_event_index]
            self.log(f"Step {self.current_event_index + 1}: {event['description']}")

            if event["type"] == "send":
                proc = self.processes[event["process"]]
                sender = event["process"]
                # On send, increment local clock and snapshot the clock.
                proc.vector_clock[sender] += 1
                tag = proc.vector_clock.copy()
                # Create and store the message.
                msg = Message(event["msg_id"], sender, tag)
                self.messages[event["msg_id"]] = msg

                # Record the x-coordinate of the send event for drawing arrows.
                x = proc.next_x
                y = proc.y
                self.send_positions[event["msg_id"]] = x

                r = 15
                # Draw a yellow circle for the send event.
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="yellow")
                self.canvas.create_text(x, y, text=event["msg_id"], font=("Arial", 10), fill="black")
                # Display the vector clock snapshot below the send event.
                self.canvas.create_text(x, y + r + 10, text=f"{vector_clock_list(tag)}", font=("Arial", 8), fill="purple")

                proc.next_x += X_SPACING
                proc.update_vector_display()

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

###############################################################################
# Main execution: create the Tkinter window and start the simulation.
###############################################################################
if __name__ == "__main__":
    root = tk.Tk()
    root.title("SES-Based Causal Ordering with Buffering (Horizontal Timelines)")
    sim = Simulation(root)
    root.mainloop()
